"""
Yield Prediction Schemas

Pydantic models for yield prediction requests and responses.
Ensures type safety and validation for API interactions.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class FruitType(str, Enum):
    """Supported fruit types (Pakistan-only)"""
    MANGO = "mango"
    ORANGE = "orange"
    GUAVA = "guava"
    GRAPEFRUIT = "grapefruit"


class SamplingPattern(str, Enum):
    """Supported sampling patterns"""
    W_SHAPED = "w-shaped"
    ZIGZAG = "zigzag"


class TrendDirection(str, Enum):
    """Yield trend directions"""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


class ModelUsed(str, Enum):
    """ML models used for prediction"""
    XGBOOST = "xgboost"
    LINEAR_REGRESSION = "linear_regression"
    BASELINE = "baseline"


# =========== REQUEST SCHEMAS ===========

class DetectionAggregateData(BaseModel):
    """Aggregated detection data from ML API"""
    total_fruits: int = Field(..., ge=0, description="Total fruit count")
    ripe_percentage: float = Field(..., ge=0, le=100, description="Percentage of ripe fruits")
    unripe_percentage: float = Field(..., ge=0, le=100, description="Percentage of unripe fruits")
    overripe_percentage: float = Field(..., ge=0, le=100, description="Percentage of overripe fruits")
    disease_percentage: float = Field(..., ge=0, le=100, description="Percentage of diseased fruits")
    average_confidence: float = Field(..., ge=0, le=1, description="Average detection confidence")
    coverage_score: float = Field(..., ge=0, le=1, description="Coverage percentage as decimal")
    detection_count: int = Field(default=0, ge=0, description="Number of detection events")


class WeatherData(BaseModel):
    """Weather aggregation data"""
    temperature_avg: float = Field(..., description="Average temperature (°C)")
    temperature_min: Optional[float] = Field(None, description="Minimum temperature (°C)")
    temperature_max: Optional[float] = Field(None, description="Maximum temperature (°C)")
    rainfall_sum: float = Field(..., ge=0, description="Total rainfall (mm)")
    humidity_avg: float = Field(..., ge=0, le=100, description="Average humidity (%)")
    humidity_min: Optional[float] = Field(None, ge=0, le=100, description="Minimum humidity (%)")
    humidity_max: Optional[float] = Field(None, ge=0, le=100, description="Maximum humidity (%)")
    data_points: int = Field(default=30, ge=1, description="Number of data points used")


class OrchardMetadata(BaseModel):
    """Orchard information"""
    area_hectares: float = Field(..., gt=0, description="Orchard area in hectares")
    fruit_type: FruitType = Field(..., description="Primary fruit type")
    days_since_planting: int = Field(default=180, ge=0, description="Days since tree planting")
    orchard_id: Optional[UUID] = Field(None, description="Optional reference to specific orchard")


class YieldPredictionRequest(BaseModel):
    """Request for yield prediction"""
    detection_aggregates: DetectionAggregateData
    weather_data: WeatherData
    orchard_metadata: OrchardMetadata


# =========== RESPONSE SCHEMAS ===========

class ContributingFactors(BaseModel):
    """Contributing factors to yield prediction"""
    health_score: float = Field(..., ge=0, le=1, description="Plant health [0-1]")
    ripeness_condition: float = Field(..., ge=0, le=1, description="Ripeness maturity [0-1]")
    disease_impact: float = Field(..., ge=0, le=1, description="Disease severity [0-1]")
    weather_favorability: float = Field(..., ge=0, le=1, description="Weather conditions [0-1]")
    data_coverage: float = Field(..., ge=0, le=1, description="Data coverage percentage [0-1]")


class SamplingDetails(BaseModel):
    """Sampling pattern and extrapolation details"""
    extrapolated_fruit_count: int = Field(..., ge=0, description="Total fruits after extrapolation")
    sampling_factor: float = Field(..., gt=0, description="Multiplier from sample to full area")
    pattern_used: SamplingPattern
    sample_coverage_percent: float = Field(..., ge=0, le=100, description="Percentage of area sampled")
    sampling_confidence: float = Field(..., ge=0, le=1, description="Confidence in extrapolation")


class BaselineComparison(BaseModel):
    """Regional baseline comparison"""
    regional_baseline_yield_kg_per_hectare: float = Field(..., description="Regional average yield")
    regional_std_dev_kg: float = Field(..., description="Standard deviation")
    variance_from_baseline_percent: float = Field(..., description="Variance from regional average (%)")


class YieldPredictionResponse(BaseModel):
    """Full yield prediction response"""
    prediction_id: UUID
    success: bool = True
    
    # Core prediction
    predicted_yield_kg: float = Field(..., description="Total predicted yield in kg")
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence [0-1]")
    confidence_interval: Dict[str, float] = Field(..., description="95% CI bounds")
    
    # Analysis
    contributing_factors: ContributingFactors
    trend_direction: TrendDirection
    model_used: ModelUsed
    
    # Detailed breakdown
    sampling: SamplingDetails
    baseline: BaselineComparison
    
    # Metadata
    fruit_type: FruitType
    orchard_area_hectares: float
    aggregation_period_days: int = 30
    timestamp: datetime
    prediction_used_fallback: bool = False


# =========== DATABASE SCHEMAS ===========

class YieldPredictionCreate(BaseModel):
    """Schema for creating yield prediction record"""
    user_id: UUID
    fruit_type: FruitType
    orchard_id: Optional[UUID] = None
    prediction_season: int
    
    orchard_area_hectares: float
    predicted_yield_kg: float
    confidence_score: float
    confidence_lower_bound_kg: float
    confidence_upper_bound_kg: float
    
    health_score: float
    ripeness_percentage: float
    disease_percentage: float
    weather_favorability: float
    coverage_score: float
    
    total_fruits_detected: int
    extrapolated_fruit_count: int
    sampling_factor: float
    sampling_pattern: SamplingPattern
    sampling_confidence: float
    detection_count: int
    
    regional_baseline_yield_kg: float
    regional_baseline_std_dev: float
    variance_from_baseline_percent: float
    
    trend_direction: TrendDirection
    model_used: ModelUsed
    model_version: Optional[str] = None
    
    user_historical_average_yield_kg: Optional[float] = None
    user_historical_trend: Optional[str] = None
    
    aggregation_period_days: int = 30
    prediction_used_fallback: bool = False
    notes: Optional[str] = None


class YieldPredictionDB(YieldPredictionCreate):
    """Database representation of yield prediction"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class YieldPredictionHistoryResponse(BaseModel):
    """Response for yield prediction history"""
    id: UUID
    prediction_date: datetime
    fruit_type: FruitType
    predicted_yield_kg: float
    confidence: float
    trend_direction: TrendDirection
    orchard_area_hectares: float


# =========== HARVEST RECORD SCHEMAS ===========

class HarvestRecordCreate(BaseModel):
    """Schema for registering actual harvest"""
    fruit_type: FruitType
    orchard_area_hectares: float = Field(..., gt=0, description="Orchard area in hectares")
    actual_yield_kg: float = Field(..., gt=0, description="Actual harvested yield in kg")
    harvest_date: str = Field(..., description="Harvest date (YYYY-MM-DD)")
    season: int = Field(..., description="Harvest year")
    weather_conditions: Optional[Dict[str, Any]] = Field(
        None,
        description="Weather during harvest season"
    )
    quality_notes: Optional[str] = Field(None, description="Quality observations")


class HarvestRecordResponse(BaseModel):
    """Response for harvest record"""
    id: UUID
    user_id: UUID
    fruit_type: FruitType
    yield_per_hectare: float
    actual_yield_kg: float
    harvest_date: str
    season: int
    created_at: datetime


# =========== SUMMARY SCHEMAS ===========

class YieldPredictionSummary(BaseModel):
    """Summary statistics for yield predictions"""
    total_predictions: int
    average_confidence: float
    average_yield_kg: float
    fruit_type_breakdown: Dict[FruitType, int]
    trend_breakdown: Dict[TrendDirection, int]
    last_prediction_date: Optional[datetime] = None


class UserYieldStats(BaseModel):
    """User's yield statistics and trends"""
    fruit_type: FruitType
    predictions_count: int
    average_predicted_yield_kg: float
    average_confidence: float
    recent_predictions: List[YieldPredictionHistoryResponse]
    harvest_records: List[HarvestRecordResponse]
    historical_average_yield_kg: Optional[float] = None
    trend: Optional[TrendDirection] = None
