from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional
from uuid import UUID
from datetime import date
import logging

from src.schemas.analytics import (
    QualityAnalyticsResponse,
    QualityAnalyticsTrendResponse,
    DiseaseRiskAnalyticsResponse,
    DiseaseRiskTrendResponse,
    YieldAnalyticsResponse,
    YieldComparisonResponse,
    ExportReadinessResponse,
    ExportReadinessDetailRequest,
    AnalyticsSummaryResponse,
    DateRangeRequest
)
from src.services.analytics_service import (
    get_quality_analytics,
    get_quality_trends,
    get_disease_risk_analytics,
    get_disease_risk_trends,
    get_yield_analytics,
    get_yield_comparison,
    get_export_readiness,
    get_analytics_summary
)
from src.api.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)

# ================= Quality Analytics Endpoints =================

@router.get("/quality", response_model=QualityAnalyticsResponse)
async def get_fruit_quality_analytics(
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive fruit quality analytics including:
    - Fruit type statistics
    - Ripeness distribution
    - Quality scores
    - Defect analysis

    **Default period:** Last 30 days if dates not specified

    **Requires authentication**

    **Note:** Returns empty analytics if no detection data is available for the user.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in authentication token"
            )

        result = await get_quality_analytics(
            user_id=UUID(user_id),
            start_date=start_date,
            end_date=end_date,
            orchard_id=orchard_id,
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in quality analytics: {error_trace}")

        # Return user-friendly error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate quality analytics. Please ensure you have detection data available. Error: {str(e)}"
        )

@router.get("/quality/trends", response_model=QualityAnalyticsTrendResponse)
async def get_fruit_quality_trends(
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get fruit quality trends over time showing:
    - Daily quality score progression
    - Defect rate trends
    - Detection volume trends

    **Default period:** Last 30 days if dates not specified

    **Requires authentication**
    """
    try:
        return await get_quality_trends(
            user_id=UUID(current_user["user_id"]),
            start_date=start_date,
            end_date=end_date,
            orchard_id=orchard_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quality trends: {str(e)}"
        )

# ================= Disease Risk Analytics Endpoints =================

@router.get("/disease-risk", response_model=DiseaseRiskAnalyticsResponse)
async def get_disease_risk_analysis(
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get disease risk analytics including:
    - Infection rates
    - Disease type distribution
    - Severity analysis
    - Risk assessment (low, medium, high, critical)
    - Actionable recommendations

    **Default period:** Last 30 days if dates not specified

    **Requires authentication**
    """
    try:
        return await get_disease_risk_analytics(
            user_id=UUID(current_user["user_id"]),
            start_date=start_date,
            end_date=end_date,
            orchard_id=orchard_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate disease risk analytics: {str(e)}"
        )

@router.get("/disease-risk/trends", response_model=DiseaseRiskTrendResponse)
async def get_disease_risk_trend_analysis(
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get disease risk trends over time showing:
    - Daily infection rate progression
    - Disease outbreak patterns
    - Risk level changes

    **Default period:** Last 30 days if dates not specified

    **Requires authentication**
    """
    try:
        return await get_disease_risk_trends(
            user_id=UUID(current_user["user_id"]),
            start_date=start_date,
            end_date=end_date,
            orchard_id=orchard_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate disease risk trends: {str(e)}"
        )

# ================= Yield Analytics Endpoints =================

@router.get("/yield", response_model=YieldAnalyticsResponse)
async def get_fruit_yield_analytics(
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get yield analytics including:
    - Total fruit count by type
    - Marketable fruit count and percentage
    - Estimated weight calculations
    - Best performing fruit types

    **Default period:** Last 30 days if dates not specified

    **Requires authentication**
    """
    try:
        return await get_yield_analytics(
            user_id=UUID(current_user["user_id"]),
            start_date=start_date,
            end_date=end_date,
            orchard_id=orchard_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate yield analytics: {str(e)}"
        )

@router.get("/yield/comparison", response_model=YieldComparisonResponse)
async def get_yield_period_comparison(
    start_date: Optional[date] = Query(None, description="Start date for current period (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for current period (YYYY-MM-DD)"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Compare yield between current period and previous period.

    **Default period:** Last 30 days vs previous 30 days

    **Requires authentication**
    """
    try:
        return await get_yield_comparison(
            user_id=UUID(current_user["user_id"]),
            start_date=start_date,
            end_date=end_date,
            orchard_id=orchard_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate yield comparison: {str(e)}"
        )

# ================= Export Readiness Endpoints =================

@router.get("/export-readiness", response_model=ExportReadinessResponse)
async def get_export_readiness_report(
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    target_market: Optional[str] = Query(None, description="Target export market (e.g., 'EU', 'US', 'Asia')"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive export readiness report.

    **Default period:** Last 30 days if dates not specified

    **Requires authentication**
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID not found in authentication token"
            )

        result = await get_export_readiness(
            user_id=UUID(user_id),
            start_date=start_date,
            end_date=end_date,
            target_market=target_market,
            orchard_id=orchard_id,
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request parameters: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in export readiness: {error_trace}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate export readiness report. Error: {str(e)}"
        )

# ================= Summary Analytics Endpoint =================

@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_comprehensive_analytics_summary(
    start_date: Optional[date] = Query(None, description="Start date for analysis (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for analysis (YYYY-MM-DD)"),
    orchard_id: Optional[UUID] = Query(None, description="Filter by orchard"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive analytics summary combining all key metrics.

    **Default period:** Last 30 days if dates not specified

    **Requires authentication**
    """
    try:
        return await get_analytics_summary(
            user_id=UUID(current_user["user_id"]),
            start_date=start_date,
            end_date=end_date,
            orchard_id=orchard_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics summary: {str(e)}"
        )

# ================= Health Check =================

@router.get("/health")
async def analytics_health_check():
    """
    Health check endpoint for analytics service
    """
    return {
        "status": "healthy",
        "service": "Analytics and Reports",
        "version": "1.0.0",
        "features": [
            "Fruit Quality Analytics",
            "Disease Risk Assessment",
            "Yield Analysis",
            "Export Readiness Reporting"
        ]
    }
