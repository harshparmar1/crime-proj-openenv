from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import Notification, User
from ..deps import get_current_user, get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    unread_only: bool = False,
):
    q = db.query(Notification).filter(Notification.user_email == user.email).order_by(Notification.id.desc())
    if unread_only:
        q = q.filter(Notification.read == False)  # noqa: E712
    rows = q.limit(100).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "read": n.read,
            "kind": n.kind,
            "report_public_id": n.report_public_id,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_email == user.email)
        .first()
    )
    if not n:
        return {"status": "not_found"}
    n.read = True
    db.commit()
    return {"status": "ok"}
