from fastapi import APIRouter, HTTPException, status, Query, Depends, UploadFile, File
from typing import List, Optional
from uuid import UUID
from src.schemas.detection import (
    DetectionResponse, 
    BatchDetectionRequest, 
    BatchDetectionResponse
)
from src.services.detection_service import (
    process_single_image,
    process_batch_images,
    get_detection_by_id,
    get_all_detections
)
from src.api.deps import get_current_user

router = APIRouter(prefix="/detection", tags=["detection"])

@router.post("/batch-fruit", response_model=BatchDetectionResponse)
async def batch_detect_fruits(
    request: BatchDetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process multiple images for fruit detection.
    Returns detection results including bounding boxes and confidence scores.
    Requires authentication.
    """
    try:
        # Use the authenticated user's ID instead of the request user_id
        return await process_batch_images(request.image_ids, UUID(current_user["user_id"]))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/fruit/results", response_model=List[DetectionResponse])
async def get_detection_results(
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    orchard_id: Optional[str] = Query(None, description="Filter by orchard ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all detection results for the authenticated user.
    Supports pagination with limit and offset parameters.
    Optionally filter by orchard_id.
    Requires authentication.
    """
    try:
        return await get_all_detections(
            UUID(current_user["user_id"]), 
            limit, 
            offset,
            orchard_id=orchard_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/fruit/{detection_id}", response_model=DetectionResponse)
async def get_detection_result(
    detection_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a specific detection result by its ID.
    Requires authentication.
    """
    try:
        return await get_detection_by_id(detection_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/results/user/{user_id}", response_model=List[DetectionResponse])
async def get_detection_results_by_user(
    user_id: str,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Retrieve all object detection results for a specific user by user ID.
    Supports pagination with limit and offset parameters.
    """
    try:
        return await get_all_detections(UUID(user_id), limit, offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )