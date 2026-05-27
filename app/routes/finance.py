from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import requires_auth
from app.db.session import get_db
from app.models.transaction import TransactionType
from app.models.user import User
from app.schemas.budget import BudgetStatusItem
from app.schemas.finance import (
    CategorySummaryResponse,
    DashboardResponse,
    SpendingTrendResponse,
)
from app.schemas.response import ApiResponse, success_response
from app.services.finance_service import (
    get_budget_status,
    get_category_summary,
    get_dashboard,
    get_spending_trend_response,
)

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/dashboard", response_model=ApiResponse[DashboardResponse])
def dashboard(
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    """
    Returns a full dashboard summary: current month income/expenses, expense
    breakdown by category, budget status, active savings goals, and the last
    6 months trend.
    """
    return success_response(get_dashboard(db, current_user))


@router.get("/budget-status", response_model=ApiResponse[list[BudgetStatusItem]])
def budget_status(
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    """Returns the current period's spending vs. budget limit for each category."""
    return success_response(get_budget_status(db, current_user))


@router.get("/spending-trend", response_model=ApiResponse[SpendingTrendResponse])
def spending_trend(
    months: int = Query(default=6, ge=1, le=24),
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    """Returns monthly income/expense totals for the last N months."""
    return success_response(
        get_spending_trend_response(db, current_user, months=months)
    )


@router.get("/category-summary", response_model=ApiResponse[CategorySummaryResponse])
def category_summary(
    type: TransactionType = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    current_user: User = Depends(requires_auth),
    db: Session = Depends(get_db),
):
    """Returns a per-category breakdown for the given transaction type and date range."""
    return success_response(get_category_summary(db, current_user, type, start, end))
