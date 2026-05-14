"""
Admin API Endpoints
CRUD operations for admin management of users, orchards, and detection results
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from uuid import UUID
import logging
from datetime import datetime

from src.schemas.user import UserResponse, UserUpdate, UserSignup, UserRole
from src.schemas.detection import DetectionResponse
from src.schemas.disease import DiseaseDetectionResponse
from src.schemas.weather import OrchardResponse, OrchardCreate, OrchardUpdate
from src.api.deps import get_current_admin
from src.core.supabase_client import supabase, admin_supabase
from src.core.security import hash_password, create_user_token
import uuid
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ==================== USER MANAGEMENT ====================

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    role: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Get all users with pagination and optional role filtering.
    
    - **limit**: Number of users to return (1-1000, default 100)
    - **offset**: Number of users to skip (default 0)
    - **role**: Optional filter by role (farmer, exporter, government, admin)
    """
    try:
        logger.info(f"👤 Admin fetching all users | limit={limit} offset={offset} role={role}")
        
        # Build query
        query = supabase.table("users").select("id, email, full_name, role, created_at")
        
        # Apply role filter if provided
        if role:
            if role not in ["farmer", "exporter", "government", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {role}. Must be one of: farmer, exporter, government, admin"
                )
            query = query.eq("role", role)
        
        # Apply pagination
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        
        logger.info(f"✅ Fetched {len(response.data)} users")
        return response.data
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    user: UserSignup,
    current_user: dict = Depends(get_current_admin)
):
    """
    Create a new user (admin only).
    
    - **email**: User email (must be unique)
    - **password**: Password (required for manual creation)
    - **full_name**: User's full name
    - **role**: User role (farmer, exporter, government, admin)
    """
    try:
        logger.info(f"👤 Admin creating new user | email={user.email} role={user.role}")
        
        # Check if user exists
        existing = supabase.table("users").select("id").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Validate password is provided
        if not user.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for manual user creation"
            )
        
        # Hash password
        password_hash = hash_password(user.password[:72])
        
        # Create user
        user_data = {
            "id": str(uuid.uuid4()),
            "email": user.email,
            "password_hash": password_hash,
            "full_name": user.full_name,
            "role": user.role.value,
            "provider": "local",
            "is_google_user": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("users").insert(user_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )
        
        created_user = result.data[0]
        logger.info(f"✅ User created successfully | user_id={created_user['id']} email={created_user['email']}")
        
        return {
            "id": created_user["id"],
            "email": created_user["email"],
            "full_name": created_user.get("full_name"),
            "role": UserRole(created_user["role"])
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Update a user's information.
    
    - **user_id**: The ID of the user to update
    - **email**: New email (optional)
    - **full_name**: New full name (optional)
    - **role**: New role (optional)
    """
    try:
        logger.info(f"👤 Admin updating user | user_id={user_id}")
        
        # Check if user exists
        user = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prepare update data (only include non-None fields)
        update_data = {}
        if user_update.email is not None:
            # Check if email is already taken by another user
            existing = supabase.table("users").select("id").eq("email", user_update.email).neq("id", user_id).execute()
            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already in use"
                )
            update_data["email"] = user_update.email
        
        if user_update.full_name is not None:
            update_data["full_name"] = user_update.full_name
        
        if user_update.role is not None:
            update_data["role"] = user_update.role.value
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Update user
        result = supabase.table("users").update(update_data).eq("id", user_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User update failed"
            )
        
        updated_user = result.data[0]
        logger.info(f"✅ User updated successfully | user_id={user_id}")
        
        return {
            "id": updated_user["id"],
            "email": updated_user["email"],
            "full_name": updated_user.get("full_name"),
            "role": UserRole(updated_user["role"])
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """
    Delete a user from the system.
    
    - **user_id**: The ID of the user to delete
    
    Note: This will cascade delete related data (images, detections, orchards)
    """
    try:
        logger.info(f"👤 Admin deleting user | user_id={user_id}")
        
        # Check if user exists
        user = supabase.table("users").select("id").eq("id", user_id).execute()
        if not user.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent self-deletion
        if user_id == current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own user account"
            )
        
        # Delete user (cascading deletes should be handled by database constraints)
        result = supabase.table("users").delete().eq("id", user_id).execute()
        
        logger.info(f"✅ User deleted successfully | user_id={user_id}")
        return None
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


# ==================== ORCHARD MANAGEMENT ====================

@router.post("/orchards", response_model=OrchardResponse, status_code=status.HTTP_201_CREATED)
async def create_orchard_admin(
    orchard: OrchardCreate,
    assign_to: Optional[str] = Query(None, description="User ID to assign the orchard to"),
    current_user: dict = Depends(get_current_admin)
):
    """
    Create a new orchard and assign it to a specific user (admin only).
    
    - **assign_to**: User ID to assign the orchard to (defaults to admin's own ID)
    """
    try:
        target_user_id = assign_to or current_user.get("user_id")
        
        # Verify target user exists if assigning to someone else
        if assign_to:
            user_check = supabase.table("users").select("id").eq("id", assign_to).execute()
            if not user_check.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID '{assign_to}' not found"
                )
        
        orchard_data = orchard.model_dump()
        orchard_data["user_id"] = target_user_id
        
        response = supabase.table("orchards").insert(orchard_data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create orchard"
            )
        
        logger.info(f"✅ Admin created orchard {response.data[0]['id']} assigned to user {target_user_id}")
        return response.data[0]
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error creating orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create orchard: {str(e)}"
        )


@router.get("/orchards", response_model=List[OrchardResponse])
async def get_all_orchards(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Get all orchards across all users with pagination.
    
    - **limit**: Number of orchards to return (1-1000, default 100)
    - **offset**: Number of orchards to skip (default 0)
    - **user_id**: Optional filter by specific user
    """
    try:
        logger.info(f"🌳 Admin fetching all orchards | limit={limit} offset={offset} user_id={user_id}")
        
        # Build query
        query = supabase.table("orchards").select("*")
        
        # Apply user filter if provided
        if user_id:
            query = query.eq("user_id", user_id)
        
        # Apply pagination
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()
        
        logger.info(f"✅ Fetched {len(response.data)} orchards")
        return response.data
        
    except Exception as e:
        logger.error(f"❌ Error fetching orchards: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orchards: {str(e)}"
        )


@router.put("/orchards/{orchard_id}", response_model=OrchardResponse)
async def update_orchard_admin(
    orchard_id: str,
    orchard_update: OrchardUpdate,
    assign_to: Optional[str] = Query(None, description="Reassign orchard to this user ID"),
    current_user: dict = Depends(get_current_admin)
):
    """
    Update an orchard's information and optionally reassign it to another user (admin only).
    
    - **orchard_id**: The ID of the orchard to update
    - **assign_to**: Optional user ID to reassign the orchard to
    """
    try:
        logger.info(f"🌳 Admin updating orchard | orchard_id={orchard_id} assign_to={assign_to}")
        
        # Check if orchard exists
        existing = supabase.table("orchards").select("*").eq("id", orchard_id).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        # Build update data from provided fields
        update_data = orchard_update.model_dump(exclude_unset=True)
        
        # Handle user reassignment
        if assign_to:
            user_check = supabase.table("users").select("id").eq("id", assign_to).execute()
            if not user_check.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID '{assign_to}' not found"
                )
            update_data["user_id"] = assign_to
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        result = supabase.table("orchards").update(update_data).eq("id", orchard_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Orchard update failed"
            )
        
        logger.info(f"✅ Orchard updated successfully | orchard_id={orchard_id}")
        return result.data[0]
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"❌ Error updating orchard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update orchard: {str(e)}"
        )


# ==================== DETECTION RESULTS MANAGEMENT ====================

@router.get("/detection-results", response_model=List[DetectionResponse])
async def get_all_detection_results(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    orchard_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Get all detection results from all users with pagination.
    
    - **limit**: Number of results to return (1-1000, default 100)
    - **offset**: Number of results to skip (default 0)
    - **user_id**: Optional filter by specific user
    - **orchard_id**: Optional filter by specific orchard
    """
    try:
        logger.info(
            f"🔍 Admin fetching all detection results | limit={limit} offset={offset} "
            f"user_id={user_id} orchard_id={orchard_id}"
        )
        
        # Build query - select only columns that exist in the table
        query = supabase.table("detection_results").select("*")
        
        # Apply filters if provided
        if user_id:
            query = query.eq("user_id", user_id)
        
        if orchard_id:
            query = query.eq("orchard_id", orchard_id)
        
        # Apply pagination
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        response = query.execute()

        # Fetch classification data for all detection IDs in one query
        detection_ids = [item.get("detection_id") for item in response.data if item.get("detection_id")]
        classification_map = {}
        if detection_ids:
            try:
                cls_response = supabase.table("classification_results").select("*").in_("detection_id", detection_ids).execute()
                for cls in cls_response.data:
                    classification_map[cls["detection_id"]] = cls
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch classification results: {e}")

        # Transform data to match DetectionResponse schema
        results = []
        for item in response.data:
            # Parse bounding_box and transform format if needed
            bbox = item.get("bounding_box", {})
            if isinstance(bbox, str):
                try:
                    bbox = json.loads(bbox)
                except:
                    bbox = {}

            # Convert from ML format (x1, x2, y1, y2) to expected format (x, y, width, height)
            if bbox and "x1" in bbox and "y1" in bbox:
                x1 = float(bbox.get("x1", 0))
                x2 = float(bbox.get("x2", 0))
                y1 = float(bbox.get("y1", 0))
                y2 = float(bbox.get("y2", 0))
                bbox = {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                }

            # Build classification from classification_results table
            cls_data = classification_map.get(item.get("detection_id"))
            if cls_data:
                classification = {
                    "ripeness_level": cls_data.get("ripeness_level"),
                    "ripeness_confidence": cls_data.get("confidence_score"),
                    "color": cls_data.get("estimated_color"),
                    "size": cls_data.get("estimated_size"),
                }
            else:
                # Fall back to inline classification column if present
                classification = item.get("classification")
                if isinstance(classification, str):
                    try:
                        classification = json.loads(classification)
                    except:
                        classification = None

            results.append({
                "detection_id": item.get("detection_id"),
                "user_id": item.get("user_id"),
                "image_id": item.get("image_id"),
                "orchard_id": item.get("orchard_id"),
                "fruit_type": item.get("fruit_type"),
                "confidence": item.get("confidence"),
                "bounding_box": bbox,
                "classification": classification,
                "created_at": item.get("created_at"),
                "annotated_image_url": item.get("annotated_image_url"),
                "annotated_image_filename": item.get("annotated_image_filename")
            })
        
        logger.info(f"✅ Fetched {len(results)} detection results")
        return results

    except Exception as e:
        logger.error(f"❌ Error fetching detection results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch detection results: {str(e)}"
        )


# ==================== DISEASE RESULTS MANAGEMENT ====================

@router.get("/disease-results", response_model=List[DiseaseDetectionResponse])
async def get_all_disease_results(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_admin)
):
    """
    Get all disease detection results across all users with pagination.
    Admin only endpoint.
    """
    try:
        logger.info(f"🔍 Admin fetching disease results | limit={limit} offset={offset} user_id={user_id}")

        query = supabase.table("disease_detections").select("*")

        if user_id:
            query = query.eq("user_id", user_id)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        response = query.execute()

        results = []
        for item in response.data:
            probabilities = item.get("probabilities")
            if isinstance(probabilities, str):
                try:
                    probabilities = json.loads(probabilities)
                except Exception:
                    probabilities = None

            results.append({
                "disease_detection_id": item.get("disease_detection_id"),
                "detection_id": item.get("detection_id"),
                "user_id": item.get("user_id"),
                "image_id": item.get("image_id"),
                "orchard_id": item.get("orchard_id"),
                "disease_type": item.get("disease_type", "unknown"),
                "is_diseased": item.get("is_diseased", False),
                "disease_confidence": item.get("disease_confidence", 0.0),
                "severity_level": item.get("severity_level"),
                "probabilities": probabilities,
                "created_at": item.get("created_at"),
            })

        logger.info(f"✅ Fetched {len(results)} disease results")
        return results

    except Exception as e:
        logger.error(f"❌ Error fetching disease results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch disease results: {str(e)}"
        )
