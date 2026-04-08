"""
Suspect Database & Criminal Intelligence Service.

Features:
  • Offender Lookup & Search
  • Recidivism Risk Prediction
  • Gang Network Tracking
  • Criminal History Analysis
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..db import Suspect, Case


def create_suspect(
    db: Session,
    name: str,
    description: str,
    age: Optional[int] = None,
    photo_url: Optional[str] = None,
    primary_crimes: Optional[list] = None,
    modus_operandi: str = "",
) -> Suspect:
    """Create a new suspect record."""
    suspect_id = f"SUSP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    suspect = Suspect(
        suspect_id=suspect_id,
        name=name,
        age=age,
        description=description,
        photo_url=photo_url,
        primary_crimes=primary_crimes or [],
        modus_operandi=modus_operandi,
    )
    
    db.add(suspect)
    db.commit()
    db.refresh(suspect)
    return suspect


def search_suspects(
    db: Session,
    query: str,
    search_type: str = "name"  # name, description, modus_operandi
) -> List[Suspect]:
    """Search suspects by various criteria."""
    query_lower = f"%{query.lower()}%"
    
    if search_type == "name":
        return db.query(Suspect).filter(
            Suspect.name.ilike(query_lower)
        ).all()
    elif search_type == "description":
        return db.query(Suspect).filter(
            Suspect.description.ilike(query_lower)
        ).all()
    elif search_type == "modus_operandi":
        return db.query(Suspect).filter(
            Suspect.modus_operandi.ilike(query_lower)
        ).all()
    else:
        # Search across all fields
        return db.query(Suspect).filter(
            or_(
                Suspect.name.ilike(query_lower),
                Suspect.description.ilike(query_lower),
                Suspect.modus_operandi.ilike(query_lower),
            )
        ).all()


def predict_recidivism_risk(suspect: Suspect) -> float:
    """
    Simple ML-based recidivism prediction (0.0 - 1.0).
    In production, this would use a trained ML model.
    
    Factors:
    - Age: Younger offenders have higher recidivism
    - Prior convictions: More convictions = higher risk
    - Crime type: Violent crimes have different risk profiles
    """
    base_score = 0.3
    
    # Prior conviction factor (up to 0.4)
    if suspect.conviction_count > 0:
        conviction_factor = min(suspect.conviction_count / 10, 1.0) * 0.4
        base_score += conviction_factor
    
    # Age factor (younger = higher risk)
    if suspect.age and suspect.age < 25:
        base_score += 0.2
    elif suspect.age and suspect.age > 60:
        base_score -= 0.1
    
    # Gang affiliation (higher risk)
    if suspect.gang_affiliated:
        base_score += 0.2
    
    # Violent crime indicator
    violent_crimes = ["Assault", "Robbery", "Homicide", "Sexual Assault"]
    if suspect.primary_crimes:
        has_violent = any(c in violent_crimes for c in suspect.primary_crimes)
        if has_violent:
            base_score += 0.15
    
    return min(max(base_score, 0.0), 1.0)


def update_recidivism_score(db: Session, suspect_id: int) -> float:
    """Update recidivism probability for a suspect."""
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        return 0.0
    
    risk_score = predict_recidivism_risk(suspect)
    suspect.recidivism_probability = risk_score
    suspect.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    return risk_score


def register_arrest(
    db: Session,
    suspect_id: int,
    crime_type: str,
    case_id: Optional[int] = None
) -> Suspect:
    """Register an arrest for a suspect."""
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        return None
    
    suspect.arrest_count += 1
    suspect.last_seen = datetime.now(timezone.utc)
    
    if crime_type not in (suspect.primary_crimes or []):
        if not suspect.primary_crimes:
            suspect.primary_crimes = []
        suspect.primary_crimes.append(crime_type)
    
    # Update recidivism risk
    update_recidivism_score(db, suspect_id)
    
    db.commit()
    db.refresh(suspect)
    return suspect


def register_conviction(
    db: Session,
    suspect_id: int,
    crime_type: str
) -> Suspect:
    """Register a conviction for a suspect."""
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        return None
    
    suspect.conviction_count += 1
    suspect.updated_at = datetime.now(timezone.utc)
    
    # Update recidivism risk
    update_recidivism_score(db, suspect_id)
    
    db.commit()
    db.refresh(suspect)
    return suspect


def update_suspect_location(
    db: Session,
    suspect_id: int,
    location: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> Suspect:
    """Update suspect's last known location."""
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        return None
    
    suspect.last_seen = datetime.now(timezone.utc)
    suspect.last_location = location
    
    db.commit()
    db.refresh(suspect)
    return suspect


def flag_as_wanted(
    db: Session,
    suspect_id: int,
    warrant_type: str
) -> Suspect:
    """Flag a suspect as wanted."""
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        return None
    
    suspect.is_wanted = True
    suspect.warrant_type = warrant_type
    suspect.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(suspect)
    return suspect


def get_high_risk_suspects(db: Session, threshold: float = 0.7) -> List[Suspect]:
    """Get high-risk suspects based on recidivism scores."""
    return db.query(Suspect).filter(
        Suspect.recidivism_probability >= threshold
    ).order_by(Suspect.recidivism_probability.desc()).all()


def get_wanted_suspects(db: Session) -> List[Suspect]:
    """Get all wanted suspects."""
    return db.query(Suspect).filter(
        Suspect.is_wanted == True
    ).order_by(Suspect.risk_score.desc()).all()


def get_gang_members(db: Session, gang_name: str) -> List[Suspect]:
    """Get all members of a specific gang."""
    return db.query(Suspect).filter(
        Suspect.gang_name == gang_name
    ).all()


def link_gang_members(db: Session, gang_name: str) -> dict:
    """Get gang network information."""
    members = get_gang_members(db, gang_name)
    
    # Simple network: just list connections
    network = {
        "gang_name": gang_name,
        "member_count": len(members),
        "members": [
            {
                "id": m.id,
                "suspect_id": m.suspect_id,
                "name": m.name,
                "risk_score": m.risk_score,
                "primary_crimes": m.primary_crimes,
                "last_location": m.last_location,
            }
            for m in members
        ]
    }
    
    return network


def get_suspect_intelligence(db: Session, suspect_id: int) -> dict:
    """Get comprehensive intelligence on a suspect."""
    suspect = db.query(Suspect).filter(Suspect.id == suspect_id).first()
    if not suspect:
        return {}
    
    return {
        "id": suspect.id,
        "suspect_id": suspect.suspect_id,
        "name": suspect.name,
        "age": suspect.age,
        "description": suspect.description,
        "photo_url": suspect.photo_url,
        "arrest_count": suspect.arrest_count,
        "conviction_count": suspect.conviction_count,
        "primary_crimes": suspect.primary_crimes,
        "modus_operandi": suspect.modus_operandi,
        "risk_score": suspect.risk_score,
        "recidivism_probability": round(suspect.recidivism_probability, 3),
        "gang_affiliated": suspect.gang_affiliated,
        "gang_name": suspect.gang_name,
        "is_wanted": suspect.is_wanted,
        "warrant_type": suspect.warrant_type,
        "last_seen": suspect.last_seen,
        "last_location": suspect.last_location,
        "created_at": suspect.created_at,
        "updated_at": suspect.updated_at,
    }
