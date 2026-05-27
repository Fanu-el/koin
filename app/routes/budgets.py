from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import requires_auth
from app.db.session import get_db
from app.models.user import User
from app.schemas.budget import BudgetCreateRequest, BudgetPublic, BudgetUpdateRequest
from app.schemas.response import ApiResponse, success_response
from app.services.budget_service import (
    create_budget,
    delete_budget,
    get_budget_or_404,
    list_user_budgets,
    update_budget,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=ApiResponse[list[BudgetPublic]])
def list_budgets(
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(list_user_budgets(db, current_user))


@router.post("", response_model=ApiResponse[BudgetPublic], status_code=201)
def create(
    payload: BudgetCreateRequest,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(create_budget(db, current_user, payload))


@router.get("/{budget_id}", response_model=ApiResponse[BudgetPublic])
def get_budget(
    budget_id: str,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(get_budget_or_404(db, current_user, budget_id))


@router.patch("/{budget_id}", response_model=ApiResponse[BudgetPublic])
def update(
    budget_id: str,
    payload: BudgetUpdateRequest,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    return success_response(update_budget(db, current_user, budget_id, payload))


@router.delete("/{budget_id}", response_model=ApiResponse[None])
def delete(
    budget_id: str,
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    delete_budget(db, current_user, budget_id)
    return success_response()
