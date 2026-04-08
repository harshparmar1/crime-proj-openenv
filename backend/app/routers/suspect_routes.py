"""
Suspect Database API Routes.

Endpoints:
  POST /suspects                   - Create new suspect
  GET  /suspects/search            - Search suspects
  GET  /suspects/{suspect_id}      - Get suspect intelligence
  POST /suspects/{suspect_id}/arrest   - Register arrest
  POST /suspects/{suspect_id}/conviction - Register conviction
  POST /suspects/{suspect_id}/wanted    - Mark as wanted
  GET  /suspects/wanted/list       - List wanted suspects
  GET  /suspects/risk/high         - List high-risk suspects
  GET  /suspects/gang/{gang_name}  - Get gang members & network
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import Suspect, get_db
from ..deps import get_current_user
from ..services.suspect_service import (
    create_suspect,
    search_suspects,
    register_arrest,
    register_conviction,
    flag_as_wanted,
    get_high_risk_suspects,
    get_wanted_suspects,
    get_gang_members,
    link_gang_members,
    get_suspect_intelligence,
    update_suspect_location,
)

router = APIRouter(prefix="/suspects", tags=["suspect-database"])


class CreateSuspectRequest(BaseModel):
    name: str
    description: str
    age: Optional[int] = None
    photo_url: Optional[str] = None
    primary_crimes: Optional[list] = None
    modus_operandi: str = ""


class ArrestRegistration(BaseModel):
    crime_type: str
    case_id: Optional[int] = None


class ConvictionRegistration(BaseModel):
    crime_type: str


class WantedFlagRequest(BaseModel):
    warrant_type: str  # felony, misdemeanor, probation_violation


class LocationUpdate(BaseModel):
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.post("")
async def create_new_suspect(
    req: CreateSuspectRequest,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Create new suspect record."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    suspect = create_suspect(
        db,
        name=req.name,
        description=req.description,
        age=req.age,
        photo_url=req.photo_url,
        primary_crimes=req.primary_crimes,
        modus_operandi=req.modus_operandi,
    )
    
    return {
        "success": True,
        "suspect_id": suspect.suspect_id,
        "message": f"Suspect {suspect.name} created"
    }


@router.get("/search")
async def search(
    q: str = Query(..., min_length=2),
    search_type: str = Query("name", enum=["name", "description", "modus_operandi", "all"]),
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Search suspects by name, description, or MO."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    suspects = search_suspects(db, q, search_type)
    
    return {
        "query": q,
        "search_type": search_type,
        "results_count": len(suspects),
        "suspects": [
            {
                "id": s.id,
                "suspect_id": s.suspect_id,
                "name": s.name,
                "age": s.age,
                "description": s.description,
                "photo_url": s.photo_url,
                "risk_score": s.risk_score,
                "is_wanted": s.is_wanted,
                "primary_crimes": s.primary_crimes,
            }
            for s in suspects
        ]
    }


@router.get("/{suspect_id}")
async def get_suspect(
    suspect_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get comprehensive suspect intelligence report."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    intelligence = get_suspect_intelligence(db, suspect_id)
    if not intelligence:
        raise HTTPException(status_code=404, detail="Suspect not found")
    
    return intelligence


@router.post("/{suspect_id}/arrest")
async def register_arrest_action(
    suspect_id: int,
    req: ArrestRegistration,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Register an arrest for a suspect."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    suspect = register_arrest(db, suspect_id, req.crime_type, req.case_id)
    
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    
    return {
        "success": True,
        "suspect_id": suspect.suspect_id,
        "arrest_count": suspect.arrest_count,
        "recidivism_risk": round(suspect.recidivism_probability, 3),
        "message": f"Arrest registered for {suspect.name}"
    }


@router.post("/{suspect_id}/conviction")
async def register_conviction_action(
    suspect_id: int,
    req: ConvictionRegistration,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Register a conviction for a suspect."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    suspect = register_conviction(db, suspect_id, req.crime_type)
    
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    
    return {
        "success": True,
        "suspect_id": suspect.suspect_id,
        "conviction_count": suspect.conviction_count,
        "recidivism_risk": round(suspect.recidivism_probability, 3),
        "message": f"Conviction registered for {suspect.name}"
    }


@router.post("/{suspect_id}/wanted")
async def mark_as_wanted(
    suspect_id: int,
    req: WantedFlagRequest,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Mark suspect as wanted."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    suspect = flag_as_wanted(db, suspect_id, req.warrant_type)
    
    if not suspect:
        raise HTTPException(status_code=404, detail="Suspect not found")
    
    return {
        "success": True,
        "suspect_id": suspect.suspect_id,
        "is_wanted": True,
        "warrant_type": suspect.warrant_type,
        "message": f"{suspect.name} marked as wanted for {req.warrant_type}"
    }


@router.get("/wanted/list")
async def list_wanted(
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get all wanted suspects."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    wanted = get_wanted_suspects(db)
    
    return {
        "wanted_count": len(wanted),
        "suspects": [
            {
                "id": s.id,
                "suspect_id": s.suspect_id,
                "name": s.name,
                "age": s.age,
                "photo_url": s.photo_url,
                "warrant_type": s.warrant_type,
                "last_seen": s.last_seen,
                "last_location": s.last_location,
                "primary_crimes": s.primary_crimes,
                "risk_score": s.risk_score,
            }
            for s in wanted
        ]
    }


@router.get("/risk/high")
async def list_high_risk(
    threshold: float = Query(0.7, ge=0.0, le=1.0),
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get high-risk suspects based on recidivism probability."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    high_risk = get_high_risk_suspects(db, threshold)
    
    return {
        "risk_threshold": threshold,
        "high_risk_count": len(high_risk),
        "suspects": [
            {
                "id": s.id,
                "suspect_id": s.suspect_id,
                "name": s.name,
                "arrest_count": s.arrest_count,
                "conviction_count": s.conviction_count,
                "recidivism_risk": round(s.recidivism_probability, 3),
                "primary_crimes": s.primary_crimes,
                "gang_affiliated": s.gang_affiliated,
            }
            for s in high_risk[:20]  # Limit to top 20
        ]
    }


@router.get("/gang/{gang_name}")
async def get_gang_network(
    gang_name: str,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get gang members and network information."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    network = link_gang_members(db, gang_name)
    
    if network["member_count"] == 0:
        raise HTTPException(status_code=404, detail="Gang not found")
    
    return network
