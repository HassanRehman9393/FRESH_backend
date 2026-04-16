"""
Yield Prediction Service

Orchestrates yield predictions by calling ML API and storing results.
Handles database interactions and ML API communication.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import httpx
from src.core.supabase_client import admin_supabase
from src.core.config import settings
from src.schemas.yield_schemas import (
    YieldPredictionRequest,
    YieldPredictionResponse,
    YieldPredictionCreate,
    YieldPredictionDB,
    HarvestRecordCreate,
    HarvestRecordResponse,
    YieldPredictionHistoryResponse,
    UserYieldStats,
    YieldPredictionSummary,
    ContributingFactors,
    SamplingDetails,
    BaselineComparison,
    YieldPredictionContextResponse,
    YieldDataSources,
    FruitType,
    TrendDirection,
    ModelUsed,
)

logger = logging.getLogger(__name__)


class YieldService:
    """Service for yield prediction operations
    
    DATA ISOLATION POLICY:
    =====================
    All detections, classifications, and disease data are STRICTLY isolated per orchard.
    
    - Detections are ONLY retrieved from images explicitly linked to the target orchard (via images.metadata.orchard_id)
    - NO user-wide detection fallback queries are performed
    - This ensures that data from Orchard A never appears when predicting for Orchard B,
      even if both orchards belong to the same user
    
    Implementation:
    - Images must have metadata.orchard_id set when uploaded
    - Context builder filters: images -> detections -> classifications/diseases
    - If no orchard-linked images exist, context building fails with actionable error
    """
    
    ML_API_TIMEOUT = settings.ml_api_timeout
    ML_API_URL = settings.ml_api_url
    
    @staticmethod
    async def _validate_orchard_ownership(
        user_id: UUID,
        orchard_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate that orchard exists and belongs to the user.
        Returns orchard record if valid, raises ValueError otherwise.
        
        This is the gatekeeper for orchard isolation - all operations must verify
        the user can access the orchard before querying its data.
        """
        orchard_id_str = str(orchard_id)
        response = admin_supabase.table("orchards").select(
            "id, area_hectares, fruit_types, created_at, user_id"
        ).eq("id", orchard_id_str).eq("user_id", str(user_id)).limit(1).execute()
        
        if not response.data:
            logger.warning(
                "🔐 [Yield Service] Orchard access denied | user_id=%s orchard_id=%s reason=not_found_or_not_owned",
                str(user_id),
                orchard_id_str,
            )
            raise ValueError("Selected orchard was not found for this user")
        
        logger.info(
            "🔐 [Yield Service] Orchard ownership verified | user_id=%s orchard_id=%s",
            str(user_id),
            orchard_id_str,
        )
        return response.data[0]
    
    @staticmethod
    async def predict_yield(
        user_id: UUID,
        request: YieldPredictionRequest,
        prediction_season: Optional[int] = None
    ) -> YieldPredictionResponse:
        """
        Predict yield for an orchard.
        
        1. Calls ML API to get prediction
        2. Stores result in database
        3. Returns response with prediction details
        
        Args:
            user_id: User making the request
            request: Yield prediction request with detection & weather data
            prediction_season: Year of prediction (defaults to current year)
        
        Returns:
            YieldPredictionResponse with prediction details
        
        Raises:
            HTTPException: If ML API call fails or database insert fails
        """
        try:
            if prediction_season is None:
                prediction_season = datetime.now().year
            
            logger.info(f"🌾 [Yield Service] Predicting yield for user {user_id}")
            logger.info(f"   Fruit type: {request.orchard_metadata.fruit_type}")
            logger.info(f"   Area: {request.orchard_metadata.area_hectares} hectares")
            
            # Call ML API for prediction
            ml_response = await YieldService._call_ml_api(request)
            
            if not ml_response.get('success'):
                logger.warning(f"⚠️  ML API returned unsuccessful response: {ml_response.get('error')}")
                # Fall back to baseline only prediction
                return await YieldService._create_baseline_prediction(
                    request, ml_response
                )
            
            logger.info("✅ ML API prediction successful")
            
            # Extract ML response data
            prediction_data = ml_response.get('prediction', {})
            sampling_data = ml_response.get('sampling', {})
            baseline_data = ml_response.get('baseline', {})
            
            # Get user's historical data for context
            historical_avg = await YieldService._get_user_historical_average(
                user_id,
                request.orchard_metadata.fruit_type
            )
            historical_trend = await YieldService._get_user_yield_trend(
                user_id,
                request.orchard_metadata.fruit_type
            )
            
            # Create database record
            db_record = YieldPredictionCreate(
                user_id=user_id,
                fruit_type=request.orchard_metadata.fruit_type,
                orchard_id=request.orchard_metadata.orchard_id,
                prediction_season=prediction_season,
                
                orchard_area_hectares=request.orchard_metadata.area_hectares,
                predicted_yield_kg=prediction_data.get('predicted_yield_kg', 0),
                confidence_score=prediction_data.get('confidence', 0),
                confidence_lower_bound_kg=prediction_data.get('confidence_interval', {}).get('lower_bound', 0),
                confidence_upper_bound_kg=prediction_data.get('confidence_interval', {}).get('upper_bound', 0),
                
                health_score=prediction_data.get('contributing_factors', {}).get('health_score', 0.5),
                ripeness_percentage=request.detection_aggregates.ripe_percentage,
                disease_percentage=request.detection_aggregates.disease_percentage,
                weather_favorability=prediction_data.get('contributing_factors', {}).get('weather_favorability', 0.5),
                coverage_score=request.detection_aggregates.coverage_score,
                
                total_fruits_detected=request.detection_aggregates.total_fruits,
                extrapolated_fruit_count=sampling_data.get('extrapolated_fruit_count', 0),
                sampling_factor=sampling_data.get('sampling_factor', 1.0),
                sampling_pattern=sampling_data.get('pattern_used', 'w-shaped'),
                sampling_confidence=sampling_data.get('sampling_confidence', 0.5),
                detection_count=request.detection_aggregates.detection_count,
                
                regional_baseline_yield_kg=baseline_data.get('regional_yield_kg_per_hectare', 0),
                regional_baseline_std_dev=baseline_data.get('regional_std_dev', 0),
                variance_from_baseline_percent=YieldService._calculate_variance(
                    prediction_data.get('predicted_yield_kg', 0),
                    baseline_data.get('regional_yield_kg_per_hectare', 0)
                ),
                
                trend_direction=prediction_data.get('trend_direction', 'unknown'),
                model_used=prediction_data.get('model_used', 'xgboost'),
                model_version='1.0',
                
                user_historical_average_yield_kg=historical_avg,
                user_historical_trend=historical_trend,
                
                aggregation_period_days=request.detection_aggregates.detection_count or 30,
                prediction_used_fallback=False,
            )
            
            # Save to database
            saved_record = await YieldService._save_prediction_to_db(db_record)
            logger.info(f"✅ Prediction saved to database: {saved_record.id}")
            
            # Format response
            response = YieldPredictionResponse(
                prediction_id=saved_record.id,
                predicted_yield_kg=prediction_data.get('predicted_yield_kg', 0),
                confidence=prediction_data.get('confidence', 0),
                confidence_interval=prediction_data.get('confidence_interval', {}),
                contributing_factors=ContributingFactors(
                    **prediction_data.get('contributing_factors', {})
                ),
                trend_direction=prediction_data.get('trend_direction', 'unknown'),
                model_used=prediction_data.get('model_used', 'xgboost'),
                sampling=SamplingDetails(**sampling_data),
                baseline=BaselineComparison(
                    regional_baseline_yield_kg_per_hectare=baseline_data.get('regional_yield_kg_per_hectare', 0),
                    regional_std_dev_kg=baseline_data.get('regional_std_dev', 0),
                    variance_from_baseline_percent=saved_record.variance_from_baseline_percent,
                ),
                fruit_type=request.orchard_metadata.fruit_type,
                orchard_area_hectares=request.orchard_metadata.area_hectares,
                timestamp=datetime.now(),
            )
            
            logger.info(f"🌾 Yield prediction completed: {response.predicted_yield_kg:.0f}kg")
            return response
            
        except Exception as e:
            logger.error(f"❌ Yield prediction failed: {str(e)}")
            raise
    
    @staticmethod
    async def _call_ml_api(request: YieldPredictionRequest) -> Dict[str, Any]:
        """Call ML API for yield prediction"""
        try:
            ml_url = f"{YieldService.ML_API_URL}/api/yield/predict"
            
            payload = {
                "detection_aggregates": request.detection_aggregates.model_dump(mode="json"),
                "weather_data": request.weather_data.model_dump(mode="json"),
                "orchard_metadata": request.orchard_metadata.model_dump(mode="json", by_alias=False),
            }
            
            logger.info(f"📡 Calling ML API: {ml_url}")
            
            async with httpx.AsyncClient(timeout=YieldService.ML_API_TIMEOUT) as client:
                response = await client.post(ml_url, json=payload)
                response.raise_for_status()
                
            result = response.json()
            logger.info(f"✅ ML API responded with status: {response.status_code}")
            return result
            
        except Exception as e:
            logger.error(f"❌ ML API call failed: {str(e)}")
            raise
    
    @staticmethod
    async def _save_prediction_to_db(prediction: YieldPredictionCreate) -> YieldPredictionDB:
        """Save prediction to database"""
        try:
            prediction_payload = prediction.model_dump(mode="json")
            logger.info(
                "💾 [Yield Service] Saving prediction | user_id=%s orchard_id=%s fruit_type=%s",
                prediction_payload.get("user_id"),
                prediction_payload.get("orchard_id"),
                prediction_payload.get("fruit_type"),
            )
            response = admin_supabase.table('yield_predictions').insert(
                prediction_payload
            ).execute()
            
            if response.data:
                return YieldPredictionDB(**response.data[0])
            else:
                raise Exception("Failed to save prediction to database")
                
        except Exception as e:
            logger.error(f"❌ Database insert failed: {str(e)}")
            raise
    
    @staticmethod
    async def get_prediction_history(
        user_id: UUID,
        fruit_type: Optional[FruitType] = None,
        orchard_id: Optional[UUID] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[YieldPredictionHistoryResponse]:
        """Get user's yield prediction history, optionally filtered by orchard"""
        try:
            query = admin_supabase.table('yield_predictions').select(
                'id, prediction_date, fruit_type, predicted_yield_kg, confidence_score, '
                'trend_direction, orchard_area_hectares'
            ).eq('user_id', str(user_id))

            if orchard_id:
                query = query.eq('orchard_id', str(orchard_id))
            if fruit_type:
                query = query.eq('fruit_type', fruit_type)
            
            response = query.order('prediction_date', desc=True).range(
                offset, offset + limit - 1
            ).execute()
            
            results = []
            for item in response.data:
                # Map DB column confidence_score to schema field confidence
                if 'confidence_score' in item and 'confidence' not in item:
                    item['confidence'] = item.pop('confidence_score')
                results.append(YieldPredictionHistoryResponse(**item))
            return results

        except Exception as e:
            logger.error(f"❌ Failed to get prediction history: {str(e)}")
            return []
    
    @staticmethod
    async def get_latest_prediction(
        user_id: UUID,
        fruit_type: FruitType
    ) -> Optional[YieldPredictionDB]:
        """Get user's most recent prediction for a fruit type"""
        try:
            response = admin_supabase.table('yield_predictions').select(
                '*'
            ).eq('user_id', str(user_id)).eq(
                'fruit_type', fruit_type
            ).order('prediction_date', desc=True).limit(1).execute()
            
            if response.data:
                return YieldPredictionDB(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get latest prediction: {str(e)}")
            return None
    
    @staticmethod
    async def register_harvest(
        user_id: UUID,
        harvest_record: HarvestRecordCreate
    ) -> HarvestRecordResponse:
        """Register actual harvest yield for future model training"""
        try:
            record_data = harvest_record.model_dump(mode="json")
            record_data['user_id'] = str(user_id)
            record_data['yield_per_hectare'] = (
                record_data['actual_yield_kg'] / record_data['orchard_area_hectares']
            )
            
            response = admin_supabase.table('user_harvest_records').insert(
                record_data
            ).execute()
            
            if response.data:
                return HarvestRecordResponse(**response.data[0])
            else:
                raise Exception("Failed to save harvest record")
                
        except Exception as e:
            logger.error(f"❌ Failed to register harvest: {str(e)}")
            raise
    
    @staticmethod
    async def get_user_harvest_records(
        user_id: UUID,
        fruit_type: Optional[FruitType] = None
    ) -> List[HarvestRecordResponse]:
        """Get user's harvest records"""
        try:
            query = admin_supabase.table('user_harvest_records').select('*').eq(
                'user_id', str(user_id)
            )
            
            if fruit_type:
                query = query.eq('fruit_type', fruit_type)
            
            response = query.order('harvest_date', desc=True).execute()
            return [HarvestRecordResponse(**item) for item in response.data]
            
        except Exception as e:
            logger.error(f"❌ Failed to get harvest records: {str(e)}")
            return []

    @staticmethod
    async def get_prediction_context_from_db(
        user_id: UUID,
        orchard_id: UUID,
        window_days: int = 30,
    ) -> YieldPredictionContextResponse:
        """
        Build yield prediction request payload from persisted DB records.
        
        ISOLATION ENFORCED: All data retrieved is strictly filtered to the target orchard.
        No cross-orchard data will be included regardless of user's other orchards.
        """
        orchard_id_str = str(orchard_id)
        effective_window_days = max(1, window_days)

        logger.info(
            "🌾 [Yield Service] Context build start (ISOLATED MODE) | user_id=%s orchard_id=%s window_days=%s",
            str(user_id),
            orchard_id_str,
            effective_window_days,
        )

        # GATE 1: Verify orchard ownership (prevents cross-user access)
        orchard = await YieldService._validate_orchard_ownership(user_id, orchard_id)
        
        logger.info(
            "🌾 [Yield Service] Orchard loaded | orchard_id=%s area_hectares=%s fruit_types=%s",
            orchard_id_str,
            orchard.get("area_hectares"),
            orchard.get("fruit_types") or [],
        )

        # GATE 2: Retrieve only images linked to THIS orchard (prevents cross-orchard data)
        image_response = admin_supabase.table("images").select(
            "id, metadata, created_at"
        ).eq("user_id", str(user_id)).contains(
            "metadata", {"orchard_id": orchard_id_str}
        ).order("created_at", desc=True).limit(300).execute()

        image_ids = [img["id"] for img in image_response.data] if image_response.data else []
        fruit_candidates = orchard.get("fruit_types") or []
        logger.info(
            "🔐 [Yield Service] Orchard-linked images query (ISOLATION) | orchard_id=%s image_count=%s",
            orchard_id_str,
            len(image_ids),
        )

        # GATE 3: Get detections ONLY from this orchard via direct orchard_id filter (DATABASE ISOLATION)
        # This provides defense-in-depth: orchard_id is stored directly in detection_results,
        # so even if image association breaks, orchard isolation is still enforced
        detections = []
        if image_ids:
            # Primary query: from image_ids AND orchard_id (dual filtering)
            logger.info(
                "🔐 [Yield Service] EXECUTING DETECTION QUERY | orchard_id=%s filters: image_ids count=%s",
                orchard_id_str,
                len(image_ids),
            )
            
            detection_response = admin_supabase.table("detection_results").select(
                "detection_id, image_id, confidence, fruit_type, orchard_id"
            ).eq("user_id", str(user_id)).eq("orchard_id", orchard_id_str).in_("image_id", image_ids).order("created_at", desc=True).limit(1000).execute()
            
            detections = detection_response.data or []
            logger.info(
                "🔐 [Detection Service] QUERY RESULT - Detection rows returned: %s | all have orchard_id=%s? Checking...",
                len(detections),
                orchard_id_str,
            )
            
            # Verify all returned detections have the correct orchard_id
            if detections:
                orchard_ids_in_result = set(d.get('orchard_id') for d in detections)
                logger.info(
                    "🔐 [Yield Service] RETURNED DETECTIONS ORCHARD_IDS: %s | Expected: %s",
                    orchard_ids_in_result,
                    orchard_id_str,
                )
                for idx, det in enumerate(detections[:3]):  # Log first 3
                    logger.info(
                        "🔐 [Yield Service] Sample detection [%s]: detection_id=%s orchard_id=%s image_id=%s",
                        idx,
                        det.get('detection_id'),
                        det.get('orchard_id'),
                        det.get('image_id'),
                    )
            
            logger.info(
                "🔐 [Yield Service] Detections from ORCHARD-ID FILTERED QUERY (ISOLATION) | orchard_id=%s detections=%s",
                orchard_id_str,
                len(detections),
            )
            
            # Fallback: if query with image_ids returns nothing but orchard_id detections exist,
            # get detections from orchard ONLY (handles unlinked images edge case)
            if not detections:
                logger.info(
                    "🔐 [Yield Service] Image-linked query returned empty, trying orchard_id-only query as fallback | orchard_id=%s",
                    orchard_id_str,
                )
                detection_response_fallback = admin_supabase.table("detection_results").select(
                    "detection_id, image_id, confidence, fruit_type, orchard_id"
                ).eq("user_id", str(user_id)).eq("orchard_id", orchard_id_str).order("created_at", desc=True).limit(1000).execute()
                detections = detection_response_fallback.data or []
                logger.info(
                    "🔐 [Yield Service] Fallback orchard_id-only query result | orchard_id=%s detections=%s",
                    orchard_id_str,
                    len(detections),
                )

        # STRICT ISOLATION: No fallback to user-wide detections.
        # Detections must be from images explicitly linked to this orchard.
        # This ensures orchard data is never mixed between orchards even if same user.
        if not detections:
            logger.warning(
                "⚠️ [Yield Service] No detections found - orchard has no linked images | user_id=%s orchard_id=%s image_count=%s",
                str(user_id),
                orchard_id_str,
                len(image_ids),
            )
            raise ValueError(
                f"No detection results found for this orchard. "
                f"Please upload images to orchard '{orchard_id}' first and they will appear here. "
                f"Currently {len(image_ids)} orchard-linked image(s) found."
            )

        detection_ids = [d["detection_id"] for d in detections if d.get("detection_id")]

        classifications = []
        diseases = []
        if detection_ids:
            # Query classifications with BOTH detection_id AND orchard_id filters (defense-in-depth)
            logger.info(
                "🔐 [Yield Service] QUERYING CLASSIFICATIONS | orchard_id=%s detection_ids count=%s",
                orchard_id_str,
                len(detection_ids),
            )
            
            classification_response = admin_supabase.table("classification_results").select(
                "detection_id, ripeness_level, orchard_id"
            ).eq("orchard_id", orchard_id_str).in_("detection_id", detection_ids).execute()
            classifications = classification_response.data or []
            
            logger.info(
                "🔐 [Yield Service] CLASSIFICATIONS RETURNED | orchard_id=%s count=%s | checking orchard isolation...",
                orchard_id_str,
                len(classifications),
            )
            
            if classifications:
                classification_orchard_ids = set(c.get('orchard_id') for c in classifications)
                logger.info(
                    "🔐 [Yield Service] Classification results have orchard_ids: %s | Expected: %s",
                    classification_orchard_ids,
                    orchard_id_str,
                )

            # Query diseases with BOTH detection_id AND orchard_id filters (defense-in-depth)
            logger.info(
                "🔐 [Yield Service] QUERYING DISEASES | orchard_id=%s detection_ids count=%s",
                orchard_id_str,
                len(detection_ids),
            )
            
            disease_response = admin_supabase.table("disease_detections").select(
                "detection_id, is_diseased, orchard_id"
            ).eq("orchard_id", orchard_id_str).in_("detection_id", detection_ids).execute()
            diseases = disease_response.data or []

            # Backward compatibility for legacy rows created before orchard_id propagation.
            # This remains orchard-safe because detection_ids are already scoped to this orchard.
            if not diseases:
                legacy_disease_response = admin_supabase.table("disease_detections").select(
                    "detection_id, is_diseased, orchard_id"
                ).in_("detection_id", detection_ids).execute()
                legacy_diseases = legacy_disease_response.data or []
                diseases = [
                    row for row in legacy_diseases
                    if row.get("orchard_id") in (None, orchard_id_str)
                ]
                logger.info(
                    "🔐 [Yield Service] Legacy disease fallback applied | orchard_id=%s legacy_rows=%s",
                    orchard_id_str,
                    len(diseases),
                )
            
            logger.info(
                "🔐 [Yield Service] DISEASES RETURNED | orchard_id=%s count=%s | checking orchard isolation...",
                orchard_id_str,
                len(diseases),
            )
            
            if diseases:
                disease_orchard_ids = set(d.get('orchard_id') for d in diseases)
                logger.info(
                    "🔐 [Yield Service] Disease results have orchard_ids: %s | Expected: %s",
                    disease_orchard_ids,
                    orchard_id_str,
                )

        logger.info(
            "🔐 [Yield Service] Linked result rows (FROM ORCHARD_ID FILTERED QUERIES) | detections=%s classifications=%s diseases=%s",
            len(detections),
            len(classifications),
            len(diseases),
        )

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=effective_window_days)
        weather_response = admin_supabase.table("weather_data").select(
            "temperature, temp_min, temp_max, humidity, rainfall, recorded_at"
        ).eq("orchard_id", orchard_id_str).gte(
            "recorded_at", start_date.isoformat()
        ).lte(
            "recorded_at", end_date.isoformat()
        ).order("recorded_at", desc=True).execute()

        weather_rows = weather_response.data or []
        if not weather_rows:
            logger.warning(
                "⚠️ [Yield Service] No weather rows found | orchard_id=%s start=%s end=%s",
                orchard_id_str,
                start_date.isoformat(),
                end_date.isoformat(),
            )
            raise ValueError("No weather history found for this orchard. Open weather dashboard to fetch weather first.")

        logger.info(
            "🌾 [Yield Service] Weather rows loaded | orchard_id=%s rows=%s start=%s end=%s",
            orchard_id_str,
            len(weather_rows),
            start_date.isoformat(),
            end_date.isoformat(),
        )

        total_fruits = len(detections)
        avg_confidence = sum(float(d.get("confidence", 0)) for d in detections) / max(total_fruits, 1)
        detection_count = len({str(d.get("image_id")) for d in detections if d.get("image_id")})
        coverage_score = min(1.0, detection_count / 20)

        ripe = 0
        unripe = 0
        overripe = 0
        for cls in classifications:
            level = str(cls.get("ripeness_level", "")).lower()
            if level == "ripe":
                ripe += 1
            elif level == "overripe":
                overripe += 1
            else:
                unripe += 1

        if not classifications:
            unripe = total_fruits

        total_classified = max(ripe + unripe + overripe, 1)
        ripe_percentage = (ripe / total_classified) * 100
        unripe_percentage = (unripe / total_classified) * 100
        overripe_percentage = (overripe / total_classified) * 100

        diseased_count = sum(1 for d in diseases if d.get("is_diseased"))
        disease_percentage = (diseased_count / max(total_fruits, 1)) * 100

        temperatures = [float(w.get("temperature", 0)) for w in weather_rows]
        temp_mins = [float(w.get("temp_min", w.get("temperature", 0))) for w in weather_rows]
        temp_maxs = [float(w.get("temp_max", w.get("temperature", 0))) for w in weather_rows]
        humidities = [float(w.get("humidity", 0)) for w in weather_rows]
        rainfalls = [float(w.get("rainfall", 0)) for w in weather_rows]

        fruit_value = fruit_candidates[0] if fruit_candidates else "mango"
        if fruit_value not in {"mango", "orange", "guava", "grapefruit"}:
            fruit_value = "mango"

        orchard_created_at_raw = orchard.get("created_at")
        orchard_created_at = datetime.utcnow()
        if orchard_created_at_raw:
            orchard_created_at = datetime.fromisoformat(str(orchard_created_at_raw).replace("Z", "+00:00")).replace(tzinfo=None)

        payload = YieldPredictionRequest(
            detection_aggregates={
                "total_fruits": total_fruits,
                "ripe_percentage": round(ripe_percentage, 2),
                "unripe_percentage": round(unripe_percentage, 2),
                "overripe_percentage": round(overripe_percentage, 2),
                "disease_percentage": round(disease_percentage, 2),
                "average_confidence": round(avg_confidence, 4),
                "coverage_score": round(coverage_score, 4),
                "detection_count": detection_count,
            },
            weather_data={
                "temperature_avg": round(sum(temperatures) / max(len(temperatures), 1), 2),
                "temperature_min": round(min(temp_mins), 2),
                "temperature_max": round(max(temp_maxs), 2),
                "rainfall_sum": round(sum(rainfalls), 2),
                "humidity_avg": round(sum(humidities) / max(len(humidities), 1), 2),
                "humidity_min": round(min(humidities), 2),
                "humidity_max": round(max(humidities), 2),
                "data_points": len(weather_rows),
            },
            orchard_metadata={
                "area_hectares": float(orchard.get("area_hectares") or 1.0),
                "fruit_type": fruit_value,
                "days_since_planting": max((datetime.utcnow() - orchard_created_at).days, 0),
                "orchard_id": orchard_id_str,
            },
        )

        logger.info(
            "✅ [Yield Service] Context build complete (ISOLATED TO ORCHARD) | orchard_id=%s total_fruits=%s detection_count=%s coverage=%s ripe_pct=%s disease_pct=%s",
            orchard_id_str,
            total_fruits,
            detection_count,
            round(coverage_score, 4),
            round(ripe_percentage, 2),
            round(disease_percentage, 2),
        )

        return YieldPredictionContextResponse(
            payload=payload,
            sources=YieldDataSources(
                orchard_id=orchard_id,
                weather_records_used=len(weather_rows),
                detection_records_used=len(detections),
                disease_records_used=len(diseases),
                classification_records_used=len(classifications),
                time_window_days=effective_window_days,
            ),
        )
    
    @staticmethod
    async def get_user_yield_stats(
        user_id: UUID,
        orchard_id: Optional[UUID] = None,
    ) -> Optional[UserYieldStats]:
        """Get comprehensive yield statistics for user, optionally filtered by orchard"""
        try:
            # Get predictions
            query = admin_supabase.table('yield_predictions').select(
                '*'
            ).eq('user_id', str(user_id))
            if orchard_id:
                query = query.eq('orchard_id', str(orchard_id))
            predictions = query.execute()
            
            # Calculate stats by fruit type
            stats_by_fruit = {}
            for pred in predictions.data:
                fruit = pred['fruit_type']
                if fruit not in stats_by_fruit:
                    stats_by_fruit[fruit] = {
                        'count': 0,
                        'total_yield': 0,
                        'total_confidence': 0,
                        'records': []
                    }
                stats_by_fruit[fruit]['count'] += 1
                stats_by_fruit[fruit]['total_yield'] += pred['predicted_yield_kg']
                stats_by_fruit[fruit]['total_confidence'] += pred['confidence_score']
                stats_by_fruit[fruit]['records'].append(pred)
            
            # Return stats for most recent fruit type
            if stats_by_fruit:
                recent = predictions.data[0]
                fruit_type = recent['fruit_type']
                fruit_stats = stats_by_fruit[fruit_type]
                
                # Map DB records to history response (confidence_score -> confidence)
                recent = []
                for p in fruit_stats['records'][:5]:
                    mapped = dict(p)
                    if 'confidence_score' in mapped and 'confidence' not in mapped:
                        mapped['confidence'] = mapped.pop('confidence_score')
                    recent.append(YieldPredictionHistoryResponse(**mapped))

                return UserYieldStats(
                    fruit_type=fruit_type,
                    predictions_count=fruit_stats['count'],
                    average_predicted_yield_kg=fruit_stats['total_yield'] / fruit_stats['count'],
                    average_confidence=fruit_stats['total_confidence'] / fruit_stats['count'],
                    recent_predictions=recent,
                    harvest_records=await YieldService.get_user_harvest_records(user_id, fruit_type),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get user yield stats: {str(e)}")
            return None
    
    @staticmethod
    async def _get_user_historical_average(
        user_id: UUID,
        fruit_type: FruitType
    ) -> Optional[float]:
        """Get user's historical average yield for a fruit type"""
        try:
            response = admin_supabase.table('user_harvest_records').select(
                'yield_per_hectare'
            ).eq('user_id', str(user_id)).eq('fruit_type', fruit_type).execute()
            
            if response.data:
                yields = [r['yield_per_hectare'] for r in response.data if r['yield_per_hectare']]
                return sum(yields) / len(yields) if yields else None
            return None
            
        except Exception as e:
            logger.error(f"⚠️  Failed to get historical average: {str(e)}")
            return None
    
    @staticmethod
    async def _get_user_yield_trend(
        user_id: UUID,
        fruit_type: FruitType
    ) -> Optional[str]:
        """Analyze user's yield trend"""
        try:
            response = admin_supabase.table('user_harvest_records').select(
                'yield_per_hectare, harvest_date'
            ).eq('user_id', str(user_id)).eq(
                'fruit_type', fruit_type
            ).order('harvest_date', desc=True).limit(10).execute()
            
            if len(response.data) < 2:
                return None
            
            yields = [r['yield_per_hectare'] for r in response.data]
            recent_avg = sum(yields[:len(yields)//2]) / (len(yields)//2)
            older_avg = sum(yields[len(yields)//2:]) / (len(yields) - len(yields)//2)
            
            change_pct = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            
            if change_pct > 5:
                return 'improving'
            elif change_pct < -5:
                return 'declining'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"⚠️  Failed to get yield trend: {str(e)}")
            return None
    
    @staticmethod
    def _calculate_variance(predicted: float, baseline: float) -> float:
        """Calculate variance percentage from baseline"""
        if baseline == 0:
            return 0
        return ((predicted - baseline) / baseline * 100)
    
    @staticmethod
    async def _create_baseline_prediction(
        request: YieldPredictionRequest,
        ml_error: Dict[str, Any]
    ) -> YieldPredictionResponse:
        """Create fallback prediction using only baseline"""
        logger.warning("⚠️  Creating baseline-only prediction (fallback)")
        # Return a basic response using regional baseline
        # This would be implemented based on fallback logic
        raise Exception("Baseline fallback not yet implemented")


# Create service instance
yield_service = YieldService()
