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

class ClassificationResult(BaseModel):
    """Schema for classification results"""
    ripeness_level: Optional[str] = None  # ripe, unripe, overripe, rotten
    ripeness_confidence: Optional[float] = None
    color: Optional[str] = None
    size: Optional[str] = None  # small, medium, large
    quality_score: Optional[float] = None  # 0-100
    defects: Optional[List[str]] = None

class DetectionResponse(BaseModel):
    """Schema for detection response with optional classification"""
    detection_id: UUID
    user_id: UUID
    image_id: UUID
    fruit_type: str
    confidence: float
    bounding_box: BoundingBox
    classification: Optional[ClassificationResult] = None  # Add classification data
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
