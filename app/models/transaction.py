from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class TransactionType(StrEnum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class TransactionCategory(StrEnum):
    # Expense categories
    FOOD = "FOOD"
    TRANSPORT = "TRANSPORT"
    HOUSING = "HOUSING"
    HEALTHCARE = "HEALTHCARE"
    ENTERTAINMENT = "ENTERTAINMENT"
    SHOPPING = "SHOPPING"
    UTILITIES = "UTILITIES"
    EDUCATION = "EDUCATION"
    PERSONAL = "PERSONAL"
    # Income categories
    SALARY = "SALARY"
    FREELANCE = "FREELANCE"
    INVESTMENT = "INVESTMENT"
    GIFT = "GIFT"
    # General
    OTHER = "OTHER"


class Transaction(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "transactions"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type"),
        nullable=False,
        index=True,
    )
    category: Mapped[TransactionCategory] = mapped_column(
        Enum(TransactionCategory, name="transaction_category"),
        nullable=False,
        index=True,
    )
    # Stored as NUMERIC(12,2) — always positive; type field indicates direction
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The actual date of the transaction (may differ from created_at)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    user = relationship("User", back_populates="transactions")
