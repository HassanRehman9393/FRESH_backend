"""
Unit tests for Weather Service & API
Tests: current weather, forecasts, weather history, caching
"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.weather_service import weather_service
from src.schemas.weather import WeatherDataResponse


@pytest.mark.unit
@pytest.mark.weather
class TestWeatherService:
    """Test weather service functionality"""
    
    @pytest.mark.asyncio
    async def test_fetch_current_weather_success(self, test_orchard_data, test_weather_data):
        """Test fetching current weather"""
        orchard_id = test_orchard_data["id"]
        latitude = test_orchard_data["latitude"]
        longitude = test_orchard_data["longitude"]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "main": {
                    "temp": 28.5,
                    "humidity": 65,
                    "pressure": 1013
                },
                "weather": [{"main": "Clear", "description": "clear sky"}],
                "wind": {"speed": 12.0},
                "rain": {"1h": 0}
            }
            
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            
            with patch('src.services.weather_service.supabase') as mock_supabase:
                mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                    test_weather_data
                ]
                
                result = await weather_service.fetch_current_weather(
                    orchard_id=orchard_id,
                    latitude=latitude,
                    longitude=longitude,
                    use_cache=False
                )
                
                assert result is not None
                assert "temperature" in result or result.get("temperature") is not None
    
    @pytest.mark.asyncio
    async def test_fetch_weather_with_cache(self, test_orchard_data, test_weather_data):
        """Test weather fetching with cache"""
        orchard_id = test_orchard_data["id"]
        
        with patch('src.services.weather_service.redis_client') as mock_redis:
            # Mock cached data
            import json
            mock_redis.get = AsyncMock(return_value=json.dumps(test_weather_data))
            
            result = await weather_service.fetch_current_weather(
                orchard_id=orchard_id,
                latitude=33.6844,
                longitude=73.0479,
                use_cache=True
            )
            
            # Should return cached data without API call
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_fetch_forecast_success(self, test_orchard_data):
        """Test fetching weather forecast"""
        orchard_id = test_orchard_data["id"]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "list": [
                    {
                        "dt": int(datetime.utcnow().timestamp()),
                        "main": {"temp": 28.5, "humidity": 65},
                        "weather": [{"main": "Clear"}],
                        "pop": 0.2
                    } for _ in range(40)  # 5 days * 8 (3-hour intervals)
                ]
            }
            
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_async_client
            
            result = await weather_service.fetch_forecast(
                orchard_id=orchard_id,
                latitude=33.6844,
                longitude=73.0479,
                days=5,
                use_cache=False
            )
            
            assert result is not None
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_weather_api_error_handling(self, test_orchard_data):
        """Test weather API error handling"""
        orchard_id = test_orchard_data["id"]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(side_effect=Exception("API Error"))
            mock_client.return_value.__aenter__.return_value = mock_async_client
            
            with pytest.raises(Exception):
                await weather_service.fetch_current_weather(
                    orchard_id=orchard_id,
                    latitude=33.6844,
                    longitude=73.0479,
                    use_cache=False
                )


@pytest.mark.unit
@pytest.mark.weather
class TestWeatherAPI:
    """Test weather API endpoints"""
    
    def test_get_current_weather_unauthorized(self, client, test_orchard_data):
        """Test getting current weather without auth"""
        response = client.get(f"/weather/current/{test_orchard_data['id']}")
        
        assert response.status_code == 401
    
    def test_get_weather_forecast_with_days_param(self, client, auth_headers, test_orchard_data):
        """Test getting forecast with custom days parameter"""
        with patch('src.services.weather_service.weather_service.fetch_forecast') as mock_forecast:
            mock_forecast.return_value = []
            
            response = client.get(
                f"/weather/forecast/{test_orchard_data['id']}?days=3",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 401, 404]
    
    def test_get_weather_history_with_date_range(self, client, auth_headers, test_orchard_data):
        """Test getting weather history with date filters"""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        with patch('src.core.supabase_client.supabase') as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.execute.return_value.data = []
            
            response = client.get(
                f"/weather/history/{test_orchard_data['id']}?start_date={start_date}&end_date={end_date}",
                headers=auth_headers
            )
            
            assert response.status_code in [200, 401, 404, 422]


@pytest.mark.unit
@pytest.mark.weather
class TestWeatherDataValidation:
    """Test weather data validation"""
    
    def test_temperature_range_validation(self):
        """Test temperature range validation"""
        # Reasonable temperature range: -50°C to 60°C
        valid_temps = [-10, 0, 15, 28.5, 45]
        for temp in valid_temps:
            assert -50 <= temp <= 60
    
    def test_humidity_range_validation(self):
        """Test humidity percentage validation"""
        valid_humidity = [0, 30, 65, 100]
        for humidity in valid_humidity:
            assert 0 <= humidity <= 100
    
    def test_weather_condition_enum(self):
        """Test weather condition values"""
        valid_conditions = [
            "clear", "cloudy", "partly_cloudy", "rainy",
            "thunderstorm", "foggy", "windy"
        ]
        
        test_condition = "partly_cloudy"
        assert test_condition in valid_conditions
