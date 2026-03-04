"""
Orchards API Endpoints
CRUD operations for orchard management
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from src.schemas.weather import OrchardCreate, OrchardUpdate, OrchardResponse, OrchardSummaryResponse
from src.core.supabase_client import supabase
from src.api.deps import get_current_user
from src.schemas.user import UserResponse
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchards", tags=["orchards"])


@router.post("", response_model=OrchardResponse, status_code=status.HTTP_201_CREATED)
async def create_orchard(
    orchard: OrchardCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create a new orchard for the authenticated user
    
    - **name**: Orchard name (required)
    - **latitude**: Latitude coordinate (-90 to 90)
    - **longitude**: Longitude coordinate (-180 to 180)
    - **area_hectares**: Optional area in hectares
    - **fruit_types**: List of fruit types grown (e.g., ["mango", "guava"])
    """
    try:
        orchard_data = orchard.model_dump()
        orchard_data["user_id"] = current_user["user_id"]
        
        response = supabase.table("orchards").insert(orchard_data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create orchard"
            )
        
        logger.info(f"Created orchard {response.data[0]['id']} for user {current_user['user_id']}")
        return response.data[0]
    
    except Exception as e:
        logger.error(f"Error creating orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create orchard: {str(e)}"
        )


@router.get("", response_model=List[OrchardResponse])
async def get_user_orchards(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get all orchards for the authenticated user
    """
    try:
        response = supabase.table("orchards")\
            .select("*")\
            .eq("user_id", current_user["user_id"])\
            .order("created_at", desc=True)\
            .execute()
        
        return response.data
    
    except Exception as e:
        logger.error(f"Error fetching orchards: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orchards"
        )


@router.get("/default", response_model=OrchardResponse)
async def get_default_orchard(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get the user's default orchard (most recently updated)
    Returns the most recently updated active orchard for the user
    """
    try:
        response = supabase.table("orchards")\
            .select("*")\
            .eq("user_id", current_user["user_id"])\
            .eq("is_active", True)\
            .order("updated_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active orchards found"
            )
        
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching default orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch default orchard"
        )


@router.get("/{orchard_id}", response_model=OrchardResponse)
async def get_orchard(
    orchard_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get a specific orchard by ID
    """
    try:
        response = supabase.table("orchards")\
            .select("*")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orchard"
        )


@router.put("/{orchard_id}", response_model=OrchardResponse)
async def update_orchard(
    orchard_id: str,
    orchard_update: OrchardUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Update an existing orchard
    """
    try:
        # Verify ownership
        existing = supabase.table("orchards")\
            .select("id")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        # Update only provided fields
        update_data = orchard_update.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        response = supabase.table("orchards")\
            .update(update_data)\
            .eq("id", orchard_id)\
            .execute()
        
        logger.info(f"Updated orchard {orchard_id}")
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update orchard"
        )


@router.delete("/{orchard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_orchard(
    orchard_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Soft delete an orchard (sets is_active=false)
    """
    try:
        # Verify ownership
        existing = supabase.table("orchards")\
            .select("id")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        # Soft delete
        supabase.table("orchards")\
            .update({"is_active": False})\
            .eq("id", orchard_id)\
            .execute()
        
        logger.info(f"Deleted orchard {orchard_id}")
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete orchard"
        )


@router.get("/default", response_model=OrchardResponse)
async def get_default_orchard(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get the user's default orchard (most recently updated)
    Returns the most recently updated active orchard for the user
    """
    try:
        response = supabase.table("orchards")\
            .select("*")\
            .eq("user_id", current_user["user_id"])\
            .eq("is_active", True)\
            .order("updated_at", desc=True)\
            .limit(1)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active orchard found. Please create an orchard first."
            )
        
        logger.info(f"Retrieved default orchard for user {current_user['user_id']}")
        return response.data[0]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching default orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch default orchard"
        )


@router.get("/{orchard_id}/summary", response_model=OrchardSummaryResponse)
async def get_orchard_summary(
    orchard_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get an orchard with summary statistics
    
    Returns orchard details along with:
    - **active_alerts**: Count of active weather alerts
    - **today_detections**: Count of detections created today
    - **health_status**: Overall health (healthy/warning/critical)
    """
    try:
        # Get orchard data
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
        
        # Get active alerts count
        alerts_response = supabase.table("weather_alerts")\
            .select("id", count="exact")\
            .eq("orchard_id", orchard_id)\
            .eq("is_active", True)\
            .execute()
        
        active_alerts = alerts_response.count if hasattr(alerts_response, 'count') else len(alerts_response.data or [])
        
        # Get today's detections count
        # Note: This assumes detection_results table will have orchard_id in the future
        # For now, we return 0 as the table doesn't have orchard_id yet
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_detections = 0
        
        # Try to get detections count if the column exists
        try:
            detections_response = supabase.table("detection_results")\
                .select("detection_id", count="exact")\
                .eq("user_id", current_user["user_id"])\
                .gte("created_at", today_start.isoformat())\
                .execute()
            
            today_detections = detections_response.count if hasattr(detections_response, 'count') else len(detections_response.data or [])
        except Exception as e:
            logger.warning(f"Could not fetch detections count: {str(e)}")
            today_detections = 0
        
        # Determine health status based on alerts
        if active_alerts == 0:
            health_status = "healthy"
        elif active_alerts <= 2:
            health_status = "warning"
        else:
            health_status = "critical"
        
        # Check for critical severity alerts
        try:
            critical_alerts = supabase.table("weather_alerts")\
                .select("id", count="exact")\
                .eq("orchard_id", orchard_id)\
                .eq("is_active", True)\
                .eq("severity", "critical")\
                .execute()
            
            critical_count = critical_alerts.count if hasattr(critical_alerts, 'count') else len(critical_alerts.data or [])
            if critical_count > 0:
                health_status = "critical"
        except Exception as e:
            logger.warning(f"Could not check critical alerts: {str(e)}")
        
        # Build summary response
        summary = {
            **orchard,
            "active_alerts": active_alerts,
            "today_detections": today_detections,
            "health_status": health_status
        }
        
        logger.info(f"Retrieved orchard summary for {orchard_id}")
        return summary
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching orchard summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch orchard summary"
        )

