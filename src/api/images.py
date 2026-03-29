from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Query
from typing import List, Optional, Any
from src.services.image_service import upload_image_service, get_image_service, delete_image_service
from src.services.multispectral_upload_service import upload_multispectral_images
from src.schemas.image import ImageCreateResponse, ImageGetResponse, MultispectralUploadResponse
from src.api.deps import get_current_user

router = APIRouter(prefix="/images", tags=["images"])

@router.post("/upload", response_model=ImageCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...), 
    metadata: Optional[Any] = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload a single image. Requires authentication."""
    result = await upload_image_service(current_user["user_id"], file, metadata)
    return result

@router.post("/batch-upload", status_code=status.HTTP_201_CREATED)
async def batch_upload_images(
    files: List[UploadFile] = File(...), 
    current_user: dict = Depends(get_current_user)
):
    """Upload multiple images. Requires authentication."""
    responses = []
    for file in files:
        try:
            resp = await upload_image_service(current_user["user_id"], file)
            responses.append(resp)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return responses

@router.get("/{image_id}", response_model=ImageGetResponse)
async def get_image(
    image_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Get image metadata. Requires authentication."""
    try:
        return await get_image_service(image_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: str, 
    current_user: dict = Depends(get_current_user)
):
    """Delete an image. Requires authentication."""
    success = await delete_image_service(image_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")

@router.post("/multispectral/upload", response_model=MultispectralUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_multispectral(
    files: List[UploadFile] = File(...),
    orchard_id: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload multispectral images (6-band sets) and create detection-ready images.
    
    Automatically groups images by base filename (e.g., IMG_0197_1, IMG_0197_2, etc.).
    Creates YOLO-ready detection images from Band 3 (Red) for fruit detection.
    Incomplete sets are stored but not processed.
    
    Args:
        files: List of multispectral band images (naming: BASENAME_BAND.ext)
        orchard_id: Optional orchard association
        
    Returns:
        MultispectralUploadResponse with detection-ready images and GPS data
    """
    try:
        return await upload_multispectral_images(
            user_id=current_user["user_id"],
            files=files,
            orchard_id=orchard_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Multispectral upload failed: {str(e)}"
        )

@router.get("/with-gps", response_model=List[ImageGetResponse])
async def get_images_with_gps(
    current_user: dict = Depends(get_current_user)
):
    """Get all images with GPS coordinates for map mosaic display.
    
    Returns all images (across all users or filtered by user) that have valid GPS data.
    These will be displayed on the map as a mosaic.
    """
    try:
        from src.core.supabase_client import admin_supabase
        from src.schemas.image import ImageGetResponse
        
        # Get all images for this user that have GPS coordinates in metadata
        result = admin_supabase.table("images").select("*").eq(
            "user_id", current_user["user_id"]
        ).execute()
        
        images_with_gps = []
        for record in result.data:
            metadata = record.get("metadata", {})
            
            # Check if image has valid GPS coordinates
            lat = metadata.get("gps_latitude")
            lon = metadata.get("gps_longitude")
            
            if lat is not None and lon is not None:
                # Validate coordinates are realistic
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    images_with_gps.append(ImageGetResponse(**record))
        
        return images_with_gps
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch images with GPS: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=List[ImageGetResponse])
async def get_images_by_user(user_id: str):
    """Get all images for a user by user_id."""
    from src.services.image_service import get_images_by_user_service
    return await get_images_by_user_service(user_id)
