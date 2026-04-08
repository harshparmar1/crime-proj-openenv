"""
Dispatch & Resource Management Service - Smart unit dispatch with optimization.

Features:
  • Smart Unit Dispatch (Haversine distance)
  • Workload Balancing
  • Route Optimization
  • Real-time Unit Availability
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..db import Officer, Case, DispatchQueue


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in km between two lat/lng coordinates."""
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_available_officers(db: Session) -> List[Officer]:
    """Get all available officers ready for dispatch."""
    return db.query(Officer).filter(
        Officer.status == "available",
    ).all()


def calculate_officer_distance(officer: Officer, case_lat: float, case_lng: float) -> Optional[float]:
    """Calculate distance from officer's current location to case location."""
    if officer.current_latitude is None or officer.current_longitude is None:
        return None
    return haversine_distance(
        officer.current_latitude, officer.current_longitude,
        case_lat, case_lng
    )


def get_optimal_officer(
    db: Session,
    case: Case,
    available_officers: Optional[List[Officer]] = None
) -> Optional[Officer]:
    """
    Smart dispatch: Select best officer based on:
    1. Distance (closest first)
    2. Workload (fewer active cases)
    3. Skill match (if applicable)
    """
    if available_officers is None:
        available_officers = get_available_officers(db)
    
    if not available_officers:
        return None
    
    if case.latitude is None or case.longitude is None:
        # No location data - assign by lowest workload
        return min(available_officers, key=lambda o: o.workload_count)
    
    # Score officers: lower distance + lower workload = higher priority
    officer_scores = []
    
    for officer in available_officers:
        distance = calculate_officer_distance(officer, case.latitude, case.longitude)
        
        if distance is None:
            continue
        
        # Composite score: 70% distance, 30% workload
        # Normalize distance (assume max 50km)
        distance_score = min(distance / 50.0, 1.0)
        workload_score = min(officer.workload_count / 10.0, 1.0)
        
        composite_score = (distance_score * 0.7) + (workload_score * 0.3)
        officer_scores.append((officer, composite_score, distance))
    
    if not officer_scores:
        return None
    
    # Return officer with lowest score
    best_officer = min(officer_scores, key=lambda x: x[1])[0]
    return best_officer


def assign_case_to_officer(
    db: Session,
    case: Case,
    officer: Officer
) -> DispatchQueue:
    """Assign a case to an officer and create dispatch queue entry."""
    now = datetime.now(timezone.utc)
    
    # Update officer workload
    officer.status = "busy"
    officer.workload_count += 1
    officer.updated_at = now
    
    # Update case assignment
    case.assigned_officer_id = officer.id
    case.assigned_at = now
    
    # Create dispatch queue entry
    estimated_arrival = 5  # minutes (basic estimate)
    if case.latitude and case.longitude and officer.current_latitude and officer.current_longitude:
        distance = calculate_officer_distance(officer, case.latitude, case.longitude)
        if distance:
            estimated_arrival = int((distance / 60) * 60)  # Assume 60 km/h average speed
    
    dispatch = DispatchQueue(
        case_id=case.id,
        assigned_officer_id=officer.id,
        status="assigned",
        estimated_arrival=estimated_arrival,
        assigned_at=now
    )
    
    db.add(dispatch)
    db.commit()
    db.refresh(dispatch)
    
    return dispatch


def auto_dispatch_case(db: Session, case: Case) -> Tuple[bool, Optional[Officer], str]:
    """
    Automatically dispatch a case to the best available officer.
    Returns: (success, assigned_officer, message)
    """
    available_officers = get_available_officers(db)
    optimal_officer = get_optimal_officer(db, case, available_officers)
    
    if not optimal_officer:
        return False, None, "No available officers for dispatch"
    
    try:
        dispatch = assign_case_to_officer(db, case, optimal_officer)
        return True, optimal_officer, f"Case assigned to {optimal_officer.user_id}"
    except Exception as e:
        db.rollback()
        return False, None, f"Dispatch failed: {str(e)}"


def complete_dispatch(db: Session, dispatch_id: int) -> bool:
    """Mark dispatch as completed."""
    dispatch = db.query(DispatchQueue).filter(DispatchQueue.id == dispatch_id).first()
    if not dispatch:
        return False
    
    dispatch.status = "completed"
    dispatch.completed_at = datetime.now(timezone.utc)
    
    # Release officer
    officer = db.query(Officer).filter(Officer.id == dispatch.assigned_officer_id).first()
    if officer:
        officer.workload_count = max(0, officer.workload_count - 1)
        if officer.workload_count == 0:
            officer.status = "available"
        officer.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    return True


def get_dispatch_queue(db: Session, status: Optional[str] = None) -> List[DispatchQueue]:
    """Get all pending dispatches."""
    query = db.query(DispatchQueue)
    if status:
        query = query.filter(DispatchQueue.status == status)
    return query.order_by(DispatchQueue.created_at).all()


def get_officer_stats(db: Session, officer_id: int) -> dict:
    """Get officer's dispatch statistics."""
    officer = db.query(Officer).filter(Officer.id == officer_id).first()
    if not officer:
        return {}
    
    dispatches = db.query(DispatchQueue).filter(
        DispatchQueue.assigned_officer_id == officer_id
    ).all()
    
    completed = [d for d in dispatches if d.status == "completed"]
    active = [d for d in dispatches if d.status in ["assigned", "en_route"]]
    
    return {
        "officer_id": officer.id,
        "badge_id": officer.badge_id,
        "current_status": officer.status,
        "workload": officer.workload_count,
        "total_dispatches": len(dispatches),
        "completed_dispatches": len(completed),
        "active_dispatches": len(active),
        "location": {
            "latitude": officer.current_latitude,
            "longitude": officer.current_longitude,
            "description": officer.current_location
        }
    }
