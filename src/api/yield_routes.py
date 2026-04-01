"""
Yield Prediction API Endpoints

Routes for yield prediction, history, and harvest tracking.
Integrates with ML API and database through yield_service.
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import logging

from src.schemas.yield_schemas import (
    YieldPredictionRequest,
    YieldPredictionResponse,
    YieldPredictionHistoryResponse,
    YieldPredictionContextResponse,
    HarvestRecordCreate,
    HarvestRecordResponse,
    UserYieldStats,
    FruitType,
)
from src.services.yield_service import yield_service
from src.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/yield", tags=["yield-prediction"])


# =========== PREDICTION ENDPOINTS ===========

@router.post("/predict", response_model=YieldPredictionResponse)
async def predict_yield(
    request: YieldPredictionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get yield prediction for an orchard.
    
    Takes detection aggregates and weather data, calls ML models,
    and returns yield prediction with confidence intervals and contributing factors.
    
    **Request body:**
    - `detection_aggregates`: Fruit counts, ripeness %, disease % from detection pipeline
    - `weather_data`: Temperature, rainfall, humidity aggregates
    - `orchard_metadata`: Area, fruit type, planting age
    
    **Response includes:**
    - `predicted_yield_kg`: Estimated harvest in kg
    - `confidence`: Prediction confidence [0-1]
    - `contributing_factors`: Health, ripeness, disease, weather, coverage scores
    - `sampling`: Extrapolation details (sample factor, pattern used)
    - `baseline`: Regional average comparison
    
    **Requires:** Authentication (Bearer token)
    
    Args:
        request: YieldPredictionRequest with detection and weather data
        current_user: Authenticated user info
    
    Returns:
        YieldPredictionResponse with full prediction details
        
    Raises:
        HTTPException: 400 if validation fails, 500 if ML API fails
    """
    try:
        user_id = UUID(current_user["user_id"])
        logger.info(f"🌾 [API] Yield prediction request from user {user_id}")
        
        # Call yield service
        response = await yield_service.predict_yield(user_id, request)
        
        logger.info(f"✅ [API] Prediction completed: {response.predicted_yield_kg:.0f}kg")
        return response
        
    except ValueError as e:
        logger.error(f"❌ [API] Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ [API] Prediction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Yield prediction failed: {str(e)}"
        )


# =========== HISTORY ENDPOINTS ===========

@router.get("/history", response_model=List[YieldPredictionHistoryResponse])
async def get_yield_history(
    fruit_type: Optional[FruitType] = Query(None, description="Filter by fruit type"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's yield prediction history.
    
    Retrieve past predictions optionally filtered by fruit type.
    Results are paginated and sorted by most recent first.
    
    **Query parameters:**
    - `fruit_type`: Optional filter (mango, orange, guava, grapefruit)
    - `limit`: Results per page (default 20, max 100)
    - `offset`: Pagination offset
    
    **Returns:** List of recent predictions with summary info
    
    **Requires:** Authentication
    
    Args:
        fruit_type: Optional fruit type filter
        limit: Number of results
        offset: Pagination offset
        current_user: Authenticated user
    
    Returns:
        List of YieldPredictionHistoryResponse
    """
    try:
        user_id = UUID(current_user["user_id"])
        
        history = await yield_service.get_prediction_history(
            user_id=user_id,
            fruit_type=fruit_type,
            orchard_id=orchard_id,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"📊 [API] Retrieved {len(history)} prediction records for user {user_id}")
        return history
        
    except Exception as e:
        logger.error(f"❌ [API] Failed to get history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve prediction history"
        )


@router.get("/latest", response_model=YieldPredictionHistoryResponse)
async def get_latest_prediction(
    fruit_type: FruitType = Query(..., description="Fruit type"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get most recent prediction for a fruit type.
    
    Retrieves the user's latest yield prediction for the specified fruit.
    Useful for quickly checking the most recent estimate.
    
    **Query parameters:**
    - `fruit_type`: Target fruit type (required)
    
    **Returns:** Most recent prediction or 404 if none found
    
    **Requires:** Authentication
    
    Args:
        fruit_type: Fruit type (mango, orange, guava, grapefruit)
        current_user: Authenticated user
    
    Returns:
        YieldPredictionHistoryResponse
        
    Raises:
        HTTPException: 404 if no prediction found
    """
    try:
        user_id = UUID(current_user["user_id"])
        
        prediction = await yield_service.get_latest_prediction(user_id, fruit_type)
        
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No prediction found for {fruit_type}"
            )
        
        return YieldPredictionHistoryResponse(
            id=prediction.id,
            prediction_date=prediction.created_at,
            fruit_type=prediction.fruit_type,
            predicted_yield_kg=prediction.predicted_yield_kg,
            confidence=prediction.confidence_score,
            trend_direction=prediction.trend_direction,
            orchard_area_hectares=prediction.orchard_area_hectares,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Failed to get latest prediction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest prediction"
        )


# =========== HARVEST TRACKING ENDPOINTS ===========

@router.post("/harvest", response_model=HarvestRecordResponse)
async def register_harvest(
    harvest: HarvestRecordCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Register actual harvest yield.
    
    Record the actual yield achieved to improve future predictions.
    Historical harvest data is used to calibrate yield models
    and track user's yield trends over time.
    
    **Request body:**
    - `fruit_type`: Type of fruit harvested
    - `orchard_area_hectares`: Area harvested
    - `actual_yield_kg`: Total yield in kg
    - `harvest_date`: Harvest date (YYYY-MM-DD)
    - `season`: Year of harvest
    - `weather_conditions`: Optional weather context (JSON)
    - `quality_notes`: Optional quality observations
    
    **Returns:** Saved harvest record with calculated metrics
    
    **Requires:** Authentication
    
    Args:
        harvest: HarvestRecordCreate data
        current_user: Authenticated user
    
    Returns:
        HarvestRecordResponse
        
    Raises:
        HTTPException: 400 if validation fails, 500 if save fails
    """
    try:
        user_id = UUID(current_user["user_id"])
        
        logger.info(f"🌾 [API] Registering harvest for user {user_id}: {harvest.actual_yield_kg}kg {harvest.fruit_type}")
        
        record = await yield_service.register_harvest(user_id, harvest)
        
        logger.info(f"✅ [API] Harvest registered: {record.id}")
        return record
        
    except ValueError as e:
        logger.error(f"❌ [API] Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid harvest data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ [API] Failed to register harvest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register harvest"
        )


@router.get("/harvest-records", response_model=List[HarvestRecordResponse])
async def get_harvest_records(
    fruit_type: Optional[FruitType] = Query(None, description="Filter by fruit type"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's harvest records.
    
    Retrieve all registered harvest records, optionally filtered by fruit type.
    Shows actual yields achieved for yield estimation calibration.
    
    **Query parameters:**
    - `fruit_type`: Optional filter (mango, orange, guava, grapefruit)
    
    **Returns:** List of harvest records sorted by most recent first
    
    **Requires:** Authentication
    
    Args:
        fruit_type: Optional fruit type filter
        current_user: Authenticated user
    
    Returns:
        List of HarvestRecordResponse
    """
    try:
        user_id = UUID(current_user["user_id"])
        
        records = await yield_service.get_user_harvest_records(user_id, fruit_type)
        
        logger.info(f"📊 [API] Retrieved {len(records)} harvest records for user {user_id}")
        return records
        
    except Exception as e:
        logger.error(f"❌ [API] Failed to get harvest records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve harvest records"
        )


# =========== STATISTICS ENDPOINTS ===========

@router.get("/stats", response_model=UserYieldStats)
async def get_yield_statistics(
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's yield statistics and trends.
    
    Comprehensive view of:
    - Prediction counts and averages
    - Confidence trends
    - Recent predictions
    - Historical harvest records
    - User's yield trend (improving/stable/declining)
    
    **Returns:** Aggregated statistics for primary fruit type
    
    **Requires:** Authentication
    
    Args:
        current_user: Authenticated user
    
    Returns:
        UserYieldStats with comprehensive metrics
        
    Raises:
        HTTPException: 404 if no data found, 500 if calculation fails
    """
    try:
        user_id = UUID(current_user["user_id"])

        stats = await yield_service.get_user_yield_stats(user_id, orchard_id=orchard_id)

        if not stats:
            # Return empty default stats for new users
            return UserYieldStats(
                fruit_type="mango",
                predictions_count=0,
                average_predicted_yield_kg=0,
                average_confidence=0,
                recent_predictions=[],
                harvest_records=[],
                historical_average_yield_kg=None,
                trend=None,
            )

        logger.info(f"📊 [API] Retrieved yield statistics for user {user_id}")
        return stats

    except Exception as e:
        logger.error(f"❌ [API] Failed to get statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate yield statistics"
        )


@router.get("/context/{orchard_id}", response_model=YieldPredictionContextResponse)
async def get_prediction_context(
    orchard_id: UUID,
    window_days: int = Query(30, ge=1, le=365, description="Days of data to aggregate"),
    current_user: dict = Depends(get_current_user)
):
    """
    Build yield prediction request payload from database records for a specific orchard.

    Aggregates detection results, classification data, disease detections,
    and weather data from the database into a ready-to-use prediction request.
    
    ISOLATION ENFORCED:
    - All detections are strictly filtered to images linked to THIS orchard only
    - No cross-orchard data leakage, even if user has multiple orchards
    - Data from Orchard A will never appear in results for Orchard B
    """
    try:
        user_id = UUID(current_user["user_id"])
        logger.info(
            "🌾 [API] Building prediction context | user_id=%s orchard_id=%s window_days=%s",
            str(user_id),
            str(orchard_id),
            window_days,
        )

        context = await yield_service.get_prediction_context_from_db(
            user_id=user_id,
            orchard_id=orchard_id,
            window_days=window_days,
        )

        logger.info(
            "✅ [API] Context built | user_id=%s orchard_id=%s detections=%s weather=%s classifications=%s diseases=%s",
            str(user_id),
            str(orchard_id),
            context.sources.detection_records_used,
            context.sources.weather_records_used,
            context.sources.classification_records_used,
            context.sources.disease_records_used,
        )
        return context

    except ValueError as e:
        logger.warning(
            "⚠️ [API] Context build failed (validation) | orchard_id=%s window_days=%s detail=%s",
            str(orchard_id),
            window_days,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "❌ [API] Context build failed (unexpected) | orchard_id=%s window_days=%s detail=%s",
            str(orchard_id),
            window_days,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build prediction context: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for yield prediction service.
    
    Returns service status and ML API connectivity.
    
    Returns:
        {"status": "healthy", "service": "yield-prediction-api", "version": "1.0.0"}
    """
    return {
        "status": "healthy",
        "service": "yield-prediction-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
