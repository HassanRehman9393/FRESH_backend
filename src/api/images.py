from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import List, Optional, Any
from src.services.image_service import upload_image_service, get_image_service, delete_image_service
from src.schemas.image import ImageCreateResponse, ImageGetResponse

router = APIRouter(prefix="/images", tags=["images"])

@router.post("/upload", response_model=ImageCreateResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...), user_id: str = "demo-user-id", metadata: Optional[Any] = None):
    result = await upload_image_service(user_id, file, metadata)
    return result

@router.post("/batch-upload", status_code=status.HTTP_201_CREATED)
async def batch_upload_images(files: List[UploadFile] = File(...), user_id: str = "demo-user-id"):
    responses = []
    for file in files:
        try:
            resp = await upload_image_service(user_id, file)
            responses.append(resp)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    return responses

@router.get("/{image_id}", response_model=ImageGetResponse)
async def get_image(image_id: str):
    try:
        return await get_image_service(image_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: str):
    success = await delete_image_service(image_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
