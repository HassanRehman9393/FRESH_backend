from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.core.supabase_client import admin_supabase
from src.schemas.detection import DetectionResponse, BatchDetectionResponse
from src.services.image_service import get_image_service
from src.services.ml_client import ml_client
import base64
import logging

logger = logging.getLogger(__name__)

async def process_single_image(image_id: UUID, user_id: UUID) -> DetectionResponse:
    """
    Process a single image for object detection using ML API.
    Fetches image from storage, sends to ML API, and saves results to database.
    """
    try:
        # Get image metadata from database
        image = await get_image_service(str(image_id))
        
        # Convert Pydantic model to dict if needed
        if hasattr(image, 'model_dump'):
            image_dict = image.model_dump()
        elif hasattr(image, 'dict'):
            image_dict = image.dict()
        else:
            image_dict = image
        
        logger.info(f"Processing image {image_id} for user {user_id}")
        logger.info(f"Image file name: {image_dict['file_name']}")
        
        # Download image from Supabase storage using the stored filename
        bucket_name = "images"
        file_name = image_dict['file_name']  # This is the storage filename like "uuid.jpg"
        
        # Download file from storage
        file_response = admin_supabase.storage.from_(bucket_name).download(file_name)
        
        if not file_response:
            raise Exception(f"Failed to download image from storage: {file_name}")
        
        logger.info(f"Downloaded image from storage, size: {len(file_response)} bytes")
        
        # Convert image bytes to base64
        image_base64 = base64.b64encode(file_response).decode('utf-8')
        
        # Send to ML API for detection
        ml_result = await ml_client.detect_fruits_base64(
            image_base64=image_base64,
            user_id=str(user_id),
            image_name=image_dict['file_name']
        )
        
        logger.info(f"ML API response received: {ml_result.get('success')}")
        
        # Extract detection results from ML response
        if not ml_result.get('success'):
            raise Exception(f"ML API returned unsuccessful response: {ml_result.get('message')}")
        
        # Get the first result from ML API response (for single image)
        if not ml_result.get('results') or len(ml_result['results']) == 0:
            raise Exception("No detection results from ML API")
        
        first_result = ml_result['results'][0]
        
        if not first_result.get('detection_results') or len(first_result['detection_results']) == 0:
            raise Exception("No fruits detected in image")
        
        # Save ALL detected fruits (not just the first one)
        detection_results = []
        
        for fruit_detection in first_result['detection_results']:
            # Prepare database record for each detected fruit
            detection_record = {
                "detection_id": str(uuid4()),
                "user_id": str(user_id),
                "image_id": str(image_id),
                "fruit_type": fruit_detection.get('fruit_type'),
                "confidence": fruit_detection.get('detection_confidence'),
                "bounding_box": fruit_detection.get('bounding_box'),
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Saving detection result for {fruit_detection.get('fruit_type')} with confidence {fruit_detection.get('detection_confidence')}")
            
            # Save to database
            result = admin_supabase.table("detection_results").insert(detection_record).execute()
            
            if not result.data:
                logger.error(f"Failed to save detection result for fruit")
                continue
            
            # Convert to response model
            saved_data = result.data[0]
            bbox_data = saved_data['bounding_box']
            
            from src.schemas.detection import BoundingBox
            
            detection_response = DetectionResponse(
                detection_id=UUID(saved_data['detection_id']),
                user_id=UUID(saved_data['user_id']),
                image_id=UUID(saved_data['image_id']),
                fruit_type=saved_data['fruit_type'],
                confidence=float(saved_data['confidence']),
                bounding_box=BoundingBox(
                    x=float(bbox_data.get('center_x', 0)),
                    y=float(bbox_data.get('center_y', 0)),
                    width=float(bbox_data.get('width', 0)),
                    height=float(bbox_data.get('height', 0))
                ),
                created_at=datetime.fromisoformat(saved_data['created_at'].replace('Z', '+00:00'))
            )
            
            detection_results.append(detection_response)
        
        logger.info(f"Saved {len(detection_results)} detection results for image {image_id}")
        
        # Return all detections
        if not detection_results:
            raise Exception("Failed to save any detection results")
            
        return detection_results
        
    except Exception as e:
        logger.error(f"Error in process_single_image: {str(e)}")
        raise Exception(f"Failed to process image {image_id}: {str(e)}")

async def process_batch_images(image_ids: List[UUID], user_id: UUID) -> BatchDetectionResponse:
    """
    Process multiple images for object detection using ML API.
    Processes each image individually using the synchronous base64 endpoint.
    """
    results = []
    failed_count = 0
    
    logger.info(f"Processing batch of {len(image_ids)} images for user {user_id}")
    
    # Process each image individually
    for image_id in image_ids:
        try:
            logger.info(f"Processing image {image_id}")
            image_results = await process_single_image(image_id, user_id)
            
            # process_single_image now returns a list of all detections for that image
            if isinstance(image_results, list):
                results.extend(image_results)  # Add all detections from this image
            else:
                results.append(image_results)  # Backward compatibility if it returns single result
                
            logger.info(f"Successfully processed image {image_id} with {len(image_results) if isinstance(image_results, list) else 1} detections")
        except Exception as e:
            logger.error(f"Failed to process image {image_id}: {str(e)}")
            failed_count += 1
            continue
    
    logger.info(f"Batch processing complete. Success: {len(results)}, Failed: {failed_count}")
    
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
    
    from src.schemas.detection import BoundingBox
    saved_data = result.data[0]
    bbox_data = saved_data['bounding_box']
    
    return DetectionResponse(
        detection_id=UUID(saved_data['detection_id']),
        user_id=UUID(saved_data['user_id']),
        image_id=UUID(saved_data['image_id']),
        fruit_type=saved_data['fruit_type'],
        confidence=float(saved_data['confidence']),
        bounding_box=BoundingBox(
            x=float(bbox_data.get('center_x', bbox_data.get('x', 0))),
            y=float(bbox_data.get('center_y', bbox_data.get('y', 0))),
            width=float(bbox_data.get('width', 0)),
            height=float(bbox_data.get('height', 0))
        ),
        created_at=datetime.fromisoformat(saved_data['created_at'].replace('Z', '+00:00'))
    )

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
    
    from src.schemas.detection import BoundingBox
    detections = []
    
    for item in result.data:
        bbox_data = item['bounding_box']
        detection = DetectionResponse(
            detection_id=UUID(item['detection_id']),
            user_id=UUID(item['user_id']),
            image_id=UUID(item['image_id']),
            fruit_type=item['fruit_type'],
            confidence=float(item['confidence']),
            bounding_box=BoundingBox(
                x=float(bbox_data.get('center_x', bbox_data.get('x', 0))),
                y=float(bbox_data.get('center_y', bbox_data.get('y', 0))),
                width=float(bbox_data.get('width', 0)),
                height=float(bbox_data.get('height', 0))
            ),
            created_at=datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
        )
        detections.append(detection)
    
    return detections