"""
Case Intelligence & Pattern Detection Service.

Features:
  • Similar Crime Detection
  • Serial Crime Identification
  • Evidence Chain Tracking
  • Case Clustering & Linking
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..db import Case, CaseLink, Evidence, Suspect


CRIME_SIMILARITY_THRESHOLD = 0.75  # 75% similarity to flag
SERIAL_CRIME_THRESHOLD = 3  # Minimum 3 similar crimes to flag as series


def extract_crime_features(case: Case) -> dict:
    """Extract features from a case for similarity analysis."""
    return {
        "crime_type": case.crime_type,
        "severity": case.severity,
        "location": case.location,
        "hour_of_day": case.incident_time.hour if case.incident_time else None,
        "day_of_week": case.incident_time.weekday() if case.incident_time else None,
    }


def calculate_case_similarity(case1: Case, case2: Case) -> float:
    """
    Calculate similarity between two cases (0.0 - 1.0).
    
    Similarity factors:
    - Crime type match: 40%
    - Location proximity: 30%
    - Temporal proximity: 20%
    - Severity match: 10%
    """
    if not case1 or not case2 or case1.id == case2.id:
        return 0.0
    
    score = 0.0
    
    # Crime type match
    if case1.crime_type == case2.crime_type:
        score += 0.40
    
    # Location proximity (within 5 km)
    if (case1.latitude and case1.longitude and case2.latitude and case2.longitude):
        from .dispatch_service import haversine_distance
        distance = haversine_distance(
            case1.latitude, case1.longitude,
            case2.latitude, case2.longitude
        )
        if distance <= 5:
            score += 0.30 * (1 - distance / 5)  # Full score if same location
        elif distance <= 10:
            score += 0.15
    
    # Temporal proximity (within 7 days)
    if case1.incident_time and case2.incident_time:
        time_diff = abs((case1.incident_time - case2.incident_time).total_seconds())
        days_diff = time_diff / 86400
        if days_diff <= 7:
            score += 0.20 * (1 - days_diff / 7)
    
    # Severity match
    if case1.severity == case2.severity:
        score += 0.10
    
    return min(score, 1.0)


def find_similar_cases(db: Session, case: Case, threshold: float = 0.7) -> List[Tuple[Case, float]]:
    """Find cases similar to the given case."""
    all_cases = db.query(Case).filter(
        and_(
            Case.id != case.id,
            Case.status != "closed"
        )
    ).all()
    
    similar = []
    for other_case in all_cases:
        similarity = calculate_case_similarity(case, other_case)
        if similarity >= threshold:
            similar.append((other_case, similarity))
    
    return sorted(similar, key=lambda x: x[1], reverse=True)


def detect_serial_crimes(db: Session, case: Case) -> Optional[List[Case]]:
    """
    Detect if a case is part of a crime series.
    Returns list of linked cases if serial crime detected, None otherwise.
    """
    similar_cases = find_similar_cases(db, case, threshold=CRIME_SIMILARITY_THRESHOLD)
    
    if len(similar_cases) >= SERIAL_CRIME_THRESHOLD - 1:  # -1 because we exclude the case itself
        return [c[0] for c in similar_cases[:5]]  # Return top 5
    
    return None


def link_cases(
    db: Session,
    case_id_1: int,
    case_id_2: int,
    link_type: str,
    similarity_score: float,
    reason: str
) -> CaseLink:
    """Create a link between two cases for investigation."""
    link = CaseLink(
        case_id_1=case_id_1,
        case_id_2=case_id_2,
        link_type=link_type,
        similarity_score=similarity_score,
        reason=reason,
        confirmed=False
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def auto_link_similar_cases(db: Session, case: Case) -> List[CaseLink]:
    """Automatically link a new case to similar existing cases."""
    similar_cases = find_similar_cases(db, case, threshold=CRIME_SIMILARITY_THRESHOLD)
    
    links = []
    for similar_case, similarity in similar_cases[:5]:  # Link to top 5
        link_type = "series" if similarity >= 0.85 else "similar_mo"
        
        link = link_cases(
            db,
            case.id,
            similar_case.id,
            link_type=link_type,
            similarity_score=similarity,
            reason=f"Auto-detected {link_type} pattern"
        )
        links.append(link)
    
    return links


def get_case_links(db: Session, case_id: int) -> List[dict]:
    """Get all cases linked to a given case."""
    links = db.query(CaseLink).filter(
        or_(CaseLink.case_id_1 == case_id, CaseLink.case_id_2 == case_id)
    ).all()
    
    result = []
    for link in links:
        case_a = link.case_1 if link.case_id_1 == case_id else link.case_2
        case_b = link.case_2 if link.case_id_1 == case_id else link.case_1
        
        result.append({
            "link_id": link.id,
            "link_type": link.link_type,
            "similarity_score": link.similarity_score,
            "confirmed": link.confirmed,
            "linked_case": {
                "id": case_b.id,
                "case_id": case_b.case_id,
                "crime_type": case_b.crime_type,
                "location": case_b.location,
                "incident_time": case_b.incident_time
            },
            "reason": link.reason
        })
    
    return result


def log_evidence_chain(db: Session, evidence_id: int, officer_id: int, action: str) -> bool:
    """Log an action in the evidence chain of custody."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        return False
    
    if not evidence.chain_log:
        evidence.chain_log = []
    
    evidence.chain_log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "officer_id": officer_id,
        "action": action
    })
    
    db.commit()
    return True


def get_evidence_chain(db: Session, evidence_id: int) -> Optional[list]:
    """Get the chain of custody for evidence."""
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    return evidence.chain_log if evidence else None


def cluster_cases_by_similarity(db: Session, crime_type: Optional[str] = None) -> List[List[Case]]:
    """
    Cluster cases by similarity for investigation.
    Returns list of case groups.
    """
    cases = db.query(Case).filter(
        Case.status.in_(["open", "investigating"])
    )
    
    if crime_type:
        cases = cases.filter(Case.crime_type == crime_type)
    
    cases = cases.all()
    
    if not cases:
        return []
    
    # Simple clustering: group by crime type and location
    clusters = {}
    for case in cases:
        key = (case.crime_type, case.location)
        if key not in clusters:
            clusters[key] = []
        clusters[key].append(case)
    
    return [group for group in clusters.values() if len(group) > 1]


def get_case_intelligence(db: Session, case_id: int) -> dict:
    """Get comprehensive intelligence report for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        return {}
    
    # Get similar cases
    similar = find_similar_cases(db, case, threshold=0.7)
    
    # Get linked cases
    links = get_case_links(db, case_id)
    
    # Get evidence
    evidence = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    
    return {
        "case": {
            "id": case.id,
            "case_id": case.case_id,
            "crime_type": case.crime_type,
            "description": case.description,
            "location": case.location,
            "severity": case.severity,
            "status": case.status,
            "incident_time": case.incident_time,
            "assigned_officer_id": case.assigned_officer_id,
        },
        "similar_cases": [
            {
                "id": c.id,
                "case_id": c.case_id,
                "crime_type": c.crime_type,
                "location": c.location,
                "similarity_score": score
            }
            for c, score in similar[:5]
        ],
        "linked_cases": links,
        "evidence_count": len(evidence),
        "evidence": [
            {
                "id": e.id,
                "evidence_id": e.evidence_id,
                "file_name": e.file_name,
                "file_type": e.file_type,
                "upload_time": e.upload_time,
                "is_critical": e.is_critical
            }
            for e in evidence
        ]
    }
