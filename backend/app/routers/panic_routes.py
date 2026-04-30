from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.state_regions import STATE_REGIONS
from ..db import Report, User
from ..deps import get_current_user, get_db
from ..services.geo import format_current_location, gps_to_state_region_hint
from ..services.notify_service import broadcast_targets_for_report, create_notification
from ..services.ws_hub import hub

router = APIRouter(prefix="/panic", tags=["panic"])


@router.post("/")
async def panic_alert(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    latitude: float = Form(...),
    longitude: float = Form(...),
    incident_time: Optional[str] = Form(None),
    snapshot: Optional[UploadFile] = File(None),
):
    st_hint, rg_hint = gps_to_state_region_hint(latitude, longitude)
    if st_hint not in STATE_REGIONS:
        st_hint = user.state
        rg_hint = STATE_REGIONS[st_hint][0]

    file_name = None
    file_content_type = None
    file_bytes = None
    if snapshot and snapshot.filename:
        file_name = snapshot.filename
        file_content_type = snapshot.content_type
        file_bytes = await snapshot.read()

    public_id = str(uuid.uuid4())
    row = Report(
        public_id=public_id,
        state=st_hint,
        region=rg_hint,
        time=(incident_time or datetime.now().astimezone().strftime("%I:%M %p")),
        crime_type="Emergency",
        actor_type="Individual",
        weapon="Unknown",
        vehicle="Unknown",
        description="PANIC BUTTON — automated distress signal",
        phone="",
        vehicle_selection="None",
        status="investigating",
        latitude=latitude,
        longitude=longitude,
        current_location=format_current_location(latitude, longitude),
        user_email=user.email,
        is_panic=True,
        file_name=file_name,
        file_content_type=file_content_type,
        file_bytes=file_bytes,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()

    await hub.broadcast(
        {
            "type": "panic",
            "public_id": public_id,
            "state": st_hint,
            "region": rg_hint,
            "current_location": format_current_location(latitude, longitude),
            "latitude": latitude,
            "longitude": longitude,
            "user": user.email,
            "ts": row.created_at.isoformat(),
        }
    )

    for email in broadcast_targets_for_report(db):
        create_notification(
            db,
            user_email=email,
            title="PANIC ALERT",
            body=f"User {user.email} triggered panic near {rg_hint}, {st_hint}",
            kind="panic",
            report_public_id=public_id,
        )

    return {"status": "ok", "report_id": public_id, "state": st_hint, "region": rg_hint}
