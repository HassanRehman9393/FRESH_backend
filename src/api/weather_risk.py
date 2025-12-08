"""
Weather Disease Risk API Endpoints
Disease risk analysis based on weather conditions
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from src.schemas.weather import (
    DiseaseRiskResponse,
    RiskLevel,
    DiseaseType,
    FruitType
)
from src.core.supabase_client import supabase
from src.api.deps import get_current_user
from src.schemas.user import UserResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["disease-risk"])


@router.get("/orchard/{orchard_id}", response_model=List[DiseaseRiskResponse])
async def get_orchard_risk_analysis(
    orchard_id: str,
    risk_level: Optional[RiskLevel] = Query(None, description="Filter by risk level"),
    fruit_type: Optional[FruitType] = Query(None, description="Filter by fruit type"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get latest disease risk analysis for a specific orchard
    
    - **orchard_id**: UUID of the orchard
    - **risk_level**: Filter by risk level (low, medium, high, critical)
    - **fruit_type**: Filter by fruit type
    
    Returns current disease risk assessments based on weather conditions
    """
    try:
        # Verify orchard ownership
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        # Get latest risk analysis (within last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        query = supabase.table("weather_disease_risk")\
            .select("*")\
            .eq("orchard_id", orchard_id)\
            .gte("calculated_at", cutoff_time.isoformat())
        
        if risk_level:
            query = query.eq("risk_level", risk_level.value)
        if fruit_type:
            query = query.eq("fruit_type", fruit_type.value)
        
        response = query\
            .order("calculated_at", desc=True)\
            .execute()
        
        return response.data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching risk analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch risk analysis"
        )


@router.get("/orchard/{orchard_id}/high-risk", response_model=List[DiseaseRiskResponse])
async def get_high_risk_diseases(
    orchard_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get high and critical risk diseases for an orchard
    
    - **orchard_id**: UUID of the orchard
    
    Returns only diseases with high or critical risk levels
    """
    try:
        # Verify orchard ownership
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        # Get latest high/critical risks (within last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        response = supabase.table("weather_disease_risk")\
            .select("*")\
            .eq("orchard_id", orchard_id)\
            .gte("calculated_at", cutoff_time.isoformat())\
            .in_("risk_level", ["high", "critical"])\
            .order("risk_score", desc=True)\
            .execute()
        
        return response.data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching high-risk diseases: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch high-risk diseases"
        )


@router.get("/disease/{disease_type}", response_model=List[DiseaseRiskResponse])
async def get_disease_risk_across_orchards(
    disease_type: DiseaseType,
    risk_level: Optional[RiskLevel] = Query(None, description="Filter by risk level"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get risk analysis for a specific disease across all user's orchards
    
    - **disease_type**: Type of disease (anthracnose, citrus_canker, etc.)
    - **risk_level**: Filter by risk level
    
    Returns risk assessments for the specified disease across all orchards
    """
    try:
        # Get user's orchards
        orchards_response = supabase.table("orchards")\
            .select("id")\
            .eq("user_id", current_user["user_id"])\
            .eq("is_active", True)\
            .execute()
        
        if not orchards_response.data:
            return []
        
        orchard_ids = [o["id"] for o in orchards_response.data]
        
        # Get latest risk analysis (within last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        query = supabase.table("weather_disease_risk")\
            .select("*")\
            .eq("disease_type", disease_type.value)\
            .in_("orchard_id", orchard_ids)\
            .gte("calculated_at", cutoff_time.isoformat())
        
        if risk_level:
            query = query.eq("risk_level", risk_level.value)
        
        response = query\
            .order("risk_score", desc=True)\
            .execute()
        
        return response.data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching disease risk: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch disease risk"
        )


@router.get("/history/{orchard_id}", response_model=List[DiseaseRiskResponse])
async def get_risk_history(
    orchard_id: str,
    disease_type: Optional[DiseaseType] = Query(None, description="Filter by disease type"),
    start_date: Optional[datetime] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (default: now)"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get historical disease risk analysis for an orchard
    
    - **orchard_id**: UUID of the orchard
    - **disease_type**: Filter by specific disease
    - **start_date**: Start date for history (default: 30 days ago)
    - **end_date**: End date for history (default: now)
    
    Returns historical risk assessments for trend analysis
    """
    try:
        # Verify orchard ownership
        orchard_response = supabase.table("orchards")\
            .select("id")\
            .eq("id", orchard_id)\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchard_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orchard not found"
            )
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        query = supabase.table("weather_disease_risk")\
            .select("*")\
            .eq("orchard_id", orchard_id)\
            .gte("calculated_at", start_date.isoformat())\
            .lte("calculated_at", end_date.isoformat())
        
        if disease_type:
            query = query.eq("disease_type", disease_type.value)
        
        response = query\
            .order("calculated_at", desc=True)\
            .execute()
        
        return response.data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching risk history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch risk history"
        )


@router.get("/summary")
async def get_risk_summary(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get risk summary across all user's orchards
    
    Returns aggregated statistics:
    - Total orchards analyzed
    - Count of critical/high/medium/low risks
    - Most at-risk orchards
    - Most prevalent diseases
    """
    try:
        
        # Get user's active orchards
        orchards_response = supabase.table("orchards")\
            .select("id, name")\
            .eq("user_id", current_user["user_id"])\
            .eq("is_active", True)\
            .execute()
        
        if not orchards_response.data:
            return {
                "total_orchards": 0,
                "risk_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "at_risk_orchards": [],
                "prevalent_diseases": []
            }
        
        orchard_ids = [o["id"] for o in orchards_response.data]
        
        # Get latest risk assessments (within last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        risks_response = supabase.table("weather_disease_risk")\
            .select("*")\
            .in_("orchard_id", orchard_ids)\
            .gte("calculated_at", cutoff_time.isoformat())\
            .execute()
        
        risks = risks_response.data
        
        # Calculate statistics
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        orchard_risk_scores = {}
        disease_counts = {}
        
        for risk in risks:
            # Count by risk level
            risk_counts[risk["risk_level"]] += 1
            
            # Track orchard risk scores
            orchard_id = risk["orchard_id"]
            if orchard_id not in orchard_risk_scores:
                orchard_risk_scores[orchard_id] = []
            orchard_risk_scores[orchard_id].append(risk["risk_score"])
            
            # Count disease occurrences
            disease = risk["disease_type"]
            disease_counts[disease] = disease_counts.get(disease, 0) + 1
        
        # Get top 5 at-risk orchards
        orchard_avg_scores = {
            oid: sum(scores) / len(scores) 
            for oid, scores in orchard_risk_scores.items()
        }
        top_orchards = sorted(
            orchard_avg_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        orchard_map = {o["id"]: o["name"] for o in orchards_response.data}
        at_risk_orchards = [
            {"orchard_id": oid, "name": orchard_map[oid], "avg_risk_score": score}
            for oid, score in top_orchards
        ]
        
        # Get top 5 prevalent diseases
        prevalent_diseases = sorted(
            disease_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        prevalent_diseases = [
            {"disease": disease, "occurrence_count": count}
            for disease, count in prevalent_diseases
        ]
        
        return {
            "total_orchards": len(orchards_response.data),
            "risk_counts": risk_counts,
            "at_risk_orchards": at_risk_orchards,
            "prevalent_diseases": prevalent_diseases,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error generating risk summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate risk summary"
        )
