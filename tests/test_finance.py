"""Tests for finance analytics endpoints."""

from datetime import date
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.models.budget import Budget, BudgetPeriod
from app.models.savings_goal import SavingsGoal, SavingsGoalStatus


class TestDashboard:
    def test_dashboard_empty(self, client, auth_headers):
        resp = client.get("/finance/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert float(data["current_month_income"]) == 0.0
        assert float(data["current_month_expenses"]) == 0.0
        assert float(data["current_month_net"]) == 0.0
        assert data["expense_breakdown"] == []
        assert data["budget_status"] == []
        assert data["active_savings_goals"] == []
        assert len(data["monthly_trend"]) == 6

    def test_dashboard_with_transactions(self, client, regular_user, auth_headers, db):
        today = date.today()
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.INCOME,
            category=TransactionCategory.SALARY, amount=3000, date=today,
        ))
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=200, date=today,
        ))
        db.commit()

        resp = client.get("/finance/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert float(data["current_month_income"]) == 3000.0
        assert float(data["current_month_expenses"]) == 200.0
        assert float(data["current_month_net"]) == 2800.0

    def test_dashboard_expense_breakdown(self, client, regular_user, auth_headers, db):
        today = date.today()
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=300, date=today,
        ))
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.TRANSPORT, amount=100, date=today,
        ))
        db.commit()

        resp = client.get("/finance/dashboard", headers=auth_headers)
        breakdown = resp.json()["data"]["expense_breakdown"]
        categories = [b["category"] for b in breakdown]
        assert "FOOD" in categories
        assert "TRANSPORT" in categories
        # FOOD should be first (highest amount)
        assert breakdown[0]["category"] == "FOOD"

    def test_dashboard_includes_active_savings_goals(self, client, regular_user, auth_headers, db):
        db.add(SavingsGoal(
            user_id=regular_user.id, name="Vacation",
            target_amount=2000, current_amount=500, status=SavingsGoalStatus.ACTIVE,
        ))
        db.commit()

        resp = client.get("/finance/dashboard", headers=auth_headers)
        goals = resp.json()["data"]["active_savings_goals"]
        assert len(goals) == 1
        assert goals[0]["name"] == "Vacation"

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/finance/dashboard")
        assert resp.status_code == 401


class TestBudgetStatus:
    def test_budget_status_empty(self, client, auth_headers):
        resp = client.get("/finance/budget-status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_budget_status_with_spending(self, client, regular_user, auth_headers, db):
        today = date.today()
        db.add(Budget(
            user_id=regular_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=500,
        ))
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=200, date=today,
        ))
        db.commit()

        resp = client.get("/finance/budget-status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        item = data[0]
        assert float(item["spent"]) == 200.0
        assert float(item["remaining"]) == 300.0
        assert item["percent_used"] == 40.0

    def test_budget_status_requires_auth(self, client):
        resp = client.get("/finance/budget-status")
        assert resp.status_code == 401


class TestSpendingTrend:
    def test_spending_trend_default_6_months(self, client, auth_headers):
        resp = client.get("/finance/spending-trend", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]["months"]) == 6

    def test_spending_trend_custom_months(self, client, auth_headers):
        resp = client.get("/finance/spending-trend?months=3", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]["months"]) == 3

    def test_spending_trend_max_24_months(self, client, auth_headers):
        resp = client.get("/finance/spending-trend?months=24", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]["months"]) == 24

    def test_spending_trend_over_limit_rejected(self, client, auth_headers):
        resp = client.get("/finance/spending-trend?months=25", headers=auth_headers)
        assert resp.status_code == 422

    def test_spending_trend_requires_auth(self, client):
        resp = client.get("/finance/spending-trend")
        assert resp.status_code == 401


class TestCategorySummary:
    def test_category_summary_expenses(self, client, regular_user, auth_headers, db):
        today = date.today()
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=150, date=today,
        ))
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=50, date=today,
        ))
        db.commit()

        start = str(today.replace(day=1))
        resp = client.get(
            f"/finance/category-summary?type=EXPENSE&start={start}&end={today}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert float(data["total"]) == 200.0
        assert data["breakdown"][0]["category"] == "FOOD"
        assert data["breakdown"][0]["count"] == 2

    def test_category_summary_requires_auth(self, client):
        today = date.today()
        resp = client.get(
            f"/finance/category-summary?type=EXPENSE&start={today}&end={today}"
        )
        assert resp.status_code == 401

    def test_category_summary_missing_params(self, client, auth_headers):
        resp = client.get("/finance/category-summary?type=EXPENSE", headers=auth_headers)
        assert resp.status_code == 422
