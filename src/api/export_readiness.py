"""
Export Readiness API Endpoints (Simplified)
Routes for grading and compliance checking
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from src.schemas.export_readiness import (
    FruitGradeRequest, FruitGradeResponse,
    ComplianceCheckRequest, ComplianceCheckResponse,
    ExportStandardResponse, MarketInfo
)
from src.services.export_readiness_service import ExportReadinessService
from src.api.deps import get_current_user
from src.core.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export Readiness"])


# ============================================================================
# GRADING ENDPOINTS
# ============================================================================

@router.post("/grade", response_model=FruitGradeResponse)
async def grade_fruit(
    request: FruitGradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Grade a single fruit for export"""
    logger.info(f"Grading fruit: {request.fruit_type} for market {request.target_market}")
    try:
        result = await ExportReadinessService.grade_fruit(request, current_user['id'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grading failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grading failed: {str(e)}"
        )


@router.get("/grades/{orchard_id}")
async def get_orchard_grades(
    orchard_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get recent grades for an orchard"""
    try:
        result = supabase.table("fruit_grades")\
            .select("*")\
            .eq("orchard_id", orchard_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data
    except Exception as e:
        logger.error(f"Failed to fetch grades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grading/distribution/{orchard_id}")
async def get_grade_distribution(
    orchard_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get grade distribution for an orchard"""
    try:
        result = supabase.table("fruit_grades")\
            .select("grade_category")\
            .eq("orchard_id", orchard_id)\
            .execute()
        
        distribution = {"premium": 0, "grade_a": 0, "grade_b": 0, "reject": 0}
        
        for grade in result.data or []:
            category = grade.get("grade_category")
            if category in distribution:
                distribution[category] += 1
        
        return [{"category": k, "count": v} for k, v in distribution.items()]
        
    except Exception as e:
        logger.error(f"Failed to get distribution: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPLIANCE ENDPOINTS
# ============================================================================

@router.post("/compliance/check", response_model=ComplianceCheckResponse)
async def check_compliance(
    request: ComplianceCheckRequest,
    current_user: dict = Depends(get_current_user)
):
    """Check compliance against export standards"""
    logger.info(f"Checking compliance for {request.fruit_type} to {request.target_market}")
    try:
        result = await ExportReadinessService.check_compliance(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STANDARDS ENDPOINTS
# ============================================================================

@router.get("/standards", response_model=ExportStandardResponse)
async def get_export_standards(
    country: str,
    fruit_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Get export standards for a specific market and fruit type"""
    try:
        result = await ExportReadinessService.get_standards(country, fruit_type)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch standards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/markets", response_model=List[MarketInfo])
async def get_available_markets(
    current_user: dict = Depends(get_current_user)
):
    """Get all available export markets"""
    try:
        result = await ExportReadinessService.get_all_markets()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch markets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# READINESS SUMMARY
# ============================================================================

@router.get("/readiness/{orchard_id}")
async def get_export_readiness_summary(
    orchard_id: str,
    target_market: str,
    current_user: dict = Depends(get_current_user)
):
    """Get export readiness summary for an orchard"""
    try:
        # Get all grades for the orchard
        grades_result = supabase.table("fruit_grades")\
            .select("*")\
            .eq("orchard_id", orchard_id)\
            .eq("target_market", target_market)\
            .execute()
        
        grades = grades_result.data or []
        
        if not grades:
            return {
                "total_fruits": 0,
                "premium_count": 0,
                "grade_a_count": 0,
                "grade_b_count": 0,
                "reject_count": 0,
                "compliance_rate": 0,
                "top_issues": []
            }
        
        # Calculate distribution
        premium = len([g for g in grades if g['grade_category'] == 'premium'])
        grade_a = len([g for g in grades if g['grade_category'] == 'grade_a'])
        grade_b = len([g for g in grades if g['grade_category'] == 'grade_b'])
        reject = len([g for g in grades if g['grade_category'] == 'reject'])
        
        # Compliance rate (non-reject percentage)
        compliant_count = premium + grade_a + grade_b
        compliance_rate = (compliant_count / len(grades)) * 100 if grades else 0
        
        return {
            "total_fruits": len(grades),
            "premium_count": premium,
            "grade_a_count": grade_a,
            "grade_b_count": grade_b,
            "reject_count": reject,
            "compliance_rate": round(compliance_rate, 1),
            "top_issues": []
        }
        
    except Exception as e:
        logger.error(f"Failed to get readiness summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
