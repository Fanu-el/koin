"""Tests for budget CRUD endpoints."""

from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import TransactionCategory


def _budget_payload(**overrides):
    base = {
        "category": "FOOD",
        "period": "MONTHLY",
        "amount_limit": "500.00",
    }
    base.update(overrides)
    return base


class TestCreateBudget:
    def test_create_budget(self, client, auth_headers):
        resp = client.post("/budgets", json=_budget_payload(), headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["category"] == "FOOD"
        assert data["period"] == "MONTHLY"
        assert float(data["amount_limit"]) == 500.0

    def test_create_weekly_budget(self, client, auth_headers):
        resp = client.post("/budgets", json=_budget_payload(period="WEEKLY", amount_limit="100.00"), headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["data"]["period"] == "WEEKLY"

    def test_duplicate_budget_rejected(self, client, auth_headers):
        client.post("/budgets", json=_budget_payload(), headers=auth_headers)
        resp = client.post("/budgets", json=_budget_payload(), headers=auth_headers)
        assert resp.status_code == 409

    def test_same_category_different_period_allowed(self, client, auth_headers):
        client.post("/budgets", json=_budget_payload(period="MONTHLY"), headers=auth_headers)
        resp = client.post("/budgets", json=_budget_payload(period="WEEKLY"), headers=auth_headers)
        assert resp.status_code == 201

    def test_create_requires_auth(self, client):
        resp = client.post("/budgets", json=_budget_payload())
        assert resp.status_code == 401

    def test_create_zero_limit_rejected(self, client, auth_headers):
        resp = client.post("/budgets", json=_budget_payload(amount_limit="0.00"), headers=auth_headers)
        assert resp.status_code == 422

    def test_create_invalid_category_rejected(self, client, auth_headers):
        resp = client.post("/budgets", json=_budget_payload(category="INVALID"), headers=auth_headers)
        assert resp.status_code == 422


class TestListBudgets:
    def test_list_own_budgets(self, client, regular_user, auth_headers, db):
        db.add(Budget(
            user_id=regular_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=300,
        ))
        db.commit()

        resp = client.get("/budgets", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_list_does_not_return_other_users_budgets(self, client, admin_user, auth_headers, db):
        db.add(Budget(
            user_id=admin_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=300,
        ))
        db.commit()

        resp = client.get("/budgets", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 0


class TestGetBudget:
    def test_get_own_budget(self, client, regular_user, auth_headers, db):
        budget = Budget(
            user_id=regular_user.id,
            category=TransactionCategory.TRANSPORT,
            period=BudgetPeriod.MONTHLY,
            amount_limit=200,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        resp = client.get(f"/budgets/{budget.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == budget.id

    def test_get_other_users_budget_returns_404(self, client, admin_user, auth_headers, db):
        budget = Budget(
            user_id=admin_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=200,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        resp = client.get(f"/budgets/{budget.id}", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateBudget:
    def test_update_amount_limit(self, client, regular_user, auth_headers, db):
        budget = Budget(
            user_id=regular_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=100,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        resp = client.patch(f"/budgets/{budget.id}", json={"amount_limit": "750.00"}, headers=auth_headers)
        assert resp.status_code == 200
        assert float(resp.json()["data"]["amount_limit"]) == 750.0

    def test_update_zero_limit_rejected(self, client, regular_user, auth_headers, db):
        budget = Budget(
            user_id=regular_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=100,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        resp = client.patch(f"/budgets/{budget.id}", json={"amount_limit": "0.00"}, headers=auth_headers)
        assert resp.status_code == 422


class TestDeleteBudget:
    def test_soft_delete(self, client, regular_user, auth_headers, db):
        budget = Budget(
            user_id=regular_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=100,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        resp = client.delete(f"/budgets/{budget.id}", headers=auth_headers)
        assert resp.status_code == 200

        list_resp = client.get("/budgets", headers=auth_headers)
        assert len(list_resp.json()["data"]) == 0

    def test_deleted_budget_allows_recreating_same_category_period(self, client, regular_user, auth_headers, db):
        # After deleting, the same category+period combo should be creatable again
        budget = Budget(
            user_id=regular_user.id,
            category=TransactionCategory.FOOD,
            period=BudgetPeriod.MONTHLY,
            amount_limit=100,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

        client.delete(f"/budgets/{budget.id}", headers=auth_headers)

        resp = client.post("/budgets", json=_budget_payload(), headers=auth_headers)
        assert resp.status_code == 201
