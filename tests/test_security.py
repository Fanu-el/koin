"""Tests for security utilities (JWT, password hashing)."""

import time
import pytest
from fastapi import HTTPException
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from datetime import timedelta


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "mysecretpassword"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_hashes_are_unique(self):
        pw = "samepassword"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2  # Different salts

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_invalid_hash_format_returns_false(self):
        assert verify_password("anything", "not-a-valid-hash") is False


class TestJWT:
    def test_access_token_roundtrip(self):
        token = create_access_token(subject="user-123")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        token = create_refresh_token(subject="user-456")
        payload = decode_refresh_token(token)
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self):
        token = create_access_token(subject="user-123")
        with pytest.raises(HTTPException) as exc_info:
            decode_refresh_token(token)
        assert exc_info.value.status_code == 401

    def test_refresh_token_rejected_as_access(self):
        token = create_refresh_token(subject="user-123")
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        token = create_access_token(subject="user-123", expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = create_access_token(subject="user-123")
        parts = token.split(".")
        # Flip a character in the payload
        tampered = parts[0] + "." + parts[1][:-1] + "X" + "." + parts[2]
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(tampered)
        assert exc_info.value.status_code == 401

    def test_garbage_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not.a.token")
        assert exc_info.value.status_code == 401
