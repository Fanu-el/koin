"""Tests for admin endpoints."""

from datetime import date
from app.models.chat import ChatSession, ChatMessage, ChatMessageRole, ChatMessageStatus
from app.models.transaction import Transaction, TransactionType, TransactionCategory
from app.models.budget import Budget, BudgetPeriod
from app.models.savings_goal import SavingsGoal


class TestAdminAnalytics:
    def test_analytics_returns_counts(self, client, regular_user, admin_headers, db):
        db.add(ChatSession(user_id=regular_user.id, title="Chat"))
        db.commit()

        resp = client.get("/admin/analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_chat_sessions" in data
        assert "total_messages" in data
        assert "active_users" in data
        assert "failed_ai_calls" in data
        assert "total_transactions" in data
        assert "total_budgets" in data
        assert "total_savings_goals" in data
        assert data["total_chat_sessions"] >= 1

    def test_analytics_requires_admin(self, client, auth_headers):
        resp = client.get("/admin/analytics", headers=auth_headers)
        assert resp.status_code == 403

    def test_analytics_requires_auth(self, client):
        resp = client.get("/admin/analytics")
        assert resp.status_code == 401


class TestAdminFinanceAnalytics:
    def test_finance_analytics_empty(self, client, admin_headers):
        resp = client.get("/admin/finance-analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_transactions"] == 0
        assert float(data["total_income_logged"]) == 0.0
        assert float(data["total_expenses_logged"]) == 0.0

    def test_finance_analytics_with_data(self, client, regular_user, admin_headers, db):
        today = date.today()
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.INCOME,
            category=TransactionCategory.SALARY, amount=5000, date=today,
        ))
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=300, date=today,
        ))
        db.commit()

        resp = client.get("/admin/finance-analytics", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_transactions"] == 2
        assert float(data["total_income_logged"]) == 5000.0
        assert float(data["total_expenses_logged"]) == 300.0

    def test_finance_analytics_requires_admin(self, client, auth_headers):
        resp = client.get("/admin/finance-analytics", headers=auth_headers)
        assert resp.status_code == 403


class TestAdminChats:
    def test_list_all_chats(self, client, regular_user, admin_user, admin_headers, db):
        db.add(ChatSession(user_id=regular_user.id, title="User Chat"))
        db.add(ChatSession(user_id=admin_user.id, title="Admin Chat"))
        db.commit()

        resp = client.get("/admin/chats", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    def test_get_chat_session(self, client, regular_user, admin_headers, db):
        session = ChatSession(user_id=regular_user.id, title="Test Chat")
        db.add(session)
        db.commit()
        db.refresh(session)

        resp = client.get(f"/admin/chats/{session.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == session.id

    def test_get_nonexistent_chat_returns_404(self, client, admin_headers):
        resp = client.get("/admin/chats/00000000-0000-0000-0000-000000000000", headers=admin_headers)
        assert resp.status_code == 404

    def test_list_chats_requires_admin(self, client, auth_headers):
        resp = client.get("/admin/chats", headers=auth_headers)
        assert resp.status_code == 403


class TestAdminEmails:
    def test_list_emails_empty(self, client, admin_headers):
        resp = client.get("/admin/emails", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_emails_requires_admin(self, client, auth_headers):
        resp = client.get("/admin/emails", headers=auth_headers)
        assert resp.status_code == 403

    def test_get_nonexistent_email_returns_404(self, client, admin_headers):
        resp = client.get("/admin/emails/00000000-0000-0000-0000-000000000000", headers=admin_headers)
        assert resp.status_code == 404


class TestAdminVerificationCodes:
    def test_list_verification_codes_empty(self, client, admin_headers):
        resp = client.get("/admin/verification-codes", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_verification_codes_requires_admin(self, client, auth_headers):
        resp = client.get("/admin/verification-codes", headers=auth_headers)
        assert resp.status_code == 403
