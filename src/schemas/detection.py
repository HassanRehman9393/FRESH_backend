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
    # Visualization fields
    annotated_image_url: Optional[str] = None
    annotated_image_filename: Optional[str] = None

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

class ProcessingOptions(BaseModel):
    """Options for complete detection processing"""
    detect_diseases: bool = Field(default=True, description="Run disease detection on fruits")
    check_weather: bool = Field(default=True, description="Fetch weather data for orchard location")
    generate_alerts: bool = Field(default=True, description="Generate alerts for critical findings")

class CompleteDetectionRequest(BaseModel):
    """Request schema for complete detection processing"""
    image_ids: List[UUID] = Field(..., description="List of image IDs to process")
    orchard_id: Optional[str] = Field(None, description="Orchard ID for weather and alerts context")
    options: ProcessingOptions = Field(default_factory=ProcessingOptions, description="Processing options")

class DetectionSummary(BaseModel):
    """Summary of detection results"""
    total_fruits: int = Field(..., description="Total number of fruits detected")
    healthy_count: int = Field(default=0, description="Number of healthy fruits")
    diseased_count: int = Field(default=0, description="Number of diseased fruits")
    critical_issues: List[str] = Field(default_factory=list, description="List of critical issues found")

class CompleteDetectionResponse(BaseModel):
    """Complete detection response with all integrated data"""
    detections: List[DetectionResponse] = Field(..., description="Fruit detection results")
    diseases: Optional[List[Any]] = Field(None, description="Disease detection results")
    weather_context: Optional[Dict[str, Any]] = Field(None, description="Weather data for orchard")
    auto_alerts: Optional[List[Dict[str, Any]]] = Field(None, description="Auto-generated alerts")
    summary: DetectionSummary = Field(..., description="Summary of results")
