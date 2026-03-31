from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..db import Notification, User


def create_notification(
    db: Session,
    *,
    user_email: str,
    title: str,
    body: str,
    kind: str = "info",
    report_public_id: str | None = None,
) -> Notification:
    row = Notification(
        user_email=user_email,
        title=title,
        body=body,
        read=False,
        kind=kind,
        report_public_id=report_public_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def broadcast_targets_for_report(db: Session) -> list[str]:
    emails = [e for (e,) in db.query(User.email).filter(User.role.in_(["police", "admin"])).distinct().all()]
    return emails
