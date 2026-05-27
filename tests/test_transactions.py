"""Tests for transaction CRUD endpoints."""

import pytest
from datetime import date
from app.models.transaction import Transaction, TransactionType, TransactionCategory


def _txn_payload(**overrides):
    base = {
        "type": "EXPENSE",
        "category": "FOOD",
        "amount": "50.00",
        "date": str(date.today()),
    }
    base.update(overrides)
    return base


class TestCreateTransaction:
    def test_create_expense(self, client, auth_headers):
        resp = client.post("/transactions", json=_txn_payload(), headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["type"] == "EXPENSE"
        assert data["category"] == "FOOD"
        assert float(data["amount"]) == 50.0

    def test_create_income(self, client, auth_headers):
        resp = client.post("/transactions", json=_txn_payload(
            type="INCOME", category="SALARY", amount="3000.00"
        ), headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["data"]["type"] == "INCOME"

    def test_create_with_description_and_note(self, client, auth_headers):
        resp = client.post("/transactions", json=_txn_payload(
            description="Lunch", note="With colleagues"
        ), headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["description"] == "Lunch"
        assert data["note"] == "With colleagues"

    def test_create_requires_auth(self, client):
        resp = client.post("/transactions", json=_txn_payload())
        assert resp.status_code == 401

    def test_create_negative_amount_rejected(self, client, auth_headers):
        resp = client.post("/transactions", json=_txn_payload(amount="-10.00"), headers=auth_headers)
        assert resp.status_code == 422

    def test_create_zero_amount_rejected(self, client, auth_headers):
        resp = client.post("/transactions", json=_txn_payload(amount="0.00"), headers=auth_headers)
        assert resp.status_code == 422

    def test_create_invalid_category_rejected(self, client, auth_headers):
        resp = client.post("/transactions", json=_txn_payload(category="INVALID"), headers=auth_headers)
        assert resp.status_code == 422


class TestListTransactions:
    def test_list_returns_own_transactions(self, client, regular_user, auth_headers, db):
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=10, date=date.today(),
        ))
        db.commit()

        resp = client.get("/transactions", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_list_filter_by_type(self, client, regular_user, auth_headers, db):
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=10, date=date.today(),
        ))
        db.add(Transaction(
            user_id=regular_user.id, type=TransactionType.INCOME,
            category=TransactionCategory.SALARY, amount=1000, date=date.today(),
        ))
        db.commit()

        resp = client.get("/transactions?type=EXPENSE", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["type"] == "EXPENSE"

    def test_list_pagination(self, client, regular_user, auth_headers, db):
        for i in range(5):
            db.add(Transaction(
                user_id=regular_user.id, type=TransactionType.EXPENSE,
                category=TransactionCategory.FOOD, amount=i + 1, date=date.today(),
            ))
        db.commit()

        resp = client.get("/transactions?limit=2&offset=0", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

        resp2 = client.get("/transactions?limit=2&offset=2", headers=auth_headers)
        assert len(resp2.json()["data"]) == 2

    def test_list_does_not_return_other_users_transactions(self, client, regular_user, admin_user, auth_headers, db):
        db.add(Transaction(
            user_id=admin_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=99, date=date.today(),
        ))
        db.commit()

        resp = client.get("/transactions", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 0

    def test_list_requires_auth(self, client):
        resp = client.get("/transactions")
        assert resp.status_code == 401


class TestGetTransaction:
    def test_get_own_transaction(self, client, regular_user, auth_headers, db):
        txn = Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=25, date=date.today(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        resp = client.get(f"/transactions/{txn.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == txn.id

    def test_get_other_users_transaction_returns_404(self, client, admin_user, auth_headers, db):
        txn = Transaction(
            user_id=admin_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=25, date=date.today(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        resp = client.get(f"/transactions/{txn.id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_nonexistent_returns_404(self, client, auth_headers):
        resp = client.get("/transactions/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateTransaction:
    def test_update_amount(self, client, regular_user, auth_headers, db):
        txn = Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=10, date=date.today(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        resp = client.patch(f"/transactions/{txn.id}", json={"amount": "99.99"}, headers=auth_headers)
        assert resp.status_code == 200
        assert float(resp.json()["data"]["amount"]) == 99.99

    def test_update_category(self, client, regular_user, auth_headers, db):
        txn = Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=10, date=date.today(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        resp = client.patch(f"/transactions/{txn.id}", json={"category": "TRANSPORT"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["category"] == "TRANSPORT"


class TestDeleteTransaction:
    def test_soft_delete(self, client, regular_user, auth_headers, db):
        txn = Transaction(
            user_id=regular_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=10, date=date.today(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        resp = client.delete(f"/transactions/{txn.id}", headers=auth_headers)
        assert resp.status_code == 200

        # Should no longer appear in list
        list_resp = client.get("/transactions", headers=auth_headers)
        ids = [t["id"] for t in list_resp.json()["data"]]
        assert txn.id not in ids

    def test_delete_other_users_transaction_returns_404(self, client, admin_user, auth_headers, db):
        txn = Transaction(
            user_id=admin_user.id, type=TransactionType.EXPENSE,
            category=TransactionCategory.FOOD, amount=10, date=date.today(),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        resp = client.delete(f"/transactions/{txn.id}", headers=auth_headers)
        assert resp.status_code == 404
