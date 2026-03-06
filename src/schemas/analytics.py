from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, date

# ================= Fruit Quality Analytics Schemas =================

class FruitQualityStats(BaseModel):
    """Statistics for a specific fruit type"""
    fruit_type: str
    total_count: int
    average_confidence: float
    ripeness_distribution: Dict[str, int] = Field(
        ..., 
        description="Distribution of ripeness levels (ripe, unripe, overripe, rotten)"
    )
    quality_score_avg: Optional[float] = Field(None, description="Average quality score (0-100)")
    defect_rate: Optional[float] = Field(None, description="Percentage of fruits with defects")
    common_defects: Optional[List[str]] = Field(None, description="Most common defect types")

class QualityAnalyticsResponse(BaseModel):
    """Response for fruit quality analytics"""
    user_id: UUID
    date_range: Dict[str, str] = Field(..., description="Start and end dates of analysis")
    total_detections: int
    total_images: int
    fruit_statistics: List[FruitQualityStats]
    overall_quality_score: float = Field(..., ge=0.0, le=100.0)
    best_performing_fruit: Optional[str] = None
    worst_performing_fruit: Optional[str] = None
    generated_at: datetime

class QualityTrendResponse(BaseModel):
    """Response for quality trend over time"""
    date: date
    total_detections: int
    average_quality_score: float
    defect_rate: float

class QualityAnalyticsTrendResponse(BaseModel):
    """Response for quality analytics with trend data"""
    user_id: UUID
    date_range: Dict[str, str]
    trends: List[QualityTrendResponse]
    generated_at: datetime

# ================= Disease Risk Analytics Schemas =================

class DiseaseTypeStats(BaseModel):
    """Statistics for a specific disease type"""
    disease_type: str
    total_cases: int
    severity_distribution: Dict[str, int] = Field(
        ..., 
        description="Distribution of severity levels (mild, moderate, severe, critical)"
    )
    average_confidence: float
    affected_fruit_types: List[str]
    risk_level: str = Field(..., description="Overall risk: low, medium, high, critical")

class DiseaseRiskAnalyticsResponse(BaseModel):
    """Response for disease risk analytics"""
    user_id: UUID
    date_range: Dict[str, str]
    total_detections: int
    diseased_count: int
    healthy_count: int
    infection_rate: float = Field(..., ge=0.0, le=100.0, description="Percentage of diseased fruits")
    disease_statistics: List[DiseaseTypeStats]
    overall_risk_level: str = Field(..., description="Overall risk: low, medium, high, critical")
    recommendations: List[str] = Field(..., description="Recommended actions based on risk level")
    generated_at: datetime

class DiseaseTrendResponse(BaseModel):
    """Response for disease trend over time"""
    date: date
    total_detections: int
    diseased_count: int
    infection_rate: float

class DiseaseRiskTrendResponse(BaseModel):
    """Response for disease risk with trend data"""
    user_id: UUID
    date_range: Dict[str, str]
    trends: List[DiseaseTrendResponse]
    generated_at: datetime

# ================= Yield Analytics Schemas =================

class FruitYieldStats(BaseModel):
    """Yield statistics for a specific fruit type"""
    fruit_type: str
    total_count: int
    marketable_count: int = Field(..., description="Count of fruits suitable for market")
    marketable_percentage: float
    average_size: Optional[str] = None
    estimated_weight_kg: Optional[float] = Field(None, description="Estimated total weight in kg")

class YieldAnalyticsResponse(BaseModel):
    """Response for yield analytics"""
    user_id: UUID
    date_range: Dict[str, str]
    total_fruit_count: int
    total_marketable_count: int
    overall_marketable_rate: float = Field(..., ge=0.0, le=100.0)
    fruit_yields: List[FruitYieldStats]
    estimated_total_weight_kg: Optional[float] = None
    best_yielding_fruit: Optional[str] = None
    generated_at: datetime

class YieldComparisonResponse(BaseModel):
    """Response for yield comparison between periods"""
    current_period: YieldAnalyticsResponse
    previous_period: Optional[YieldAnalyticsResponse] = None
    growth_rate: Optional[float] = Field(None, description="Percentage change from previous period")
    generated_at: datetime

# ================= Export Readiness Schemas =================

class ExportQualityMetrics(BaseModel):
    """Quality metrics for export assessment"""
    ripeness_compliance: float = Field(..., ge=0.0, le=100.0, description="% meeting ripeness standards")
    size_compliance: float = Field(..., ge=0.0, le=100.0, description="% meeting size standards")
    defect_compliance: float = Field(..., ge=0.0, le=100.0, description="% meeting defect-free standards")
    disease_free_rate: float = Field(..., ge=0.0, le=100.0, description="% disease-free")
    overall_compliance: float = Field(..., ge=0.0, le=100.0, description="Overall export readiness score")

class FruitExportReadiness(BaseModel):
    """Export readiness for a specific fruit type"""
    fruit_type: str
    total_count: int
    export_ready_count: int
    export_ready_percentage: float
    quality_metrics: ExportQualityMetrics
    rejection_reasons: Dict[str, int] = Field(..., description="Count of fruits rejected by reason")
    recommended_actions: List[str]

class ExportReadinessResponse(BaseModel):
    """Response for export readiness report"""
    user_id: UUID
    report_date: datetime
    date_range: Dict[str, str]
    total_fruit_analyzed: int
    total_export_ready: int
    overall_readiness_score: float = Field(..., ge=0.0, le=100.0)
    fruit_readiness: List[FruitExportReadiness]
    market_recommendations: List[str] = Field(..., description="Recommendations for different markets")
    compliance_summary: Dict[str, Any] = Field(..., description="Summary of compliance with export standards")
    generated_at: datetime

class ExportReadinessDetailRequest(BaseModel):
    """Request for detailed export readiness analysis"""
    target_market: Optional[str] = Field(None, description="Target export market (e.g., 'EU', 'US', 'Asia')")
    quality_standards: Optional[str] = Field(None, description="Quality standard to apply (e.g., 'premium', 'standard')")

# ================= General Analytics Request Schemas =================

class DateRangeRequest(BaseModel):
    """Request schema for date range queries"""
    start_date: Optional[date] = Field(None, description="Start date for analytics (defaults to 30 days ago)")
    end_date: Optional[date] = Field(None, description="End date for analytics (defaults to today)")

class AnalyticsSummaryResponse(BaseModel):
    """Comprehensive analytics summary"""
    user_id: UUID
    date_range: Dict[str, str]
    quality_score: float = Field(..., ge=0.0, le=100.0)
    disease_risk_level: str
    infection_rate: float
    total_yield: int
    marketable_yield: int
    export_readiness_score: float = Field(..., ge=0.0, le=100.0)
    top_performing_fruit: Optional[str] = None
    areas_for_improvement: List[str]
    generated_at: datetime
