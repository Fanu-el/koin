from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.savings_goal import SavingsGoal, SavingsGoalStatus
from app.models.user import User
from app.schemas.savings_goal import SavingsGoalCreateRequest, SavingsGoalUpdateRequest


def list_user_savings_goals(
    db: Session,
    user: User,
    status_filter: SavingsGoalStatus | None = None,
) -> list[SavingsGoal]:
    query = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == user.id,
        SavingsGoal.deleted_at.is_(None),
    )
    if status_filter:
        query = query.filter(SavingsGoal.status == status_filter)
    return query.order_by(SavingsGoal.created_at.desc()).all()


def get_savings_goal_or_404(db: Session, user: User, goal_id: str) -> SavingsGoal:
    goal = db.get(SavingsGoal, goal_id)
    if goal is None or goal.deleted_at is not None or goal.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Savings goal not found",
        )
    return goal


def create_savings_goal(
    db: Session,
    user: User,
    payload: SavingsGoalCreateRequest,
) -> SavingsGoal:
    goal = SavingsGoal(
        user_id=user.id,
        name=payload.name.strip(),
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        target_date=payload.target_date,
        description=payload.description,
        status=SavingsGoalStatus.ACTIVE,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def update_savings_goal(
    db: Session,
    user: User,
    goal_id: str,
    payload: SavingsGoalUpdateRequest,
) -> SavingsGoal:
    goal = get_savings_goal_or_404(db, user, goal_id)
    if payload.name is not None:
        goal.name = payload.name.strip()
    if payload.target_amount is not None:
        goal.target_amount = payload.target_amount
    if payload.current_amount is not None:
        goal.current_amount = payload.current_amount
        # Auto-complete when target is reached
        if goal.current_amount >= goal.target_amount:
            goal.status = SavingsGoalStatus.COMPLETED
    if payload.target_date is not None:
        goal.target_date = payload.target_date
    if payload.description is not None:
        goal.description = payload.description
    if payload.status is not None:
        goal.status = payload.status
    db.commit()
    db.refresh(goal)
    return goal


def delete_savings_goal(db: Session, user: User, goal_id: str) -> None:
    goal = get_savings_goal_or_404(db, user, goal_id)
    goal.deleted_at = datetime.now(timezone.utc)
    db.commit()
