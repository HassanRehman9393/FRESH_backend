from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.core.supabase_client import admin_supabase
from src.schemas.disease import DiseaseDetectionResponse, BatchDiseaseDetectionResponse
from src.services.detection_service import get_detection_by_id

async def process_single_disease_detection(detection_id: UUID, user_id: UUID) -> DiseaseDetectionResponse:
    """
    Process a single detection for disease analysis.
    For now, returns dummy data for testing.
    TODO: Integrate with actual ML disease detection model
    """
    try:
        # First verify the detection exists
        detection = await get_detection_by_id(detection_id)
        
        # Dummy disease detection result for testing
        disease_detection_id = str(uuid4())
        current_time = datetime.utcnow()
        
        # In real implementation, this would be the result from ML disease model
        dummy_result = {
            "disease_detection_id": disease_detection_id,
            "detection_id": str(detection_id),
            "user_id": str(user_id),
            "image_id": str(detection.image_id),
            "disease_type": "healthy",  # Dummy value: healthy, anthracnose, citrus_canker, unknown
            "is_diseased": False,       # Dummy value
            "disease_confidence": 0.92, # Dummy confidence score
            "severity_level": None,     # None for healthy fruits
            "probabilities": {          # Dummy probabilities
                "healthy": 0.92,
                "anthracnose": 0.05,
                "citrus_canker": 0.03
            },
            "created_at": current_time.isoformat()
        }
        
        print(f"Attempting to save disease detection result: {dummy_result}")
        
        # Save to database
        result = admin_supabase.table("disease_detections").insert(dummy_result).execute()
        
        print(f"Database insert result: {result}")
        
        if not result.data:
            raise Exception("Failed to save disease detection result - no data returned")
            
        # Create response object
        response_data = result.data[0]
        print(f"Response data from DB: {response_data}")
        
        return DiseaseDetectionResponse(**response_data)
        
    except Exception as e:
        print(f"Error in process_single_disease_detection: {str(e)}")
        raise Exception(f"Failed to process disease detection {detection_id}: {str(e)}")

async def process_batch_disease_detection(detection_ids: List[UUID], user_id: UUID) -> BatchDiseaseDetectionResponse:
    """Process multiple detections for disease analysis"""
    results = []
    failed_count = 0
    diseased_count = 0
    healthy_count = 0
    
    print(f"Processing batch of {len(detection_ids)} disease detections for user {user_id}")
    
    for detection_id in detection_ids:
        try:
            print(f"Processing disease detection for: {detection_id}")
            result = await process_single_disease_detection(detection_id, user_id)
            results.append(result)
            
            # Count diseased vs healthy
            if result.is_diseased:
                diseased_count += 1
            else:
                healthy_count += 1
                
            print(f"Successfully processed disease detection: {detection_id}")
        except Exception as e:
            print(f"Failed to process disease detection {detection_id}: {str(e)}")
            failed_count += 1
    
    print(f"Batch disease detection complete. Success: {len(results)}, Failed: {failed_count}, Diseased: {diseased_count}, Healthy: {healthy_count}")
            
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
