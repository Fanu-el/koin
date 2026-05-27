"""
Finance analytics service.

Provides dashboard data, budget status checks, and spending summaries.
Also exposes plain-Python functions used by the LangChain agent tools so
the agent can fetch real user data during a conversation.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetPeriod
from app.models.savings_goal import SavingsGoal, SavingsGoalStatus
from app.models.transaction import Transaction, TransactionCategory, TransactionType
from app.models.user import User
from app.schemas.budget import BudgetPublic, BudgetStatusItem
from app.schemas.finance import (
    CategoryBreakdownItem,
    CategorySummaryResponse,
    DashboardResponse,
    MonthlyTrendItem,
    SpendingTrendResponse,
)
from app.schemas.savings_goal import SavingsGoalPublic

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def get_dashboard(db: Session, user: User) -> DashboardResponse:
    today = date.today()
    month_start = today.replace(day=1)

    income = _sum_transactions(db, user.id, TransactionType.INCOME, month_start, today)
    expenses = _sum_transactions(
        db, user.id, TransactionType.EXPENSE, month_start, today
    )

    expense_breakdown = get_expense_breakdown(db, user.id, month_start, today)
    budget_status = get_budget_status(db, user)
    active_goals = (
        db.query(SavingsGoal)
        .filter(
            SavingsGoal.user_id == user.id,
            SavingsGoal.status == SavingsGoalStatus.ACTIVE,
            SavingsGoal.deleted_at.is_(None),
        )
        .order_by(SavingsGoal.created_at.desc())
        .all()
    )
    monthly_trend = get_monthly_trend(db, user.id, months=6)

    return DashboardResponse(
        current_month_income=income,
        current_month_expenses=expenses,
        current_month_net=income - expenses,
        expense_breakdown=expense_breakdown,
        budget_status=budget_status,
        active_savings_goals=[
            SavingsGoalPublic.model_validate(g) for g in active_goals
        ],
        monthly_trend=monthly_trend,
    )


# ---------------------------------------------------------------------------
# Budget status
# ---------------------------------------------------------------------------


def get_budget_status(db: Session, user: User) -> list[BudgetStatusItem]:
    today = date.today()
    budgets = (
        db.query(Budget)
        .filter(Budget.user_id == user.id, Budget.deleted_at.is_(None))
        .all()
    )
    items: list[BudgetStatusItem] = []
    for budget in budgets:
        period_start, period_end = _period_range(today, budget.period)
        spent = _sum_transactions(
            db,
            user.id,
            TransactionType.EXPENSE,
            period_start,
            period_end,
            category=budget.category,
        )
        limit = Decimal(str(budget.amount_limit))
        remaining = max(Decimal("0"), limit - spent)
        percent_used = float(spent / limit * 100) if limit > 0 else 0.0
        items.append(
            BudgetStatusItem(
                budget=BudgetPublic.model_validate(budget),
                spent=spent,
                remaining=remaining,
                percent_used=round(percent_used, 1),
            )
        )
    return items


# ---------------------------------------------------------------------------
# Spending trend
# ---------------------------------------------------------------------------


def get_monthly_trend(
    db: Session, user_id: str, months: int = 6
) -> list[MonthlyTrendItem]:
    today = date.today()
    result: list[MonthlyTrendItem] = []
    for i in range(months - 1, -1, -1):
        # Walk backwards by month
        month_date = _subtract_months(today, i)
        m_start = month_date.replace(day=1)
        m_end = _month_end(m_start)
        income = _sum_transactions(db, user_id, TransactionType.INCOME, m_start, m_end)
        expenses = _sum_transactions(
            db, user_id, TransactionType.EXPENSE, m_start, m_end
        )
        result.append(
            MonthlyTrendItem(
                year=m_start.year,
                month=m_start.month,
                income=income,
                expenses=expenses,
                net=income - expenses,
            )
        )
    return result


def get_spending_trend_response(
    db: Session, user: User, months: int = 6
) -> SpendingTrendResponse:
    return SpendingTrendResponse(months=get_monthly_trend(db, user.id, months=months))


# ---------------------------------------------------------------------------
# Category breakdown
# ---------------------------------------------------------------------------


def get_expense_breakdown(
    db: Session,
    user_id: str,
    start: date,
    end: date,
) -> list[CategoryBreakdownItem]:
    rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.deleted_at.is_(None),
        )
        .group_by(Transaction.category)
        .all()
    )
    grand_total = sum(Decimal(str(r.total)) for r in rows) or Decimal("1")
    return [
        CategoryBreakdownItem(
            category=r.category,
            total=Decimal(str(r.total)),
            count=r.count,
            percent=round(float(Decimal(str(r.total)) / grand_total * 100), 1),
        )
        for r in sorted(rows, key=lambda x: x.total, reverse=True)
    ]


def get_category_summary(
    db: Session,
    user: User,
    transaction_type: TransactionType,
    start: date,
    end: date,
) -> CategorySummaryResponse:
    breakdown = (
        get_expense_breakdown(db, user.id, start, end)
        if transaction_type == TransactionType.EXPENSE
        else _get_income_breakdown(db, user.id, start, end)
    )
    total = sum(item.total for item in breakdown)
    return CategorySummaryResponse(
        type=transaction_type, breakdown=breakdown, total=total
    )


# ---------------------------------------------------------------------------
# Agent-friendly plain-string helpers (called from agent tools)
# ---------------------------------------------------------------------------


def agent_get_expense_summary(
    db: Session, user_id: str, period: str = "current_month"
) -> str:
    """Return a human-readable expense summary for the given period keyword."""
    start, end = _resolve_period(period)
    rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.deleted_at.is_(None),
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    if not rows:
        return f"No expenses recorded for {period.replace('_', ' ')}."

    grand_total = sum(Decimal(str(r.total)) for r in rows)
    lines = [f"Expenses for {period.replace('_', ' ')} (total: {grand_total:.2f}):"]
    for r in rows:
        lines.append(f"  {r.category}: {Decimal(str(r.total)):.2f}")
    return "\n".join(lines)


def agent_get_income_summary(
    db: Session, user_id: str, period: str = "current_month"
) -> str:
    """Return a human-readable income summary for the given period keyword."""
    start, end = _resolve_period(period)
    total = _sum_transactions(db, user_id, TransactionType.INCOME, start, end)
    if total == 0:
        return f"No income recorded for {period.replace('_', ' ')}."
    return f"Total income for {period.replace('_', ' ')}: {total:.2f}"


def agent_get_budget_status(db: Session, user_id: str) -> str:
    """Return a human-readable budget status for the current period."""
    today = date.today()
    budgets = (
        db.query(Budget)
        .filter(Budget.user_id == user_id, Budget.deleted_at.is_(None))
        .all()
    )
    if not budgets:
        return "No budgets set up yet."

    lines = ["Budget status:"]
    for budget in budgets:
        period_start, period_end = _period_range(today, budget.period)
        spent = _sum_transactions(
            db,
            user_id,
            TransactionType.EXPENSE,
            period_start,
            period_end,
            category=budget.category,
        )
        limit = Decimal(str(budget.amount_limit))
        remaining = max(Decimal("0"), limit - spent)
        pct = round(float(spent / limit * 100), 1) if limit > 0 else 0.0
        status_emoji = "✅" if pct < 80 else ("⚠️" if pct < 100 else "🚨")
        lines.append(
            f"  {status_emoji} {budget.category} ({budget.period.lower()}): "
            f"{spent:.2f} / {limit:.2f} ({pct}% used, {remaining:.2f} remaining)"
        )
    return "\n".join(lines)


def agent_get_savings_goals(db: Session, user_id: str) -> str:
    """Return a human-readable summary of active savings goals."""
    goals = (
        db.query(SavingsGoal)
        .filter(
            SavingsGoal.user_id == user_id,
            SavingsGoal.status == SavingsGoalStatus.ACTIVE,
            SavingsGoal.deleted_at.is_(None),
        )
        .all()
    )
    if not goals:
        return "No active savings goals."

    lines = ["Active savings goals:"]
    for goal in goals:
        target = Decimal(str(goal.target_amount))
        current = Decimal(str(goal.current_amount))
        pct = round(float(current / target * 100), 1) if target > 0 else 0.0
        due = f", target date: {goal.target_date}" if goal.target_date else ""
        lines.append(f"  {goal.name}: {current:.2f} / {target:.2f} ({pct}%){due}")
    return "\n".join(lines)


def agent_get_spending_trend(db: Session, user_id: str, months: int = 3) -> str:
    """Return a human-readable spending trend for the last N months."""
    trend = get_monthly_trend(db, user_id, months=months)
    if not trend:
        return "No transaction data available."
    lines = [f"Spending trend (last {months} months):"]
    for item in trend:
        lines.append(
            f"  {item.year}-{item.month:02d}: income {item.income:.2f}, "
            f"expenses {item.expenses:.2f}, net {item.net:.2f}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _sum_transactions(
    db: Session,
    user_id: str,
    txn_type: TransactionType,
    start: date,
    end: date,
    category: TransactionCategory | None = None,
) -> Decimal:
    query = db.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == txn_type,
        Transaction.date >= start,
        Transaction.date <= end,
        Transaction.deleted_at.is_(None),
    )
    if category:
        query = query.filter(Transaction.category == category)
    result = query.scalar()
    return Decimal(str(result)) if result else Decimal("0")


def _get_income_breakdown(
    db: Session,
    user_id: str,
    start: date,
    end: date,
) -> list[CategoryBreakdownItem]:
    rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.INCOME,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.deleted_at.is_(None),
        )
        .group_by(Transaction.category)
        .all()
    )
    grand_total = sum(Decimal(str(r.total)) for r in rows) or Decimal("1")
    return [
        CategoryBreakdownItem(
            category=r.category,
            total=Decimal(str(r.total)),
            count=r.count,
            percent=round(float(Decimal(str(r.total)) / grand_total * 100), 1),
        )
        for r in sorted(rows, key=lambda x: x.total, reverse=True)
    ]


def _period_range(today: date, period: BudgetPeriod) -> tuple[date, date]:
    if period == BudgetPeriod.MONTHLY:
        return today.replace(day=1), _month_end(today.replace(day=1))
    # Weekly: Monday to Sunday
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def _resolve_period(period: str) -> tuple[date, date]:
    today = date.today()
    if period == "current_month":
        return today.replace(day=1), today
    if period == "last_month":
        first_of_current = today.replace(day=1)
        last_month_end = first_of_current - timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    if period == "current_week":
        monday = today - timedelta(days=today.weekday())
        return monday, today
    if period == "last_30_days":
        return today - timedelta(days=30), today
    if period == "last_90_days":
        return today - timedelta(days=90), today
    if period == "this_year":
        return today.replace(month=1, day=1), today
    # Default to current month
    return today.replace(day=1), today


def _subtract_months(d: date, months: int) -> date:
    month = d.month - months
    year = d.year
    while month <= 0:
        month += 12
        year -= 1
    # Clamp day to valid range for the target month
    max_day = calendar.monthrange(year, month)[1]
    return d.replace(year=year, month=month, day=min(d.day, max_day))


def _month_end(first_of_month: date) -> date:
    last_day = calendar.monthrange(first_of_month.year, first_of_month.month)[1]
    return first_of_month.replace(day=last_day)
