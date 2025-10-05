from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.core.supabase_client import admin_supabase
from src.schemas.detection import DetectionResponse, BatchDetectionResponse
from src.services.image_service import get_image_service

async def process_single_image(image_id: UUID, user_id: UUID) -> DetectionResponse:
    """
    Process a single image for object detection.
    For now, returns dummy data for testing.
    TODO: Integrate with actual ML model
    """
    try:
        # First verify the image exists and user has access
        await get_image_service(str(image_id))
        
        # Dummy detection result for testing
        detection_id = str(uuid4())
        current_time = datetime.utcnow()
        
        # In real implementation, this would be the result from ML model
        dummy_result = {
            "detection_id": detection_id,
            "user_id": str(user_id),
            "image_id": str(image_id),
            "fruit_type": "orange",  # Dummy value
            "confidence": 0.95,      # Dummy confidence score
            "bounding_box": {        # Dummy bounding box
                "x": 100.0,
                "y": 100.0,
                "width": 200.0,
                "height": 200.0
            },
            "created_at": current_time.isoformat()
        }
        
        print(f"Attempting to save detection result: {dummy_result}")
        
        # Save to database
        result = admin_supabase.table("detection_results").insert(dummy_result).execute()
        
        print(f"Database insert result: {result}")
        
        if not result.data:
            raise Exception("Failed to save detection result - no data returned")
            
        # Create response object
        response_data = result.data[0]
        print(f"Response data from DB: {response_data}")
        
        return DetectionResponse(**response_data)
        
    except Exception as e:
        print(f"Error in process_single_image: {str(e)}")
        raise Exception(f"Failed to process image {image_id}: {str(e)}")

async def process_batch_images(image_ids: List[UUID], user_id: UUID) -> BatchDetectionResponse:
    """Process multiple images for object detection"""
    results = []
    failed_count = 0
    
    print(f"Processing batch of {len(image_ids)} images for user {user_id}")
    
    for image_id in image_ids:
        try:
            print(f"Processing image: {image_id}")
            result = await process_single_image(image_id, user_id)
            results.append(result)
            print(f"Successfully processed image: {image_id}")
        except Exception as e:
            print(f"Failed to process image {image_id}: {str(e)}")
            failed_count += 1
    
    print(f"Batch processing complete. Success: {len(results)}, Failed: {failed_count}")
            
    return BatchDetectionResponse(
        results=results,
        total_count=len(image_ids),
        success_count=len(results),
        failed_count=failed_count
    )

async def get_detection_by_id(detection_id: UUID) -> DetectionResponse:
    """Retrieve a specific detection result"""
    result = admin_supabase.table("detection_results").select("*").eq("detection_id", str(detection_id)).execute()
    
    if not result.data:
        raise Exception("Detection result not found")
        
    return DetectionResponse(**result.data[0])

async def get_all_detections(user_id: UUID, limit: int = 10, offset: int = 0) -> List[DetectionResponse]:
    """Retrieve all detection results for a user"""
    result = admin_supabase.table("detection_results")\
        .select("*")\
        .eq("user_id", str(user_id))\
        .order("created_at", desc=True)\
        .limit(limit)\
        .offset(offset)\
        .execute()
        
    if not result.data:
        return []
        
    return [DetectionResponse(**item) for item in result.data]