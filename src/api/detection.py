from fastapi import APIRouter, HTTPException, status, Query, Depends, UploadFile, File
from typing import List, Optional
from uuid import UUID
from src.schemas.detection import (
    DetectionResponse, 
    BatchDetectionRequest, 
    BatchDetectionResponse,
    CompleteDetectionRequest,
    CompleteDetectionResponse,
    DetectionSummary
)
from src.services.detection_service import (
    process_single_image,
    process_batch_images,
    get_detection_by_id,
    get_all_detections
)
from src.api.deps import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detection", tags=["detection"])

@router.post("/batch-fruit", response_model=BatchDetectionResponse)
async def batch_detect_fruits(
    request: BatchDetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process multiple images for fruit detection.
    Returns detection results including bounding boxes and confidence scores.
    Requires authentication.
    """
    try:
        # Use the authenticated user's ID instead of the request user_id
        return await process_batch_images(request.image_ids, UUID(current_user["user_id"]))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/fruit/results", response_model=List[DetectionResponse])
async def get_detection_results(
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    orchard_id: Optional[str] = Query(None, description="Filter by orchard ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all detection results for the authenticated user.
    Supports pagination with limit and offset parameters.
    Optionally filter by orchard_id.
    Requires authentication.
    """
    try:
        return await get_all_detections(
            UUID(current_user["user_id"]), 
            limit, 
            offset,
            orchard_id=orchard_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/fruit/{detection_id}", response_model=DetectionResponse)
async def get_detection_result(
    detection_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a specific detection result by its ID.
    Requires authentication.
    """
    try:
        return await get_detection_by_id(detection_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/results/user/{user_id}", response_model=List[DetectionResponse])
async def get_detection_results_by_user(
    user_id: str,
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    Retrieve all object detection results for a specific user by user ID.
    Supports pagination with limit and offset parameters.
    """
    try:
        return await get_all_detections(UUID(user_id), limit, offset)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/process-complete", response_model=CompleteDetectionResponse)
async def process_complete_detection(
    request: CompleteDetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Unified endpoint that combines fruit detection, disease analysis, weather correlation,
    and alert generation into a single workflow.
    
    **Workflow:**
    1. Detect fruits in provided images
    2. Optionally analyze detected fruits for diseases
    3. Optionally fetch weather data for orchard location
    4. Optionally generate alerts for critical findings
    5. Return unified response with comprehensive summary
    
    **Parameters:**
    - **image_ids**: List of image UUIDs to process
    - **orchard_id**: Optional orchard UUID for weather/alert context
    - **options**:
        - **detect_diseases**: Run disease detection (default: true)
        - **check_weather**: Fetch weather data (default: true)
        - **generate_alerts**: Generate alerts (default: true)
    
    **Authentication:** JWT token required
    
    **Returns:** Complete detection response with all integrated data
    """
    try:
        from src.services.disease_service import process_single_disease_detection
        from src.services.weather_service import weather_service
        from src.services.alert_service import alert_service
        from src.core.supabase_client import supabase
        
        logger.info(f"🚀 Starting complete detection workflow for user {current_user['user_id']}")
        logger.info(f"📸 Processing {len(request.image_ids)} images")
        logger.info(f"🏭 Orchard ID: {request.orchard_id}")
        logger.info(f"⚙️ Options: diseases={request.options.detect_diseases}, weather={request.options.check_weather}, alerts={request.options.generate_alerts}")
        
        # Initialize response components
        detections = []
        diseases = []
        weather_context = None
        auto_alerts = []
        orchard_data = None
        
        # Step 1: Validate orchard if provided
        if request.orchard_id:
            logger.info(f"🔍 Validating orchard {request.orchard_id}")
            orchard_response = supabase.table("orchards")\
                .select("*")\
                .eq("id", request.orchard_id)\
                .eq("user_id", current_user["user_id"])\
                .execute()
            
            if not orchard_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Orchard {request.orchard_id} not found or does not belong to user"
                )
            
            orchard_data = orchard_response.data[0]
            logger.info(f"✅ Orchard validated: {orchard_data['name']}")
        
        # Step 2: Run fruit detection
        logger.info("🍎 Step 1/4: Running fruit detection...")
        try:
            batch_result = await process_batch_images(request.image_ids, UUID(current_user["user_id"]))
            detections = batch_result.results
            logger.info(f"✅ Detected {len(detections)} fruits")
        except Exception as e:
            logger.error(f"❌ Fruit detection failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Fruit detection failed: {str(e)}"
            )
        
        # Step 3: Run disease detection if requested
        diseased_count = 0
        healthy_count = 0
        
        if request.options.detect_diseases and detections:
            logger.info(f"🔬 Step 2/4: Running disease detection on {len(detections)} fruits...")
            for detection in detections:
                try:
                    disease_result = await process_single_disease_detection(
                        detection.detection_id,
                        UUID(current_user["user_id"])
                    )
                    
                    # Convert Pydantic model to dict for JSON serialization
                    if hasattr(disease_result, 'model_dump'):
                        disease_dict = disease_result.model_dump()
                    elif hasattr(disease_result, 'dict'):
                        disease_dict = disease_result.dict()
                    else:
                        disease_dict = disease_result
                    
                    diseases.append(disease_dict)
                    
                    # Track counts
                    if disease_result.is_diseased:
                        diseased_count += 1
                    else:
                        healthy_count += 1
                        
                except Exception as e:
                    logger.warning(f"⚠️ Disease detection failed for detection {detection.detection_id}: {str(e)}")
                    # Continue with other detections even if one fails
                    continue
            
            logger.info(f"✅ Disease analysis complete: {healthy_count} healthy, {diseased_count} diseased")
        else:
            logger.info("⏭️ Step 2/4: Disease detection skipped")
            healthy_count = len(detections)
        
        # Step 4: Fetch weather data if requested and orchard is provided
        if request.options.check_weather and request.orchard_id and orchard_data:
            logger.info(f"🌤️ Step 3/4: Fetching weather data for orchard...")
            try:
                weather_data = await weather_service.fetch_current_weather(
                    orchard_id=request.orchard_id,
                    latitude=float(orchard_data["latitude"]),
                    longitude=float(orchard_data["longitude"]),
                    use_cache=True
                )
                
                # Convert to dict if needed
                if hasattr(weather_data, 'model_dump'):
                    weather_context = weather_data.model_dump()
                elif hasattr(weather_data, 'dict'):
                    weather_context = weather_data.dict()
                else:
                    weather_context = weather_data
                    
                logger.info(f"✅ Weather data retrieved: {weather_context.get('temperature')}°C, {weather_context.get('humidity')}% humidity")
            except Exception as e:
                logger.warning(f"⚠️ Weather data fetch failed: {str(e)}")
                # Don't fail the entire request if weather fails
        else:
            logger.info("⏭️ Step 3/4: Weather check skipped")
        
        # Step 5: Generate alerts if requested and conditions are met
        critical_issues = []
        
        if request.options.generate_alerts and request.orchard_id and orchard_data:
            logger.info(f"🚨 Step 4/4: Generating alerts for critical findings...")
            
            # Alert for high disease rate
            if diseased_count > 0:
                disease_rate = (diseased_count / len(detections)) * 100
                
                if disease_rate >= 50:  # Critical: 50%+ diseased
                    severity = "critical"
                    critical_issues.append(f"Critical disease outbreak: {disease_rate:.1f}% of fruits diseased")
                elif disease_rate >= 30:  # High: 30-49% diseased
                    severity = "high"
                    critical_issues.append(f"High disease rate: {disease_rate:.1f}% of fruits diseased")
                elif disease_rate >= 15:  # Medium: 15-29% diseased
                    severity = "medium"
                else:
                    severity = "low"
                
                if disease_rate >= 15:  # Only create alert if >= 15%
                    try:
                        alert_data = {
                            "orchard_id": request.orchard_id,
                            "alert_type": "disease_risk",
                            "severity": severity,
                            "title": f"Disease Detection Alert - {disease_rate:.1f}% Affected",
                            "message": f"Disease detected in {diseased_count} out of {len(detections)} fruits ({disease_rate:.1f}%). Immediate inspection recommended.",
                            "is_active": True,
                            "metadata": {
                                "diseased_count": diseased_count,
                                "total_count": len(detections),
                                "disease_rate": disease_rate,
                                "detection_ids": [str(d.detection_id) for d in detections]
                            }
                        }
                        
                        created_alert = await alert_service.create_alert(
                            alert_data=alert_data,
                            orchard_data=orchard_data
                        )
                        
                        if created_alert:
                            auto_alerts.append(created_alert)
                            logger.info(f"✅ Disease alert created: {severity.upper()}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to create disease alert: {str(e)}")
            
            # Alert for weather conditions if available
            if weather_context:
                try:
                    # High humidity alert (>85% can promote fungal diseases)
                    humidity = weather_context.get('humidity', 0)
                    if humidity > 85:
                        severity = "high" if humidity > 90 else "medium"
                        critical_issues.append(f"High humidity detected: {humidity}%")
                        
                        alert_data = {
                            "orchard_id": request.orchard_id,
                            "alert_type": "high_humidity",
                            "severity": severity,
                            "title": f"High Humidity Alert - {humidity}%",
                            "message": f"Current humidity ({humidity}%) may promote fungal diseases. Monitor fruit health closely.",
                            "is_active": True,
                            "metadata": {
                                "humidity": humidity,
                                "temperature": weather_context.get('temperature')
                            }
                        }
                        
                        created_alert = await alert_service.create_alert(
                            alert_data=alert_data,
                            orchard_data=orchard_data
                        )
                        
                        if created_alert:
                            auto_alerts.append(created_alert)
                            logger.info(f"✅ Humidity alert created: {severity.upper()}")
                    
                    # Extreme temperature alert
                    temp = weather_context.get('temperature', 0)
                    if temp > 40 or temp < 5:
                        severity = "high" if (temp > 45 or temp < 2) else "medium"
                        critical_issues.append(f"Extreme temperature: {temp}°C")
                        
                        alert_data = {
                            "orchard_id": request.orchard_id,
                            "alert_type": "extreme_temp",
                            "severity": severity,
                            "title": f"Extreme Temperature Alert - {temp}°C",
                            "message": f"Current temperature ({temp}°C) may stress fruit trees. Take protective measures.",
                            "is_active": True,
                            "metadata": {
                                "temperature": temp,
                                "humidity": humidity
                            }
                        }
                        
                        created_alert = await alert_service.create_alert(
                            alert_data=alert_data,
                            orchard_data=orchard_data
                        )
                        
                        if created_alert:
                            auto_alerts.append(created_alert)
                            logger.info(f"✅ Temperature alert created: {severity.upper()}")
                            
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create weather alerts: {str(e)}")
            
            logger.info(f"✅ Alert generation complete: {len(auto_alerts)} alerts created")
        else:
            logger.info("⏭️ Step 4/4: Alert generation skipped")
        
        # Build summary
        summary = DetectionSummary(
            total_fruits=len(detections),
            healthy_count=healthy_count,
            diseased_count=diseased_count,
            critical_issues=critical_issues
        )
        
        logger.info(f"✅ Complete detection workflow finished successfully")
        logger.info(f"📊 Summary: {summary.total_fruits} total, {summary.healthy_count} healthy, {summary.diseased_count} diseased")
        
        # Build and return response
        return CompleteDetectionResponse(
            detections=detections,
            diseases=diseases if request.options.detect_diseases else None,
            weather_context=weather_context if request.options.check_weather else None,
            auto_alerts=auto_alerts if request.options.generate_alerts else None,
            summary=summary
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Complete detection workflow failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Complete detection workflow failed: {str(e)}"
        )