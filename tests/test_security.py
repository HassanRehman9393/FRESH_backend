"""
TC-BE-01 … TC-BE-10  — Security layer: password hashing & JWT
"""
import pytest
import time
import uuid
from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    create_user_token,
)


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_returns_string(self):
        """TC-BE-01: hash_password returns a non-empty string."""
        h = hash_password("mysecret")
        assert isinstance(h, str) and len(h) > 0

    def test_hash_is_different_each_call(self):
        """TC-BE-02: bcrypt salts produce unique hashes for same input."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_verify_correct_password(self):
        """TC-BE-03: verify_password returns True for correct plain-text."""
        pw = "correct_password"
        h = hash_password(pw)
        assert verify_password(pw, h) is True

    def test_verify_wrong_password(self):
        """TC-BE-04: verify_password returns False for wrong plain-text."""
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_verify_empty_password_fails(self):
        """TC-BE-05: Empty string does not match a real password hash."""
        h = hash_password("realpassword")
        assert verify_password("", h) is False

    def test_long_password_handled(self):
        """TC-BE-06: Passwords > 72 bytes are truncated (bcrypt limit) consistently."""
        long_pw = "a" * 80
        h = hash_password(long_pw)
        # bcrypt truncates at 72 bytes, so the same first 72 chars must verify
        assert verify_password(long_pw, h) is True


# ── JWT tokens ────────────────────────────────────────────────────────────────

class TestJWT:
    def test_create_access_token_structure(self):
        """TC-BE-07: create_access_token returns a three-part JWT string."""
        token = create_access_token({"sub": "user-id"})
        assert token.count(".") == 2

    def test_verify_valid_token(self):
        """TC-BE-08: Valid token decodes and contains expected claims."""
        uid = str(uuid.uuid4())
        token = create_user_token(uid, "test@example.com", "farmer")
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == uid
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "farmer"

    def test_verify_tampered_token_returns_none(self):
        """TC-BE-09: Tampered signature returns None."""
        token = create_user_token(str(uuid.uuid4()), "x@x.com", "farmer")
        tampered = token[:-5] + "AAAAA"
        assert verify_token(tampered) is None

    def test_verify_expired_token_returns_none(self):
        """TC-BE-10: Expired token returns None."""
        from datetime import timedelta
        token = create_access_token({"sub": "uid"}, expires_delta=timedelta(seconds=-1))
        assert verify_token(token) is None
