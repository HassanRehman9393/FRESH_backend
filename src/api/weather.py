"""
Weather API Endpoints
Real-time weather data and forecasts
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
from src.schemas.weather import (
    CurrentWeatherResponse, 
    WeatherDataResponse,
    WeatherForecastResponse
)
from src.services.weather_service import weather_service
from src.core.supabase_client import supabase
from src.api.deps import get_current_user
from src.schemas.user import UserResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current/{orchard_id}", response_model=CurrentWeatherResponse)
async def get_current_weather(
    orchard_id: str,
    use_cache: bool = Query(default=True, description="Use cached data if available"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get current weather for a specific orchard
    
    - **orchard_id**: UUID of the orchard
    - **use_cache**: Whether to use cached data (default: true)
    
    Returns real-time weather data including temperature, humidity, rainfall, etc.
    """
    try:
        # Verify orchard ownership
        orchard_response = supabase.table("orchards")\
            .select("*")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        orchard = orchard_response.data[0]
        
        # Fetch weather data
        weather_data = await weather_service.fetch_current_weather(
            orchard_id=orchard_id,
            latitude=float(orchard["latitude"]),
            longitude=float(orchard["longitude"]),
            use_cache=use_cache
        )
        
        # Extract recorded_at based on whether it's dict or object
        if isinstance(weather_data, dict):
            recorded_at = weather_data.get("recorded_at")
        else:
            recorded_at = weather_data.recorded_at
        
        return CurrentWeatherResponse(
            orchard_id=orchard_id,
            orchard_name=orchard["name"],
            location={
                "latitude": float(orchard["latitude"]),
                "longitude": float(orchard["longitude"])
            },
            weather=weather_data,
            cached=use_cache,
            last_updated=recorded_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current weather: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch weather data: {str(e)}"
        )


@router.get("/forecast/{orchard_id}", response_model=List[WeatherForecastResponse])
async def get_weather_forecast(
    orchard_id: str,
    days: int = Query(default=5, ge=1, le=7, description="Number of forecast days (1-7)"),
    use_cache: bool = Query(default=True, description="Use cached data if available"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get weather forecast for a specific orchard
    
    - **orchard_id**: UUID of the orchard
    - **days**: Number of days to forecast (1-7, default: 5)
    - **use_cache**: Whether to use cached data (default: true)
    
    Returns hourly forecast data for the specified number of days
    """
    try:
        # Verify orchard ownership
        orchard_response = supabase.table("orchards")\
            .select("*")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        orchard = orchard_response.data[0]
        
        # Fetch forecast data
        forecast_data = await weather_service.fetch_forecast(
            orchard_id=orchard_id,
            latitude=float(orchard["latitude"]),
            longitude=float(orchard["longitude"]),
            days=days,
            use_cache=use_cache
        )
        
        return forecast_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching forecast: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch forecast data: {str(e)}"
        )


@router.get("/history/{orchard_id}", response_model=List[WeatherDataResponse])
async def get_weather_history(
    orchard_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date (default: 7 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: now)"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get historical weather data for a specific orchard
    
    - **orchard_id**: UUID of the orchard
    - **start_date**: Start date for history (default: 7 days ago)
    - **end_date**: End date for history (default: now)
    
    Returns stored weather records from the database
    """
    try:
        # Verify orchard ownership
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # Fetch historical data
        response = supabase.table("weather_data")\
            .select("*")\
            .eq("orchard_id", orchard_id)\
            .gte("recorded_at", start_date.isoformat())\
            .lte("recorded_at", end_date.isoformat())\
            .order("recorded_at", desc=True)\
            .execute()
        
        return response.data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching weather history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch weather history"
        )


@router.post("/update/{orchard_id}", response_model=CurrentWeatherResponse)
async def force_weather_update(
    orchard_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Force an immediate weather data update for an orchard
    
    - **orchard_id**: UUID of the orchard
    
    Bypasses cache and fetches fresh data from OpenWeatherMap API
    """
    try:
        # Verify orchard ownership
        orchard_response = supabase.table("orchards")\
            .select("*")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        orchard = orchard_response.data[0]
        
        # Force fresh fetch (no cache)
        weather_data = await weather_service.fetch_current_weather(
            orchard_id=orchard_id,
            latitude=float(orchard["latitude"]),
            longitude=float(orchard["longitude"]),
            use_cache=False
        )
        
        logger.info(f"Forced weather update for orchard {orchard_id}")
        
        return CurrentWeatherResponse(
            orchard_id=orchard_id,
            orchard_name=orchard["name"],
            location={
                "latitude": float(orchard["latitude"]),
                "longitude": float(orchard["longitude"])
            },
            weather=weather_data,
            cached=False,
            last_updated=weather_data.recorded_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error forcing weather update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update weather data: {str(e)}"
        )
