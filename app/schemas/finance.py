from decimal import Decimal

from pydantic import BaseModel

from app.models.transaction import TransactionCategory, TransactionType
from app.schemas.budget import BudgetStatusItem
from app.schemas.savings_goal import SavingsGoalPublic


class CategoryBreakdownItem(BaseModel):
    category: TransactionCategory
    total: Decimal
    count: int
    percent: float


class MonthlyTrendItem(BaseModel):
    year: int
    month: int
    income: Decimal
    expenses: Decimal
    net: Decimal


class DashboardResponse(BaseModel):
    """Top-level summary for the mobile dashboard."""

    current_month_income: Decimal
    current_month_expenses: Decimal
    current_month_net: Decimal
    expense_breakdown: list[CategoryBreakdownItem]
    budget_status: list[BudgetStatusItem]
    active_savings_goals: list[SavingsGoalPublic]
    monthly_trend: list[MonthlyTrendItem]


class SpendingTrendResponse(BaseModel):
    months: list[MonthlyTrendItem]


class CategorySummaryResponse(BaseModel):
    type: TransactionType
    breakdown: list[CategoryBreakdownItem]
    total: Decimal


class AdminFinanceAnalyticsResponse(BaseModel):
    total_users: int
    total_transactions: int
    total_income_logged: Decimal
    total_expenses_logged: Decimal
    total_budgets: int
    total_savings_goals: int
