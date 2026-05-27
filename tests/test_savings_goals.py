"""Tests for savings goal CRUD endpoints."""

from datetime import date, timedelta
from app.models.savings_goal import SavingsGoal, SavingsGoalStatus


def _goal_payload(**overrides):
    base = {
        "name": "Emergency Fund",
        "target_amount": "1000.00",
        "current_amount": "0.00",
    }
    base.update(overrides)
    return base


class TestCreateSavingsGoal:
    def test_create_goal(self, client, auth_headers):
        resp = client.post("/savings-goals", json=_goal_payload(), headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "Emergency Fund"
        assert float(data["target_amount"]) == 1000.0
        assert data["status"] == "ACTIVE"

    def test_create_with_target_date(self, client, auth_headers):
        future = str(date.today() + timedelta(days=365))
        resp = client.post("/savings-goals", json=_goal_payload(target_date=future), headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["data"]["target_date"] == future

    def test_create_with_description(self, client, auth_headers):
        resp = client.post("/savings-goals", json=_goal_payload(description="For emergencies"), headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["data"]["description"] == "For emergencies"

    def test_create_requires_auth(self, client):
        resp = client.post("/savings-goals", json=_goal_payload())
        assert resp.status_code == 401

    def test_create_zero_target_rejected(self, client, auth_headers):
        resp = client.post("/savings-goals", json=_goal_payload(target_amount="0.00"), headers=auth_headers)
        assert resp.status_code == 422

    def test_create_negative_current_rejected(self, client, auth_headers):
        resp = client.post("/savings-goals", json=_goal_payload(current_amount="-1.00"), headers=auth_headers)
        assert resp.status_code == 422


class TestListSavingsGoals:
    def test_list_own_goals(self, client, regular_user, auth_headers, db):
        db.add(SavingsGoal(
            user_id=regular_user.id, name="Vacation", target_amount=2000, current_amount=0,
        ))
        db.commit()

        resp = client.get("/savings-goals", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_list_filter_by_status(self, client, regular_user, auth_headers, db):
        db.add(SavingsGoal(
            user_id=regular_user.id, name="Active Goal",
            target_amount=500, current_amount=0, status=SavingsGoalStatus.ACTIVE,
        ))
        db.add(SavingsGoal(
            user_id=regular_user.id, name="Completed Goal",
            target_amount=100, current_amount=100, status=SavingsGoalStatus.COMPLETED,
        ))
        db.commit()

        resp = client.get("/savings-goals?status=ACTIVE", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["status"] == "ACTIVE"

    def test_list_does_not_return_other_users_goals(self, client, admin_user, auth_headers, db):
        db.add(SavingsGoal(
            user_id=admin_user.id, name="Admin Goal", target_amount=999, current_amount=0,
        ))
        db.commit()

        resp = client.get("/savings-goals", headers=auth_headers)
        assert len(resp.json()["data"]) == 0


class TestGetSavingsGoal:
    def test_get_own_goal(self, client, regular_user, auth_headers, db):
        goal = SavingsGoal(
            user_id=regular_user.id, name="Car", target_amount=5000, current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        resp = client.get(f"/savings-goals/{goal.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == goal.id

    def test_get_other_users_goal_returns_404(self, client, admin_user, auth_headers, db):
        goal = SavingsGoal(
            user_id=admin_user.id, name="Admin Car", target_amount=5000, current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        resp = client.get(f"/savings-goals/{goal.id}", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateSavingsGoal:
    def test_update_name(self, client, regular_user, auth_headers, db):
        goal = SavingsGoal(
            user_id=regular_user.id, name="Old Name", target_amount=1000, current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        resp = client.patch(f"/savings-goals/{goal.id}", json={"name": "New Name"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New Name"

    def test_auto_complete_when_target_reached(self, client, regular_user, auth_headers, db):
        goal = SavingsGoal(
            user_id=regular_user.id, name="House", target_amount=1000, current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        resp = client.patch(f"/savings-goals/{goal.id}", json={"current_amount": "1000.00"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "COMPLETED"

    def test_auto_complete_when_exceeds_target(self, client, regular_user, auth_headers, db):
        goal = SavingsGoal(
            user_id=regular_user.id, name="House2", target_amount=1000, current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        resp = client.patch(f"/savings-goals/{goal.id}", json={"current_amount": "1500.00"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "COMPLETED"

    def test_manual_cancel(self, client, regular_user, auth_headers, db):
        goal = SavingsGoal(
            user_id=regular_user.id, name="Cancelled", target_amount=500, current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        resp = client.patch(f"/savings-goals/{goal.id}", json={"status": "CANCELLED"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "CANCELLED"


class TestDeleteSavingsGoal:
    def test_soft_delete(self, client, regular_user, auth_headers, db):
        goal = SavingsGoal(
            user_id=regular_user.id, name="Delete Me", target_amount=100, current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)

        resp = client.delete(f"/savings-goals/{goal.id}", headers=auth_headers)
        assert resp.status_code == 200

        list_resp = client.get("/savings-goals", headers=auth_headers)
        assert len(list_resp.json()["data"]) == 0
