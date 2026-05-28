from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import requires_auth
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationPublic
from app.schemas.response import ApiResponse, success_response
from app.services.notification_service import (
    list_user_notifications,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=ApiResponse[list[NotificationPublic]])
def list_notifications(current_user: User = Depends(requires_auth), db: Session = Depends(get_db)):
    return success_response(list_user_notifications(db, current_user))


@router.patch("/{notification_id}/read", response_model=ApiResponse[NotificationPublic])
def read_notification(notification_id: str, current_user: User = Depends(requires_auth), db: Session = Depends(get_db)):
    n = mark_notification_read(db, current_user, notification_id)
    return success_response(n)
