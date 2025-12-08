"""
Weather Module Pydantic Schemas
Validation models for weather integration, alerts, and disease risk analysis
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal


# ============================================================================
# ENUMS
# ============================================================================

class Severity(str, Enum):
    """Alert and risk severity levels"""
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskLevel(str, Enum):
    """Disease risk assessment levels"""
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertType(str, Enum):
    """Weather alert types"""
    high_humidity = "high_humidity"
    rainfall = "rainfall"
    extreme_temp = "extreme_temp"
    disease_risk = "disease_risk"
    wind_alert = "wind_alert"
    frost_warning = "frost_warning"


class WeatherCondition(str, Enum):
    """Weather condition categories"""
    clear = "clear"
    clouds = "clouds"
    rain = "rain"
    drizzle = "drizzle"
    thunderstorm = "thunderstorm"
    snow = "snow"
    mist = "mist"
    fog = "fog"


class DiseaseType(str, Enum):
    """Fruit disease types"""
    anthracnose = "anthracnose"
    citrus_canker = "citrus_canker"
    black_spot = "black_spot"
    fruit_fly = "fruit_fly"
    powdery_mildew = "powdery_mildew"
    sooty_mold = "sooty_mold"


class FruitType(str, Enum):
    """Supported fruit types"""
    mango = "mango"
    guava = "guava"
    citrus = "citrus"
    grapefruit = "grapefruit"
    orange = "orange"


# ============================================================================
# ORCHARD SCHEMAS
# ============================================================================

class OrchardBase(BaseModel):
    """Base orchard schema"""
    name: str = Field(..., min_length=1, max_length=255)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    area_hectares: Optional[float] = Field(None, gt=0)
    fruit_types: List[FruitType] = Field(default_factory=list)


class OrchardCreate(OrchardBase):
    """Schema for creating new orchard"""
    pass


class OrchardUpdate(BaseModel):
    """Schema for updating orchard"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    area_hectares: Optional[float] = Field(None, gt=0)
    fruit_types: Optional[List[FruitType]] = None
    is_active: Optional[bool] = None


class OrchardResponse(OrchardBase):
    """Schema for orchard response"""
    id: str
    user_id: str
    is_active: bool = True  # Default to True if column doesn't exist
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# WEATHER DATA SCHEMAS
# ============================================================================

class WeatherDataBase(BaseModel):
    """Base weather data schema - matches database columns"""
    temperature: float = Field(..., ge=-50, le=60)
    humidity: float = Field(..., ge=0, le=100)
    rainfall: float = Field(default=0, ge=0)
    wind_speed: Optional[float] = Field(None, ge=0)
    weather_condition: Optional[WeatherCondition] = None


class WeatherDataCreate(WeatherDataBase):
    """Schema for creating weather data record"""
    orchard_id: str
    source: str = "openweathermap"
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class WeatherDataResponse(WeatherDataBase):
    """Schema for weather data response"""
    id: str
    orchard_id: str
    source: str
    recorded_at: datetime
    created_at: Optional[datetime] = None  # May not be returned

    class Config:
        from_attributes = True


class CurrentWeatherResponse(BaseModel):
    """Schema for current weather API response"""
    orchard_id: str
    orchard_name: str
    location: Dict[str, float]  # {"latitude": 24.8607, "longitude": 67.0011}
    weather: WeatherDataResponse
    cached: bool = False
    last_updated: datetime


# ============================================================================
# WEATHER FORECAST SCHEMAS
# ============================================================================

class WeatherForecastBase(BaseModel):
    """Base weather forecast schema"""
    forecast_time: datetime
    temperature: float = Field(..., ge=-50, le=60)
    feels_like: Optional[float] = Field(None, ge=-50, le=60)
    humidity: float = Field(..., ge=0, le=100)
    rainfall_probability: Optional[float] = Field(None, ge=0, le=100)
    rainfall_amount: float = Field(default=0, ge=0)
    wind_speed: Optional[float] = Field(None, ge=0)
    weather_condition: Optional[WeatherCondition] = None
    weather_description: Optional[str] = None


class WeatherForecastCreate(WeatherForecastBase):
    """Schema for creating forecast record"""
    orchard_id: str
    source: str = "openweathermap"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class WeatherForecastResponse(WeatherForecastBase):
    """Schema for forecast response"""
    id: str
    orchard_id: str
    source: str
    fetched_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ForecastResponse(BaseModel):
    """Schema for complete forecast API response"""
    orchard_id: str
    orchard_name: str
    forecasts: List[WeatherForecastResponse]
    total_count: int
    fetched_at: datetime


# ============================================================================
# ALERT RULE SCHEMAS
# ============================================================================

class AlertRuleBase(BaseModel):
    """Base alert rule schema"""
    rule_name: str = Field(..., min_length=1, max_length=100)
    condition_type: str  # "humidity", "temperature", "rainfall", etc.
    threshold_value: float
    operator: str = Field(..., pattern="^(>|<|>=|<=|=)$")
    disease_risk: Optional[DiseaseType] = None
    fruit_types: List[FruitType] = Field(default_factory=list)
    alert_message_en: str
    alert_message_ur: Optional[str] = None
    recommendation_en: Optional[str] = None
    recommendation_ur: Optional[str] = None
    severity: Severity = Severity.medium
    is_enabled: bool = True


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating alert rule"""
    pass


class AlertRuleUpdate(BaseModel):
    """Schema for updating alert rule"""
    threshold_value: Optional[float] = None
    alert_message_en: Optional[str] = None
    alert_message_ur: Optional[str] = None
    recommendation_en: Optional[str] = None
    recommendation_ur: Optional[str] = None
    severity: Optional[Severity] = None
    is_enabled: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    """Schema for alert rule response"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# WEATHER ALERT SCHEMAS
# ============================================================================

class WeatherAlertBase(BaseModel):
    """Base weather alert schema - matches database structure"""
    alert_type: str = Field(..., max_length=100)
    severity: Severity
    message: str
    recommendation: Optional[str] = None


class WeatherAlertCreate(WeatherAlertBase):
    """Schema for creating weather alert"""
    orchard_id: str


class WeatherAlertUpdate(BaseModel):
    """Schema for updating alert"""
    is_active: Optional[bool] = None
    acknowledged_at: Optional[datetime] = None


class WeatherAlertResponse(WeatherAlertBase):
    """Schema for weather alert response"""
    id: str
    orchard_id: str
    is_active: bool
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Schema for paginated alert list"""
    alerts: List[WeatherAlertResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool


# ============================================================================
# DISEASE RISK SCHEMAS
# ============================================================================

class DiseaseRiskBase(BaseModel):
    """Base disease risk schema"""
    disease_type: DiseaseType
    fruit_type: FruitType
    risk_level: RiskLevel
    risk_score: float = Field(..., ge=0, le=100)
    contributing_factors: Optional[Dict[str, Any]] = None
    recommendation_en: Optional[str] = None
    recommendation_ur: Optional[str] = None
    confidence_level: Optional[float] = Field(None, ge=0, le=100)


class DiseaseRiskCreate(DiseaseRiskBase):
    """Schema for creating disease risk assessment"""
    orchard_id: str
    weather_snapshot: Optional[Dict[str, Any]] = None
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class DiseaseRiskResponse(DiseaseRiskBase):
    """Schema for disease risk response"""
    id: str
    orchard_id: str
    weather_snapshot: Optional[Dict[str, Any]] = None
    calculated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RiskAnalysisRequest(BaseModel):
    """Schema for risk analysis request"""
    orchard_id: str
    fruit_types: Optional[List[FruitType]] = None


class RiskAnalysisResponse(BaseModel):
    """Schema for risk analysis response"""
    orchard_id: str
    orchard_name: str
    risks: List[DiseaseRiskResponse]
    overall_risk_level: RiskLevel
    analysis_timestamp: datetime
    weather_conditions: Optional[Dict[str, Any]] = None


# ============================================================================
# WEATHER CACHE SCHEMAS
# ============================================================================

class WeatherCacheCreate(BaseModel):
    """Schema for creating cache entry"""
    cache_key: str = Field(..., max_length=255)
    cache_type: str  # "current", "forecast", "alerts"
    orchard_id: Optional[str] = None
    data: Dict[str, Any]
    expires_at: datetime


class WeatherCacheResponse(BaseModel):
    """Schema for cache response"""
    id: str
    cache_key: str
    cache_type: str
    orchard_id: Optional[str] = None
    data: Dict[str, Any]
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# OPENWEATHERMAP API RESPONSE SCHEMAS
# ============================================================================

class OpenWeatherCurrentResponse(BaseModel):
    """Schema for OpenWeatherMap current weather API response"""
    coord: Dict[str, float]
    weather: List[Dict[str, Any]]
    main: Dict[str, float]
    wind: Dict[str, float]
    clouds: Dict[str, int]
    dt: int
    sys: Dict[str, Any]
    timezone: int
    name: str


class OpenWeatherForecastResponse(BaseModel):
    """Schema for OpenWeatherMap forecast API response"""
    cod: str
    list: List[Dict[str, Any]]
    city: Dict[str, Any]


# ============================================================================
# UTILITY SCHEMAS
# ============================================================================

class WeatherHistoryRequest(BaseModel):
    """Schema for weather history request"""
    orchard_id: str
    start_date: datetime
    end_date: datetime
    interval: Optional[str] = "hourly"  # "hourly", "daily", "weekly"


class WeatherHistoryResponse(BaseModel):
    """Schema for weather history response"""
    orchard_id: str
    period: Dict[str, datetime]  # {"start": ..., "end": ...}
    data_points: List[WeatherDataResponse]
    total_count: int
    interval: str


class WeatherStatsResponse(BaseModel):
    """Schema for weather statistics"""
    orchard_id: str
    period: Dict[str, datetime]
    avg_temperature: float
    min_temperature: float
    max_temperature: float
    avg_humidity: float
    total_rainfall: float
    avg_wind_speed: Optional[float] = None
    dominant_condition: Optional[str] = None
    data_points_count: int


class BilingualMessage(BaseModel):
    """Schema for bilingual messages"""
    en: str
    ur: Optional[str] = None


class NotificationPayload(BaseModel):
    """Schema for notification payload"""
    user_id: str
    title: BilingualMessage
    message: BilingualMessage
    alert_id: Optional[str] = None
    orchard_id: Optional[str] = None
    severity: Severity
    action_url: Optional[str] = None
    send_push: bool = True
    send_email: bool = False
    send_sms: bool = False


# ============================================================================
# HEALTH CHECK
# ============================================================================

class WeatherServiceHealth(BaseModel):
    """Schema for weather service health check"""
    status: str  # "healthy", "degraded", "unhealthy"
    api_available: bool
    cache_available: bool
    last_update: Optional[datetime] = None
    active_orchards: int
    pending_alerts: int
    error_message: Optional[str] = None
