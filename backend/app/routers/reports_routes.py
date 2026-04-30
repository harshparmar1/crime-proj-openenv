from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.state_regions import STATE_REGIONS
from ..db import Report, User
from ..deps import get_current_user, get_db, optional_current_user
from ..services.geo import approximate_lat_lng, format_current_location
from ..services.notify_service import broadcast_targets_for_report, create_notification
from ..services.ws_hub import hub

router = APIRouter(tags=["reports"])


@router.post("/report")
async def create_report(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(optional_current_user)],
    state: str = Form(...),
    region: str = Form(...),
    time: str = Form(...),
    crime_type: str = Form(...),
    actor_type: str = Form(...),
    weapon: str = Form(...),
    vehicle: str = Form(...),
    description: str = Form(...),
    phone: str = Form(...),
    vehicle_selection: str = Form(...),
    file: Optional[UploadFile] = File(None),
    voice: Optional[UploadFile] = File(None),
    voice_transcript: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
):
    if state not in STATE_REGIONS:
        raise HTTPException(status_code=400, detail="Invalid state")
    if region not in STATE_REGIONS[state]:
        raise HTTPException(status_code=400, detail="Invalid region for state")

    file_name = None
    file_content_type = None
    file_bytes = None
    if file and file.filename:
        file_name = file.filename
        file_content_type = file.content_type
        file_bytes = await file.read()

    voice_name = None
    voice_ct = None
    voice_bytes = None
    if voice and voice.filename:
        voice_name = voice.filename
        voice_ct = voice.content_type
        voice_bytes = await voice.read()

    vt_clean = (voice_transcript or "").strip()
    voice_transcript_val = vt_clean if vt_clean else None

    public_id = str(uuid.uuid4())
    lat, lng = latitude, longitude
    if lat is None or lng is None:
        lat, lng = approximate_lat_lng(state, region)

    row = Report(
        public_id=public_id,
        state=state,
        region=region,
        time=time,
        crime_type=crime_type,
        actor_type=actor_type,
        weapon=weapon,
        vehicle=vehicle,
        description=description,
        phone=phone,
        vehicle_selection=vehicle_selection,
        status="pending",
        latitude=lat,
        longitude=lng,
        user_email=user.email if user else None,
        is_panic=False,
        file_name=file_name,
        file_content_type=file_content_type,
        file_bytes=file_bytes,
        voice_file_name=voice_name,
        voice_content_type=voice_ct,
        voice_bytes=voice_bytes,
        voice_transcript=voice_transcript_val,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()

    await hub.broadcast(
        {
            "type": "crime_report",
            "public_id": public_id,
            "state": state,
            "region": region,
            "crime_type": crime_type,
            "latitude": lat,
            "longitude": lng,
            "ts": row.created_at.isoformat(),
        }
    )

    for email in broadcast_targets_for_report(db):
        create_notification(
            db,
            user_email=email,
            title="New crime report",
            body=f"{crime_type} in {region}, {state}",
            kind="crime_report",
            report_public_id=public_id,
        )

    return {
        "status": "success",
        "message": "Submitted successfully",
        "report_id": public_id,
        "submitted_at": row.created_at.isoformat(),
        "incident_time": time,
    }


def _report_public_dict(r: Report) -> dict:
    has_file = bool(r.file_bytes and len(r.file_bytes) > 0)
    has_voice = bool(r.voice_bytes and len(r.voice_bytes) > 0)
    return {
        "public_id": r.public_id,
        "state": r.state,
        "region": r.region,
        "current_location": format_current_location(r.latitude, r.longitude),
        "time": r.time,
        "crime_type": r.crime_type,
        "actor_type": r.actor_type,
        "weapon": r.weapon,
        "vehicle": r.vehicle,
        "vehicle_selection": r.vehicle_selection,
        "description": r.description,
        "phone": r.phone,
        "status": r.status,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "user_email": r.user_email,
        "is_panic": r.is_panic,
        "file_name": r.file_name,
        "file_content_type": r.file_content_type,
        "has_file": has_file,
        "voice_file_name": r.voice_file_name,
        "voice_content_type": r.voice_content_type,
        "has_voice": has_voice,
        "voice_transcript": r.voice_transcript,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/reports")
def list_all_reports(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Police and admin: full list of submitted reports (no binary bodies)."""
    if user.role not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Only police or admin can list all reports")
    rows = db.query(Report).order_by(Report.created_at.desc()).limit(500).all()
    return [_report_public_dict(r) for r in rows]


@router.get("/reports/{public_id}/voice")
def get_report_voice_file(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    if user.role not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Only police or admin can download voice evidence")
    r = db.query(Report).filter(Report.public_id == public_id).first()
    if not r or not r.voice_bytes:
        raise HTTPException(status_code=404, detail="No voice recording for this report")
    media = r.voice_content_type or "audio/webm"
    fname = r.voice_file_name or "voice-evidence"
    return Response(
        content=r.voice_bytes,
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{fname}"'},
    )


@router.get("/reports/{public_id}/file")
def get_report_evidence_file(
    public_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    if user.role not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Only police or admin can download evidence")
    r = db.query(Report).filter(Report.public_id == public_id).first()
    if not r or not r.file_bytes:
        raise HTTPException(status_code=404, detail="No file for this report")
    media = r.file_content_type or "application/octet-stream"
    fname = r.file_name or "evidence"
    return Response(
        content=r.file_bytes,
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{fname}"'},
    )


@router.get("/reports/tracking")
def list_my_reports(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    q = db.query(Report).filter(Report.user_email == user.email).order_by(Report.created_at.desc())
    return [
        {
            "report_id": r.public_id,
            "status": r.status,
            "state": r.state,
            "region": r.region,
            "crime_type": r.crime_type,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in q.limit(100).all()
    ]


class StatusBody(BaseModel):
    status: Literal["pending", "investigating", "resolved", "rejected"]


@router.patch("/reports/{public_id}/status")
def patch_report_status(
    public_id: str,
    body: StatusBody,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    if user.role not in ("police", "admin"):
        raise HTTPException(status_code=403, detail="Only police or admin can update status")
    r = db.query(Report).filter(Report.public_id == public_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    r.status = body.status
    db.commit()
    if r.user_email:
        create_notification(
            db,
            user_email=r.user_email,
            title="Report status updated",
            body=f"Your report {public_id} is now {body.status}.",
            kind="status_update",
            report_public_id=public_id,
        )
    return {"status": "ok", "report_id": public_id, "new_status": body.status}
