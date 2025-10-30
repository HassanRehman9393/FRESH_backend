from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import List, Optional, Any
from src.services.image_service import upload_image_service, get_image_service, delete_image_service
from src.schemas.image import ImageCreateResponse, ImageGetResponse
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

@router.get("/user/{user_id}", response_model=List[ImageGetResponse])
async def get_images_by_user(user_id: str):
    """Get all images for a user by user_id."""
    from src.services.image_service import get_images_by_user_service
    return await get_images_by_user_service(user_id)
