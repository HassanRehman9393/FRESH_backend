"""
Weather Alerts API Endpoints
Alert management and notifications
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime
from src.schemas.weather import (
    WeatherAlertResponse,
    WeatherAlertUpdate,
    AlertListResponse,
    Severity
)
from src.core.supabase_client import supabase
from src.api.deps import get_current_user
from src.schemas.user import UserResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def get_user_alerts(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    severity: Optional[Severity] = Query(None, description="Filter by severity"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    orchard_id: Optional[str] = Query(None, description="Filter by orchard ID"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get all weather alerts for the authenticated user
    
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (1-100, default: 20)
    - **severity**: Filter by severity (low, medium, high, critical)
    - **is_active**: Filter by active status
    - **is_acknowledged**: Filter by acknowledged status
    - **orchard_id**: Filter by specific orchard
    
    Returns paginated list of alerts sorted by creation date (newest first)
    """
    try:
        # First get user's orchard IDs
        user_orchards = supabase.table("orchards")\
            .select("id")\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not user_orchards.data:
            return AlertListResponse(
                alerts=[],
                total_count=0,
                page=page,
                page_size=page_size,
                has_more=False
            )
        
        orchard_ids = [o["id"] for o in user_orchards.data]
        
        # Build query for alerts belonging to user's orchards
        query = supabase.table("weather_alerts")\
            .select("*", count="exact")\
            .in_("orchard_id", orchard_ids)
        
        # Apply filters
        if severity:
            query = query.eq("severity", severity.value)
        if is_active is not None:
            query = query.eq("is_active", is_active)
        if is_acknowledged is not None:
            if is_acknowledged:
                query = query.not_.is_("acknowledged_at", "null")
            else:
                query = query.is_("acknowledged_at", "null")
        if orchard_id:
            query = query.eq("orchard_id", orchard_id)
        
        # Get total count
        count_response = query.execute()
        total_count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
        
        # Apply pagination
        offset = (page - 1) * page_size
        response = query\
            .order("created_at", desc=True)\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        has_more = (offset + page_size) < total_count
        
        return AlertListResponse(
            alerts=response.data,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
    
    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alerts"
        )


@router.get("/active", response_model=List[WeatherAlertResponse])
async def get_active_alerts(
    orchard_id: Optional[str] = Query(None, description="Filter by orchard ID"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get all active (unacknowledged) alerts for the user
    
    - **orchard_id**: Optional filter by specific orchard
    
    Returns only active, unacknowledged alerts sorted by severity
    """
    try:
        # Get user's orchard IDs
        user_orchards = supabase.table("orchards")\
            .select("id")\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not user_orchards.data:
            return []
        
        orchard_ids = [o["id"] for o in user_orchards.data]
        
        query = supabase.table("weather_alerts")\
            .select("*")\
            .in_("orchard_id", orchard_ids)\
            .eq("is_active", True)\
            .is_("acknowledged_at", "null")
        
        if orchard_id:
            query = query.eq("orchard_id", orchard_id)
        
        response = query\
            .order("severity", desc=True)\
            .order("triggered_at", desc=True)\
            .execute()
        
        return response.data
    
    except Exception as e:
        logger.error(f"Error fetching active alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch active alerts"
        )


@router.get("/{alert_id}", response_model=WeatherAlertResponse)
async def get_alert(
    alert_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get a specific alert by ID
    """
    try:
        # Get alert
        alert_response = supabase.table("weather_alerts")\
            .select("*")\
            .eq("id", alert_id)\
            .execute()
        
        if not alert_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        alert = alert_response.data[0]
        
        # Verify user owns the orchard
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", alert["orchard_id"])\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        return alert
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alert"
        )


@router.patch("/{alert_id}/acknowledge", response_model=WeatherAlertResponse)
async def acknowledge_alert(
    alert_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Mark an alert as acknowledged
    
    - **alert_id**: UUID of the alert to acknowledge
    
    Sets is_acknowledged=true and records the acknowledgment timestamp
    """
    try:
        # Get alert and verify ownership through orchard
        alert_response = supabase.table("weather_alerts")\
            .select("*")\
            .eq("id", alert_id)\
            .execute()
        
        if not alert_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        alert = alert_response.data[0]
        
        # Verify user owns the orchard
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", alert["orchard_id"])\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Update alert
        response = supabase.table("weather_alerts")\
            .update({
                "acknowledged_at": datetime.utcnow().isoformat()
            })\
            .eq("id", alert_id)\
            .execute()
        
        logger.info(f"Alert {alert_id} acknowledged by user {current_user['user_id']}")
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge alert"
        )


@router.patch("/{alert_id}/dismiss", response_model=WeatherAlertResponse)
async def dismiss_alert(
    alert_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Dismiss an alert (mark as inactive)
    
    - **alert_id**: UUID of the alert to dismiss
    
    Sets is_active=false to hide the alert from active lists
    """
    try:
        # Get alert and verify ownership through orchard
        alert_response = supabase.table("weather_alerts")\
            .select("*")\
            .eq("id", alert_id)\
            .execute()
        
        if not alert_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        alert = alert_response.data[0]
        
        # Verify user owns the orchard
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", alert["orchard_id"])\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Dismiss alert
        response = supabase.table("weather_alerts")\
            .update({"is_active": False})\
            .eq("id", alert_id)\
            .execute()
        
        logger.info(f"Alert {alert_id} dismissed by user {current_user['user_id']}")
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dismiss alert"
        )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Permanently delete an alert
    
    - **alert_id**: UUID of the alert to delete
    
    Warning: This action cannot be undone
    """
    try:
        # Get alert and verify ownership through orchard
        alert_response = supabase.table("weather_alerts")\
            .select("*")\
            .eq("id", alert_id)\
            .execute()
        
        if not alert_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        alert = alert_response.data[0]
        
        # Verify user owns the orchard
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", alert["orchard_id"])\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Delete alert
        supabase.table("weather_alerts")\
            .delete()\
            .eq("id", alert_id)\
            .execute()
        
        logger.info(f"Alert {alert_id} deleted by user {current_user['user_id']}")
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert"
        )
