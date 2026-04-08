"""
Dispatch & Resource Management API Routes.

Endpoints:
  POST /dispatch/auto-assign      - Auto-assign case to best officer
  GET  /dispatch/queue            - Get pending dispatch queue
  GET  /dispatch/officers         - List available officers
  POST /dispatch/complete         - Mark dispatch as completed
  GET  /dispatch/{dispatch_id}    - Get dispatch details
  GET  /dispatch/stats/{officer}  - Get officer dispatch stats
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import Officer, Case, DispatchQueue, get_db
from ..deps import get_current_user
from ..services.dispatch_service import (
    auto_dispatch_case,
    get_available_officers,
    get_dispatch_queue,
    complete_dispatch,
    get_officer_stats,
)

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


class DispatchAssignRequest(BaseModel):
    case_id: int
    auto_assign: bool = True


class DispatchResponse(BaseModel):
    id: int
    case_id: int
    assigned_officer_id: Optional[int]
    status: str
    estimated_arrival: int
    created_at: datetime
    assigned_at: Optional[datetime]
    completed_at: Optional[datetime]


class OfficerAvailabilityResponse(BaseModel):
    id: int
    badge_id: str
    name: str
    status: str
    workload: int
    current_location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    shift: str


class DispatchQueueResponse(BaseModel):
    id: int
    case_id: int
    status: str
    officer_badge_id: Optional[str]
    estimated_arrival: int
    created_at: datetime


@router.post("/auto-assign")
async def auto_assign(
    req: DispatchAssignRequest,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Auto-assign a case to the nearest available officer."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403, detail="Only police can dispatch")
    
    case = db.query(Case).filter(Case.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if case.assigned_officer_id:
        raise HTTPException(status_code=400, detail="Case already assigned")
    
    success, officer, message = auto_dispatch_case(db, case)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    dispatch = db.query(DispatchQueue).filter(
        DispatchQueue.case_id == case.id
    ).first()
    
    return {
        "success": True,
        "message": message,
        "dispatch": {
            "id": dispatch.id,
            "case_id": dispatch.case_id,
            "assigned_officer": officer.badge_id if officer else None,
            "estimated_arrival": dispatch.estimated_arrival,
            "status": dispatch.status
        }
    }


@router.get("/queue")
async def get_queue(
    status: Optional[str] = Query(None, description="Filter by status: pending, assigned, en_route, on_scene, completed"),
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get dispatch queue with optional status filter."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    dispatches = get_dispatch_queue(db, status)
    
    response = []
    for d in dispatches:
        officer_badge = None
        if d.assigned_officer_id:
            officer = db.query(Officer).filter(Officer.id == d.assigned_officer_id).first()
            officer_badge = officer.badge_id if officer else None
        
        response.append({
            "id": d.id,
            "case_id": d.case_id,
            "status": d.status,
            "officer_badge": officer_badge,
            "estimated_arrival": d.estimated_arrival,
            "created_at": d.created_at,
            "assigned_at": d.assigned_at
        })
    
    return response


@router.get("/officers")
async def list_available_officers(
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get list of available officers for dispatch."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    officers = get_available_officers(db)
    
    response = []
    for officer in officers:
        response.append({
            "id": officer.id,
            "badge_id": officer.badge_id,
            "status": officer.status,
            "workload": officer.workload_count,
            "current_location": officer.current_location,
            "latitude": officer.current_latitude,
            "longitude": officer.current_longitude,
            "shift": officer.shift,
            "rank": officer.rank
        })
    
    return response


@router.post("/complete/{dispatch_id}")
async def complete_dispatch_action(
    dispatch_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Mark a dispatch as completed."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    success = complete_dispatch(db, dispatch_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    return {"success": True, "message": "Dispatch completed and officer released"}


@router.get("/{dispatch_id}")
async def get_dispatch_details(
    dispatch_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get specific dispatch details."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    dispatch = db.query(DispatchQueue).filter(DispatchQueue.id == dispatch_id).first()
    if not dispatch:
        raise HTTPException(status_code=404)
    
    officer = None
    if dispatch.assigned_officer_id:
        officer = db.query(Officer).filter(Officer.id == dispatch.assigned_officer_id).first()
    
    case = db.query(Case).filter(Case.id == dispatch.case_id).first()
    
    return {
        "id": dispatch.id,
        "case": {
            "id": case.id if case else None,
            "case_id": case.case_id if case else None,
            "crime_type": case.crime_type if case else None,
            "location": case.location if case else None,
            "severity": case.severity if case else None,
        },
        "officer": {
            "id": officer.id if officer else None,
            "badge_id": officer.badge_id if officer else None,
            "location": officer.current_location if officer else None,
        } if officer else None,
        "status": dispatch.status,
        "estimated_arrival": dispatch.estimated_arrival,
        "created_at": dispatch.created_at,
        "assigned_at": dispatch.assigned_at,
        "completed_at": dispatch.completed_at
    }


@router.get("/stats/{officer_id}")
async def officer_dispatch_stats(
    officer_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get officer's dispatch statistics."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    stats = get_officer_stats(db, officer_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Officer not found")
    
    return stats
