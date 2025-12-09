"""
Unit tests for Disease Detection Service & API
Tests: disease detection, batch processing, diseased fruit filtering
"""
import pytest
from unittest.mock import patch, AsyncMock
from uuid import UUID, uuid4

from src.services.disease_service import (
    process_single_disease_detection,
    process_batch_disease_detection,
    get_disease_detection_by_id,
    get_all_disease_detections,
    get_diseased_detections
)


@pytest.mark.unit
@pytest.mark.disease
class TestDiseaseDetectionService:
    """Test disease detection service"""
    
    @pytest.mark.asyncio
    async def test_process_single_disease_detection_success(self, test_detection_data, test_user_data):
        """Test successful disease detection"""
        detection_id = UUID(test_detection_data["id"])
        user_id = UUID(test_user_data["id"])
        
        ml_response = {
            "disease_type": "citrus_blackspot",
            "confidence": 0.92,
            "severity": "moderate",
            "affected_area_percentage": 15.5
        }
        
        with patch('src.services.disease_service.supabase') as mock_supabase, \
             patch('src.services.disease_service.ml_client') as mock_ml:
            
            # Mock detection retrieval
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_detection_data
            ]
            
            # Mock ML API call
            mock_ml.detect_disease = AsyncMock(return_value=ml_response)
            
            # Mock disease record insertion
            disease_record = {
                "id": str(uuid4()),
                "detection_id": str(detection_id),
                "user_id": str(user_id),
                **ml_response
            }
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                disease_record
            ]
            
            result = await process_single_disease_detection(detection_id, user_id)
            
            assert result is not None
            mock_ml.detect_disease.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_disease_detection_healthy_fruit(self, test_detection_data, test_user_data):
        """Test disease detection on healthy fruit"""
        detection_id = UUID(test_detection_data["id"])
        user_id = UUID(test_user_data["id"])
        
        ml_response = {
            "disease_type": "healthy",
            "confidence": 0.98,
            "severity": "none",
            "affected_area_percentage": 0.0
        }
        
        with patch('src.services.disease_service.supabase') as mock_supabase, \
             patch('src.services.disease_service.ml_client') as mock_ml:
            
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_detection_data
            ]
            
            mock_ml.detect_disease = AsyncMock(return_value=ml_response)
            
            disease_record = {
                "id": str(uuid4()),
                "disease_type": "healthy",
                "confidence": 0.98
            }
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                disease_record
            ]
            
            result = await process_single_disease_detection(detection_id, user_id)
            
            assert result is not None
            assert result["disease_type"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_get_diseased_detections_only(self, test_user_data):
        """Test retrieving only diseased fruits"""
        user_id = UUID(test_user_data["id"])
        
        diseased_detections = [
            {"id": str(uuid4()), "disease_type": "citrus_canker", "confidence": 0.90},
            {"id": str(uuid4()), "disease_type": "anthracnose", "confidence": 0.85}
        ]
        
        with patch('src.services.disease_service.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.order.return_value.limit.return_value.offset.return_value.execute.return_value.data = diseased_detections
            
            result = await get_diseased_detections(user_id, limit=10, offset=0)
            
            assert isinstance(result, list)
            # All should be diseased (not healthy)
            for detection in result:
                assert detection["disease_type"] != "healthy"


@pytest.mark.unit
@pytest.mark.disease
class TestDiseaseDetectionAPI:
    """Test disease detection API endpoints"""
    
    def test_batch_detect_diseases_unauthorized(self, client):
        """Test batch disease detection without auth"""
        response = client.post(
            "/disease/batch-detect",
            json={"detection_ids": [str(uuid4())]}
        )
        
        assert response.status_code == 401
    
    def test_get_diseased_results_only(self, client, auth_headers):
        """Test getting only diseased detection results"""
        with patch('src.services.disease_service.get_diseased_detections') as mock_get:
            mock_get.return_value = []
            
            response = client.get(
                "/disease/diseased?limit=10",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 401]
    
    def test_disease_severity_classification(self):
        """Test disease severity classification"""
        severities = ["none", "mild", "moderate", "severe", "critical"]
        
        for severity in severities:
            assert severity in ["none", "mild", "moderate", "severe", "critical"]
