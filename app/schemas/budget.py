from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.budget import BudgetPeriod
from app.models.transaction import TransactionCategory


class BudgetCreateRequest(BaseModel):
    category: TransactionCategory
    period: BudgetPeriod
    amount_limit: Decimal = Field(gt=0, decimal_places=2)


class BudgetUpdateRequest(BaseModel):
    amount_limit: Decimal = Field(gt=0, decimal_places=2)


class BudgetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    category: TransactionCategory
    period: BudgetPeriod
    amount_limit: Decimal
    created_at: datetime
    updated_at: datetime


class BudgetStatusItem(BaseModel):
    """Budget for a category alongside how much was actually spent."""

    budget: BudgetPublic
    spent: Decimal
    remaining: Decimal
    percent_used: float
