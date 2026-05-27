from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, UUIDPrimaryKeyMixin
from app.models.transaction import TransactionCategory


class BudgetPeriod(StrEnum):
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class Budget(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "budgets"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    category: Mapped[TransactionCategory] = mapped_column(
        Enum(TransactionCategory, name="transaction_category"),
        nullable=False,
        index=True,
    )
    period: Mapped[BudgetPeriod] = mapped_column(
        Enum(BudgetPeriod, name="budget_period"),
        nullable=False,
        index=True,
    )
    # The spending limit for this category in the given period
    amount_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    user = relationship("User", back_populates="budgets")
