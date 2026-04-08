from __future__ import annotations

import os
from datetime import datetime
from typing import Generator

from dotenv import load_dotenv
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Float, Integer, LargeBinary, String, Text, create_engine, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker, relationship


def _database_url() -> str:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)
    return os.getenv("DATABASE_URL", "sqlite:///./crime_reports.db")


DATABASE_URL = _database_url()

_engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="citizen")
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Otp(Base):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    otp: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True, nullable=True)
    state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    time: Mapped[str] = mapped_column(String(32), nullable=False)
    crime_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    weapon: Mapped[str] = mapped_column(String(16), nullable=False)
    vehicle: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    vehicle_selection: Mapped[str] = mapped_column(String(32), nullable=False, default="None")

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_panic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    voice_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voice_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    voice_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    voice_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, default="info")
    report_public_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias for use in route dependencies
get_db = get_db_session


# ═══════════════════════════════════════════════════════════════════════════════
# POLICE INTELLIGENCE SYSTEM MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class Officer(Base):
    """Police officer entity for dispatch & assignment."""
    __tablename__ = "officers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    badge_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    rank: Mapped[str] = mapped_column(String(64), default="Officer")  # Officer, Sergeant, Detective, etc.
    station: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Availability & Location
    status: Mapped[str] = mapped_column(String(32), default="available")  # available, busy, off_duty
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Workload & Shift
    shift: Mapped[str] = mapped_column(String(32), default="day")  # day, night, swing
    workload_count: Mapped[int] = mapped_column(Integer, default=0)  # Number of active cases
    shift_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shift_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cases = relationship("Case", back_populates="assigned_officer")
    patrol_logs = relationship("PatrolLog", back_populates="officer")


class Case(Base):
    """Police case entity - distinct from citizen reports."""
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)  # CASE-2024-001
    report_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("reports.id"), nullable=True)
    
    # Case Details
    crime_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="low")  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(32), default="open")  # open, investigating, solved, closed
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1=high, 2=medium, 3=low
    
    # Location & Time
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    incident_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Assignment
    assigned_officer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("officers.id"), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    assigned_officer = relationship("Officer", back_populates="cases")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    linked_cases = relationship("CaseLink", foreign_keys="CaseLink.case_id_1", back_populates="case_1")


class Evidence(Base):
    """Evidence tracking with chain of custody."""
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)  # EVD-2024-001
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    
    # File Info
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)  # photo, video, audio, document
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    
    # Custody Chain
    uploaded_by_officer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("officers.id"), nullable=True)
    upload_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    # Metadata
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    chain_log: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{timestamp, officer, action}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    case = relationship("Case", back_populates="evidence")


class CaseLink(Base):
    """Case linking for pattern detection and serial crimes."""
    __tablename__ = "case_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id_1: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    case_id_2: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    
    # Linkage Details
    link_type: Mapped[str] = mapped_column(String(64), nullable=False)  # similar_mo, series, related_location
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 1.0
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # Manually confirmed by investigator
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    case_1 = relationship("Case", foreign_keys=[case_id_1])
    case_2 = relationship("Case", foreign_keys=[case_id_2])


class Suspect(Base):
    """Criminal database with recidivism prediction."""
    __tablename__ = "suspects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suspect_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)  # SUSP-2024-001
    
    # Personal Info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    # Criminal History
    arrest_count: Mapped[int] = mapped_column(Integer, default=0)
    conviction_count: Mapped[int] = mapped_column(Integer, default=0)
    primary_crimes: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [crime_types]
    modus_operandi: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    # Risk Assessment
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 1.0
    recidivism_probability: Mapped[float] = mapped_column(Float, default=0.0)  # ML predicted
    gang_affiliated: Mapped[bool] = mapped_column(Boolean, default=False)
    gang_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_wanted: Mapped[bool] = mapped_column(Boolean, default=False)
    warrant_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Status
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PatrolLog(Base):
    """Officer patrol activity and location tracking."""
    __tablename__ = "patrol_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    officer_id: Mapped[int] = mapped_column(Integer, ForeignKey("officers.id"), nullable=False)
    
    # Route & Location
    beat_area: Mapped[str] = mapped_column(String(128), nullable=False)
    route_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Activity
    activity_type: Mapped[str] = mapped_column(String(64), default="patrol")  # patrol, stop, ticket, assistance
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    officer = relationship("Officer", back_populates="patrol_logs")


class BeatRisk(Base):
    """Real-time risk assessment for patrol beats."""
    __tablename__ = "beat_risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    beat_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    
    # Risk Metrics
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 1.0
    threat_level: Mapped[str] = mapped_column(String(32), default="low")  # low, medium, high, critical
    recent_incidents: Mapped[int] = mapped_column(Integer, default=0)
    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Recommended Response
    recommended_roster_size: Mapped[int] = mapped_column(Integer, default=2)
    armed_crime_warning: Mapped[bool] = mapped_column(Boolean, default=False)


class DispatchQueue(Base):
    """Real-time dispatch queue for unit assignment."""
    __tablename__ = "dispatch_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    
    # Dispatch Info
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending, assigned, en_route, on_scene, completed
    assigned_officer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("officers.id"), nullable=True)
    estimated_arrival: Mapped[int] = mapped_column(Integer, default=0)  # minutes
    
    # Timing
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComplianceLog(Base):
    """Audit trail for all system actions."""
    __tablename__ = "compliance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    officer_id: Mapped[int] = mapped_column(Integer, ForeignKey("officers.id"), nullable=False)
    
    # Action Details
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # case_created, evidence_logged, suspect_linked
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)  # case, evidence, suspect
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
