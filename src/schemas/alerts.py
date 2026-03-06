from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class AlertType(str, Enum):
    """Alert type categories"""
    DISEASE_DETECTED = "disease_detected"
    QUALITY_WARNING = "quality_warning"
    YIELD_ALERT = "yield_alert"
    EXPORT_REJECTION = "export_rejection"
    SYSTEM_NOTIFICATION = "system_notification"

class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertBase(BaseModel):
    """Base alert schema"""
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message/description")
    alert_type: AlertType = Field(..., description="Type of alert")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    related_detection_id: Optional[UUID] = Field(None, description="Related detection ID if applicable")
    related_image_id: Optional[UUID] = Field(None, description="Related image ID if applicable")
    metadata: Optional[dict] = Field(None, description="Additional alert metadata")

class AlertCreate(AlertBase):
    """Schema for creating a new alert"""
    user_id: UUID = Field(..., description="User ID who receives the alert")

class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    is_acknowledged: Optional[bool] = Field(None, description="Mark alert as acknowledged")
    is_active: Optional[bool] = Field(None, description="Mark alert as active/inactive")

class AlertResponse(AlertBase):
    """Alert response schema"""
    id: UUID = Field(..., description="Alert ID")
    user_id: UUID = Field(..., description="User ID")
    is_acknowledged: bool = Field(..., description="Whether alert has been acknowledged")
    is_active: bool = Field(..., description="Whether alert is active")
    created_at: datetime = Field(..., description="Alert creation timestamp")
    acknowledged_at: Optional[datetime] = Field(None, description="Alert acknowledgment timestamp")
    
    class Config:
        from_attributes = True

class AlertListResponse(BaseModel):
    """Response schema for listing alerts"""
    alerts: List[AlertResponse]
    total: int
    unread_count: int
    critical_count: int

class AlertStatsResponse(BaseModel):
    """Alert statistics response"""
    user_id: UUID
    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    by_type: dict = Field(..., description="Alert count by type")
    by_severity: dict = Field(..., description="Alert count by severity")
    recent_critical: List[AlertResponse] = Field(..., description="Recent critical alerts")
    generated_at: datetime
