from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import os
import smtplib
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..core.config import ALLOW_OPEN_POLICE_REGISTER, POLICE_REGISTER_SECRET
from ..core.security import create_access_token, hash_password, verify_password
from ..core.state_regions import STATE_REGIONS
from ..db import Otp, SessionLocal, User
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _send_otp_email(to_email: str, otp: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user or "noreply@crime-dashboard.local")

    if not smtp_host or not smtp_user or not smtp_pass:
        print(f"[OTP] Email provider not configured. OTP for {to_email}: {otp}")
        return False

    msg = EmailMessage()
    msg["Subject"] = "Your OTP for CRIMEWATCH AI Platform"
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg.set_content(f"Your OTP is {otp}. It is valid for 10 minutes.")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    return True


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    state: str
    role: Literal["citizen", "police", "admin"] = "citizen"
    police_register_secret: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOtpRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _create_fresh_otp(db: Session, email: str) -> str:
    otp = f"{random.randint(100000, 999999)}"
    expires_at = _utc_now() + timedelta(minutes=10)
    db.add(Otp(email=email, otp=otp, expires_at=expires_at, used=False))
    return otp


def _normalize_role(payload: RegisterRequest) -> str:
    if payload.role == "citizen":
        return "citizen"
    if payload.role == "admin":
        raise HTTPException(status_code=403, detail="Admin accounts cannot self-register")
    if payload.role == "police":
        if ALLOW_OPEN_POLICE_REGISTER:
            return "police"
        if POLICE_REGISTER_SECRET and payload.police_register_secret == POLICE_REGISTER_SECRET:
            return "police"
        raise HTTPException(status_code=403, detail="Police registration requires a valid secret")
    return "citizen"


@router.post("/register")
def register_user(payload: RegisterRequest):
    if payload.state not in STATE_REGIONS:
        raise HTTPException(status_code=400, detail="Invalid state")

    role = _normalize_role(payload)
    db = SessionLocal()
    otp = ""
    try:
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        pwd_hash = hash_password(payload.password)
        user = User(
            username=payload.username,
            email=payload.email,
            password="",
            password_hash=pwd_hash,
            state=payload.state,
            role=role,
            verified=False,
            created_at=_utc_now(),
        )
        db.add(user)

        otp = _create_fresh_otp(db, payload.email)
        db.commit()
    finally:
        db.close()

    email_sent = _send_otp_email(payload.email, otp)
    return {
        "status": "otp_sent",
        "message": "OTP sent to email" if email_sent else "Email not configured; use dev OTP",
        "dev_otp": None if email_sent else otp,
    }


@router.post("/resend-otp")
def resend_otp(payload: ResendOtpRequest):
    db = SessionLocal()
    otp = ""
    try:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.verified:
            raise HTTPException(status_code=400, detail="User already verified")

        otp = _create_fresh_otp(db, payload.email)
        db.commit()
    finally:
        db.close()

    email_sent = _send_otp_email(payload.email, otp)
    return {
        "status": "otp_sent",
        "message": "OTP re-sent" if email_sent else "Email not configured; use dev OTP",
        "dev_otp": None if email_sent else otp,
    }


@router.post("/verify-otp")
def verify_otp(payload: VerifyOtpRequest):
    db = SessionLocal()
    try:
        row = (
            db.query(Otp)
            .filter(Otp.email == payload.email)
            .order_by(Otp.id.desc())
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="OTP not found")
        if row.used:
            raise HTTPException(status_code=400, detail="OTP already used")
        expires_at = _to_utc(row.expires_at)
        if _utc_now() > expires_at:
            raise HTTPException(status_code=400, detail="OTP expired")
        if payload.otp != row.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        row.used = True
        user = db.query(User).filter(User.email == payload.email).first()
        if user:
            user.verified = True
        db.commit()
    finally:
        db.close()
    return {"status": "verified", "message": "Registration complete"}


@router.post("/login")
def login(payload: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == payload.email).first()
    finally:
        db.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.verified:
        raise HTTPException(status_code=403, detail="Please verify OTP first")

    ok = False
    if user.password_hash:
        ok = verify_password(payload.password, user.password_hash)
    elif user.password.startswith("$2"):
        ok = verify_password(payload.password, user.password)
    else:
        ok = user.password == payload.password
        if ok:
            db = SessionLocal()
            try:
                u = db.query(User).filter(User.email == payload.email).first()
                if u:
                    u.password_hash = hash_password(payload.password)
                    u.password = ""
                    db.commit()
            finally:
                db.close()

    if not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        user.email,
        {"role": user.role, "username": user.username, "state": user.state},
    )
    return {
        "status": "success",
        "token": token,
        "user": {
            "username": user.username,
            "email": user.email,
            "state": user.state,
            "role": user.role,
        },
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "status": "success",
        "user": {
            "username": user.username,
            "email": user.email,
            "state": user.state,
            "role": user.role,
        },
    }
