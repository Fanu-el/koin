from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import TransactionCategory, TransactionType
from app.models.user import User
from app.schemas.budget import BudgetCreateRequest, BudgetUpdateRequest


def list_user_budgets(db: Session, user: User) -> list[Budget]:
    return (
        db.query(Budget)
        .filter(
            Budget.user_id == user.id,
            Budget.deleted_at.is_(None),
        )
        .order_by(Budget.category)
        .all()
    )


def get_budget_or_404(db: Session, user: User, budget_id: str) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None or budget.deleted_at is not None or budget.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    return budget


def create_budget(
    db: Session,
    user: User,
    payload: BudgetCreateRequest,
) -> Budget:
    # Enforce uniqueness at the service layer (in addition to DB constraint)
    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == user.id,
            Budget.category == payload.category,
            Budget.period == payload.period,
            Budget.deleted_at.is_(None),
        )
        .one_or_none()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {payload.period.lower()} budget for {payload.category} already exists",
        )

    budget = Budget(
        user_id=user.id,
        category=payload.category,
        period=payload.period,
        amount_limit=payload.amount_limit,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def update_budget(
    db: Session,
    user: User,
    budget_id: str,
    payload: BudgetUpdateRequest,
) -> Budget:
    budget = get_budget_or_404(db, user, budget_id)
    budget.amount_limit = payload.amount_limit
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, user: User, budget_id: str) -> None:
    budget = get_budget_or_404(db, user, budget_id)
    budget.deleted_at = datetime.now(timezone.utc)
    db.commit()
