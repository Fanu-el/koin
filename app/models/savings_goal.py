from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AuditMixin, Base, UUIDPrimaryKeyMixin


class SavingsGoalStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SavingsGoal(UUIDPrimaryKeyMixin, AuditMixin, Base):
    __tablename__ = "savings_goals"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    target_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    current_amount: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[SavingsGoalStatus] = mapped_column(
        Enum(SavingsGoalStatus, name="savings_goal_status"),
        default=SavingsGoalStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="savings_goals")
