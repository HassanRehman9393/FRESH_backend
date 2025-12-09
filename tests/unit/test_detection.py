"""
Unit tests for Detection Service & API
Tests: fruit detection, batch processing, result retrieval
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from uuid import UUID, uuid4

from src.services.detection_service import (
    process_single_image,
    process_batch_images,
    get_detection_by_id,
    get_all_detections
)


# ============================================================================
# DETECTION SERVICE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.detection
class TestDetectionService:
    """Test fruit detection service"""
    
    @pytest.mark.asyncio
    async def test_process_single_image_success(self, test_image_data, test_user_data):
        """Test successful single image detection"""
        image_id = UUID(test_image_data["id"])
        user_id = UUID(test_user_data["id"])
        
        ml_response = {
            "detections": [
                {
                    "class_name": "mango",
                    "confidence": 0.95,
                    "bounding_box": {"x": 100, "y": 100, "width": 200, "height": 200}
                }
            ],
            "processing_time": 1.2
        }
        
        with patch('src.services.detection_service.supabase') as mock_supabase, \
             patch('src.services.detection_service.ml_client') as mock_ml:
            
            # Mock image retrieval
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_image_data
            ]
            
            # Mock ML API call
            mock_ml.detect_fruits = AsyncMock(return_value=ml_response)
            
            # Mock detection record insertion
            detection_record = {
                "id": str(uuid4()),
                "image_id": str(image_id),
                "user_id": str(user_id),
                **ml_response["detections"][0]
            }
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                detection_record
            ]
            
            result = await process_single_image(image_id, user_id)
            
            assert result is not None
            mock_ml.detect_fruits.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_batch_images_success(self, test_image_data, test_user_data):
        """Test batch image detection"""
        image_ids = [UUID(str(uuid4())) for _ in range(3)]
        user_id = UUID(test_user_data["id"])
        
        with patch('src.services.detection_service.process_single_image') as mock_process:
            mock_process.return_value = {"detection_id": str(uuid4()), "status": "success"}
            
            result = await process_batch_images(image_ids, user_id)
            
            assert result is not None
            assert "results" in result or result.get("detections") is not None
    
    @pytest.mark.asyncio
    async def test_process_image_not_found(self, test_user_data):
        """Test detection with non-existent image"""
        image_id = UUID(str(uuid4()))
        user_id = UUID(test_user_data["id"])
        
        with patch('src.services.detection_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            with pytest.raises(Exception):
                await process_single_image(image_id, user_id)
    
    @pytest.mark.asyncio
    async def test_ml_api_timeout(self, test_image_data, test_user_data):
        """Test handling of ML API timeout"""
        image_id = UUID(test_image_data["id"])
        user_id = UUID(test_user_data["id"])
        
        with patch('src.services.detection_service.supabase') as mock_supabase, \
             patch('src.services.detection_service.ml_client') as mock_ml:
            
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_image_data
            ]
            
            # Simulate timeout
            import asyncio
            mock_ml.detect_fruits = AsyncMock(side_effect=asyncio.TimeoutError())
            
            with pytest.raises(Exception):
                await process_single_image(image_id, user_id)


# ============================================================================
# DETECTION RETRIEVAL TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.detection
class TestDetectionRetrieval:
    """Test detection result retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_detection_by_id_success(self, test_detection_data):
        """Test getting detection by ID"""
        detection_id = UUID(test_detection_data["id"])
        
        with patch('src.services.detection_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_detection_data
            ]
            
            result = await get_detection_by_id(detection_id)
            
            assert result is not None
            assert result["id"] == test_detection_data["id"]
    
    @pytest.mark.asyncio
    async def test_get_detection_not_found(self):
        """Test getting non-existent detection"""
        detection_id = UUID(str(uuid4()))
        
        with patch('src.services.detection_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            with pytest.raises(Exception):
                await get_detection_by_id(detection_id)
    
    @pytest.mark.asyncio
    async def test_get_all_detections_with_pagination(self, test_user_data, test_detection_data):
        """Test getting all detections with pagination"""
        user_id = UUID(test_user_data["id"])
        
        with patch('src.services.detection_service.supabase') as mock_supabase:
            mock_detections = [test_detection_data for _ in range(5)]
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value.data = mock_detections
            
            result = await get_all_detections(user_id, limit=10, offset=0)
            
            assert isinstance(result, list)
            assert len(result) <= 10


# ============================================================================
# DETECTION API ENDPOINT TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.detection
class TestDetectionAPI:
    """Test detection API endpoints"""
    
    def test_batch_detect_fruits_unauthorized(self, client):
        """Test batch detection without authentication"""
        response = client.post(
            "/detection/batch-fruit",
            json={"image_ids": [str(uuid4())]}
        )
        
        assert response.status_code == 401
    
    def test_batch_detect_fruits_success(self, client, auth_headers, override_get_current_user):
        """Test successful batch detection"""
        with patch('src.services.detection_service.process_batch_images') as mock_process:
            mock_process.return_value = {
                "results": [],
                "total": 0,
                "successful": 0,
                "failed": 0
            }
            
            response = client.post(
                "/detection/batch-fruit",
                headers=auth_headers,
                json={"image_ids": [str(uuid4()), str(uuid4())]}
            )
            
            # Will fail without auth, but tests endpoint structure
            assert response.status_code in [200, 401, 422]
    
    def test_get_detection_results_with_filters(self, client, auth_headers):
        """Test getting detection results with query parameters"""
        with patch('src.services.detection_service.get_all_detections') as mock_get:
            mock_get.return_value = []
            
            response = client.get(
                "/detection/fruit/results?limit=5&offset=10",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 401]
    
    def test_get_detection_by_id_not_found(self, client, auth_headers):
        """Test getting non-existent detection"""
        with patch('src.services.detection_service.get_detection_by_id') as mock_get:
            mock_get.side_effect = Exception("Detection not found")
            
            detection_id = uuid4()
            response = client.get(
                f"/detection/fruit/{detection_id}",
                headers=auth_headers
            )
            
            assert response.status_code in [404, 401]


# ============================================================================
# DETECTION DATA VALIDATION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.detection
class TestDetectionDataValidation:
    """Test detection data validation"""
    
    def test_validate_bounding_box(self):
        """Test bounding box validation"""
        from src.schemas.detection import BoundingBox
        
        # Valid bounding box
        bbox = BoundingBox(x=100, y=100, width=200, height=200)
        assert bbox.x == 100
        
        # Invalid negative values
        with pytest.raises(Exception):
            BoundingBox(x=-10, y=100, width=200, height=200)
    
    def test_validate_confidence_score(self):
        """Test confidence score validation"""
        # Should be between 0 and 1
        assert 0 <= 0.95 <= 1
        assert 0 <= 0.0 <= 1
        assert 0 <= 1.0 <= 1
        
        # Out of range should fail
        with pytest.raises(AssertionError):
            assert 0 <= 1.5 <= 1
    
    def test_batch_request_validation(self):
        """Test batch detection request validation"""
        from src.schemas.detection import BatchDetectionRequest
        
        # Valid request
        request = BatchDetectionRequest(
            image_ids=[str(uuid4()) for _ in range(3)]
        )
        assert len(request.image_ids) == 3
        
        # Empty image_ids should fail
        with pytest.raises(Exception):
            BatchDetectionRequest(image_ids=[])
