from datetime import datetime
from pydantic import BaseModel


class NotificationPublic(BaseModel):
    id: str
    type: str
    title: str
    body: str
    read: bool
    created_at: datetime


class NotificationCreateRequest(BaseModel):
    title: str
    body: str
    type: str | None = "INFO"
