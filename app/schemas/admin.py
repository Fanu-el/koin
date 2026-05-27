from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.email import EmailStatus
from app.models.verification_code import VerificationCodePurpose


class EmailPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    to_email: str
    subject: str
    body: str
    status: EmailStatus
    provider: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class VerificationCodePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    email: str
    purpose: VerificationCodePurpose
    expires_at: datetime
    consumed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class AnalyticsResponse(BaseModel):
    total_chat_sessions: int
    total_messages: int
    active_users: int
    failed_ai_calls: int
    total_transactions: int
    total_budgets: int
    total_savings_goals: int
