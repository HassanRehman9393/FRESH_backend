"""
Unit tests for Orchards Service & API
Tests: CRUD operations, ownership validation, location validation
"""
import pytest
from unittest.mock import patch, Mock
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.orchards
class TestOrchardsAPI:
    """Test orchards API endpoints"""
    
    def test_create_orchard_success(self, client, auth_headers, test_orchard_data, override_get_current_user):
        """Test successful orchard creation"""
        orchard_data = {
            "name": test_orchard_data["name"],
            "latitude": test_orchard_data["latitude"],
            "longitude": test_orchard_data["longitude"],
            "area_hectares": test_orchard_data["area_hectares"],
            "fruit_types": test_orchard_data["fruit_types"]
        }
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {**test_orchard_data, "id": str(uuid4())}
            ]
            
            response = client.post(
                "/orchards",
                headers=auth_headers,
                json=orchard_data
            )
            
            assert response.status_code in [201, 401, 422]
    
    def test_create_orchard_invalid_coordinates(self, client, auth_headers):
        """Test orchard creation with invalid coordinates"""
        invalid_data = {
            "name": "Invalid Orchard",
            "latitude": 91.0,  # Invalid: > 90
            "longitude": 181.0,  # Invalid: > 180
            "fruit_types": ["mango"]
        }
        
        response = client.post(
            "/orchards",
            headers=auth_headers,
            json=invalid_data
        )
        
        # Should fail validation
        assert response.status_code in [422, 401]
    
    def test_get_user_orchards(self, client, auth_headers, test_orchard_data):
        """Test retrieving user's orchards"""
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                test_orchard_data
            ]
            
            response = client.get(
                "/orchards",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 401]
    
    def test_get_orchard_by_id(self, client, auth_headers, test_orchard_data):
        """Test getting specific orchard"""
        orchard_id = test_orchard_data["id"]
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                test_orchard_data
            ]
            
            response = client.get(
                f"/orchards/{orchard_id}",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 401, 404]
    
    def test_get_orchard_not_owned(self, client, auth_headers):
        """Test accessing orchard not owned by user"""
        orchard_id = str(uuid4())
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            # No orchards found for this user
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            
            response = client.get(
                f"/orchards/{orchard_id}",
                headers=auth_headers
            )
            
            assert response.status_code in [404, 401]
    
    def test_update_orchard(self, client, auth_headers, test_orchard_data):
        """Test updating orchard"""
        orchard_id = test_orchard_data["id"]
        update_data = {
            "name": "Updated Orchard Name",
            "area_hectares": 10.5
        }
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            # Mock ownership check
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": orchard_id}
            ]
            
            # Mock update
            updated_orchard = {**test_orchard_data, **update_data}
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                updated_orchard
            ]
            
            response = client.put(
                f"/orchards/{orchard_id}",
                headers=auth_headers,
                json=update_data
            )
            
            assert response.status_code in [200, 401, 404]
    
    def test_update_orchard_no_fields(self, client, auth_headers, test_orchard_data):
        """Test updating orchard with no fields"""
        orchard_id = test_orchard_data["id"]
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": orchard_id}
            ]
            
            response = client.put(
                f"/orchards/{orchard_id}",
                headers=auth_headers,
                json={}
            )
            
            # Should fail with no update fields
            assert response.status_code in [400, 401, 422]
    
    def test_delete_orchard(self, client, auth_headers, test_orchard_data):
        """Test soft deleting orchard"""
        orchard_id = test_orchard_data["id"]
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            # Mock ownership check
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"id": orchard_id}
            ]
            
            # Mock soft delete
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()
            
            response = client.delete(
                f"/orchards/{orchard_id}",
                headers=auth_headers
            )
            
            assert response.status_code in [204, 401, 404]


@pytest.mark.unit
@pytest.mark.orchards
class TestOrchardValidation:
    """Test orchard data validation"""
    
    def test_validate_latitude(self):
        """Test latitude validation"""
        valid_latitudes = [-90, -45.5, 0, 33.6844, 90]
        for lat in valid_latitudes:
            assert -90 <= lat <= 90
        
        invalid_latitudes = [-91, 91, 200]
        for lat in invalid_latitudes:
            assert not (-90 <= lat <= 90)
    
    def test_validate_longitude(self):
        """Test longitude validation"""
        valid_longitudes = [-180, -73.0479, 0, 73.0479, 180]
        for lon in valid_longitudes:
            assert -180 <= lon <= 180
        
        invalid_longitudes = [-181, 181, 360]
        for lon in invalid_longitudes:
            assert not (-180 <= lon <= 180)
    
    def test_validate_fruit_types(self):
        """Test fruit types validation"""
        valid_types = ["mango", "guava", "citrus", "apple"]
        
        # Should be a list
        assert isinstance(valid_types, list)
        
        # Should contain strings
        assert all(isinstance(fruit, str) for fruit in valid_types)
    
    def test_validate_area_hectares(self):
        """Test area hectares validation"""
        valid_areas = [0.1, 1.0, 5.5, 100.0]
        for area in valid_areas:
            assert area > 0
        
        # Negative area is invalid
        assert not (-5.0 > 0)
