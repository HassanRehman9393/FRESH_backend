"""
Test script for WeatherService
Run this to verify OpenWeatherMap API integration works
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.weather_service import weather_service
from src.core.config import settings


async def test_weather_api():
    """Test OpenWeatherMap API with sample coordinates"""
    
    print("🌤️  Testing Weather Service...")
    print(f"API Key configured: {'Yes' if settings.openweather_api_key else 'No'}")
    print()
    
    if not settings.openweather_api_key:
        print("❌ Error: OPENWEATHER_API_KEY not set in .env file")
        print("Please add: OPENWEATHER_API_KEY=your_api_key_here")
        return
    
    # Test coordinates (Karachi, Pakistan)
    test_lat = 24.8607
    test_lon = 67.0011
    test_orchard_id = "test-orchard-123"
    
    try:
        print(f"📍 Fetching weather for coordinates: {test_lat}, {test_lon}")
        print("   (Karachi, Pakistan)")
        print()
        
        # Test current weather
        print("1️⃣  Testing Current Weather API...")
        weather_data = await weather_service.fetch_current_weather(
            orchard_id=test_orchard_id,
            latitude=test_lat,
            longitude=test_lon,
            use_cache=False
        )
        
        print(f"✅ Success!")
        print(f"   Temperature: {weather_data.temperature}°C")
        print(f"   Humidity: {weather_data.humidity}%")
        print(f"   Condition: {weather_data.weather_condition}")
        print(f"   Description: {weather_data.weather_description}")
        if weather_data.rainfall > 0:
            print(f"   Rainfall: {weather_data.rainfall}mm")
        print()
        
        # Test forecast
        print("2️⃣  Testing 5-Day Forecast API...")
        forecast_data = await weather_service.fetch_forecast(
            orchard_id=test_orchard_id,
            latitude=test_lat,
            longitude=test_lon,
            days=5,
            use_cache=False
        )
        
        print(f"✅ Success!")
        print(f"   Forecast points: {len(forecast_data)}")
        if forecast_data:
            next_forecast = forecast_data[0]
            print(f"   Next forecast: {next_forecast.forecast_time}")
            print(f"   Temperature: {next_forecast.temperature}°C")
            print(f"   Humidity: {next_forecast.humidity}%")
        print()
        
        print("🎉 All tests passed! Weather service is working correctly.")
        print()
        print("Next steps:")
        print("1. Create an orchard in the database")
        print("2. Test the API endpoints")
        print("3. Implement alert rules")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
        print("Common issues:")
        print("- Invalid API key")
        print("- API rate limit exceeded (1000 calls/day on free tier)")
        print("- Network connectivity issues")
        print("- Database connection issues")


if __name__ == "__main__":
    asyncio.run(test_weather_api())
