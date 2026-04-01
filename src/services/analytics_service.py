from uuid import UUID
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from src.core.supabase_client import admin_supabase
from src.schemas.analytics import (
    QualityAnalyticsResponse,
    FruitQualityStats,
    DiseaseRiskAnalyticsResponse,
    DiseaseTypeStats,
    YieldAnalyticsResponse,
    FruitYieldStats,
    ExportReadinessResponse,
    FruitExportReadiness,
    ExportQualityMetrics,
    AnalyticsSummaryResponse,
    QualityAnalyticsTrendResponse,
    QualityTrendResponse,
    DiseaseRiskTrendResponse,
    DiseaseTrendResponse,
    YieldComparisonResponse
)
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ================= Helper Functions =================

def get_date_range(start_date: Optional[date], end_date: Optional[date]) -> Dict[str, str]:
    """
    Get date range for analytics. Defaults to last 30 days if not specified.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat()
    }

def calculate_risk_level(infection_rate: float) -> str:
    """Calculate risk level based on infection rate"""
    if infection_rate >= 30:
        return "critical"
    elif infection_rate >= 20:
        return "high"
    elif infection_rate >= 10:
        return "medium"
    else:
        return "low"

def get_disease_recommendations(risk_level: str, disease_stats: List[DiseaseTypeStats]) -> List[str]:
    """Generate recommendations based on disease risk"""
    recommendations = []
    
    if risk_level == "critical":
        recommendations.append("🚨 URGENT: Immediate intervention required to prevent disease spread")
        recommendations.append("Consider quarantine measures for affected areas")
        recommendations.append("Consult with agricultural extension services")
    elif risk_level == "high":
        recommendations.append("⚠️ HIGH RISK: Implement intensive disease management protocols")
        recommendations.append("Increase monitoring frequency")
    elif risk_level == "medium":
        recommendations.append("⚡ MODERATE RISK: Maintain regular monitoring and preventive measures")
    else:
        recommendations.append("✅ LOW RISK: Continue current disease management practices")
    
    # Add disease-specific recommendations
    for disease in disease_stats:
        if disease.disease_type == "anthracnose":
            recommendations.append("For Anthracnose: Apply appropriate fungicides and improve air circulation")
        elif disease.disease_type == "citrus_canker":
            recommendations.append("For Citrus Canker: Remove infected plant material and apply copper-based treatments")
    
    return recommendations

def calculate_export_compliance(detection_data: Dict[str, Any]) -> ExportQualityMetrics:
    """Calculate export compliance metrics from detection data"""
    classification = detection_data.get("classification", {})
    
    # Ripeness compliance (ripe fruits are export-ready)
    ripeness = classification.get("ripeness_level", "unknown")
    ripeness_compliant = ripeness == "ripe"
    
    # Size compliance (medium and large are export-ready)
    size = classification.get("size", "unknown")
    size_compliant = size in ["medium", "large"]
    
    # Defect compliance (no defects or minimal defects)
    defects = classification.get("defects", [])
    defect_compliant = len(defects) == 0
    
    # Disease-free (no disease detected)
    disease_free = not detection_data.get("has_disease", False)
    
    # Calculate overall compliance
    compliance_factors = [ripeness_compliant, size_compliant, defect_compliant, disease_free]
    overall = (sum(compliance_factors) / len(compliance_factors)) * 100
    
    return ExportQualityMetrics(
        ripeness_compliance=100.0 if ripeness_compliant else 0.0,
        size_compliance=100.0 if size_compliant else 0.0,
        defect_compliance=100.0 if defect_compliant else 0.0,
        disease_free_rate=100.0 if disease_free else 0.0,
        overall_compliance=round(overall, 2)
    )

# ================= Quality Analytics =================

async def get_quality_analytics(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    orchard_id: Optional[UUID] = None,
) -> QualityAnalyticsResponse:
    """
    Generate fruit quality analytics for a user within a date range.
    Analyzes detection results with classification data.
    """
    try:
        logger.info(f"Generating quality analytics for user {user_id}")
        date_range = get_date_range(start_date, end_date)
        logger.info(f"Date range: {date_range}")

        # Fetch detection results from detection_results table
        query = admin_supabase.table("detection_results") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .gte("created_at", f"{date_range['start']}T00:00:00") \
            .lte("created_at", f"{date_range['end']}T23:59:59")
        if orchard_id:
            query = query.eq("orchard_id", str(orchard_id))
        
        logger.info(f"Executing query for detection results")
        result = query.execute()
        detections = result.data if result.data else []
        logger.info(f"Found {len(detections)} detections")
        
        if not detections:
            # Return empty analytics
            return QualityAnalyticsResponse(
                user_id=user_id,
                date_range=date_range,
                total_detections=0,
                total_images=0,
                fruit_statistics=[],
                overall_quality_score=0.0,
                generated_at=datetime.utcnow()
            )
        
        # Fetch classification results for all detections
        detection_ids = [d['detection_id'] for d in detections]
        classification_query = admin_supabase.table("classification_results") \
            .select("*") \
            .in_("detection_id", detection_ids)
        
        classification_result = classification_query.execute()
        classifications = {c['detection_id']: c for c in (classification_result.data or [])}
        logger.info(f"Found {len(classifications)} classification results")
        
        # Group detections by fruit type
        fruit_groups = defaultdict(list)
        image_ids = set()
        
        for detection in detections:
            image_ids.add(detection['image_id'])
            fruit_type = detection.get('fruit_type', 'unknown')
            
            # Merge classification data if available
            detection_with_classification = detection.copy()
            classification_data = classifications.get(detection['detection_id'])
            if classification_data:
                detection_with_classification['classification'] = classification_data
            
            fruit_groups[fruit_type].append(detection_with_classification)
        
        # Calculate statistics for each fruit type
        fruit_stats = []
        total_quality_score = 0.0
        quality_scores = []
        
        for fruit_type, fruit_detections in fruit_groups.items():
            # Ripeness distribution
            ripeness_dist = defaultdict(int)
            defects_list = []
            quality_scores_fruit = []
            confidences = []
            
            for det in fruit_detections:
                confidences.append(det.get('confidence', 0.0))
                
                # Get classification data
                classification = det.get('classification', {})
                
                # Ripeness distribution
                ripeness = classification.get('ripeness_level', 'unknown')
                ripeness_dist[ripeness] += 1
                
                # Calculate quality score from classification data
                # Quality score is based on ripeness and confidence
                ripeness_conf = classification.get('confidence_score', 0)
                if ripeness == 'ripe':
                    quality_score = 90 + (ripeness_conf * 10)  # 90-100
                elif ripeness == 'unripe':
                    quality_score = 60 + (ripeness_conf * 20)  # 60-80
                elif ripeness == 'overripe':
                    quality_score = 40 + (ripeness_conf * 20)  # 40-60
                else:
                    quality_score = 50
                
                quality_scores_fruit.append(quality_score)
            
            # Calculate averages
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            avg_quality = sum(quality_scores_fruit) / len(quality_scores_fruit) if quality_scores_fruit else 0.0
            
            # Defect rate
            total_fruits = len(fruit_detections)
            fruits_with_defects = len([d for d in fruit_detections if d.get("classification", {}).get("defects")])
            defect_rate = (fruits_with_defects / total_fruits * 100) if total_fruits > 0 else 0.0
            
            # Common defects
            defect_counts = defaultdict(int)
            for defect in defects_list:
                defect_counts[defect] += 1
            common_defects = sorted(defect_counts.keys(), key=lambda x: defect_counts[x], reverse=True)[:3]
            
            fruit_stats.append(FruitQualityStats(
                fruit_type=fruit_type,
                total_count=len(fruit_detections),
                average_confidence=round(avg_confidence, 3),
                ripeness_distribution=dict(ripeness_dist),
                quality_score_avg=round(avg_quality, 2) if avg_quality > 0 else None,
                defect_rate=round(defect_rate, 2),
                common_defects=common_defects if common_defects else None
            ))
            
            if avg_quality > 0:
                quality_scores.append(avg_quality)
        
        # Overall quality score
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Best and worst performing fruits
        fruit_stats_sorted = sorted(fruit_stats, key=lambda x: x.quality_score_avg or 0, reverse=True)
        best_fruit = fruit_stats_sorted[0].fruit_type if fruit_stats_sorted else None
        worst_fruit = fruit_stats_sorted[-1].fruit_type if len(fruit_stats_sorted) > 1 else None
        
        return QualityAnalyticsResponse(
            user_id=user_id,
            date_range=date_range,
            total_detections=len(detections),
            total_images=len(image_ids),
            fruit_statistics=fruit_stats,
            overall_quality_score=round(overall_quality, 2),
            best_performing_fruit=best_fruit,
            worst_performing_fruit=worst_fruit,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating quality analytics: {str(e)}")
        raise Exception(f"Failed to generate quality analytics: {str(e)}")

async def get_quality_trends(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    orchard_id: Optional[UUID] = None,
) -> QualityAnalyticsTrendResponse:
    """
    Generate quality trend analytics over time.
    Shows daily quality metrics.
    """
    try:
        date_range = get_date_range(start_date, end_date)

        # Fetch detections from detection_results
        query = admin_supabase.table("detection_results") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .gte("created_at", f"{date_range['start']}T00:00:00") \
            .lte("created_at", f"{date_range['end']}T23:59:59")
        if orchard_id:
            query = query.eq("orchard_id", str(orchard_id))

        result = query.execute()
        detections = result.data if result.data else []
        
        # Fetch classification results
        if detections:
            detection_ids = [d['detection_id'] for d in detections]
            classification_query = admin_supabase.table("classification_results") \
                .select("*") \
                .in_("detection_id", detection_ids)
            
            classification_result = classification_query.execute()
            classifications = {c['detection_id']: c for c in (classification_result.data or [])}
        else:
            classifications = {}
        
        # Group by date
        daily_data = defaultdict(lambda: {"detections": [], "quality_scores": [], "defects": 0})
        
        for det in detections:
            det_date = datetime.fromisoformat(det["created_at"].replace('Z', '+00:00')).date()
            daily_data[det_date]["detections"].append(det)
            
            # Get classification data
            classification = classifications.get(det['detection_id'], {})
            
            # Calculate quality score from ripeness
            ripeness = classification.get("ripeness_level", "unknown")
            ripeness_conf = classification.get("confidence_score", 0)
            if ripeness == 'ripe':
                quality_score = 90 + (ripeness_conf * 10)
            elif ripeness == 'unripe':
                quality_score = 60 + (ripeness_conf * 20)
            elif ripeness == 'overripe':
                quality_score = 40 + (ripeness_conf * 20)
            else:
                quality_score = 50
            
            daily_data[det_date]["quality_scores"].append(quality_score)
        
        # Calculate trends
        trends = []
        for day in sorted(daily_data.keys()):
            data = daily_data[day]
            total = len(data["detections"])
            avg_quality = sum(data["quality_scores"]) / len(data["quality_scores"]) if data["quality_scores"] else 0.0
            defect_rate = (data["defects"] / total * 100) if total > 0 else 0.0
            
            trends.append(QualityTrendResponse(
                date=day,
                total_detections=total,
                average_quality_score=round(avg_quality, 2),
                defect_rate=round(defect_rate, 2)
            ))
        
        return QualityAnalyticsTrendResponse(
            user_id=user_id,
            date_range=date_range,
            trends=trends,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating quality trends: {str(e)}")
        raise Exception(f"Failed to generate quality trends: {str(e)}")

# ================= Disease Risk Analytics =================

async def get_disease_risk_analytics(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    orchard_id: Optional[UUID] = None,
) -> DiseaseRiskAnalyticsResponse:
    """
    Generate disease risk analytics for a user within a date range.
    Analyzes disease detection results and provides risk assessment.
    """
    try:
        date_range = get_date_range(start_date, end_date)

        # Fetch disease detections from disease_detections table
        query = admin_supabase.table("disease_detections") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .gte("created_at", f"{date_range['start']}T00:00:00") \
            .lte("created_at", f"{date_range['end']}T23:59:59")
        if orchard_id:
            query = query.eq("orchard_id", str(orchard_id))
        
        result = query.execute()
        disease_detections = result.data if result.data else []
        
        logger.info(f"Found {len(disease_detections)} disease detection records")
        
        # Fetch detection results to get fruit types
        if disease_detections:
            detection_ids = list(set([d['detection_id'] for d in disease_detections]))
            det_query = admin_supabase.table("detection_results") \
                .select("detection_id, fruit_type") \
                .in_("detection_id", detection_ids)
            
            det_result = det_query.execute()
            fruit_types_map = {d['detection_id']: d['fruit_type'] for d in (det_result.data or [])}
            logger.info(f"Found fruit types for {len(fruit_types_map)} detections")
        else:
            fruit_types_map = {}
        
        if not disease_detections:
            return DiseaseRiskAnalyticsResponse(
                user_id=user_id,
                date_range=date_range,
                total_detections=0,
                diseased_count=0,
                healthy_count=0,
                infection_rate=0.0,
                disease_statistics=[],
                overall_risk_level="low",
                recommendations=["No disease detections in this period. Continue preventive monitoring."],
                generated_at=datetime.utcnow()
            )
        
        # Count diseased vs healthy
        diseased_count = sum(1 for d in disease_detections if d.get("is_diseased", False))
        healthy_count = len(disease_detections) - diseased_count
        infection_rate = (diseased_count / len(disease_detections) * 100) if disease_detections else 0.0
        
        # Group by disease type
        disease_groups = defaultdict(list)
        for detection in disease_detections:
            if detection.get("is_diseased", False):
                disease_type = detection.get("disease_type", "unknown")
                disease_groups[disease_type].append(detection)
        
        # Calculate statistics for each disease type
        disease_stats = []
        for disease_type, disease_detections_type in disease_groups.items():
            # Severity distribution
            severity_dist = defaultdict(int)
            confidences = []
            affected_fruits = set()
            
            for det in disease_detections_type:
                severity = det.get("severity_level", "unknown")
                if severity:
                    severity_dist[severity] += 1
                
                confidence = det.get("disease_confidence", 0.0)
                confidences.append(confidence)
                
                # Get fruit type from detection_results mapping
                fruit_type = fruit_types_map.get(det['detection_id'], 'unknown')
                affected_fruits.add(fruit_type)
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Calculate risk level for this disease
            disease_infection_rate = (len(disease_detections_type) / diseased_count * 100) if diseased_count > 0 else 0.0
            disease_risk = calculate_risk_level(disease_infection_rate)
            
            disease_stats.append(DiseaseTypeStats(
                disease_type=disease_type,
                total_cases=len(disease_detections_type),
                severity_distribution=dict(severity_dist),
                average_confidence=round(avg_confidence, 3),
                affected_fruit_types=list(affected_fruits),
                risk_level=disease_risk
            ))
        
        # Overall risk level
        overall_risk = calculate_risk_level(infection_rate)
        
        # Generate recommendations
        recommendations = get_disease_recommendations(overall_risk, disease_stats)
        
        return DiseaseRiskAnalyticsResponse(
            user_id=user_id,
            date_range=date_range,
            total_detections=len(disease_detections),
            diseased_count=diseased_count,
            healthy_count=healthy_count,
            infection_rate=round(infection_rate, 2),
            disease_statistics=disease_stats,
            overall_risk_level=overall_risk,
            recommendations=recommendations,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating disease risk analytics: {str(e)}")
        raise Exception(f"Failed to generate disease risk analytics: {str(e)}")

async def get_disease_risk_trends(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    orchard_id: Optional[UUID] = None,
) -> DiseaseRiskTrendResponse:
    """
    Generate disease risk trend analytics over time.
    Shows daily disease detection metrics.
    """
    try:
        date_range = get_date_range(start_date, end_date)

        # Fetch disease detections
        query = admin_supabase.table("disease_detections") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .gte("created_at", f"{date_range['start']}T00:00:00") \
            .lte("created_at", f"{date_range['end']}T23:59:59")
        if orchard_id:
            query = query.eq("orchard_id", str(orchard_id))
        
        result = query.execute()
        disease_detections = result.data if result.data else []
        
        # Group by date
        daily_data = defaultdict(lambda: {"total": 0, "diseased": 0})
        
        for det in disease_detections:
            det_date = datetime.fromisoformat(det["created_at"].replace('Z', '+00:00')).date()
            daily_data[det_date]["total"] += 1
            if det.get("is_diseased", False):
                daily_data[det_date]["diseased"] += 1
        
        # Calculate trends
        trends = []
        for day in sorted(daily_data.keys()):
            data = daily_data[day]
            infection_rate = (data["diseased"] / data["total"] * 100) if data["total"] > 0 else 0.0
            
            trends.append(DiseaseTrendResponse(
                date=day,
                total_detections=data["total"],
                diseased_count=data["diseased"],
                infection_rate=round(infection_rate, 2)
            ))
        
        return DiseaseRiskTrendResponse(
            user_id=user_id,
            date_range=date_range,
            trends=trends,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating disease risk trends: {str(e)}")
        raise Exception(f"Failed to generate disease risk trends: {str(e)}")

# ================= Yield Analytics =================

async def get_yield_analytics(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    orchard_id: Optional[UUID] = None,
) -> YieldAnalyticsResponse:
    """
    Generate yield analytics for a user within a date range.
    Calculates total yield and marketable yield based on quality criteria.
    """
    try:
        date_range = get_date_range(start_date, end_date)

        # Fetch detection results from detection_results table
        query = admin_supabase.table("detection_results") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .gte("created_at", f"{date_range['start']}T00:00:00") \
            .lte("created_at", f"{date_range['end']}T23:59:59")
        if orchard_id:
            query = query.eq("orchard_id", str(orchard_id))
        
        result = query.execute()
        detections = result.data if result.data else []
        
        logger.info(f"Found {len(detections)} detections for yield analytics")
        
        if not detections:
            return YieldAnalyticsResponse(
                user_id=user_id,
                date_range=date_range,
                total_fruit_count=0,
                total_marketable_count=0,
                overall_marketable_rate=0.0,
                fruit_yields=[],
                generated_at=datetime.utcnow()
            )
        
        # Fetch classification results for all detections
        detection_ids = [d['detection_id'] for d in detections]
        classification_query = admin_supabase.table("classification_results") \
            .select("*") \
            .in_("detection_id", detection_ids)
        
        classification_result = classification_query.execute()
        classifications = {c['detection_id']: c for c in (classification_result.data or [])}
        
        # Merge classification data with detections
        for det in detections:
            det['classification'] = classifications.get(det['detection_id'], {})
        
        # Group by fruit type
        fruit_groups = defaultdict(list)
        for detection in detections:
            fruit_type = detection.get("fruit_type", "unknown")
            fruit_groups[fruit_type].append(detection)
        
        # Calculate yield for each fruit type
        fruit_yields = []
        total_marketable = 0
        estimated_total_weight = 0.0
        
        # Weight estimates per fruit (kg) - rough estimates
        weight_estimates = {
            "apple": 0.2,
            "orange": 0.15,
            "mango": 0.3,
            "banana": 0.15,
            "guava": 0.1,
            "grapefruit": 0.3
        }
        
        for fruit_type, fruit_detections in fruit_groups.items():
            marketable_count = 0
            sizes = []
            
            for det in fruit_detections:
                classification = det.get("classification", {})
                
                # Marketable criteria: ripe or unripe, no severe defects, good quality
                ripeness = classification.get("ripeness_level", "unknown")
                defects = classification.get("defects", [])
                quality_score = classification.get("quality_score", 0)
                
                is_marketable = (
                    ripeness in ["ripe", "unripe"] and
                    len(defects) <= 1 and  # Max 1 minor defect
                    quality_score >= 60  # Quality threshold
                )
                
                if is_marketable:
                    marketable_count += 1
                
                size = classification.get("size")
                if size:
                    sizes.append(size)
            
            total = len(fruit_detections)
            marketable_pct = (marketable_count / total * 100) if total > 0 else 0.0
            
            # Estimate weight
            weight_per_fruit = weight_estimates.get(fruit_type.lower(), 0.2)
            estimated_weight = total * weight_per_fruit
            estimated_total_weight += estimated_weight
            
            # Average size
            avg_size = max(set(sizes), key=sizes.count) if sizes else None
            
            fruit_yields.append(FruitYieldStats(
                fruit_type=fruit_type,
                total_count=total,
                marketable_count=marketable_count,
                marketable_percentage=round(marketable_pct, 2),
                average_size=avg_size,
                estimated_weight_kg=round(estimated_weight, 2)
            ))
            
            total_marketable += marketable_count
        
        # Overall marketable rate
        total_fruits = len(detections)
        overall_marketable_rate = (total_marketable / total_fruits * 100) if total_fruits > 0 else 0.0
        
        # Best yielding fruit
        fruit_yields_sorted = sorted(fruit_yields, key=lambda x: x.marketable_percentage, reverse=True)
        best_yielding = fruit_yields_sorted[0].fruit_type if fruit_yields_sorted else None
        
        return YieldAnalyticsResponse(
            user_id=user_id,
            date_range=date_range,
            total_fruit_count=total_fruits,
            total_marketable_count=total_marketable,
            overall_marketable_rate=round(overall_marketable_rate, 2),
            fruit_yields=fruit_yields,
            estimated_total_weight_kg=round(estimated_total_weight, 2) if estimated_total_weight > 0 else None,
            best_yielding_fruit=best_yielding,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating yield analytics: {str(e)}")
        raise Exception(f"Failed to generate yield analytics: {str(e)}")

async def get_yield_comparison(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    orchard_id: Optional[UUID] = None,
) -> YieldComparisonResponse:
    """
    Compare yield between current period and previous period.
    """
    try:
        # Get current period analytics
        current = await get_yield_analytics(user_id, start_date, end_date, orchard_id=orchard_id)

        # Calculate previous period dates
        if start_date and end_date:
            period_days = (end_date - start_date).days
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days)
        else:
            # Default 30 days
            prev_end = date.today() - timedelta(days=31)
            prev_start = prev_end - timedelta(days=30)

        # Get previous period analytics
        try:
            previous = await get_yield_analytics(user_id, prev_start, prev_end, orchard_id=orchard_id)
        except:
            previous = None
        
        # Calculate growth rate
        growth_rate = None
        if previous and previous.total_fruit_count > 0:
            growth_rate = ((current.total_fruit_count - previous.total_fruit_count) / 
                          previous.total_fruit_count * 100)
            growth_rate = round(growth_rate, 2)
        
        return YieldComparisonResponse(
            current_period=current,
            previous_period=previous,
            growth_rate=growth_rate,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating yield comparison: {str(e)}")
        raise Exception(f"Failed to generate yield comparison: {str(e)}")

# ================= Export Readiness =================

async def get_export_readiness(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    target_market: Optional[str] = None,
    orchard_id: Optional[UUID] = None,
) -> ExportReadinessResponse:
    """
    Generate export readiness report for a user within a date range.
    Assesses fruits against export quality standards.
    """
    try:
        date_range = get_date_range(start_date, end_date)

        logger.info(f"Generating export readiness report for user {user_id}")
        logger.info(f"Date range: {date_range}, Target market: {target_market}")

        # Fetch detection results from detection_results table
        detections_query = admin_supabase.table("detection_results") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .gte("created_at", f"{date_range['start']}T00:00:00") \
            .lte("created_at", f"{date_range['end']}T23:59:59")
        if orchard_id:
            detections_query = detections_query.eq("orchard_id", str(orchard_id))
        
        detections_result = detections_query.execute()
        detections = detections_result.data if detections_result.data else []
        
        logger.info(f"Found {len(detections)} detection results")
        
        if not detections:
            return ExportReadinessResponse(
                user_id=user_id,
                report_date=datetime.utcnow(),
                date_range=date_range,
                total_fruit_analyzed=0,
                total_export_ready=0,
                overall_readiness_score=0.0,
                fruit_readiness=[],
                market_recommendations=["No data available for the selected period. Please upload and process images first."],
                compliance_summary={
                    "export_ready_rate": 0.0,
                    "average_compliance_score": 0.0,
                    "target_market": target_market or "General"
                },
                generated_at=datetime.utcnow()
            )
        
        # Fetch classification results for all detections
        detection_ids = [d['detection_id'] for d in detections]
        classification_query = admin_supabase.table("classification_results") \
            .select("*") \
            .in_("detection_id", detection_ids)
        
        classification_result = classification_query.execute()
        classifications = {c['detection_id']: c for c in (classification_result.data or [])}
        logger.info(f"Found {len(classifications)} classification results")
        
        # Fetch disease detections
        disease_query = admin_supabase.table("disease_detections") \
            .select("detection_id, is_diseased, disease_type") \
            .in_("detection_id", detection_ids)
        
        disease_result = disease_query.execute()
        disease_data = {d["detection_id"]: d for d in (disease_result.data or [])}
        logger.info(f"Found {len(disease_data)} disease detection records")
        
        logger.info(f"Found {len(disease_data)} disease detection records")
        
        # Merge classification and disease data with detections
        for det in detections:
            det_id = det['detection_id']
            det['classification'] = classifications.get(det_id, {})
            disease_info = disease_data.get(det_id, {})
            det['has_disease'] = disease_info.get('is_diseased', False)
            det['disease_type'] = disease_info.get('disease_type')
        
        # Group by fruit type
        fruit_groups = defaultdict(list)
        for detection in detections:
            fruit_type = detection.get("fruit_type", "unknown")
            fruit_groups[fruit_type].append(detection)
        
        # Calculate export readiness for each fruit type
        fruit_readiness_list = []
        total_export_ready = 0
        all_compliance_metrics = []
        
        for fruit_type, fruit_detections in fruit_groups.items():
            export_ready_count = 0
            rejection_reasons = defaultdict(int)
            compliance_metrics_list = []
            
            for det in fruit_detections:
                # Calculate compliance for this fruit
                compliance = calculate_export_compliance(det)
                compliance_metrics_list.append(compliance)
                
                # Export ready if overall compliance >= 75%
                if compliance.overall_compliance >= 75:
                    export_ready_count += 1
                else:
                    # Track rejection reasons
                    if compliance.ripeness_compliance < 100:
                        rejection_reasons["Poor ripeness"] += 1
                    if compliance.size_compliance < 100:
                        rejection_reasons["Size not meeting standards"] += 1
                    if compliance.defect_compliance < 100:
                        rejection_reasons["Surface defects"] += 1
                    if compliance.disease_free_rate < 100:
                        rejection_reasons["Disease detected"] += 1
            
            total = len(fruit_detections)
            export_ready_pct = (export_ready_count / total * 100) if total > 0 else 0.0
            
            # Average compliance metrics
            avg_compliance = ExportQualityMetrics(
                ripeness_compliance=round(sum(c.ripeness_compliance for c in compliance_metrics_list) / len(compliance_metrics_list), 2),
                size_compliance=round(sum(c.size_compliance for c in compliance_metrics_list) / len(compliance_metrics_list), 2),
                defect_compliance=round(sum(c.defect_compliance for c in compliance_metrics_list) / len(compliance_metrics_list), 2),
                disease_free_rate=round(sum(c.disease_free_rate for c in compliance_metrics_list) / len(compliance_metrics_list), 2),
                overall_compliance=round(sum(c.overall_compliance for c in compliance_metrics_list) / len(compliance_metrics_list), 2)
            )
            
            all_compliance_metrics.append(avg_compliance)
            
            # Generate recommendations
            recommendations = []
            if avg_compliance.ripeness_compliance < 80:
                recommendations.append("Improve harvest timing for optimal ripeness")
            if avg_compliance.size_compliance < 80:
                recommendations.append("Focus on growing larger fruits through better cultivation")
            if avg_compliance.defect_compliance < 80:
                recommendations.append("Enhance fruit handling and pest management")
            if avg_compliance.disease_free_rate < 90:
                recommendations.append("Strengthen disease prevention and treatment protocols")
            
            if not recommendations:
                recommendations.append("Maintain current quality standards")
            
            fruit_readiness_list.append(FruitExportReadiness(
                fruit_type=fruit_type,
                total_count=total,
                export_ready_count=export_ready_count,
                export_ready_percentage=round(export_ready_pct, 2),
                quality_metrics=avg_compliance,
                rejection_reasons=dict(rejection_reasons),
                recommended_actions=recommendations
            ))
            
            total_export_ready += export_ready_count
        
        # Overall readiness score
        total_fruits = len(detections)
        overall_readiness = (total_export_ready / total_fruits * 100) if total_fruits > 0 else 0.0
        
        # Market recommendations based on quality
        market_recs = []
        if overall_readiness >= 90:
            market_recs.append("✅ Premium export markets (EU, US, Japan) - Excellent quality")
            market_recs.append("Suitable for high-value organic certifications")
        elif overall_readiness >= 75:
            market_recs.append("✅ Standard export markets (Asia, Middle East) - Good quality")
            market_recs.append("Consider quality improvements for premium markets")
        elif overall_readiness >= 60:
            market_recs.append("⚠️ Domestic markets recommended - Quality needs improvement")
            market_recs.append("Focus on quality enhancement before targeting export")
        else:
            market_recs.append("🚨 Processing/juice markets - Fresh export not recommended")
            market_recs.append("Significant quality improvements required for fresh export")
        
        # Compliance summary
        avg_overall_compliance = sum(c.overall_compliance for c in all_compliance_metrics) / len(all_compliance_metrics) if all_compliance_metrics else 0
        compliance_summary = {
            "export_ready_rate": round(overall_readiness, 2),
            "average_compliance_score": round(avg_overall_compliance, 2),
            "total_analyzed": total_fruits,
            "total_export_ready": total_export_ready,
            "rejection_rate": round(100 - overall_readiness, 2),
            "target_market": target_market or "General"
        }
        
        return ExportReadinessResponse(
            user_id=user_id,
            report_date=datetime.utcnow(),
            date_range=date_range,
            total_fruit_analyzed=total_fruits,
            total_export_ready=total_export_ready,
            overall_readiness_score=round(overall_readiness, 2),
            fruit_readiness=fruit_readiness_list,
            market_recommendations=market_recs,
            compliance_summary=compliance_summary,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating export readiness report: {str(e)}")
        raise Exception(f"Failed to generate export readiness report: {str(e)}")

# ================= Summary Analytics =================

async def get_analytics_summary(
    user_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    orchard_id: Optional[UUID] = None,
) -> AnalyticsSummaryResponse:
    """
    Generate comprehensive analytics summary combining all metrics.
    """
    try:
        date_range = get_date_range(start_date, end_date)

        # Get all analytics in parallel would be ideal, but for simplicity doing sequentially
        quality = await get_quality_analytics(user_id, start_date, end_date, orchard_id=orchard_id)
        disease = await get_disease_risk_analytics(user_id, start_date, end_date, orchard_id=orchard_id)
        yield_data = await get_yield_analytics(user_id, start_date, end_date, orchard_id=orchard_id)
        export = await get_export_readiness(user_id, start_date, end_date, orchard_id=orchard_id)
        
        # Identify areas for improvement
        areas_for_improvement = []
        if quality.overall_quality_score < 70:
            areas_for_improvement.append("🔴 Fruit quality needs improvement - focus on cultivation practices")
        if disease.infection_rate > 15:
            areas_for_improvement.append("🔴 High disease rate - enhance disease management protocols")
        if yield_data.overall_marketable_rate < 70:
            areas_for_improvement.append("🔴 Low marketable yield - improve quality control and handling")
        if export.overall_readiness_score < 75:
            areas_for_improvement.append("🔴 Export readiness below standard - address compliance gaps")
        
        if not areas_for_improvement:
            areas_for_improvement.append("✅ All metrics performing well - maintain current practices")
        
        return AnalyticsSummaryResponse(
            user_id=user_id,
            date_range=date_range,
            quality_score=quality.overall_quality_score,
            disease_risk_level=disease.overall_risk_level,
            infection_rate=disease.infection_rate,
            total_yield=yield_data.total_fruit_count,
            marketable_yield=yield_data.total_marketable_count,
            export_readiness_score=export.overall_readiness_score,
            top_performing_fruit=quality.best_performing_fruit,
            areas_for_improvement=areas_for_improvement,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error generating analytics summary: {str(e)}")
        raise Exception(f"Failed to generate analytics summary: {str(e)}")
