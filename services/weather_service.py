import httpx
from typing import Optional, Dict, Any
import logging

class WeatherService:
    def __init__(self):
        self.api_key = "your-openweather-api-key"  # Replace with actual API key
        self.base_url = "http://api.openweathermap.org/data/2.5"
    
    async def get_weather_forecast(self, city: str, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """
        Get weather forecast for a city and date range
        """
        try:
            # Get coordinates for the city
            coords = await self._get_city_coordinates(city)
            if not coords:
                return None
            
            # Get weather forecast
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "lat": coords["lat"],
                        "lon": coords["lon"],
                        "appid": self.api_key,
                        "units": "metric"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._process_forecast_data(data, start_date, end_date)
                else:
                    logging.error(f"Weather API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logging.error(f"Weather service error: {e}")
            return None
    
    async def _get_city_coordinates(self, city: str) -> Optional[Dict[str, float]]:
        """
        Get coordinates for a city
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "q": city,
                        "appid": self.api_key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "lat": data["coord"]["lat"],
                        "lon": data["coord"]["lon"]
                    }
                else:
                    return None
                    
        except Exception as e:
            logging.error(f"City coordinates error: {e}")
            return None
    
    def _process_forecast_data(self, data: Dict[str, Any], start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Process weather forecast data for the trip dates
        """
        from datetime import datetime
        
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Filter forecasts for trip dates
        trip_forecasts = []
        for item in data.get("list", []):
            forecast_dt = datetime.fromtimestamp(item["dt"])
            if start_dt <= forecast_dt <= end_dt:
                trip_forecasts.append({
                    "date": forecast_dt.isoformat(),
                    "temperature": item["main"]["temp"],
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"],
                    "humidity": item["main"]["humidity"],
                    "wind_speed": item.get("wind", {}).get("speed", 0)
                })
        
        # Calculate summary
        if trip_forecasts:
            avg_temp = sum(f["temperature"] for f in trip_forecasts) / len(trip_forecasts)
            min_temp = min(f["temperature"] for f in trip_forecasts)
            max_temp = max(f["temperature"] for f in trip_forecasts)
            
            return {
                "summary": {
                    "average_temperature": round(avg_temp, 1),
                    "min_temperature": round(min_temp, 1),
                    "max_temperature": round(max_temp, 1),
                    "forecast_days": len(trip_forecasts)
                },
                "daily_forecasts": trip_forecasts
            }
        
        return {"summary": {}, "daily_forecasts": []}

# Global weather service instance
weather_service = WeatherService()




