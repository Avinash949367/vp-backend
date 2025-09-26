from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from models import User
from auth import get_current_user
from services.weather_service import weather_service

router = APIRouter()

@router.get("/{city}")
async def get_weather_forecast(
    city: str, 
    start_date: str, 
    end_date: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get weather forecast for a city and date range
    """
    try:
        forecast = await weather_service.get_weather_forecast(city, start_date, end_date)
        if forecast:
            return forecast
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Weather forecast not available for this location"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get weather forecast: {str(e)}"
        )




