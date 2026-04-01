from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.core.supabase_client import admin_supabase
from src.schemas.detection import DetectionResponse, BatchDetectionResponse
from src.services.image_service import get_image_service
from src.services.ml_client import ml_client
import base64
import logging
import re
import json

logger = logging.getLogger(__name__)

def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Parse timestamp string handling malformed microseconds.
    Handles timestamps with 5 digits in microseconds (e.g., '2025-12-08T18:35:13.38692+00:00')
    """
    try:
        # Remove 'Z' and replace with '+00:00' if present
        timestamp_str = timestamp_str.replace('Z', '+00:00')
        
        # Fix microseconds if they have wrong number of digits
        # Pattern: YYYY-MM-DDTHH:MM:SS.xxxxx+00:00 (5 digits) -> YYYY-MM-DDTHH:MM:SS.xxxxxx+00:00 (6 digits)
        match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d+)([\+\-]\d{2}:\d{2})', timestamp_str)
        if match:
            date_part, microseconds, timezone = match.groups()
            # Pad or truncate microseconds to exactly 6 digits
            microseconds = microseconds.ljust(6, '0')[:6]
            timestamp_str = f"{date_part}.{microseconds}{timezone}"
        
        return datetime.fromisoformat(timestamp_str)
    except Exception as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}. Using current time.")
        return datetime.utcnow()

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
        
        logger.info(
            f"📸 [Detection Service] Processing image | image_id={image_id} user_id={user_id}"
        )
        logger.info(
            f"📸 [Detection Service] Image file name: {image_dict['file_name']}"
        )
        logger.info(
            f"📸 [Detection Service] Full image metadata from DB: {image_dict.get('metadata', {})}"
        )
        
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
        
        # Extract visualization if available
        visualization_base64 = first_result.get('visualization_base64')
        annotated_url = None
        annotated_filename = None
        
        logger.info(f"📊 [Detection Service] Checking for visualization in ML response")
        logger.info(f"📊 [Detection Service] visualization_available: {first_result.get('visualization_available')}")
        logger.info(f"📊 [Detection Service] visualization_base64 exists: {visualization_base64 is not None}")
        
        if visualization_base64:
            try:
                logger.info(f"🎨 [Detection Service] Processing visualization for image {image_id}")
                logger.info(f"🎨 [Detection Service] Original visualization_base64 length: {len(visualization_base64)} chars")
                
                # Remove data URI prefix if present
                if ',' in visualization_base64:
                    logger.info(f"🎨 [Detection Service] Removing data URI prefix")
                    visualization_base64 = visualization_base64.split(',', 1)[1]
                
                # Decode base64 to bytes
                img_data = base64.b64decode(visualization_base64)
                logger.info(f"🎨 [Detection Service] Decoded visualization, size: {len(img_data)} bytes")
                
                # Generate filename for annotated image
                annotated_filename = f"annotated_{image_id}.jpg"
                logger.info(f"💾 [Detection Service] Uploading to bucket: detection-visualizations")
                logger.info(f"💾 [Detection Service] Filename: {annotated_filename}")
                
                # Upload to Supabase Storage 'detection-visualizations' bucket
                upload_result = admin_supabase.storage.from_('detection-visualizations').upload(
                    path=annotated_filename,
                    file=img_data,
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )
                logger.info(f"💾 [Detection Service] Upload result: {upload_result}")
                
                # Get public URL
                annotated_url = admin_supabase.storage.from_('detection-visualizations').get_public_url(annotated_filename)
                logger.info(f"✅ [Detection Service] Visualization uploaded successfully!")
                logger.info(f"✅ [Detection Service] Public URL: {annotated_url}")
                logger.info(f"✅ [Detection Service] URL length: {len(annotated_url)} chars")
                
            except Exception as viz_error:
                logger.error(f"Failed to process visualization: {str(viz_error)}")
                # Don't fail the entire detection if visualization fails
        
        # Extract orchard_id from image metadata for strict database-level isolation
        metadata = image_dict.get('metadata', {})

        # Handle case where metadata might be a JSON string instead of dict
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
                logger.warning(f"⚠️ [Detection Service] Could not parse metadata JSON string for image {image_id}")

        if not isinstance(metadata, dict):
            metadata = {}

        orchard_id = metadata.get('orchard_id')
        if not orchard_id:
            # Fallback: query images table directly in case model parsing dropped metadata
            try:
                image_metadata_response = admin_supabase.table("images").select("metadata").eq("id", str(image_id)).limit(1).execute()
                if image_metadata_response.data:
                    raw_metadata = image_metadata_response.data[0].get("metadata", {})
                    if isinstance(raw_metadata, str):
                        try:
                            raw_metadata = json.loads(raw_metadata)
                        except Exception:
                            raw_metadata = {}
                    if isinstance(raw_metadata, dict):
                        orchard_id = raw_metadata.get("orchard_id")
            except Exception as fallback_err:
                logger.warning(f"⚠️ [Detection Service] Failed fallback orchard_id lookup for image {image_id}: {fallback_err}")

        if not orchard_id:
            raise Exception(
                f"Image {image_id} is missing orchard_id in metadata; refusing to create detection_results with NULL orchard_id"
            )

        logger.info(
            f"🔐 [Detection Service] Image linked to orchard={orchard_id} | image_id={image_id} - detections will be stored with orchard isolation"
        )
        
        logger.info(
            f"🔐 [Detection Service] EXTRACTED orchard_id | image_id={image_id} orchard_id={orchard_id} type={type(orchard_id)}"
        )
        
        # Save ALL detected fruits (not just the first one)
        detection_results = []
        
        for fruit_detection in first_result['detection_results']:
            # Extract classification data from ML API response (it's included in detection results)
            classification_data = None
            if fruit_detection.get('ripeness_level'):
                classification_data = {
                    'ripeness_level': fruit_detection.get('ripeness_level'),
                    'ripeness_confidence': fruit_detection.get('classification_confidence'),
                    'color': fruit_detection.get('estimated_color'),
                    'size': fruit_detection.get('estimated_size'),
                    'quality_score': None,  # Can be calculated if needed
                    'defects': []  # Can be populated if disease detected
                }
                
                # Add disease info to defects if present
                if fruit_detection.get('is_diseased'):
                    classification_data['defects'].append(fruit_detection.get('disease_type', 'unknown_disease'))
                    
                logger.info(f"Classification data extracted: {classification_data}")
            
            # Generate detection_id upfront to use across all tables
            detection_id = str(uuid4())
            
            # 1. Save to detection_results table (fruit detection data) WITH ORCHARD_ID FOR ISOLATION
            detection_record = {
                "detection_id": detection_id,
                "user_id": str(user_id),
                "image_id": str(image_id),
                "orchard_id": orchard_id,  # DATABASE-LEVEL ISOLATION: Store orchard_id directly
                "fruit_type": fruit_detection.get('fruit_type'),
                "confidence": fruit_detection.get('detection_confidence'),
                "bounding_box": fruit_detection.get('bounding_box'),
                "annotated_image_url": annotated_url,
                "annotated_image_filename": annotated_filename,
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"💾 [Detection Service] Saving detection result for {fruit_detection.get('fruit_type')} with confidence {fruit_detection.get('detection_confidence')}")
            logger.info(f"💾 [Detection Service] annotated_image_url in record: {annotated_url}")
            logger.info(f"💾 [Detection Service] annotated_image_filename in record: {annotated_filename}")
            logger.info(f"🔐 [Detection Service] DETECTION RECORD BEFORE INSERT: detection_id={detection_record['detection_id']} orchard_id={detection_record['orchard_id']} user_id={detection_record['user_id']} image_id={detection_record['image_id']}")
            
            detection_result = admin_supabase.table("detection_results").insert(detection_record).execute()
            
            if not detection_result.data:
                logger.error(f"Failed to save detection result for fruit")
                continue
            
            saved_detection = detection_result.data[0]
            logger.info(f"🔐 [Detection Service] DETECTION RECORD AFTER INSERT: detection_id={saved_detection.get('detection_id')} stored_orchard_id={saved_detection.get('orchard_id')} from_db={saved_detection.get('orchard_id')}")
            bbox_data = saved_detection['bounding_box']
            
            # 2. Save to classification_results table (ripeness/color/size data) WITH ORCHARD_ID FOR ISOLATION
            if classification_data:
                classification_record = {
                    "detection_id": detection_id,
                    "orchard_id": orchard_id,  # DATABASE-LEVEL ISOLATION: Store orchard_id directly
                    "ripeness_level": classification_data.get('ripeness_level'),
                    "confidence_score": classification_data.get('ripeness_confidence'),
                    "estimated_color": classification_data.get('color'),
                    "estimated_size": classification_data.get('size'),
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Saving classification result for detection {detection_id}")
                classification_result = admin_supabase.table("classification_results").insert(classification_record).execute()
                
                if not classification_result.data:
                    logger.warning(f"Failed to save classification result")
            
            # 3. Save to disease_detections table (disease data) WITH ORCHARD_ID FOR ISOLATION
            if fruit_detection.get('is_diseased') is not None:
                disease_record = {
                    "detection_id": detection_id,
                    "user_id": str(user_id),
                    "image_id": str(image_id),
                    "orchard_id": orchard_id,  # DATABASE-LEVEL ISOLATION: Store orchard_id directly
                    "disease_type": fruit_detection.get('disease_type', 'unknown'),
                    "is_diseased": fruit_detection.get('is_diseased', False),
                    "disease_confidence": fruit_detection.get('disease_confidence', 0.0),
                    "severity_level": None,  # Can be added if ML API provides it
                    "probabilities": None,  # Can be added if ML API provides it
                    "created_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Saving disease detection result for detection {detection_id}")
                disease_result = admin_supabase.table("disease_detections").insert(disease_record).execute()
                
                if not disease_result.data:
                    logger.warning(f"Failed to save disease detection result")
            
            from src.schemas.detection import BoundingBox, ClassificationResult
            
            # Build classification response if available
            classification_response = None
            if classification_data:
                classification_response = ClassificationResult(
                    ripeness_level=classification_data.get('ripeness_level'),
                    ripeness_confidence=classification_data.get('ripeness_confidence'),
                    color=classification_data.get('color'),
                    size=classification_data.get('size'),
                    quality_score=classification_data.get('quality_score'),
                    defects=classification_data.get('defects', [])
                )
            
            detection_response = DetectionResponse(
                detection_id=UUID(saved_detection['detection_id']),
                user_id=UUID(saved_detection['user_id']),
                image_id=UUID(saved_detection['image_id']),
                orchard_id=UUID(saved_detection['orchard_id']) if saved_detection.get('orchard_id') else None,
                fruit_type=saved_detection['fruit_type'],
                confidence=float(saved_detection['confidence']),
                bounding_box=BoundingBox(
                    x=float(bbox_data.get('center_x', 0)),
                    y=float(bbox_data.get('center_y', 0)),
                    width=float(bbox_data.get('width', 0)),
                    height=float(bbox_data.get('height', 0))
                ),
                classification=classification_response,
                created_at=parse_timestamp(saved_detection['created_at']),
                annotated_image_url=saved_detection.get('annotated_image_url'),
                annotated_image_filename=saved_detection.get('annotated_image_filename')
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
    """Retrieve a specific detection result with classification data"""
    # Get detection data
    result = admin_supabase.table("detection_results").select("*").eq("detection_id", str(detection_id)).execute()
    
    if not result.data:
        raise Exception("Detection result not found")
    
    from src.schemas.detection import BoundingBox, ClassificationResult
    saved_data = result.data[0]
    bbox_data = saved_data['bounding_box']
    
    # Get classification data from classification_results table
    classification_response = None
    classification_result = admin_supabase.table("classification_results")\
        .select("*")\
        .eq("detection_id", str(detection_id))\
        .execute()
    
    if classification_result.data:
        class_data = classification_result.data[0]
        
        # Get disease data
        disease_result = admin_supabase.table("disease_detections")\
            .select("*")\
            .eq("detection_id", str(detection_id))\
            .execute()
        
        defects = []
        if disease_result.data and disease_result.data[0].get('is_diseased'):
            defects.append(disease_result.data[0].get('disease_type', 'unknown'))
        
        classification_response = ClassificationResult(
            ripeness_level=class_data.get('ripeness_level'),
            ripeness_confidence=class_data.get('confidence_score'),
            color=class_data.get('estimated_color'),
            size=class_data.get('estimated_size'),
            quality_score=None,
            defects=defects
        )
    
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
        classification=classification_response,
        created_at=parse_timestamp(saved_data['created_at']),
        annotated_image_url=saved_data.get('annotated_image_url'),
        annotated_image_filename=saved_data.get('annotated_image_filename')
    )

async def get_all_detections(user_id: UUID, limit: int = 10, offset: int = 0, orchard_id: UUID = None) -> List[DetectionResponse]:
    """Retrieve all detection results for a user with classification data, optionally filtered by orchard"""
    filter_mode = "user_plus_orchard" if orchard_id else "user_only"
    logger.info(
        "🔎 [Detection Service] Fetch detections request | mode=%s user_id=%s orchard_id=%s limit=%s offset=%s",
        filter_mode,
        str(user_id),
        str(orchard_id) if orchard_id else None,
        limit,
        offset,
    )

    query = admin_supabase.table("detection_results")\
        .select("*")\
        .eq("user_id", str(user_id))
    if orchard_id:
        query = query.eq("orchard_id", str(orchard_id))
    result = query.order("created_at", desc=True)\
        .limit(limit)\
        .offset(offset)\
        .execute()

    returned_count = len(result.data) if result.data else 0
    returned_user_ids = sorted({row.get("user_id") for row in (result.data or []) if row.get("user_id")})
    returned_orchard_ids = sorted({row.get("orchard_id") for row in (result.data or []) if row.get("orchard_id")})
    sample_detection_ids = [row.get("detection_id") for row in (result.data or [])[:5]]
    logger.info(
        "🔎 [Detection Service] Fetch detections response | mode=%s returned=%s users=%s orchards=%s sample_detection_ids=%s",
        filter_mode,
        returned_count,
        returned_user_ids,
        returned_orchard_ids,
        sample_detection_ids,
    )
        
    if not result.data:
        return []
    
    from src.schemas.detection import BoundingBox, ClassificationResult
    detections = []
    
    for item in result.data:
        bbox_data = item['bounding_box']
        detection_id = item['detection_id']
        
        # Get classification data from classification_results table
        classification_response = None
        classification_result = admin_supabase.table("classification_results")\
            .select("*")\
            .eq("detection_id", detection_id)\
            .execute()
        
        if classification_result.data:
            class_data = classification_result.data[0]
            
            # Get disease data
            disease_result = admin_supabase.table("disease_detections")\
                .select("*")\
                .eq("detection_id", detection_id)\
                .execute()
            
            defects = []
            if disease_result.data and disease_result.data[0].get('is_diseased'):
                defects.append(disease_result.data[0].get('disease_type', 'unknown'))
            
            classification_response = ClassificationResult(
                ripeness_level=class_data.get('ripeness_level'),
                ripeness_confidence=class_data.get('confidence_score'),
                color=class_data.get('estimated_color'),
                size=class_data.get('estimated_size'),
                quality_score=None,
                defects=defects
            )
        
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
            classification=classification_response,
            created_at=parse_timestamp(item['created_at']),
            annotated_image_url=item.get('annotated_image_url'),
            annotated_image_filename=item.get('annotated_image_filename')
        )
        detections.append(detection)
    
    return detections