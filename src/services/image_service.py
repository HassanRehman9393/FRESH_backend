from src.core.supabase_client import supabase, admin_supabase
from src.schemas.image import ImageCreateResponse, ImageGetResponse
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, Any
import os
from fastapi import UploadFile
import aiofiles
import tempfile

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
        
        # Get public URL
        public_url = admin_supabase.storage.from_('images').get_public_url(file_name)
        
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
    storage_file_name = f"{image_id}{file_extension}"
    print(f"Generated storage file name: {storage_file_name}")
    
    # Upload to storage and get public URL
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
    metadata.update({
        "original_filename": file.filename,
        "storage_filename": storage_file_name,
        "content_type": file.content_type
    })
    
    # Create database record using admin client for now (we'll add RLS policies later)
    data = {
        "id": image_id,
        "user_id": user_id,
        "file_path": file_path,
        "file_name": storage_file_name,  # Store the storage filename instead of original
        "metadata": metadata,
        "created_at": now.isoformat()
    }
    
    try:
        result = admin_supabase.table("images").insert(data).execute()
        if not result.data:
            raise Exception("No data returned from database insert")
        print(f"Successfully created database record for image {image_id}")
        return ImageCreateResponse(**result.data[0])
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
