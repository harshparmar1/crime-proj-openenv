"""
Database Seed Data for Police Intelligence System.

Creates sample officers, cases, suspects, and other records for testing.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from ..db import (
    Officer, Case, Suspect, Evidence, PatrolLog, BeatRisk,
    User, DispatchQueue
)


def seed_sample_data(db: Session) -> None:
    """Populate database with sample data for testing."""
    
    # Check if data already exists
    existing_officers = db.query(Officer).count()
    if existing_officers > 0:
        print("Sample data already exists. Skipping seed.")
        return
    
    print("Seeding database with sample data...")
    
    # Create sample users (officers)
    users_data = [
        {"id": 101, "username": "officer_smith", "email": "smith@police.com", "state": "Maharashtra"},
        {"id": 102, "username": "officer_johnson", "email": "johnson@police.com", "state": "Maharashtra"},
        {"id": 103, "username": "officer_williams", "email": "williams@police.com", "state": "Karnataka"},
        {"id": 104, "username": "detective_brown", "email": "brown@police.com", "state": "Maharashtra"},
    ]
    
    # Create sample officers
    officers_data = [
        {
            "user_id": 101,
            "badge_id": "BADGE-001",
            "rank": "Officer",
            "station": "Mumbai Central",
            "status": "available",
            "current_latitude": 19.076,
            "current_longitude": 72.877,
            "current_location": "Mumbai Downtown",
            "shift": "day",
            "workload_count": 1,
        },
        {
            "user_id": 102,
            "badge_id": "BADGE-002",
            "rank": "Officer",
            "station": "Mumbai Central",
            "status": "available",
            "current_latitude": 19.085,
            "current_longitude": 72.885,
            "current_location": "Mumbai Harbor",
            "shift": "day",
            "workload_count": 0,
        },
        {
            "user_id": 103,
            "badge_id": "BADGE-003",
            "rank": "Sergeant",
            "station": "Bangalore Central",
            "status": "busy",
            "current_latitude": 12.972,
            "current_longitude": 77.594,
            "current_location": "Bangalore Tech Park",
            "shift": "night",
            "workload_count": 2,
        },
        {
            "user_id": 104,
            "badge_id": "BADGE-004",
            "rank": "Detective",
            "station": "Mumbai Central",
            "status": "available",
            "current_latitude": 19.076,
            "current_longitude": 72.877,
            "current_location": "Police HQ",
            "shift": "day",
            "workload_count": 3,
        },
    ]
    
    officers = []
    for data in officers_data:
        officer = Officer(**data)
        db.add(officer)
        officers.append(officer)
    db.commit()
    
    # Create sample cases
    now = datetime.now(timezone.utc)
    cases_data = [
        {
            "case_id": "CASE-2024-001",
            "crime_type": "Robbery",
            "description": "Jewelry store robbery on main street",
            "severity": "high",
            "status": "investigating",
            "priority": 1,
            "location": "Mumbai Downtown",
            "latitude": 19.076,
            "longitude": 72.877,
            "incident_time": now - timedelta(hours=2),
            "assigned_officer_id": officers[0].id,
        },
        {
            "case_id": "CASE-2024-002",
            "crime_type": "Theft",
            "description": "Apartment break-in, items stolen",
            "severity": "medium",
            "status": "open",
            "priority": 2,
            "location": "Mumbai Downtown",
            "latitude": 19.077,
            "longitude": 72.878,
            "incident_time": now - timedelta(hours=5),
        },
        {
            "case_id": "CASE-2024-003",
            "crime_type": "Cybercrime",
            "description": "Phishing scam targeting financial accounts",
            "severity": "medium",
            "status": "investigating",
            "priority": 2,
            "location": "Bangalore Tech Park",
            "latitude": 12.972,
            "longitude": 77.594,
            "incident_time": now - timedelta(hours=1),
            "assigned_officer_id": officers[2].id,
        },
        {
            "case_id": "CASE-2024-004",
            "crime_type": "Assault",
            "description": "Physical altercation at local venue",
            "severity": "medium",
            "status": "open",
            "priority": 2,
            "location": "Mumbai Harbor",
            "latitude": 19.085,
            "longitude": 72.885,
            "incident_time": now - timedelta(hours=8),
        },
    ]
    
    cases = []
    for data in cases_data:
        case = Case(**data)
        db.add(case)
        cases.append(case)
    db.commit()
    
    # Create sample suspects
    suspects_data = [
        {
            "suspect_id": "SUSP-2024-001",
            "name": "Raj Kumar",
            "age": 28,
            "description": "Height: 5'10\", Medium build, Tattoo on left arm",
            "arrest_count": 5,
            "conviction_count": 2,
            "primary_crimes": ["Theft", "Robbery"],
            "modus_operandi": "Targets jewelry stores, operates at night",
            "risk_score": 0.85,
            "gang_affiliated": True,
            "gang_name": "Downtown Gang",
            "is_wanted": True,
            "warrant_type": "felony",
        },
        {
            "suspect_id": "SUSP-2024-002",
            "name": "Priya Singh",
            "age": 32,
            "description": "Height: 5'6\", Slim, Known for tech crimes",
            "arrest_count": 2,
            "conviction_count": 1,
            "primary_crimes": ["Cybercrime", "Fraud"],
            "modus_operandi": "Online phishing and fraud schemes",
            "risk_score": 0.65,
            "gang_affiliated": False,
        },
        {
            "suspect_id": "SUSP-2024-003",
            "name": "Vikram Mehta",
            "age": 19,
            "description": "Height: 5'8\", Athletic build, Gang member",
            "arrest_count": 8,
            "conviction_count": 3,
            "primary_crimes": ["Assault", "Robbery", "Drug related"],
            "modus_operandi": "Street-level robberies and assaults",
            "risk_score": 0.92,
            "gang_affiliated": True,
            "gang_name": "Downtown Gang",
        },
    ]
    
    suspects = []
    for data in suspects_data:
        suspect = Suspect(**data)
        db.add(suspect)
        suspects.append(suspect)
    db.commit()
    
    # Update recidivism scores
    from ..services.suspect_service import update_recidivism_score
    for suspect in suspects:
        update_recidivism_score(db, suspect.id)
    
    # Create sample beat risks
    beats_data = [
        {
            "beat_name": "Downtown Mumbai",
            "risk_score": 0.78,
            "threat_level": "high",
            "recent_incidents": 5,
            "recommended_roster_size": 4,
            "armed_crime_warning": True,
        },
        {
            "beat_name": "Mumbai Harbor",
            "risk_score": 0.45,
            "threat_level": "medium",
            "recent_incidents": 2,
            "recommended_roster_size": 2,
            "armed_crime_warning": False,
        },
        {
            "beat_name": "Bangalore Tech Park",
            "risk_score": 0.52,
            "threat_level": "medium",
            "recent_incidents": 3,
            "recommended_roster_size": 3,
            "armed_crime_warning": False,
        },
    ]
    
    for data in beats_data:
        beat = BeatRisk(**data)
        db.add(beat)
    db.commit()
    
    # Create sample patrol logs
    patrol_logs_data = [
        {
            "officer_id": officers[0].id,
            "beat_area": "Downtown Mumbai",
            "route_name": "Route A",
            "latitude": 19.076,
            "longitude": 72.877,
            "activity_type": "patrol",
            "duration_minutes": 45,
            "notes": "Routine patrol, no incidents",
            "timestamp": now - timedelta(hours=1),
        },
        {
            "officer_id": officers[1].id,
            "beat_area": "Mumbai Harbor",
            "route_name": "Route B",
            "latitude": 19.085,
            "longitude": 72.885,
            "activity_type": "stop",
            "duration_minutes": 15,
            "notes": "Vehicle stop, driver warning issued",
            "timestamp": now - timedelta(hours=2),
        },
    ]
    
    for data in patrol_logs_data:
        log = PatrolLog(**data)
        db.add(log)
    db.commit()
    
    print(f"✓ Created {len(officers)} officers")
    print(f"✓ Created {len(cases)} cases")
    print(f"✓ Created {len(suspects)} suspects")
    print(f"✓ Created {len(beats_data)} beat risk zones")
    print("Database seeding complete!")
