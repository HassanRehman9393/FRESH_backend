"""
Pytest configuration and shared fixtures for FRESH Backend tests
"""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import Mock, AsyncMock, patch
import uuid
from datetime import datetime, timedelta

from main import app
from src.core.config import settings
from src.core.security import create_user_token


# ============================================================================
# FIXTURES: Application & Clients
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Synchronous test client for FastAPI application.
    Use for most API endpoint tests.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async test client for FastAPI application.
    Use for testing async endpoints and dependencies.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# FIXTURES: Test Data
# ============================================================================

@pytest.fixture
def test_user_data():
    """Standard test user data."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "farmer",
        "password": "TestPass123!",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqNk7C0jOu"  # hashed "TestPass123!"
    }


@pytest.fixture
def test_orchard_data():
    """Standard test orchard data."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Orchard",
        "latitude": 33.6844,
        "longitude": 73.0479,
        "area_hectares": 5.0,
        "fruit_types": ["mango", "guava"],
        "is_active": True
    }


@pytest.fixture
def test_image_data():
    """Standard test image data."""
    return {
        "id": str(uuid.uuid4()),
        "filename": "test_image.jpg",
        "file_path": "images/test/test_image.jpg",
        "file_size": 1024000,
        "mime_type": "image/jpeg",
        "url": "https://storage.example.com/test_image.jpg"
    }


@pytest.fixture
def test_detection_data():
    """Standard test detection result data."""
    return {
        "id": str(uuid.uuid4()),
        "detection_type": "fruit",
        "confidence": 0.95,
        "bounding_box": {"x": 100, "y": 100, "width": 200, "height": 200},
        "class_name": "mango",
        "metadata": {"ripeness": "ripe"}
    }


@pytest.fixture
def test_weather_data():
    """Standard test weather data."""
    return {
        "id": str(uuid.uuid4()),
        "temperature": 28.5,
        "humidity": 65.0,
        "rainfall": 2.5,
        "wind_speed": 12.0,
        "conditions": "partly_cloudy",
        "recorded_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# FIXTURES: Authentication
# ============================================================================

@pytest.fixture
def auth_token(test_user_data):
    """Generate a valid JWT token for testing."""
    return create_user_token(
        test_user_data["id"],
        test_user_data["email"],
        test_user_data["role"]
    )


@pytest.fixture
def auth_headers(auth_token):
    """Headers with valid authentication token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_current_user(test_user_data):
    """Mock authenticated user for dependency injection."""
    return {
        "user_id": test_user_data["id"],
        "email": test_user_data["email"],
        "role": test_user_data["role"]
    }


# ============================================================================
# FIXTURES: Database Mocking
# ============================================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = Mock()
    
    # Mock table method returns self for chaining
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.gte.return_value = mock
    mock.lte.return_value = mock
    mock.in_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    
    # Mock execute returns data
    execute_mock = Mock()
    execute_mock.data = []
    mock.execute.return_value = execute_mock
    
    return mock


@pytest.fixture
def mock_supabase_with_user(mock_supabase, test_user_data):
    """Mock Supabase client with user data."""
    execute_mock = Mock()
    execute_mock.data = [test_user_data]
    mock_supabase.execute.return_value = execute_mock
    return mock_supabase


# ============================================================================
# FIXTURES: External Service Mocking
# ============================================================================

@pytest.fixture
def mock_ml_client():
    """Mock ML API client."""
    mock = AsyncMock()
    mock.detect_fruits.return_value = {
        "detections": [],
        "processing_time": 1.5
    }
    mock.detect_disease.return_value = {
        "disease_type": "healthy",
        "confidence": 0.98
    }
    return mock


@pytest.fixture
def mock_weather_api():
    """Mock OpenWeather API responses."""
    with patch('httpx.AsyncClient') as mock:
        async_mock = AsyncMock()
        async_mock.get.return_value.json.return_value = {
            "main": {
                "temp": 28.5,
                "humidity": 65
            },
            "weather": [{"main": "Clear"}],
            "wind": {"speed": 12}
        }
        mock.return_value.__aenter__.return_value = async_mock
        yield mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    mock = AsyncMock()
    mock.send_alert_email.return_value = True
    return mock


# ============================================================================
# FIXTURES: File Upload Mocking
# ============================================================================

@pytest.fixture
def mock_upload_file():
    """Mock UploadFile for testing file uploads."""
    from io import BytesIO
    from fastapi import UploadFile
    
    file_content = b"fake image content"
    file = UploadFile(
        filename="test_image.jpg",
        file=BytesIO(file_content)
    )
    file.content_type = "image/jpeg"
    return file


@pytest.fixture
def mock_storage_client():
    """Mock Supabase storage client."""
    mock = Mock()
    mock.upload.return_value = {"path": "test/image.jpg"}
    mock.get_public_url.return_value = "https://storage.example.com/image.jpg"
    mock.remove.return_value = True
    return mock


# ============================================================================
# FIXTURES: Dependency Overrides
# ============================================================================

@pytest.fixture
def override_get_current_user(mock_current_user):
    """Override get_current_user dependency."""
    from src.api.deps import get_current_user
    
    async def override():
        return mock_current_user
    
    app.dependency_overrides[get_current_user] = override
    yield
    app.dependency_overrides.clear()


# ============================================================================
# FIXTURES: Test Database (if needed for integration tests)
# ============================================================================

@pytest.fixture(scope="session")
def test_database_url():
    """Test database URL (can be overridden via environment)."""
    import os
    return os.getenv("TEST_DATABASE_URL", settings.database_url)


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def freeze_time():
    """Freeze time for testing time-dependent features."""
    from freezegun import freeze_time as ft
    frozen_time = datetime(2024, 1, 1, 12, 0, 0)
    with ft(frozen_time):
        yield frozen_time


@pytest.fixture
def faker_instance():
    """Faker instance for generating test data."""
    from faker import Faker
    return Faker()


# ============================================================================
# HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Suppress specific warnings if needed
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to all tests in tests/unit/
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to all tests in tests/integration/
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
