from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.user import User


def create_notification(db: Session, user: User, title: str, body: str, type: str = "INFO") -> Notification:
    n = Notification(user_id=user.id, title=title, body=body, type=type)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def list_user_notifications(db: Session, user: User) -> List[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.deleted_at.is_(None))
        .order_by(Notification.created_at.desc())
        .all()
    )


def mark_notification_read(db: Session, user: User, notification_id: str) -> Notification:
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id or n.deleted_at is not None:
        raise Exception("Notification not found")
    n.read = True
    n.updated_at = datetime.now()
    db.commit()
    db.refresh(n)
    return n
