from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionCategory, TransactionType


class TransactionCreateRequest(BaseModel):
    type: TransactionType
    category: TransactionCategory
    amount: Decimal = Field(gt=0, decimal_places=2)
    description: Optional[str] = Field(default=None, max_length=255)
    note: Optional[str] = Field(default=None, max_length=2000)
    date: date


class TransactionUpdateRequest(BaseModel):
    type: Optional[TransactionType] = None
    category: Optional[TransactionCategory] = None
    amount: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)
    description: Optional[str] = Field(default=None, max_length=255)
    note: Optional[str] = Field(default=None, max_length=2000)
    date: Optional[date] = None


class TransactionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: TransactionType
    category: TransactionCategory
    amount: Decimal
    description: Optional[str]
    note: Optional[str]
    date: date
    created_at: datetime
    updated_at: datetime
