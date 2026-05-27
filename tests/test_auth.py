"""Tests for authentication endpoints."""

import pytest
from app.models.user import User, UserStatus
from app.models.verification_code import VerificationCode, VerificationCodePurpose
from app.core.security import hash_password, create_refresh_token


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_success(self, client, seeded_roles):
        resp = client.post("/auth/register", json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "securepass1",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["is_error"] is False
        assert "Verification code sent" in body["data"]["message"]

    def test_register_duplicate_email(self, client, regular_user, seeded_roles):
        resp = client.post("/auth/register", json={
            "name": "Dup",
            "email": "user@example.com",
            "password": "securepass1",
        })
        assert resp.status_code == 409

    def test_register_invalid_email(self, client, seeded_roles):
        resp = client.post("/auth/register", json={
            "name": "Bad",
            "email": "not-an-email",
            "password": "securepass1",
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client, seeded_roles):
        resp = client.post("/auth/register", json={
            "name": "Short",
            "email": "short@example.com",
            "password": "abc",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_success(self, client, regular_user):
        resp = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, regular_user):
        resp = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client, seeded_roles):
        resp = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_pending_user(self, client, db, seeded_roles):
        from app.models.role import RoleKey
        user = User(
            name="Pending",
            email="pending@example.com",
            hashed_password=hash_password("password123"),
            status=UserStatus.PENDING,
            role_id=seeded_roles[RoleKey.USER].id,
        )
        db.add(user)
        db.commit()
        resp = client.post("/auth/login", json={
            "email": "pending@example.com",
            "password": "password123",
        })
        assert resp.status_code == 403

    def test_login_banned_user(self, client, db, seeded_roles):
        from app.models.role import RoleKey
        user = User(
            name="Banned",
            email="banned@example.com",
            hashed_password=hash_password("password123"),
            status=UserStatus.BANNED,
            role_id=seeded_roles[RoleKey.USER].id,
        )
        db.add(user)
        db.commit()
        resp = client.post("/auth/login", json={
            "email": "banned@example.com",
            "password": "password123",
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------

class TestMe:
    def test_me_returns_current_user(self, client, regular_user, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == "user@example.com"
        assert data["name"] == "Test User"

    def test_me_requires_auth(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------

class TestRefresh:
    def test_refresh_success(self, client, regular_user):
        refresh_token = create_refresh_token(subject=regular_user.id)
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    def test_refresh_invalid_token(self, client):
        resp = client.post("/auth/refresh", json={"refresh_token": "bad.token.here"})
        assert resp.status_code == 401

    def test_refresh_with_access_token_fails(self, client, user_token):
        # Access tokens must not be accepted as refresh tokens
        resp = client.post("/auth/refresh", json={"refresh_token": user_token})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_success(self, client, auth_headers):
        resp = client.post("/auth/logout", headers=auth_headers)
        assert resp.status_code == 200
        assert "Logged out" in resp.json()["data"]["message"]

    def test_logout_requires_auth(self, client):
        resp = client.post("/auth/logout")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

class TestEmailVerification:
    def test_verify_email_success(self, client, db, seeded_roles):
        from app.models.role import RoleKey
        from datetime import datetime, timedelta, timezone
        from app.core.security import hash_password as hp

        user = User(
            name="Unverified",
            email="unverified@example.com",
            hashed_password=hp("password123"),
            status=UserStatus.PENDING,
            role_id=seeded_roles[RoleKey.USER].id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        raw_code = "123456"
        vc = VerificationCode(
            user_id=user.id,
            email=user.email,
            code_hash=hp(raw_code),
            purpose=VerificationCodePurpose.EMAIL_VERIFICATION,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(vc)
        db.commit()

        resp = client.post("/auth/verify-email", json={
            "email": "unverified@example.com",
            "code": raw_code,
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    def test_verify_email_wrong_code(self, client, db, seeded_roles):
        from app.models.role import RoleKey
        from datetime import datetime, timedelta, timezone

        user = User(
            name="Unverified2",
            email="unverified2@example.com",
            hashed_password=hash_password("password123"),
            status=UserStatus.PENDING,
            role_id=seeded_roles[RoleKey.USER].id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        vc = VerificationCode(
            user_id=user.id,
            email=user.email,
            code_hash=hash_password("999999"),
            purpose=VerificationCodePurpose.EMAIL_VERIFICATION,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(vc)
        db.commit()

        resp = client.post("/auth/verify-email", json={
            "email": "unverified2@example.com",
            "code": "000000",
        })
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------

class TestPasswordReset:
    def test_forgot_password_unknown_email_returns_generic(self, client, seeded_roles):
        # Should not reveal whether email exists
        resp = client.post("/auth/forgot-password", json={"email": "ghost@example.com"})
        assert resp.status_code == 200
        assert "If the email exists" in resp.json()["data"]["message"]

    def test_reset_password_success(self, client, db, regular_user):
        from datetime import datetime, timedelta, timezone

        raw_code = "654321"
        vc = VerificationCode(
            user_id=regular_user.id,
            email=regular_user.email,
            code_hash=hash_password(raw_code),
            purpose=VerificationCodePurpose.PASSWORD_RESET,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(vc)
        db.commit()

        resp = client.post("/auth/reset-password", json={
            "email": "user@example.com",
            "code": raw_code,
            "new_password": "newpassword123",
        })
        assert resp.status_code == 200
        assert "reset successfully" in resp.json()["data"]["message"]

        # Old password should no longer work
        login = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "password123",
        })
        assert login.status_code == 401

        # New password should work
        login2 = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "newpassword123",
        })
        assert login2.status_code == 200
