from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
import base64
import logging
from src.core.supabase_client import admin_supabase
from src.schemas.disease import DiseaseDetectionResponse, BatchDiseaseDetectionResponse
from src.services.detection_service import get_detection_by_id
from src.services.image_service import get_image_service
from src.services.ml_client import ml_client

logger = logging.getLogger(__name__)

async def process_single_disease_detection(detection_id: UUID, user_id: UUID) -> DiseaseDetectionResponse:
    """
    Process a single detection for disease analysis using ML API.
    Fetches image from storage, sends to ML API, and saves disease results to database.
    """
    try:
        # First verify the detection exists
        detection = await get_detection_by_id(detection_id)
        
        # Get image metadata from database
        image = await get_image_service(str(detection.image_id))
        
        # Convert Pydantic model to dict if needed
        if hasattr(image, 'model_dump'):
            image_dict = image.model_dump()
        elif hasattr(image, 'dict'):
            image_dict = image.dict()
        else:
            image_dict = image
        
        logger.info(f"Processing disease detection for image {detection.image_id}")
        
        # Download image from Supabase storage using stored filename
        bucket_name = "images"
        file_name = image_dict['file_name']  # This is the storage filename like "uuid.jpg"
        
        # Download file from storage
        file_response = admin_supabase.storage.from_(bucket_name).download(file_name)
        
        if not file_response:
            raise Exception(f"Failed to download image from storage: {file_name}")
        
        logger.info(f"Downloaded image from storage for disease detection")
        
        # Convert image bytes to base64
        image_base64 = base64.b64encode(file_response).decode('utf-8')
        
        logger.info(f"🔍 Sending to ML API - fruit_type: {detection.fruit_type}, image size: {len(file_response)/1024:.1f}KB")
        
        # Send to ML API for disease detection
        ml_result = await ml_client.detect_disease_base64(
            image_base64=image_base64,
            user_id=str(user_id),
            image_name=image_dict['file_name'],
            fruit_type=detection.fruit_type  # Use detected fruit type as hint
        )
        
        logger.info(f"✅ ML disease detection response received: success={ml_result.get('success')}, message={ml_result.get('message')}")
        logger.info(f"📊 Disease results count: {len(ml_result.get('disease_results', []))}")
        
        # Extract disease detection results from ML response
        if not ml_result.get('success'):
            raise Exception(f"ML API returned unsuccessful response: {ml_result.get('message')}")
        
        if not ml_result.get('disease_results') or len(ml_result['disease_results']) == 0:
            raise Exception("No disease detection results from ML API")
        
        # Get the first disease detection result
        first_disease = ml_result['disease_results'][0]
        
        # Extract orchard_id from detection for strict orchard-level isolation
        orchard_id = detection.orchard_id if hasattr(detection, 'orchard_id') else None
        if not orchard_id:
            logger.warning(f"⚠️ [Disease Service] Detection {detection_id} has no orchard_id - disease detection will not be orchard-linked")
        else:
            logger.info(f"🔐 [Disease Service] Detection linked to orchard={orchard_id} - disease detection will be stored with orchard isolation")
        
        # Prepare database record with orchard_id for isolation
        disease_record = {
            "disease_detection_id": str(uuid4()),
            "detection_id": str(detection_id),
            "user_id": str(user_id),
            "image_id": str(detection.image_id),
            "orchard_id": orchard_id,  # DATABASE-LEVEL ISOLATION: Store orchard_id directly
            "disease_type": first_disease.get('disease_type'),
            "is_diseased": first_disease.get('is_diseased'),
            "disease_confidence": first_disease.get('confidence'),
            "severity_level": first_disease.get('severity'),
            "probabilities": first_disease.get('probabilities'),
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"🔐 [Disease Service] DISEASE RECORD BEFORE INSERT: disease_detection_id={disease_record['disease_detection_id']} orchard_id={disease_record['orchard_id']} detection_id={disease_record['detection_id']}")
        
        logger.info(f"Saving disease detection result to database")
        
        # Save to database
        result = admin_supabase.table("disease_detections").insert(disease_record).execute()
        
        if not result.data:
            raise Exception("Failed to save disease detection result")
        
        # Create response object
        response_data = result.data[0]
        
        logger.info(f"🔐 [Disease Service] DISEASE RECORD AFTER INSERT: disease_detection_id={response_data.get('disease_detection_id')} stored_orchard_id={response_data.get('orchard_id')} detection_id={response_data.get('detection_id')}")
        
        return DiseaseDetectionResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Error in process_single_disease_detection: {str(e)}")
        raise Exception(f"Failed to process disease detection {detection_id}: {str(e)}")

async def process_batch_disease_detection(detection_ids: List[UUID], user_id: UUID) -> BatchDiseaseDetectionResponse:
    """Process multiple detections for disease analysis"""
    results = []
    failed_count = 0
    diseased_count = 0
    healthy_count = 0
    
    logger.info(f"Processing batch of {len(detection_ids)} disease detections for user {user_id}")
    
    for detection_id in detection_ids:
        try:
            logger.info(f"Processing disease detection for: {detection_id}")
            result = await process_single_disease_detection(detection_id, user_id)
            results.append(result)
            
            # Count diseased vs healthy
            if result.is_diseased:
                diseased_count += 1
            else:
                healthy_count += 1
                
            logger.info(f"Successfully processed disease detection: {detection_id}")
        except Exception as e:
            logger.error(f"Failed to process disease detection {detection_id}: {str(e)}")
            failed_count += 1
    
    logger.info(f"Batch disease detection complete. Success: {len(results)}, Failed: {failed_count}, Diseased: {diseased_count}, Healthy: {healthy_count}")
            
    return BatchDiseaseDetectionResponse(
        results=results,
        total_count=len(detection_ids),
        success_count=len(results),
        failed_count=failed_count,
        diseased_count=diseased_count,
        healthy_count=healthy_count
    )


async def get_disease_detection_by_id(disease_detection_id: UUID) -> DiseaseDetectionResponse:
    """Retrieve a specific disease detection result"""
    result = admin_supabase.table("disease_detections")\
        .select("*")\
        .eq("disease_detection_id", str(disease_detection_id))\
        .execute()
    
    if not result.data:
        raise Exception("Disease detection result not found")
        
    return DiseaseDetectionResponse(**result.data[0])

async def get_all_disease_detections(user_id: UUID, limit: int = 10, offset: int = 0) -> List[DiseaseDetectionResponse]:
    """Retrieve all disease detection results for a user"""
    result = admin_supabase.table("disease_detections")\
        .select("*")\
        .eq("user_id", str(user_id))\
        .order("created_at", desc=True)\
        .limit(limit)\
        .offset(offset)\
        .execute()
        
    if not result.data:
        return []
        
    return [DiseaseDetectionResponse(**item) for item in result.data]

async def get_diseased_detections(user_id: UUID, limit: int = 10, offset: int = 0) -> List[DiseaseDetectionResponse]:
    """Retrieve only diseased detection results for a user"""
    result = admin_supabase.table("disease_detections")\
        .select("*")\
        .eq("user_id", str(user_id))\
        .eq("is_diseased", True)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .offset(offset)\
        .execute()
        
    if not result.data:
        return []
        
    return [DiseaseDetectionResponse(**item) for item in result.data]
