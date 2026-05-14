"""
TC-BE-11 … TC-BE-25  — Auth API endpoints (/api/auth/signup, /api/auth/login)
All Supabase calls are mocked.
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── helpers ───────────────────────────────────────────────────────────────────

def _supabase_empty():
    """Return a mock Supabase chain that finds nothing."""
    m = MagicMock()
    m.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    return m

def _supabase_with_user(user_data: dict):
    """Return a mock Supabase chain that finds one user."""
    m = MagicMock()
    m.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user_data]
    m.table.return_value.insert.return_value.execute.return_value.data = [user_data]
    return m


# ── Signup ────────────────────────────────────────────────────────────────────

class TestSignup:
    PAYLOAD = {
        "email": "newuser@test.com",
        "password": "securepass123",
        "full_name": "New User",
        "role": "farmer",
    }

    def test_signup_success(self):
        """TC-BE-11: Valid signup returns 201 with access_token."""
        new_user = {
            "id": str(uuid.uuid4()),
            "email": self.PAYLOAD["email"],
            "full_name": self.PAYLOAD["full_name"],
            "role": "farmer",
        }
        mock_sb = MagicMock()
        # select returns empty (user doesn't exist)
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        # insert returns created user
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [new_user]

        with patch("src.services.auth_service.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post("/api/auth/signup", json=self.PAYLOAD)

        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["email"] == self.PAYLOAD["email"]

    def test_signup_duplicate_email_returns_409(self):
        """TC-BE-12: Duplicate email returns 409 Conflict."""
        existing = {"id": str(uuid.uuid4()), "email": self.PAYLOAD["email"]}
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [existing]

        with patch("src.services.auth_service.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post("/api/auth/signup", json=self.PAYLOAD)

        assert resp.status_code == 409

    def test_signup_missing_password_returns_400_or_422(self):
        """TC-BE-13: Missing password returns 400 (service-level) or 422 (schema-level)."""
        from main import app
        client = TestClient(app)
        bad = {k: v for k, v in self.PAYLOAD.items() if k != "password"}
        resp = client.post("/api/auth/signup", json=bad)
        # UserSignup.password is Optional; service enforces requirement returning 400
        assert resp.status_code in (400, 422)

    def test_signup_invalid_email_returns_422(self):
        """TC-BE-14: Malformed email returns 422."""
        from main import app
        client = TestClient(app)
        resp = client.post("/api/auth/signup", json={**self.PAYLOAD, "email": "not-an-email"})
        assert resp.status_code == 422

    def test_signup_invalid_role_returns_422(self):
        """TC-BE-15: Unknown role returns 422."""
        from main import app
        client = TestClient(app)
        resp = client.post("/api/auth/signup", json={**self.PAYLOAD, "role": "hacker"})
        assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    def _user_with_hash(self, password: str) -> dict:
        from src.core.security import hash_password
        return {
            "id": str(uuid.uuid4()),
            "email": "farmer@test.com",
            "full_name": "Farmer",
            "role": "farmer",
            "password_hash": hash_password(password),
            "is_google_user": False,
            "provider": "local",
        }

    def test_login_success(self):
        """TC-BE-16: Correct credentials return 200 with access_token."""
        user = self._user_with_hash("correct123")
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]

        with patch("src.services.auth_service.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post("/api/auth/login", json={"email": user["email"], "password": "correct123"})

        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password_returns_401(self):
        """TC-BE-17: Wrong password returns 401 Unauthorized."""
        user = self._user_with_hash("correct123")
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]

        with patch("src.services.auth_service.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post("/api/auth/login", json={"email": user["email"], "password": "wrong"})

        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self):
        """TC-BE-18: Unknown email returns 401 (not 404 to avoid user enumeration)."""
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch("src.services.auth_service.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "pass"})

        assert resp.status_code == 401

    def test_login_google_user_returns_400(self):
        """TC-BE-19: Google-only account attempting password login returns 400."""
        user = {
            "id": str(uuid.uuid4()),
            "email": "google@test.com",
            "password_hash": None,
            "role": "farmer",
            "is_google_user": True,
            "provider": "google",
        }
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [user]

        with patch("src.services.auth_service.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post("/api/auth/login", json={"email": user["email"], "password": "anypassword"})

        assert resp.status_code == 400

    def test_login_missing_fields_returns_422(self):
        """TC-BE-20: Missing email returns 422."""
        from main import app
        client = TestClient(app)
        resp = client.post("/api/auth/login", json={"password": "pass"})
        assert resp.status_code == 422


# ── Protected route without token ─────────────────────────────────────────────

class TestAuthGuard:
    def test_protected_route_without_token_returns_403(self):
        """TC-BE-21: Accessing protected route with no token returns 403."""
        from main import app
        client = TestClient(app)
        resp = client.get("/api/detection/fruit/results")
        assert resp.status_code in (401, 403)

    def test_protected_route_with_invalid_token_returns_401(self):
        """TC-BE-22: Invalid Bearer token returns 401."""
        from main import app
        client = TestClient(app)
        resp = client.get(
            "/api/detection/fruit/results",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert resp.status_code == 401

    def test_admin_route_with_farmer_token_returns_403(self):
        """TC-BE-23: Farmer JWT accessing admin endpoint returns 403."""
        from src.core.security import create_user_token
        token = create_user_token(str(uuid.uuid4()), "farmer@x.com", "farmer")

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.execute.return_value.data = []

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/admin/users",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 403

    def test_admin_route_with_admin_token_returns_200(self):
        """TC-BE-24: Admin JWT accessing admin/users returns 200."""
        from src.core.security import create_user_token
        token = create_user_token(str(uuid.uuid4()), "admin@x.com", "admin")

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.execute.return_value.data = []
        mock_sb.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value.data = []

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/admin/users",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_expired_token_returns_401(self):
        """TC-BE-25: Expired JWT returns 401."""
        from src.core.security import create_access_token
        from datetime import timedelta
        token = create_access_token({"sub": str(uuid.uuid4()), "email": "x@x.com", "role": "farmer"}, expires_delta=timedelta(seconds=-1))
        from main import app
        client = TestClient(app)
        resp = client.get(
            "/api/detection/fruit/results",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401
