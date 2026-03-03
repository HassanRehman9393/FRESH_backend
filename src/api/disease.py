from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional
from uuid import UUID
from src.schemas.disease import (
    DiseaseDetectionResponse, 
    BatchDiseaseDetectionRequest, 
    BatchDiseaseDetectionResponse
)
from src.services.disease_service import (
    process_single_disease_detection,
    process_batch_disease_detection,
    get_disease_detection_by_id,
    get_all_disease_detections,
    get_diseased_detections
)
from src.api.deps import get_current_user

router = APIRouter(prefix="/disease", tags=["disease"])

@router.post("/batch-detect", response_model=BatchDiseaseDetectionResponse)
async def batch_detect_diseases(
    request: BatchDiseaseDetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process multiple detection results for disease analysis.
    Analyzes fruits that have already been detected for diseases.
    Returns disease detection results including disease type, confidence, and severity.
    Requires authentication.
    """
    try:
        # Use the authenticated user's ID
        return await process_batch_disease_detection(request.detection_ids, UUID(current_user["user_id"]))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/results", response_model=List[DiseaseDetectionResponse])
async def get_disease_detection_results(
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    orchard_id: Optional[str] = Query(None, description="Filter by orchard ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all disease detection results for the authenticated user.
    Supports pagination with limit and offset parameters.
    Optionally filter by orchard_id.
    Requires authentication.
    """
    try:
        return await get_all_disease_detections(
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

@router.get("/results/user/{user_id}", response_model=List[DiseaseDetectionResponse])
async def get_disease_results_by_user(
    user_id: str,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Retrieve all disease detection results for a specific user by user ID.
    Supports pagination with limit and offset parameters.
    """
    from src.services.disease_service import get_all_disease_detections
    try:
        return await get_all_disease_detections(user_id, limit, offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/diseased", response_model=List[DiseaseDetectionResponse])
async def get_diseased_results(
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve only diseased detection results for the authenticated user.
    Filters out healthy fruits and returns only those with diseases detected.
    Supports pagination with limit and offset parameters.
    Requires authentication.
    """
    try:
        return await get_diseased_detections(UUID(current_user["user_id"]), limit, offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{disease_detection_id}", response_model=DiseaseDetectionResponse)
async def get_disease_detection_result(
    disease_detection_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a specific disease detection result by its ID.
    Requires authentication.
    """
    try:
        return await get_disease_detection_by_id(disease_detection_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
