from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class DetectionCreate(BaseModel):
    """Schema for creating a detection request"""
    image_id: UUID
    user_id: UUID

class BoundingBox(BaseModel):
    """Schema for bounding box coordinates"""
    x: float
    y: float
    width: float
    height: float

class DetectionResponse(BaseModel):
    """Schema for detection response"""
    detection_id: UUID
    user_id: UUID
    image_id: UUID
    fruit_type: str
    confidence: float
    bounding_box: BoundingBox
    created_at: datetime

class BatchDetectionRequest(BaseModel):
    """Schema for batch detection request"""
    image_ids: List[UUID]
    # user_id will come from authentication, no need to include in request

class BatchDetectionResponse(BaseModel):
    """Schema for batch detection response"""
    results: List[DetectionResponse]
    total_count: int
    success_count: int
    failed_count: int
