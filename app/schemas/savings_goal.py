from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.savings_goal import SavingsGoalStatus


class SavingsGoalCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    target_amount: Decimal = Field(gt=0, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    target_date: Optional[date] = None
    description: Optional[str] = Field(default=None, max_length=2000)


class SavingsGoalUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    target_amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    current_amount: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    target_date: Optional[date] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[SavingsGoalStatus] = None


class SavingsGoalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: Optional[date]
    status: SavingsGoalStatus
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
