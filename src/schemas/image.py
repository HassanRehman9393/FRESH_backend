from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class ImageCreateResponse(BaseModel):
    id: UUID
    user_id: UUID
    file_path: str
    file_name: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

class ImageGetResponse(BaseModel):
    id: UUID
    user_id: UUID
    file_path: str
    file_name: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

class MultispectralUploadResponse(BaseModel):
    """Response for multispectral image upload"""
    complete_sets: List[Dict[str, Any]]  # Successfully processed sets
    incomplete_sets: List[Dict[str, Any]]  # Sets missing bands
    composite_images: List[ImageCreateResponse]  # Generated composite images
    band_images: List[ImageCreateResponse]  # All uploaded band images
    total_uploads: int
    processed_sets: int
    discarded_images: int
