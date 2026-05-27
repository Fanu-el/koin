from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import requires_auth
from app.db.session import get_db
from app.models.savings_goal import SavingsGoalStatus
from app.models.user import User
from app.schemas.response import ApiResponse, success_response
from app.schemas.savings_goal import (
    SavingsGoalCreateRequest,
    SavingsGoalPublic,
    SavingsGoalUpdateRequest,
)
from app.services.savings_goal_service import (
    create_savings_goal,
    delete_savings_goal,
    get_savings_goal_or_404,
    list_user_savings_goals,
    update_savings_goal,
)

router = APIRouter(prefix="/savings-goals", tags=["savings-goals"])


@router.get("", response_model=ApiResponse[list[SavingsGoalPublic]])
def list_goals(
    status: SavingsGoalStatus | None = Query(default=None),
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(
        list_user_savings_goals(db, current_user, status_filter=status)
    )


@router.post("", response_model=ApiResponse[SavingsGoalPublic], status_code=201)
def create(
    payload: SavingsGoalCreateRequest,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(create_savings_goal(db, current_user, payload))


@router.get("/{goal_id}", response_model=ApiResponse[SavingsGoalPublic])
def get_goal(
    goal_id: str,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(get_savings_goal_or_404(db, current_user, goal_id))


@router.patch("/{goal_id}", response_model=ApiResponse[SavingsGoalPublic])
def update(
    goal_id: str,
    payload: SavingsGoalUpdateRequest,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(update_savings_goal(db, current_user, goal_id, payload))


@router.delete("/{goal_id}", response_model=ApiResponse[None])
def delete(
    goal_id: str,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    delete_savings_goal(db, current_user, goal_id)
    return success_response()
