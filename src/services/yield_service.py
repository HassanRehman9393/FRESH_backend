"""
Yield Prediction Service

Orchestrates yield predictions by calling ML API and storing results.
Handles database interactions and ML API communication.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime
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
    FruitType,
    TrendDirection,
    ModelUsed,
)

logger = logging.getLogger(__name__)


class YieldService:
    """Service for yield prediction operations"""
    
    ML_API_TIMEOUT = settings.ml_api_timeout
    ML_API_URL = settings.ml_api_url
    
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
                "detection_aggregates": request.detection_aggregates.model_dump(),
                "weather_data": request.weather_data.model_dump(),
                "orchard_metadata": request.orchard_metadata.model_dump(by_alias=False),
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
            response = admin_supabase.table('yield_predictions').insert(
                prediction.model_dump()
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
        limit: int = 20,
        offset: int = 0
    ) -> List[YieldPredictionHistoryResponse]:
        """Get user's yield prediction history"""
        try:
            query = admin_supabase.table('yield_predictions').select(
                'id, prediction_date, fruit_type, predicted_yield_kg, confidence, '
                'trend_direction, orchard_area_hectares'
            ).eq('user_id', str(user_id))
            
            if fruit_type:
                query = query.eq('fruit_type', fruit_type)
            
            response = query.order('prediction_date', desc=True).range(
                offset, offset + limit - 1
            ).execute()
            
            return [YieldPredictionHistoryResponse(**item) for item in response.data]
            
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
            record_data = harvest_record.model_dump()
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
    async def get_user_yield_stats(user_id: UUID) -> Optional[UserYieldStats]:
        """Get comprehensive yield statistics for user"""
        try:
            # Get predictions
            predictions = admin_supabase.table('yield_predictions').select(
                '*'
            ).eq('user_id', str(user_id)).execute()
            
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
                
                return UserYieldStats(
                    fruit_type=fruit_type,
                    predictions_count=fruit_stats['count'],
                    average_predicted_yield_kg=fruit_stats['total_yield'] / fruit_stats['count'],
                    average_confidence=fruit_stats['total_confidence'] / fruit_stats['count'],
                    recent_predictions=[
                        YieldPredictionHistoryResponse(**p) for p in fruit_stats['records'][:5]
                    ],
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
