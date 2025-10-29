from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class DiseaseDetectionCreate(BaseModel):
    """Schema for creating a disease detection request"""
    detection_id: UUID
    user_id: UUID
    image_id: UUID

class DiseaseDetectionResponse(BaseModel):
    """Schema for disease detection response"""
    disease_detection_id: UUID
    detection_id: UUID
    user_id: UUID
    image_id: UUID
    disease_type: str = Field(..., description="One of: healthy, anthracnose, citrus_canker, unknown")
    is_diseased: bool
    disease_confidence: float = Field(..., ge=0.0, le=1.0)
    severity_level: Optional[str] = Field(None, description="One of: mild, moderate, severe, critical")
    probabilities: Optional[Dict[str, float]] = None
    created_at: datetime

class BatchDiseaseDetectionRequest(BaseModel):
    """Schema for batch disease detection request"""
    detection_ids: List[UUID] = Field(..., description="List of detection IDs to analyze for diseases")
    # user_id will come from authentication, no need to include in request

class BatchDiseaseDetectionResponse(BaseModel):
    """Schema for batch disease detection response"""
    results: List[DiseaseDetectionResponse]
    total_count: int
    success_count: int
    failed_count: int
    diseased_count: int = Field(..., description="Number of diseased fruits detected")
    healthy_count: int = Field(..., description="Number of healthy fruits detected")
