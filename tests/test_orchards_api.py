"""
TC-BE-26 … TC-BE-38  — Orchards API endpoints
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.core.security import create_user_token


def _token(role="farmer"):
    return create_user_token(str(uuid.uuid4()), f"{role}@test.com", role)


def _orchard(user_id: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": "Test Orchard",
        "latitude": 30.3753,
        "longitude": 69.3451,
        "area_hectares": 5.0,
        "fruit_types": ["mango", "guava"],
        "is_active": True,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }


class TestOrchardCreate:
    PAYLOAD = {
        "name": "Green Valley",
        "latitude": 30.3753,
        "longitude": 69.3451,
        "area_hectares": 10.0,
        "fruit_types": ["mango"],
    }

    def test_create_orchard_success(self):
        """TC-BE-26: Authenticated farmer creates an orchard, returns 201."""
        token = _token("farmer")
        uid = "farmer-uid"
        orch = {**self.PAYLOAD, "id": str(uuid.uuid4()), "user_id": uid,
                "is_active": True, "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"}
        mock_sb = MagicMock()
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [orch]

        with patch("src.api.orchards.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.post(
                "/api/orchards",
                json=self.PAYLOAD,
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 201
        assert resp.json()["name"] == self.PAYLOAD["name"]

    def test_create_orchard_unauthenticated_returns_403(self):
        """TC-BE-27: Unauthenticated request returns 403."""
        from main import app
        client = TestClient(app)
        resp = client.post("/api/orchards", json=self.PAYLOAD)
        assert resp.status_code in (401, 403)

    def test_create_orchard_missing_name_returns_422(self):
        """TC-BE-28: Missing required 'name' field returns 422."""
        token = _token()
        from main import app
        client = TestClient(app)
        bad = {k: v for k, v in self.PAYLOAD.items() if k != "name"}
        resp = client.post("/api/orchards", json=bad, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422

    def test_create_orchard_invalid_latitude_returns_422(self):
        """TC-BE-29: Latitude > 90 returns 422."""
        token = _token()
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/api/orchards",
            json={**self.PAYLOAD, "latitude": 999},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422


class TestOrchardRead:
    def test_get_orchards_returns_list(self):
        """TC-BE-30: Authenticated user gets their orchards as a list."""
        token = _token()
        uid = str(uuid.uuid4())
        orchards = [_orchard(uid)]
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = orchards

        with patch("src.api.orchards.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get("/api/orchards", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_orchards_empty_list(self):
        """TC-BE-31: User with no orchards gets empty list."""
        token = _token()
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

        with patch("src.api.orchards.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.get("/api/orchards", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200
        assert resp.json() == []


class TestOrchardUpdate:
    def test_update_orchard_success(self):
        """TC-BE-32: Owner updating their orchard returns updated record."""
        uid = str(uuid.uuid4())
        token = create_user_token(uid, "farmer@test.com", "farmer")
        orch_id = str(uuid.uuid4())
        updated = _orchard(uid)
        updated["id"] = orch_id
        updated["name"] = "Updated Name"

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [updated]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [updated]

        with patch("src.api.orchards.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.put(
                f"/api/orchards/{orch_id}",
                json={"name": "Updated Name"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 200

    def test_update_nonexistent_orchard_returns_404(self):
        """TC-BE-33: Updating a non-existent orchard returns 404."""
        uid = str(uuid.uuid4())
        token = create_user_token(uid, "farmer@test.com", "farmer")

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with patch("src.api.orchards.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.put(
                f"/api/orchards/{uuid.uuid4()}",
                json={"name": "Ghost"},
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 404


class TestOrchardDelete:
    def test_delete_orchard_success(self):
        """TC-BE-34: Deleting own orchard returns 200/204."""
        uid = str(uuid.uuid4())
        token = create_user_token(uid, "farmer@test.com", "farmer")
        orch_id = str(uuid.uuid4())
        orch = _orchard(uid)
        orch["id"] = orch_id

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [orch]
        mock_sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = [orch]

        with patch("src.api.orchards.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.delete(
                f"/api/orchards/{orch_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code in (200, 204)

    def test_delete_nonexistent_orchard_returns_404(self):
        """TC-BE-35: Deleting a non-existent orchard returns 404."""
        uid = str(uuid.uuid4())
        token = create_user_token(uid, "farmer@test.com", "farmer")

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with patch("src.api.orchards.supabase", mock_sb):
            from main import app
            client = TestClient(app)
            resp = client.delete(
                f"/api/orchards/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"}
            )
        assert resp.status_code == 404


class TestOrchardValidation:
    def test_fruit_types_must_be_list(self):
        """TC-BE-36: fruit_types as string (not list) returns 422."""
        token = _token()
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/api/orchards",
            json={"name": "X", "latitude": 30.0, "longitude": 70.0, "fruit_types": "mango"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422

    def test_longitude_out_of_range_returns_422(self):
        """TC-BE-37: Longitude > 180 returns 422."""
        token = _token()
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/api/orchards",
            json={"name": "X", "latitude": 30.0, "longitude": 200.0, "fruit_types": ["mango"]},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422

    def test_negative_area_returns_422(self):
        """TC-BE-38: Negative area_hectares returns 422."""
        token = _token()
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/api/orchards",
            json={"name": "X", "latitude": 30.0, "longitude": 70.0,
                  "fruit_types": ["mango"], "area_hectares": -1},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 422
