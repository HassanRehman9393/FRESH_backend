from src.core.supabase_client import supabase, admin_supabase
from src.schemas.image import ImageCreateResponse, ImageGetResponse
from src.services.gps_extractor_service import GPSExtractorService
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, Any
import os
from fastapi import UploadFile
import aiofiles
import tempfile
import logging

logger = logging.getLogger(__name__)

async def upload_to_supabase_storage(file: UploadFile, file_name: str) -> str:
    """Upload file to Supabase storage and return the public URL"""
    temp_file = None
    try:
        # Reset file pointer to beginning
        await file.seek(0)
        
        # Read file content
        contents = await file.read()
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(contents)
        temp_file.flush()
        temp_file.close()  # Important: close the file before uploading
        
        # Upload to Supabase storage using admin client
        with open(temp_file.name, 'rb') as f:
            result = admin_supabase.storage.from_('images').upload(
                path=file_name,
                file=f,
                file_options={"content-type": file.content_type}
            )
        
        # Get public URL and clean up trailing query params
        public_url = admin_supabase.storage.from_('images').get_public_url(file_name)
        # Remove trailing ? if present (Supabase SDK adds it sometimes)
        if public_url and public_url.endswith('?'):
            public_url = public_url[:-1]
        
        return public_url
    except Exception as e:
        raise Exception(f"Failed to upload file to storage: {str(e)}")
    finally:
        # Clean up temp file in finally block to ensure it happens
        if temp_file is not None:
            try:
                os.unlink(temp_file.name)
            except:
                pass  # Ignore cleanup errors

async def upload_image_service(user_id: str, file: UploadFile, metadata: Optional[Dict[str, Any]] = None) -> ImageCreateResponse:
    """Upload image to storage and create database record"""
    image_id = str(uuid4())
    now = datetime.utcnow()
    
    # Get original file extension and ensure it's lowercase
    file_extension = os.path.splitext(file.filename)[1].lower()
    # Store images under user-specific directory for security and organization
    storage_file_name = f"{user_id}/{image_id}{file_extension}"
    print(f"Generated storage file name: {storage_file_name}")
    
    # Read file content for GPS extraction before upload
    await file.seek(0)
    file_bytes = await file.read()
    
    # Extract GPS data from image EXIF
    print(f"🔍 Extracting GPS data from {file.filename}...")
    gps_data = GPSExtractorService.extract_gps_from_exif(file_bytes, file.filename)
    
    # Upload to storage and get public URL
    await file.seek(0)  # Reset file pointer after reading
    file_path = await upload_to_supabase_storage(file, storage_file_name)
    print(f"File uploaded to storage at: {file_path}")
    
    # Ensure metadata is a dictionary
    if isinstance(metadata, str):
        try:
            import json
            metadata = json.loads(metadata)
        except:
            metadata = {"data": metadata}
    
    # Add file information to metadata
    if metadata is None:
        metadata = {}
    
    logger.info(
        "📸 [Image Service] Image metadata before update | user_id=%s image_id=%s incoming_metadata=%s",
        user_id,
        image_id,
        metadata,
    )
    
    metadata.update({
        "original_filename": file.filename,
        "storage_filename": storage_file_name,
        "content_type": file.content_type
    })
    
    logger.info(
        "📸 [Image Service] Metadata after file info update | user_id=%s image_id=%s metadata_keys=%s",
        user_id,
        image_id,
        list(metadata.keys()),
    )
    
    # Log orchard_id presence EARLY
    if "orchard_id" in metadata:
        logger.info(
            "🔐 [Image Service] ORCHARD_ID PRESENT IN METADATA | user_id=%s image_id=%s orchard_id=%s",
            user_id,
            image_id,
            metadata["orchard_id"],
        )
    else:
        logger.warning(
            "⚠️ [Image Service] ORCHARD_ID MISSING FROM METADATA | user_id=%s image_id=%s",
            user_id,
            image_id,
        )
    
    # Add GPS data to metadata if available
    if gps_data:
        metadata.update(gps_data)
        logger.info(f"✅ GPS data added to metadata: {gps_data}")
    else:
        logger.info(f"⚠️ No GPS data found in image")
    
    # Create database record using admin client for now (we'll add RLS policies later)
    data = {
        "id": image_id,
        "user_id": user_id,
        "file_path": file_path,
        "file_name": storage_file_name,  # Store the storage filename instead of original
        "metadata": metadata,
        "created_at": now.isoformat()
    }
    
    logger.info(
        "💾 [Image Service] INSERTING IMAGE RECORD INTO DB | user_id=%s image_id=%s orchard_id=%s metadata=%s",
        user_id,
        image_id,
        metadata.get("orchard_id", "MISSING"),
        metadata,
    )
    
    try:
        result = admin_supabase.table("images").insert(data).execute()
        if not result.data:
            raise Exception("No data returned from database insert")
        inserted_record = result.data[0]
        logger.info(
            "✅ [Image Service] IMAGE RECORD INSERTED INTO DB | user_id=%s image_id=%s orchard_id_in_db=%s",
            user_id,
            image_id,
            inserted_record.get("metadata", {}).get("orchard_id", "MISSING_IN_RESPONSE"),
        )
        return ImageCreateResponse(**inserted_record)
    except Exception as e:
        # If database insert fails, try to delete the uploaded file
        print(f"Database insert failed: {str(e)}")
        try:
            print(f"Attempting to remove file from storage: {storage_file_name}")
            admin_supabase.storage.from_('images').remove(storage_file_name)
        except Exception as cleanup_error:
            print(f"Cleanup error: {str(cleanup_error)}")
        raise Exception(f"Image upload failed: {str(e)}")

# Get image by ID
async def get_image_service(image_id: str) -> ImageGetResponse:
    result = admin_supabase.table("images").select("*").eq("id", image_id).execute()
    if not result.data:
        raise Exception("Image not found")
    return ImageGetResponse(**result.data[0])

# Delete image by ID
async def delete_image_service(image_id: str) -> bool:
    try:
        # First get the image to get its file path
        image = await get_image_service(image_id)
        print(f"Found image with path: {image.file_path}")
        
        # The file name should be the same as what we saved: {image_id}{extension}
        file_extension = os.path.splitext(image.file_name)[1]
        storage_file_name = f"{image_id}{file_extension}"
        print(f"Attempting to delete storage file: {storage_file_name}")
        
        try:
            # List files in bucket first to verify
            bucket_files = admin_supabase.storage.from_('images').list()
            print(f"Files in bucket: {bucket_files}")
            
            # Delete from storage first
            storage_result = admin_supabase.storage.from_('images').remove(storage_file_name)
            print(f"Storage deletion result: {storage_result}")
        except Exception as storage_error:
            print(f"Storage deletion error: {str(storage_error)}")
            # Continue with database deletion even if storage deletion fails
        
        # Then delete from database
        result = admin_supabase.table("images").delete().eq("id", image_id).execute()
        
        if not result.data:
            raise Exception("Failed to delete image from database")
        
        print(f"Successfully deleted image {image_id} from database")
        return True
        
    except Exception as e:
        print(f"Delete operation failed: {str(e)}")
        raise Exception(f"Failed to delete image: {str(e)}")
    finally:
        print("Delete operation completed")

# Get all images for a user by user_id
async def get_images_by_user_service(user_id: str) -> list:
    result = admin_supabase.table("images").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return []
    return [ImageGetResponse(**item) for item in result.data]
