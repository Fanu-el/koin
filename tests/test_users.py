"""Tests for user management endpoints."""

from app.models.user import User, UserStatus
from app.core.security import hash_password


class TestUpdateProfile:
    def test_update_name(self, client, regular_user, auth_headers):
        resp = client.patch("/users/update-profile", json={"name": "New Name"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New Name"

    def test_update_name_too_short(self, client, auth_headers):
        resp = client.patch("/users/update-profile", json={"name": ""}, headers=auth_headers)
        assert resp.status_code == 422

    def test_update_profile_requires_auth(self, client):
        resp = client.patch("/users/update-profile", json={"name": "X"})
        assert resp.status_code == 401


class TestDeleteAccount:
    def test_delete_own_account(self, client, regular_user, auth_headers, db):
        resp = client.delete("/users/me", headers=auth_headers)
        assert resp.status_code == 200

        db.refresh(regular_user)
        assert regular_user.status == UserStatus.DELETED
        assert regular_user.deleted_at is not None

    def test_delete_account_requires_auth(self, client):
        resp = client.delete("/users/me")
        assert resp.status_code == 401


class TestListUsers:
    def test_list_users_as_admin(self, client, regular_user, admin_headers):
        resp = client.get("/users", headers=admin_headers)
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()["data"]]
        assert "user@example.com" in emails

    def test_list_users_forbidden_for_regular_user(self, client, auth_headers):
        resp = client.get("/users", headers=auth_headers)
        assert resp.status_code == 403

    def test_list_users_requires_auth(self, client):
        resp = client.get("/users")
        assert resp.status_code == 401


class TestBanUnban:
    def test_ban_user(self, client, regular_user, admin_headers, db):
        resp = client.patch(f"/users/{regular_user.id}/ban", headers=admin_headers)
        assert resp.status_code == 200
        db.refresh(regular_user)
        assert regular_user.status == UserStatus.BANNED

    def test_unban_user(self, client, regular_user, admin_headers, db):
        regular_user.status = UserStatus.BANNED
        db.commit()

        resp = client.patch(f"/users/{regular_user.id}/unban", headers=admin_headers)
        assert resp.status_code == 200
        db.refresh(regular_user)
        assert regular_user.status == UserStatus.ACTIVE

    def test_ban_requires_admin(self, client, regular_user, auth_headers):
        resp = client.patch(f"/users/{regular_user.id}/ban", headers=auth_headers)
        assert resp.status_code == 403

    def test_ban_nonexistent_user(self, client, admin_headers):
        resp = client.patch("/users/00000000-0000-0000-0000-000000000000/ban", headers=admin_headers)
        assert resp.status_code == 404

    def test_cannot_ban_super_admin(self, client, admin_user, admin_headers):
        resp = client.patch(f"/users/{admin_user.id}/ban", headers=admin_headers)
        assert resp.status_code == 403
