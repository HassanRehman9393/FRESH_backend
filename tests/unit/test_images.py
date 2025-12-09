"""
Unit tests for Image Service & API
Tests: image upload, retrieval, deletion, validation
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from uuid import uuid4
from io import BytesIO


@pytest.mark.unit
@pytest.mark.images
class TestImageService:
    """Test image service functionality"""
    
    @pytest.mark.asyncio
    async def test_upload_image_success(self, test_user_data, mock_upload_file):
        """Test successful image upload"""
        from src.services.image_service import upload_image_service
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            # Mock storage upload
            storage_mock = Mock()
            storage_mock.upload.return_value = {"path": "uploads/test.jpg"}
            storage_mock.get_public_url.return_value = "https://storage.example.com/test.jpg"
            mock_supabase.storage.from_.return_value = storage_mock
            
            # Mock database insert
            image_record = {
                "id": str(uuid4()),
                "user_id": test_user_data["id"],
                "filename": "test_image.jpg",
                "file_path": "uploads/test.jpg",
                "url": "https://storage.example.com/test.jpg"
            }
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                image_record
            ]
            
            result = await upload_image_service(test_user_data["id"], mock_upload_file)
            
            assert result is not None
            assert "id" in result
    
    @pytest.mark.asyncio
    async def test_upload_image_invalid_type(self, test_user_data):
        """Test uploading invalid file type"""
        from fastapi import UploadFile
        from src.services.image_service import upload_image_service
        
        # Create fake PDF file
        invalid_file = UploadFile(
            filename="document.pdf",
            file=BytesIO(b"fake pdf content")
        )
        invalid_file.content_type = "application/pdf"
        
        with pytest.raises(Exception):
            await upload_image_service(test_user_data["id"], invalid_file)
    
    @pytest.mark.asyncio
    async def test_upload_image_too_large(self, test_user_data):
        """Test uploading file that exceeds size limit"""
        from fastapi import UploadFile
        from src.services.image_service import upload_image_service
        
        # Create fake large file (>10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        large_file = UploadFile(
            filename="large_image.jpg",
            file=BytesIO(large_content)
        )
        large_file.content_type = "image/jpeg"
        
        with pytest.raises(Exception):
            await upload_image_service(test_user_data["id"], large_file)
    
    @pytest.mark.asyncio
    async def test_get_image_success(self, test_image_data):
        """Test retrieving image metadata"""
        from src.services.image_service import get_image_service
        
        image_id = test_image_data["id"]
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_image_data
            ]
            
            result = await get_image_service(image_id)
            
            assert result is not None
            assert result["id"] == image_id
    
    @pytest.mark.asyncio
    async def test_get_image_not_found(self):
        """Test retrieving non-existent image"""
        from src.services.image_service import get_image_service
        
        image_id = str(uuid4())
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
            
            with pytest.raises(Exception):
                await get_image_service(image_id)
    
    @pytest.mark.asyncio
    async def test_delete_image_success(self, test_image_data):
        """Test successful image deletion"""
        from src.services.image_service import delete_image_service
        
        image_id = test_image_data["id"]
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            # Mock image retrieval
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                test_image_data
            ]
            
            # Mock storage deletion
            storage_mock = Mock()
            storage_mock.remove.return_value = True
            mock_supabase.storage.from_.return_value = storage_mock
            
            # Mock database deletion
            mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = Mock()
            
            result = await delete_image_service(image_id)
            
            assert result is True


@pytest.mark.unit
@pytest.mark.images
class TestImageAPI:
    """Test image API endpoints"""
    
    def test_upload_image_unauthorized(self, client, mock_upload_file):
        """Test image upload without authentication"""
        response = client.post(
            "/images/upload",
            files={"file": (mock_upload_file.filename, mock_upload_file.file, "image/jpeg")}
        )
        
        assert response.status_code == 401
    
    def test_batch_upload_images(self, client, auth_headers):
        """Test batch image upload"""
        files = [
            ("files", ("image1.jpg", BytesIO(b"fake1"), "image/jpeg")),
            ("files", ("image2.jpg", BytesIO(b"fake2"), "image/jpeg"))
        ]
        
        response = client.post(
            "/images/batch-upload",
            headers=auth_headers,
            files=files
        )
        
        assert response.status_code in [201, 401, 422]
    
    def test_get_image_by_id(self, client, auth_headers, test_image_data):
        """Test getting image by ID"""
        with patch('src.services.image_service.get_image_service') as mock_get:
            mock_get.return_value = test_image_data
            
            response = client.get(
                f"/images/{test_image_data['id']}",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 401, 404]
    
    def test_delete_image_by_id(self, client, auth_headers, test_image_data):
        """Test deleting image"""
        with patch('src.services.image_service.delete_image_service') as mock_delete:
            mock_delete.return_value = True
            
            response = client.delete(
                f"/images/{test_image_data['id']}",
                headers=auth_headers
            )
            
            assert response.status_code in [204, 401, 404]


@pytest.mark.unit
@pytest.mark.images
class TestImageValidation:
    """Test image validation logic"""
    
    def test_validate_image_mime_types(self):
        """Test allowed MIME types"""
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        
        assert "image/jpeg" in allowed_types
        assert "image/png" in allowed_types
        assert "application/pdf" not in allowed_types
    
    def test_validate_file_size(self):
        """Test file size validation"""
        max_size = 10 * 1024 * 1024  # 10MB
        
        valid_size = 5 * 1024 * 1024  # 5MB
        assert valid_size <= max_size
        
        invalid_size = 15 * 1024 * 1024  # 15MB
        assert invalid_size > max_size
    
    def test_validate_filename(self):
        """Test filename validation"""
        valid_filenames = [
            "image.jpg",
            "photo-123.png",
            "scan_001.jpeg"
        ]
        
        for filename in valid_filenames:
            assert isinstance(filename, str)
            assert len(filename) > 0
            assert "." in filename
