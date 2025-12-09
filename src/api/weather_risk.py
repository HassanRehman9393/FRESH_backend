"""
Disease Risk Summary API
Aggregates weather alerts into actionable disease risk intelligence
Simplified architecture - uses weather_alerts as single source of truth
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.core.supabase_client import supabase
from src.api.deps import get_current_user
from src.schemas.user import UserResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["disease-risk"])


@router.get("/summary")
async def get_risk_summary(
    current_user: UserResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive disease risk summary across all user orchards
    
    Analyzes recent weather alerts to provide actionable intelligence:
    - Total orchards monitored
    - Alert severity distribution (critical, high, medium, low)
    - Most at-risk orchards (by alert severity and count)
    - Most prevalent diseases threatening your orchards
    - Recent alert trends
    
    **Data Source:** Aggregates from weather_alerts table (last 7 days)
    
    **Returns:**
    ```json
    {
      "total_orchards": 5,
      "alerts_summary": {
        "total_alerts": 12,
        "critical": 3,
        "high": 5,
        "medium": 3,
        "low": 1,
        "unacknowledged": 8
      },
      "at_risk_orchards": [
        {
          "orchard_id": "uuid",
          "orchard_name": "Mango Farm A",
          "alert_count": 4,
          "highest_severity": "critical",
          "critical_count": 2,
          "latest_alert": "2025-12-09T10:30:00Z"
        }
      ],
      "disease_threats": [
        {
          "disease": "anthracnose",
          "affected_orchards": 3,
          "total_alerts": 5,
          "severity_breakdown": {"critical": 3, "high": 2}
        }
      ],
      "last_updated": "2025-12-09T18:00:00Z"
    }
    ```
    """
    try:
        # Get user's orchards
        orchards_response = supabase.table("orchards")\
            .select("id, name, fruit_types")\
            .eq("user_id", current_user["user_id"])\
            .execute()
        
        if not orchards_response.data:
            return {
                "total_orchards": 0,
                "alerts_summary": {
                    "total_alerts": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "unacknowledged": 0
                },
                "at_risk_orchards": [],
                "disease_threats": [],
                "last_updated": datetime.utcnow().isoformat()
            }
        
        orchards = orchards_response.data
        orchard_ids = [o["id"] for o in orchards]
        orchard_map = {o["id"]: {"name": o["name"], "fruit_types": o.get("fruit_types", [])} for o in orchards}
        
        # Get alerts from last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        alerts_response = supabase.table("weather_alerts")\
            .select("*")\
            .in_("orchard_id", orchard_ids)\
            .gte("triggered_at", seven_days_ago.isoformat())\
            .order("triggered_at", desc=True)\
            .execute()
        
        alerts = alerts_response.data or []
        
        # Calculate alert severity distribution
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        unacknowledged_count = 0
        
        for alert in alerts:
            severity = alert.get("severity", "low")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            if alert.get("acknowledged_at") is None:
                unacknowledged_count += 1
        
        # Analyze orchards at risk (group alerts by orchard)
        orchard_alerts = {}
        for alert in alerts:
            orch_id = alert["orchard_id"]
            if orch_id not in orchard_alerts:
                orchard_alerts[orch_id] = {
                    "alerts": [],
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0
                }
            
            orchard_alerts[orch_id]["alerts"].append(alert)
            severity = alert.get("severity", "low")
            orchard_alerts[orch_id][f"{severity}_count"] += 1
        
        # Build at-risk orchards list (sorted by severity priority)
        at_risk_orchards = []
        
        for orch_id, data in orchard_alerts.items():
            orchard_info = orchard_map.get(orch_id, {"name": "Unknown", "fruit_types": []})
            
            # Calculate risk score (weighted by severity)
            risk_score = (
                data["critical_count"] * 4 +
                data["high_count"] * 3 +
                data["medium_count"] * 2 +
                data["low_count"] * 1
            )
            
            # Determine highest severity
            if data["critical_count"] > 0:
                highest_severity = "critical"
            elif data["high_count"] > 0:
                highest_severity = "high"
            elif data["medium_count"] > 0:
                highest_severity = "medium"
            else:
                highest_severity = "low"
            
            # Get latest alert timestamp
            latest_alert = max(a["triggered_at"] for a in data["alerts"]) if data["alerts"] else None
            
            at_risk_orchards.append({
                "orchard_id": orch_id,
                "orchard_name": orchard_info["name"],
                "fruit_types": orchard_info["fruit_types"],
                "alert_count": len(data["alerts"]),
                "highest_severity": highest_severity,
                "critical_count": data["critical_count"],
                "high_count": data["high_count"],
                "medium_count": data["medium_count"],
                "low_count": data["low_count"],
                "risk_score": risk_score,
                "latest_alert": latest_alert
            })
        
        # Sort by risk score (descending), then by alert count
        at_risk_orchards.sort(key=lambda x: (x["risk_score"], x["alert_count"]), reverse=True)
        
        # Analyze disease threats (extract from diseases_at_risk arrays)
        disease_data = {}
        
        for alert in alerts:
            diseases = alert.get("diseases_at_risk") or []
            severity = alert.get("severity", "low")
            orch_id = alert["orchard_id"]
            
            for disease in diseases:
                if disease not in disease_data:
                    disease_data[disease] = {
                        "orchards": set(),
                        "alerts": [],
                        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0}
                    }
                
                disease_data[disease]["orchards"].add(orch_id)
                disease_data[disease]["alerts"].append(alert)
                disease_data[disease]["severity_counts"][severity] += 1
        
        # Build disease threats list
        disease_threats = []
        for disease, data in disease_data.items():
            # Calculate threat score (weighted by severity and affected orchards)
            threat_score = (
                data["severity_counts"]["critical"] * 4 +
                data["severity_counts"]["high"] * 3 +
                data["severity_counts"]["medium"] * 2 +
                data["severity_counts"]["low"] * 1
            ) * len(data["orchards"])  # Multiply by number of affected orchards
            
            disease_threats.append({
                "disease": disease,
                "affected_orchards": len(data["orchards"]),
                "total_alerts": len(data["alerts"]),
                "severity_breakdown": data["severity_counts"],
                "threat_score": threat_score
            })
        
        # Sort diseases by threat score
        disease_threats.sort(key=lambda x: x["threat_score"], reverse=True)
        
        # Remove threat_score from output (internal calculation only)
        for threat in disease_threats:
            del threat["threat_score"]
        
        # Build final summary response
        return {
            "total_orchards": len(orchards),
            "alerts_summary": {
                "total_alerts": len(alerts),
                "critical": severity_counts["critical"],
                "high": severity_counts["high"],
                "medium": severity_counts["medium"],
                "low": severity_counts["low"],
                "unacknowledged": unacknowledged_count
            },
            "at_risk_orchards": at_risk_orchards[:5],  # Top 5 most at-risk
            "disease_threats": disease_threats[:10],  # Top 10 diseases
            "analysis_period": "Last 7 days",
            "last_updated": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error generating risk summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate risk summary: {str(e)}"
        )
