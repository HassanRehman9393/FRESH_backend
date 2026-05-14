"""
TC-BE-39 … TC-BE-55  — Detection & Disease API endpoints
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from src.core.security import create_user_token


def _token(role="farmer"):
    uid = str(uuid.uuid4())
    return create_user_token(uid, f"{role}@test.com", role), uid


def _detection(user_id: str) -> dict:
    return {
        "detection_id": str(uuid.uuid4()),
        "user_id": user_id,
        "image_id": str(uuid.uuid4()),
        "orchard_id": str(uuid.uuid4()),
        "fruit_type": "mango",
        "confidence": 0.92,
        "bounding_box": {"x": 10.0, "y": 20.0, "width": 100.0, "height": 80.0},
        "classification": {
            "ripeness_level": "ripe",
            "ripeness_confidence": 0.88,
            "color": "yellow",
            "size": "medium",
        },
        "annotated_image_url": None,
        "annotated_image_filename": None,
        "created_at": "2025-01-01T00:00:00",
    }


def _disease(user_id: str) -> dict:
    return {
        "disease_detection_id": str(uuid.uuid4()),
        "detection_id": str(uuid.uuid4()),
        "user_id": user_id,
        "image_id": str(uuid.uuid4()),
        "orchard_id": str(uuid.uuid4()),
        "disease_type": "anthracnose",
        "is_diseased": True,
        "disease_confidence": 0.87,
        "severity_level": None,
        "probabilities": {"healthy": 0.13, "anthracnose": 0.87},
        "created_at": "2025-01-01T00:00:00",
    }


# ── Detection results list ────────────────────────────────────────────────────

class TestDetectionResults:
    def test_get_detections_authenticated(self):
        """TC-BE-39: Authenticated user retrieves detection results list."""
        token, uid = _token()
        det = _detection(uid)

        mock_sb = MagicMock()
        # detection_results query
        mock_sb.table.return_value.select.return_value.eq.return_value\
            .order.return_value.range.return_value.execute.return_value.data = [det]
        # classification_results join query
        mock_sb.table.return_value.select.return_value.in_.return_value\
            .execute.return_value.data = []

        with patch("src.services.detection_service.admin_supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/detection/fruit/results",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_detections_unauthenticated_returns_403(self):
        """TC-BE-40: No token on detection results returns 403."""
        from main import app
        client = TestClient(app)
        resp = client.get("/api/detection/fruit/results")
        assert resp.status_code in (401, 403)

    def test_get_detections_limit_parameter(self):
        """TC-BE-41: limit query param is respected (max 100)."""
        token, uid = _token()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value\
            .order.return_value.range.return_value.execute.return_value.data = []
        mock_sb.table.return_value.select.return_value.in_.return_value\
            .execute.return_value.data = []

        with patch("src.services.detection_service.admin_supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/detection/fruit/results?limit=5&offset=0",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_get_detections_limit_over_max_returns_422(self):
        """TC-BE-42: limit > 100 returns 422 (FastAPI Query validation)."""
        token, _ = _token()
        from main import app
        client = TestClient(app)
        resp = client.get(
            "/api/detection/fruit/results?limit=999",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422


# ── Batch fruit detection ─────────────────────────────────────────────────────

class TestBatchDetection:
    def test_batch_detect_empty_image_ids_returns_200_or_400(self):
        """TC-BE-43: Batch detect with empty image_ids returns 200 (empty result) or 400."""
        token, _ = _token()
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/api/detection/batch-fruit",
            json={"image_ids": []},
            headers={"Authorization": f"Bearer {token}"}
        )
        # Service accepts empty list and returns empty BatchDetectionResponse
        assert resp.status_code in (200, 400, 422)

    def test_batch_detect_invalid_uuid_returns_422(self):
        """TC-BE-44: Non-UUID image_id returns 422."""
        token, _ = _token()
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/api/detection/batch-fruit",
            json={"image_ids": ["not-a-uuid"]},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422


# ── Admin detection results ───────────────────────────────────────────────────

class TestAdminDetectionResults:
    def test_admin_gets_all_detections(self):
        """TC-BE-45: Admin fetches all detection results including classification join."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        uid = str(uuid.uuid4())
        det = _detection(uid)

        mock_sb = MagicMock()
        q = mock_sb.table.return_value.select.return_value
        q.order.return_value.range.return_value.execute.return_value.data = [det]
        q.in_.return_value.execute.return_value.data = []

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/admin/detection-results",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_admin_detection_classification_joined(self):
        """TC-BE-46: Classification ripeness_level is present when classification table has data."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        uid = str(uuid.uuid4())
        det = _detection(uid)
        det_id = det["detection_id"]
        cls_record = {
            "detection_id": det_id,
            "ripeness_level": "ripe",
            "confidence_score": 0.90,
            "estimated_color": "yellow",
            "estimated_size": "medium",
        }

        mock_sb = MagicMock()
        q = mock_sb.table.return_value.select.return_value
        q.order.return_value.range.return_value.execute.return_value.data = [det]
        q.in_.return_value.execute.return_value.data = [cls_record]

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/admin/detection-results",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["classification"]["ripeness_level"] == "ripe"

    def test_admin_detection_filter_by_user_id(self):
        """TC-BE-47: user_id query param filters results."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        target_uid = str(uuid.uuid4())

        mock_sb = MagicMock()
        q = mock_sb.table.return_value.select.return_value
        q.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
        q.in_.return_value.execute.return_value.data = []

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                f"/api/admin/detection-results?user_id={target_uid}",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200


# ── Disease detection ─────────────────────────────────────────────────────────

class TestDiseaseResults:
    def test_get_disease_results_authenticated(self):
        """TC-BE-48: Farmer retrieves their disease results."""
        token, uid = _token()
        disease = _disease(uid)
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value\
            .order.return_value.range.return_value.execute.return_value.data = [disease]

        with patch("src.services.disease_service.admin_supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/disease/results",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_get_disease_results_limit_max_100(self):
        """TC-BE-49: Disease results limit capped at 100; 500 returns 422."""
        token, _ = _token()
        from main import app
        client = TestClient(app)
        resp = client.get(
            "/api/disease/results?limit=500",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422

    def test_admin_get_all_disease_results(self):
        """TC-BE-50: Admin fetches disease results with limit up to 1000."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        uid = str(uuid.uuid4())
        disease = _disease(uid)

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value\
            .order.return_value.range.return_value.execute.return_value.data = [disease]

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/admin/disease-results",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_admin_disease_results_limit_1000_allowed(self):
        """TC-BE-51: Admin disease results endpoint allows limit=1000."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value\
            .order.return_value.range.return_value.execute.return_value.data = []

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/admin/disease-results?limit=1000",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_admin_disease_results_limit_over_1000_returns_422(self):
        """TC-BE-52: Admin disease results limit > 1000 returns 422."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        from main import app
        client = TestClient(app)
        resp = client.get(
            "/api/admin/disease-results?limit=1001",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422


# ── Admin user management ─────────────────────────────────────────────────────

class TestAdminUsers:
    def test_admin_list_users(self):
        """TC-BE-53: Admin can list all users."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        users = [{"id": str(uuid.uuid4()), "email": "u@test.com", "full_name": "U", "role": "farmer"}]
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value\
            .order.return_value.range.return_value.execute.return_value.data = users

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get(
                "/api/admin/users",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_admin_create_user(self):
        """TC-BE-54: Admin creates a new user via admin endpoint (min password 8 chars)."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        new_user = {
            "id": str(uuid.uuid4()),
            "email": "newfarmer@test.com",
            "full_name": "New Farmer",
            "role": "farmer",
        }
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [new_user]

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post(
                "/api/admin/users",
                # password min_length=8 per UserSignup schema
                json={"email": "newfarmer@test.com", "password": "password1", "full_name": "New Farmer", "role": "farmer"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code in (200, 201)

    def test_admin_delete_user(self):
        """TC-BE-55: Admin deletes a user by ID."""
        token = create_user_token(str(uuid.uuid4()), "admin@test.com", "admin")
        uid = str(uuid.uuid4())
        mock_sb = MagicMock()
        mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [{"id": uid}]

        with patch("src.api.admin.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.delete(
                f"/api/admin/users/{uid}",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code in (200, 204)
