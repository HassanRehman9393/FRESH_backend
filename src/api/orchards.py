"""
Orchards API Endpoints
CRUD operations for orchard management
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from src.schemas.weather import OrchardCreate, OrchardUpdate, OrchardResponse
from src.core.supabase_client import supabase
from src.api.deps import get_current_user
from src.schemas.user import UserResponse
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
