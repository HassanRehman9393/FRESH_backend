"""
Weather Service
Handles OpenWeatherMap API integration, caching, and weather data management
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from src.core.config import settings
from src.core.supabase_client import supabase
from src.schemas.weather import (
    WeatherDataCreate,
    WeatherDataResponse,
    WeatherForecastCreate,
    WeatherForecastResponse,
    CurrentWeatherResponse,
    ForecastResponse,
    WeatherCacheCreate,
    WeatherCondition,
    DailyForecastResponse
)

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service for fetching and managing weather data from OpenWeatherMap API
    """
    
    def __init__(self):
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.api_key = settings.openweather_api_key
        self.cache_ttl_minutes = settings.weather_cache_ttl_minutes
        self.timeout = httpx.Timeout(10.0, connect=5.0)
    
    async def _make_api_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to OpenWeatherMap API with error handling
        """
        params["appid"] = self.api_key
        params["units"] = "metric"  # Celsius temperature
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"OpenWeatherMap API timeout for {endpoint}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Weather service timeout. Please try again."
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenWeatherMap API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Weather API authentication failed. Please contact administrator."
                )
            elif e.response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Weather data not found for this location."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Weather service temporarily unavailable."
                )
        except Exception as e:
            logger.error(f"Unexpected error fetching weather data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch weather data."
            )
    
    def _parse_current_weather(
        self, 
        api_response: Dict[str, Any], 
        orchard_id: str
    ) -> WeatherDataCreate:
        """
        Parse OpenWeatherMap current weather API response into our schema
        Only use fields that exist in the database table
        """
        main = api_response.get("main", {})
        wind = api_response.get("wind", {})
        rain = api_response.get("rain", {})
        weather = api_response.get("weather", [{}])[0]
        
        return WeatherDataCreate(
            orchard_id=orchard_id,
            temperature=main.get("temp", 0.0),
            feels_like=main.get("feels_like"),
            temp_min=main.get("temp_min"),
            temp_max=main.get("temp_max"),
            humidity=main.get("humidity", 0.0),
            pressure=main.get("pressure"),
            rainfall=rain.get("1h", 0.0),  # rainfall in last 1 hour
            wind_speed=wind.get("speed"),
            visibility=api_response.get("visibility"),
            weather_condition=self._map_weather_condition(weather.get("main", "")),
            description=weather.get("description"),
            source="openweathermap",
            recorded_at=datetime.fromtimestamp(api_response.get("dt", datetime.utcnow().timestamp()))
        )
    
    def _map_weather_condition(self, condition: str) -> Optional[WeatherCondition]:
        """
        Map OpenWeatherMap weather condition to our enum
        """
        condition_mapping = {
            "Clear": WeatherCondition.clear,
            "Clouds": WeatherCondition.clouds,
            "Rain": WeatherCondition.rain,
            "Drizzle": WeatherCondition.drizzle,
            "Thunderstorm": WeatherCondition.thunderstorm,
            "Snow": WeatherCondition.snow,
            "Mist": WeatherCondition.mist,
            "Fog": WeatherCondition.fog,
        }
        return condition_mapping.get(condition)
    
    def _parse_forecast_data(
        self,
        api_response: Dict[str, Any],
        orchard_id: str
    ) -> List[WeatherForecastResponse]:
        """
        Parse OpenWeatherMap 5-day forecast API response
        Returns WeatherForecastResponse objects directly
        """
        forecasts = []
        forecast_list = api_response.get("list", [])
        
        for item in forecast_list:
            main = item.get("main", {})
            wind = item.get("wind", {})
            rain = item.get("rain", {})
            weather = item.get("weather", [{}])[0]
            forecast_time = datetime.fromtimestamp(item.get("dt"))
            
            forecast = WeatherForecastResponse(
                id=f"{orchard_id}_{item.get('dt')}",  # Generate unique ID
                orchard_id=orchard_id,
                forecast_time=forecast_time,
                temperature=main.get("temp", 0.0),
                feels_like=main.get("feels_like"),
                humidity=main.get("humidity", 0.0),
                rainfall_probability=item.get("pop", 0.0) * 100,  # Convert to percentage
                rainfall_amount=rain.get("3h", 0.0),  # 3-hour rainfall
                wind_speed=wind.get("speed"),
                weather_condition=self._map_weather_condition(weather.get("main", "")),
                weather_description=weather.get("description"),
                source="openweathermap",
                fetched_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            forecasts.append(forecast)
        
        return forecasts
    
    async def _get_cached_weather(
        self, 
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached weather data if not expired
        """
        try:
            result = supabase.table("weather_cache")\
                .select("*")\
                .eq("cache_key", cache_key)\
                .gte("expires_at", datetime.utcnow().isoformat())\
                .execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Cache hit for key: {cache_key}")
                return result.data[0]["data"]
            
            logger.info(f"Cache miss for key: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving cache: {str(e)}")
            return None
    
    async def _set_cache(
        self,
        cache_key: str,
        cache_type: str,
        orchard_id: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Store weather data in cache
        """
        try:
            expires_at = datetime.utcnow() + timedelta(minutes=self.cache_ttl_minutes)
            
            # Check if cache entry exists
            existing = supabase.table("weather_cache")\
                .select("id")\
                .eq("cache_key", cache_key)\
                .execute()
            
            if existing.data:
                # Update existing cache
                supabase.table("weather_cache")\
                    .update({
                        "data": data,
                        "expires_at": expires_at.isoformat()
                    })\
                    .eq("cache_key", cache_key)\
                    .execute()
            else:
                # Create new cache entry
                cache_data = WeatherCacheCreate(
                    cache_key=cache_key,
                    cache_type=cache_type,
                    orchard_id=orchard_id,
                    data=data,
                    expires_at=expires_at
                )
                
                supabase.table("weather_cache")\
                    .insert(cache_data.model_dump())\
                    .execute()
            
            logger.info(f"Cache set for key: {cache_key}")
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            # Don't raise error - caching is optional
    
    async def fetch_current_weather(
        self,
        orchard_id: str,
        latitude: float,
        longitude: float,
        use_cache: bool = True
    ) -> WeatherDataResponse:
        """
        Fetch current weather for orchard location
        """
        cache_key = f"weather:current:{orchard_id}"
        
        # Try cache first
        if use_cache:
            cached_data = await self._get_cached_weather(cache_key)
            if cached_data:
                return WeatherDataResponse(**cached_data)
        
        # Fetch from API
        params = {
            "lat": latitude,
            "lon": longitude
        }
        
        api_response = await self._make_api_request("weather", params)
        
        # Parse response
        weather_data = self._parse_current_weather(api_response, orchard_id)
        
        # Store in database
        result = supabase.table("weather_data")\
            .insert(weather_data.model_dump(mode='json'))\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store weather data"
            )
        
        weather_response = WeatherDataResponse(**result.data[0])
        
        # Cache the response
        await self._set_cache(
            cache_key,
            "current",
            orchard_id,
            weather_response.model_dump(mode='json')
        )
        
        return weather_response
    
    def _aggregate_daily_forecasts(
        self,
        hourly_forecasts: List[WeatherForecastResponse],
        days: int = 7
    ) -> List[DailyForecastResponse]:
        """
        Aggregate hourly forecasts into daily summaries
        """
        from collections import defaultdict
        
        if not hourly_forecasts:
            return []
        
        # Group forecasts by date
        daily_data = defaultdict(list)
        for forecast in hourly_forecasts:
            # Handle both datetime objects and strings
            if isinstance(forecast.forecast_time, str):
                forecast_dt = datetime.fromisoformat(forecast.forecast_time.replace('Z', '+00:00'))
            else:
                forecast_dt = forecast.forecast_time
            
            date_key = forecast_dt.date().isoformat()
            daily_data[date_key].append({
                'forecast': forecast,
                'datetime': forecast_dt
            })
        
        # Aggregate each day
        daily_forecasts = []
        for date_str, items in sorted(daily_data.items())[:7]:  # Limit to 7 days
            forecasts = [item['forecast'] for item in items]
            forecast_times = [item['datetime'] for item in items]
            date_obj = datetime.fromisoformat(date_str)
            
            # Get day and night temps (day: 12-18, night: 0-6 or 21-23)
            day_temps = [f.temperature for f, dt in zip(forecasts, forecast_times) if 12 <= dt.hour <= 18]
            night_temps = [f.temperature for f, dt in zip(forecasts, forecast_times) if dt.hour <= 6 or dt.hour >= 21]
            
            temp_day = sum(day_temps) / len(day_temps) if day_temps else forecasts[0].temperature
            temp_night = sum(night_temps) / len(night_temps) if night_temps else forecasts[-1].temperature
            
            # Get most common weather condition (use midday forecast)
            midday_idx = next((i for i, dt in enumerate(forecast_times) if 12 <= dt.hour <= 15), 0)
            midday_forecast = forecasts[midday_idx]
            
            # Map weather condition to icon code
            icon_map = {
                "clear": "01d",
                "clouds": "03d",
                "rain": "10d",
                "drizzle": "09d",
                "thunderstorm": "11d",
                "snow": "13d",
                "mist": "50d",
                "fog": "50d"
            }
            condition_str = str(midday_forecast.weather_condition.value) if midday_forecast.weather_condition else "clear"
            icon_code = icon_map.get(condition_str, "01d")
            
            # Calculate wind speed average (only for non-None values)
            wind_speeds = [f.wind_speed for f in forecasts if f.wind_speed is not None]
            avg_wind_speed = sum(wind_speeds) / len(wind_speeds) if wind_speeds else 0.0
            
            daily_forecast = DailyForecastResponse(
                date=date_str,
                day_of_week=date_obj.strftime('%A'),
                temp_day=round(temp_day, 1),
                temp_night=round(temp_night, 1),
                temp_min=round(min(f.temperature for f in forecasts), 1),
                temp_max=round(max(f.temperature for f in forecasts), 1),
                humidity=round(sum(f.humidity for f in forecasts) / len(forecasts), 1),
                description=midday_forecast.weather_description or "",
                icon=icon_code,
                wind_speed=round(avg_wind_speed, 1),
                precipitation_probability=round(max((f.rainfall_probability or 0) for f in forecasts), 1),
                rain_amount=round(sum(f.rainfall_amount for f in forecasts), 2)
            )
            daily_forecasts.append(daily_forecast)
        
        # Limit to requested number of days
        return daily_forecasts[:days]
    
    async def fetch_forecast(
        self,
        orchard_id: str,
        latitude: float,
        longitude: float,
        days: int = 7,
        use_cache: bool = True
    ) -> List[DailyForecastResponse]:
        """
        Fetch 7-day weather forecast aggregated into daily summaries
        Returns daily forecast data
        """
        cache_key = f"weather:forecast:{orchard_id}:{days}"
        
        # Try cache first
        if use_cache:
            cached_data = await self._get_cached_weather(cache_key)
            if cached_data:
                return [DailyForecastResponse(**item) for item in cached_data]
        
        # Fetch from API (get more data points for better daily aggregation)
        # OpenWeatherMap free tier provides 5 days / 3-hour forecast (40 data points)
        params = {
            "lat": latitude,
            "lon": longitude,
            "cnt": 40,  # Maximum available: 5 days of 3-hour intervals
            "appid": self.api_key,
            "units": "metric"
        }
        
        api_response = await self._make_api_request("forecast", params)
        
        # Parse hourly response
        hourly_forecasts = self._parse_forecast_data(api_response, orchard_id)
        
        # Aggregate into daily forecasts
        daily_forecasts = self._aggregate_daily_forecasts(hourly_forecasts, days)
        
        # Cache the daily responses
        await self._set_cache(
            cache_key,
            "forecast",
            orchard_id,
            [f.model_dump(mode='json') for f in daily_forecasts]
        )
        
        return daily_forecasts
    
    async def get_current_weather_for_orchard(
        self,
        orchard_id: str,
        use_cache: bool = True
    ) -> CurrentWeatherResponse:
        """
        Get current weather for an orchard (fetches orchard details first)
        """
        # Fetch orchard details
        orchard_result = supabase.table("orchards")\
            .select("*")\
            .eq("id", orchard_id)\
            .eq("is_active", True)\
            .execute()
        
        if not orchard_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found or inactive"
            )
        
        orchard = orchard_result.data[0]
        
        # Fetch weather
        weather = await self.fetch_current_weather(
            orchard_id,
            float(orchard["latitude"]),
            float(orchard["longitude"]),
            use_cache
        )
        
        return CurrentWeatherResponse(
            orchard_id=orchard_id,
            orchard_name=orchard["name"],
            location={
                "latitude": float(orchard["latitude"]),
                "longitude": float(orchard["longitude"])
            },
            weather=weather,
            cached=use_cache,
            last_updated=weather.recorded_at
        )
    
    async def get_forecast_for_orchard(
        self,
        orchard_id: str,
        days: int = 5,
        use_cache: bool = True
    ) -> ForecastResponse:
        """
        Get weather forecast for an orchard
        """
        # Fetch orchard details
        orchard_result = supabase.table("orchards")\
            .select("*")\
            .eq("id", orchard_id)\
            .eq("is_active", True)\
            .execute()
        
        if not orchard_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found or inactive"
            )
        
        orchard = orchard_result.data[0]
        
        # Fetch forecast
        forecasts = await self.fetch_forecast(
            orchard_id,
            float(orchard["latitude"]),
            float(orchard["longitude"]),
            days,
            use_cache
        )
        
        return ForecastResponse(
            orchard_id=orchard_id,
            orchard_name=orchard["name"],
            forecasts=forecasts,
            total_count=len(forecasts),
            fetched_at=datetime.utcnow()
        )
    
    async def get_weather_history(
        self,
        orchard_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100
    ) -> List[WeatherDataResponse]:
        """
        Retrieve historical weather data for an orchard
        """
        result = supabase.table("weather_data")\
            .select("*")\
            .eq("orchard_id", orchard_id)\
            .gte("recorded_at", start_date.isoformat())\
            .lte("recorded_at", end_date.isoformat())\
            .order("recorded_at", desc=True)\
            .limit(limit)\
            .execute()
        
        if not result.data:
            return []
        
        return [WeatherDataResponse(**item) for item in result.data]
    
    async def update_all_orchards_weather(self) -> Dict[str, Any]:
        """
        Background task: Update weather for all active orchards
        """
        # Fetch all active orchards
        orchards_result = supabase.table("orchards")\
            .select("*")\
            .eq("is_active", True)\
            .execute()
        
        if not orchards_result.data:
            logger.info("No active orchards to update")
            return {"updated": 0, "failed": 0}
        
        updated_count = 0
        failed_count = 0
        
        for orchard in orchards_result.data:
            try:
                await self.fetch_current_weather(
                    orchard["id"],
                    float(orchard["latitude"]),
                    float(orchard["longitude"]),
                    use_cache=False  # Always fetch fresh data for background updates
                )
                updated_count += 1
                logger.info(f"Updated weather for orchard: {orchard['name']}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to update weather for orchard {orchard['name']}: {str(e)}")
        
        logger.info(f"Weather update complete. Updated: {updated_count}, Failed: {failed_count}")
        return {"updated": updated_count, "failed": failed_count, "total": len(orchards_result.data)}


# Singleton instance
weather_service = WeatherService()
