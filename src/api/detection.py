from fastapi import APIRouter, HTTPException, status, Query
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

router = APIRouter(prefix="/detection", tags=["detection"])

@router.post("/batch-fruit", response_model=BatchDetectionResponse)
async def batch_detect_fruits(request: BatchDetectionRequest):
    """
    Process multiple images for fruit detection.
    Returns detection results including bounding boxes and confidence scores.
    """
    try:
        return await process_batch_images(request.image_ids, request.user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/fruit/results", response_model=List[DetectionResponse])
async def get_detection_results(
    user_id: UUID,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Retrieve all detection results for a user.
    Supports pagination with limit and offset parameters.
    """
    try:
        return await get_all_detections(user_id, limit, offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/fruit/{detection_id}", response_model=DetectionResponse)
async def get_detection_result(detection_id: UUID):
    """
    Retrieve a specific detection result by its ID.
    """
    try:
        return await get_detection_by_id(detection_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )