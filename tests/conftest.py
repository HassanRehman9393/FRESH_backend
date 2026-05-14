"""
Shared pytest fixtures for FRESH Backend tests.
Uses monkeypatching to avoid real DB/ML calls in unit tests.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import uuid

# ── patch heavy imports before the app loads ──────────────────────────────────
@pytest.fixture(autouse=True, scope="session")
def _patch_supabase():
    with patch("src.core.supabase_client.supabase", MagicMock()), \
         patch("src.core.supabase_client.admin_supabase", MagicMock()):
        yield

@pytest.fixture(scope="session")
def app(_patch_supabase):
    import sys, importlib
    # ensure fresh import after patches
    for mod in list(sys.modules.keys()):
        if mod.startswith("src."):
            sys.modules.pop(mod, None)
    from main import app as _app  # noqa: E402
    return _app

@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)

# ── helper factories ──────────────────────────────────────────────────────────
def make_user(role: str = "farmer") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "full_name": "Test User",
        "role": role,
        "provider": "local",
        "is_google_user": False,
        "password_hash": "$2b$12$placeholder_hash",
    }

def make_jwt(user_id: str, email: str, role: str) -> str:
    from src.core.security import create_user_token
    return create_user_token(user_id, email, role)

@pytest.fixture
def farmer_token():
    uid = str(uuid.uuid4())
    return make_jwt(uid, "farmer@test.com", "farmer"), uid

@pytest.fixture
def admin_token():
    uid = str(uuid.uuid4())
    return make_jwt(uid, "admin@test.com", "admin"), uid
