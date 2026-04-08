"""
Case Intelligence & Pattern Detection API Routes.

Endpoints:
  GET  /cases/intelligent/{case_id}  - Get intelligence report
  GET  /cases/similar/{case_id}      - Find similar cases
  GET  /cases/linked/{case_id}       - Get linked cases
  POST /cases/link                   - Manually link cases
  GET  /cases/serial                 - List potential serial crimes
  POST /evidence/{evidence_id}/chain - Log evidence chain action
  GET  /evidence/{evidence_id}/chain - Get evidence chain
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import Case, get_db, Officer
from ..deps import get_current_user
from ..services.case_intelligence_service import (
    find_similar_cases,
    link_cases,
    get_case_links,
    detect_serial_crimes,
    get_case_intelligence,
    log_evidence_chain,
    get_evidence_chain,
    auto_link_similar_cases,
)

router = APIRouter(prefix="/cases", tags=["case-intelligence"])


class CaseLinkRequest(BaseModel):
    case_id_1: int
    case_id_2: int
    link_type: str  # similar_mo, series, related_location
    reason: str


class EvidenceChainLogRequest(BaseModel):
    action: str  # viewed, transferred, analyzed, etc.


@router.get("/intelligent/{case_id}")
async def get_case_intelligence_report(
    case_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get comprehensive intelligence report for a case."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    intelligence = get_case_intelligence(db, case_id)
    if not intelligence:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return intelligence


@router.get("/similar/{case_id}")
async def find_similar(
    case_id: int,
    threshold: float = 0.7,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Find cases similar to the specified case."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    similar = find_similar_cases(db, case, threshold=threshold)
    
    return {
        "case_id": case_id,
        "similar_cases_found": len(similar),
        "similar_cases": [
            {
                "id": c.id,
                "case_id": c.case_id,
                "crime_type": c.crime_type,
                "location": c.location,
                "incident_time": c.incident_time,
                "similarity_score": round(score, 3),
                "severity": c.severity
            }
            for c, score in similar
        ]
    }


@router.get("/linked/{case_id}")
async def get_linked_cases(
    case_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get all manually linked cases."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    links = get_case_links(db, case_id)
    
    return {
        "case_id": case_id,
        "linked_count": len(links),
        "links": links
    }


@router.post("/link")
async def manually_link_cases(
    req: CaseLinkRequest,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Manually link two cases during investigation."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    case1 = db.query(Case).filter(Case.id == req.case_id_1).first()
    case2 = db.query(Case).filter(Case.id == req.case_id_2).first()
    
    if not case1 or not case2:
        raise HTTPException(status_code=404, detail="One or both cases not found")
    
    try:
        # Calculate similarity for documentation
        from ..services.case_intelligence_service import calculate_case_similarity
        similarity = calculate_case_similarity(case1, case2)
        
        link = link_cases(
            db,
            req.case_id_1,
            req.case_id_2,
            link_type=req.link_type,
            similarity_score=similarity,
            reason=req.reason
        )
        
        return {
            "success": True,
            "link_id": link.id,
            "message": f"Cases linked as {req.link_type}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/serial")
async def list_potential_serials(
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """List potential serial crime series."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    open_cases = db.query(Case).filter(
        Case.status.in_(["open", "investigating"])
    ).all()
    
    series_groups = []
    processed = set()
    
    for case in open_cases:
        if case.id in processed:
            continue
        
        serial_cases = detect_serial_crimes(db, case)
        if serial_cases:
            group = [case] + serial_cases
            series_groups.append({
                "primary_case_id": case.case_id,
                "crime_type": case.crime_type,
                "case_count": len(group),
                "severity": case.severity,
                "location": case.location,
                "cases": [
                    {
                        "id": c.id,
                        "case_id": c.case_id,
                        "incident_time": c.incident_time,
                    }
                    for c in group
                ]
            })
            processed.update([c.id for c in group])
    
    return {
        "potential_series_found": len(series_groups),
        "series": series_groups
    }


@router.post("/evidence/{evidence_id}/chain")
async def log_evidence_action(
    evidence_id: int,
    req: EvidenceChainLogRequest,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Log an action in evidence chain of custody."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    # Get officer ID from current user
    officer = db.query(Officer).filter(Officer.user_id == user.get("id")).first()
    if not officer:
        raise HTTPException(status_code=403, detail="Officer record not found")
    
    success = log_evidence_chain(db, evidence_id, officer.id, req.action)
    
    if not success:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    return {
        "success": True,
        "message": f"Evidence action logged: {req.action}",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/evidence/{evidence_id}/chain")
async def get_evidence_custody_chain(
    evidence_id: int,
    db: Annotated[Session, Depends(get_db)] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get evidence chain of custody log."""
    if user.get("role") not in ["police", "admin"]:
        raise HTTPException(status_code=403)
    
    chain = get_evidence_chain(db, evidence_id)
    
    if chain is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    return {
        "evidence_id": evidence_id,
        "chain_entries": len(chain),
        "chain": chain
    }
