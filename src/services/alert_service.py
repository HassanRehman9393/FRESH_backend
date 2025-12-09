"""
Alert Service - Evaluates weather forecasts against alert rules
Automatically generates alerts for Pakistani fruit orchards
Includes email notification support for immediate farmer alerts
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from src.core.supabase_client import supabase
from src.services.weather_service import WeatherService
from src.services.email_service import email_service
from src.schemas.weather import WeatherForecastResponse

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service for evaluating alert rules and generating weather alerts
    """
    
    def __init__(self):
        self.weather_service = WeatherService()
    
    async def evaluate_orchard_alerts(
        self,
        orchard_id: str,
        orchard_data: Dict[str, Any],
        use_historical: bool = True,
        use_forecast: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all alert rules for a specific orchard using both historical and forecast data
        
        Args:
            orchard_id: UUID of the orchard
            orchard_data: Orchard details including fruit_types, latitude, longitude
            use_historical: Evaluate using historical weather_data from database
            use_forecast: Evaluate using forecast data from API
        
        Returns:
            List of triggered alerts to be created
        """
        try:
            alerts_to_create = []
            
            # Evaluate historical weather data (past 7 days)
            if use_historical:
                historical_alerts = await self._evaluate_historical_data(
                    orchard_id=orchard_id,
                    fruit_types=orchard_data["fruit_types"]
                )
                alerts_to_create.extend(historical_alerts)
            
            # Evaluate forecast data (next 5 days)
            if use_forecast:
                forecast_alerts = await self._evaluate_forecast_data(
                    orchard_id=orchard_id,
                    orchard_data=orchard_data
                )
                alerts_to_create.extend(forecast_alerts)
            
            return alerts_to_create
        
        except Exception as e:
            logger.error(f"Error evaluating alerts for orchard {orchard_id}: {str(e)}")
            return []
    
    async def _evaluate_forecast_data(
        self,
        orchard_id: str,
        orchard_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate alert rules using forecast data from API
        """
        try:
            alerts_to_create = []
            
            # Get weather forecast (5 days)
            forecast = await self.weather_service.fetch_forecast(
                orchard_id=orchard_id,
                latitude=float(orchard_data["latitude"]),
                longitude=float(orchard_data["longitude"]),
                days=5,
                use_cache=True
            )
            
            if not forecast:
                logger.warning(f"No forecast data available for orchard {orchard_id}")
                return []
            
            # Get applicable alert rules for this orchard's fruit types
            rules = self._get_applicable_rules(orchard_data["fruit_types"])
            
            if not rules:
                logger.info(f"No forecast alert rules found for orchard {orchard_id}")
                return []
            
            # Evaluate each rule
            for rule in rules:
                triggered_alert = self._evaluate_rule(
                    rule=rule,
                    forecast=forecast,
                    orchard_id=orchard_id
                )
                
                if triggered_alert:
                    # Check if similar alert already exists (avoid duplicates)
                    if not self._alert_already_exists(orchard_id, rule["rule_code"]):
                        alerts_to_create.append(triggered_alert)
                        logger.info(
                            f"Forecast alert triggered: {rule['rule_code']} for orchard {orchard_id}"
                        )
            
            return alerts_to_create
        
        except Exception as e:
            logger.error(f"Error evaluating forecast alerts: {str(e)}")
            return []
    
    async def _evaluate_historical_data(
        self,
        orchard_id: str,
        fruit_types: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate alert rules using historical weather_data from database
        
        Args:
            orchard_id: UUID of the orchard
            fruit_types: List of fruit types for this orchard
        
        Returns:
            List of triggered alerts based on historical patterns
        """
        try:
            alerts_to_create = []
            
            # Fetch last 7 days of weather data from weather_data table
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            response = supabase.table("weather_data")\
                .select("*")\
                .eq("orchard_id", orchard_id)\
                .gte("recorded_at", seven_days_ago.isoformat())\
                .order("recorded_at", desc=False)\
                .execute()
            
            if not response.data:
                logger.info(f"No historical weather data found for orchard {orchard_id}")
                return []
            
            weather_records = response.data
            logger.info(f"Evaluating {len(weather_records)} historical records for orchard {orchard_id}")
            
            # Get applicable alert rules
            rules = self._get_applicable_rules(fruit_types)
            
            if not rules:
                logger.info(f"No historical alert rules found for orchard {orchard_id}")
                return []
            
            # Group weather records by date
            daily_data = self._group_historical_by_day(weather_records)
            
            # Evaluate each rule against historical data
            for rule in rules:
                triggered_alert = self._evaluate_rule_historical(
                    rule=rule,
                    daily_data=daily_data,
                    orchard_id=orchard_id
                )
                
                if triggered_alert:
                    # Check if similar alert already exists (avoid duplicates)
                    if not self._alert_already_exists(orchard_id, rule["rule_code"]):
                        alerts_to_create.append(triggered_alert)
                        logger.info(
                            f"Historical alert triggered: {rule['rule_code']} for orchard {orchard_id}"
                        )
            
            return alerts_to_create
        
        except Exception as e:
            logger.error(f"Error evaluating historical data: {str(e)}")
            return []
    
    def _get_applicable_rules(self, fruit_types: List[str]) -> List[Dict[str, Any]]:
        """
        Get alert rules applicable to given fruit types
        
        Args:
            fruit_types: List of fruit types (e.g., ['mango', 'citrus'])
        
        Returns:
            List of applicable alert rules
        """
        try:
            # Query rules that match fruit types or apply to 'all'
            response = supabase.table("alert_rules")\
                .select("*")\
                .eq("is_active", True)\
                .execute()
            
            if not response.data:
                return []
            
            # Filter rules that apply to this orchard's fruits
            applicable_rules = []
            for rule in response.data:
                rule_fruits = rule.get("fruit_types", [])
                
                # Check if rule applies to 'all' or matches any of the orchard's fruits
                if 'all' in rule_fruits or any(fruit in rule_fruits for fruit in fruit_types):
                    applicable_rules.append(rule)
            
            # Sort by priority (1 = highest)
            applicable_rules.sort(key=lambda x: x.get("priority", 5))
            
            return applicable_rules
        
        except Exception as e:
            logger.error(f"Error fetching alert rules: {str(e)}")
            return []
    
    def _evaluate_rule(
        self,
        rule: Dict[str, Any],
        forecast: List[WeatherForecastResponse],
        orchard_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single alert rule against forecast data
        
        Args:
            rule: Alert rule configuration
            forecast: List of weather forecast data points
            orchard_id: UUID of the orchard
        
        Returns:
            Alert data if rule is triggered, None otherwise
        """
        try:
            consecutive_days = rule.get("consecutive_days", 1)
            forecast_window = rule.get("forecast_window", 5)
            
            # Group forecast by day (average daily values)
            daily_forecasts = self._group_forecast_by_day(forecast[:forecast_window * 8])
            
            if len(daily_forecasts) < consecutive_days:
                return None
            
            # Check if condition is met for required consecutive days
            matching_days = 0
            
            for day_data in daily_forecasts:
                if self._check_conditions(rule, day_data):
                    matching_days += 1
                    if matching_days >= consecutive_days:
                        # Rule triggered!
                        return self._create_alert_data(rule, orchard_id, day_data)
                else:
                    matching_days = 0  # Reset if condition breaks
            
            return None
        
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.get('rule_code')}: {str(e)}")
            return None
    
    def _group_historical_by_day(
        self,
        weather_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Group historical weather_data records by day with proper aggregation
        
        Args:
            weather_records: List of weather_data records from database
                            (temperature, humidity, rainfall, wind_speed, weather_condition, recorded_at)
        
        Returns:
            List of daily aggregated weather data matching alert rule structure
        """
        daily_data = {}
        
        for record in weather_records:
            # Parse recorded_at to get date
            recorded_at = datetime.fromisoformat(record['recorded_at'].replace('Z', '+00:00'))
            date = recorded_at.date()
            
            if date not in daily_data:
                daily_data[date] = {
                    'date': date,
                    'temperatures': [],
                    'humidities': [],
                    'wind_speeds': [],
                    'rainfall_total': 0,
                    'weather_conditions': []
                }
            
            # Aggregate data (matching weather_data table structure)
            daily_data[date]['temperatures'].append(float(record['temperature']))
            daily_data[date]['humidities'].append(float(record['humidity']))
            daily_data[date]['rainfall_total'] += float(record.get('rainfall', 0) or 0)
            
            if record.get('wind_speed'):
                daily_data[date]['wind_speeds'].append(float(record['wind_speed']))
            
            if record.get('weather_condition'):
                daily_data[date]['weather_conditions'].append(record['weather_condition'])
        
        # Calculate daily statistics
        result = []
        for date, data in sorted(daily_data.items()):
            result.append({
                'date': date,
                'temp_avg': sum(data['temperatures']) / len(data['temperatures']),
                'temp_max': max(data['temperatures']),
                'temp_min': min(data['temperatures']),
                'humidity_avg': sum(data['humidities']) / len(data['humidities']),
                'humidity_max': max(data['humidities']),
                'humidity_min': min(data['humidities']),
                'wind_speed_max': max(data['wind_speeds']) if data['wind_speeds'] else 0,
                'rainfall_total': data['rainfall_total'],
                'weather_conditions': data['weather_conditions'],
                'record_count': len(data['temperatures'])
            })
        
        return result
    
    def _group_forecast_by_day(
        self,
        forecast: List[WeatherForecastResponse]
    ) -> List[Dict[str, Any]]:
        """
        Group 3-hour forecast intervals into daily averages
        
        Args:
            forecast: List of 3-hour forecast data points
        
        Returns:
            List of daily averaged weather data
        """
        daily_data = {}
        
        for item in forecast:
            date = item.forecast_time.date()
            
            if date not in daily_data:
                daily_data[date] = {
                    'date': date,
                    'temperatures': [],
                    'humidities': [],
                    'wind_speeds': [],
                    'rainfall_total': 0,
                    'rainfall_probability_max': 0
                }
            
            daily_data[date]['temperatures'].append(item.temperature)
            daily_data[date]['humidities'].append(item.humidity)
            if item.wind_speed:
                daily_data[date]['wind_speeds'].append(item.wind_speed)
            daily_data[date]['rainfall_total'] += item.rainfall_amount or 0
            daily_data[date]['rainfall_probability_max'] = max(
                daily_data[date]['rainfall_probability_max'],
                item.rainfall_probability or 0
            )
        
        # Calculate averages
        result = []
        for date, data in sorted(daily_data.items()):
            result.append({
                'date': date,
                'temp_avg': sum(data['temperatures']) / len(data['temperatures']),
                'temp_max': max(data['temperatures']),
                'temp_min': min(data['temperatures']),
                'humidity_avg': sum(data['humidities']) / len(data['humidities']),
                'humidity_max': max(data['humidities']),
                'wind_speed_max': max(data['wind_speeds']) if data['wind_speeds'] else 0,
                'rainfall_total': data['rainfall_total'],
                'rainfall_probability': data['rainfall_probability_max']
            })
        
        return result
    
    def _evaluate_rule_historical(
        self,
        rule: Dict[str, Any],
        daily_data: List[Dict[str, Any]],
        orchard_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single alert rule against historical daily data
        
        Args:
            rule: Alert rule to evaluate
            daily_data: List of daily aggregated historical weather data
            orchard_id: UUID of the orchard
        
        Returns:
            Alert data if rule is triggered, None otherwise
        """
        consecutive_days_required = rule.get("consecutive_days", 1)
        consecutive_count = 0
        matching_days = []
        
        # Check each day against rule conditions
        for day_data in daily_data:
            if self._check_conditions(rule, day_data):
                consecutive_count += 1
                matching_days.append(day_data)
                
                # If consecutive requirement met, trigger alert
                if consecutive_count >= consecutive_days_required:
                    logger.info(
                        f"Historical rule {rule['rule_code']} triggered: "
                        f"{consecutive_count} consecutive days matched"
                    )
                    return self._create_alert_data(rule, orchard_id, matching_days[-1])
            else:
                # Reset counter if conditions not met
                consecutive_count = 0
                matching_days = []
        
        return None
    
    def _check_conditions(
        self,
        rule: Dict[str, Any],
        day_data: Dict[str, Any]
    ) -> bool:
        """
        Check if weather conditions match alert rule thresholds
        Works with both forecast and historical data (weather_data table structure)
        
        Args:
            rule: Alert rule with threshold conditions
            day_data: Daily weather data (temp_avg, temp_max, temp_min, humidity_avg, humidity_max, 
                      humidity_min, wind_speed_max, rainfall_total)
        
        Returns:
            True if all conditions are met, False otherwise
        """
        # Temperature checks
        if rule.get("temperature_min") is not None:
            if day_data['temp_max'] < float(rule["temperature_min"]):
                return False
        
        if rule.get("temperature_max") is not None:
            if day_data['temp_min'] > float(rule["temperature_max"]):
                return False
        
        # Humidity checks
        if rule.get("humidity_min") is not None:
            if day_data['humidity_max'] < float(rule["humidity_min"]):
                return False
        
        if rule.get("humidity_max") is not None:
            if day_data['humidity_min'] > float(rule["humidity_max"]):
                return False
        
        # Rainfall checks
        if rule.get("rainfall_min") is not None:
            if day_data['rainfall_total'] < float(rule["rainfall_min"]):
                return False
        
        if rule.get("rainfall_max") is not None:
            if day_data['rainfall_total'] > float(rule["rainfall_max"]):
                return False
        
        # Wind speed check
        if rule.get("wind_speed_max") is not None:
            if day_data['wind_speed_max'] > float(rule["wind_speed_max"]):
                return False
        
        # All conditions met
        return True
    
    def _create_alert_data(
        self,
        rule: Dict[str, Any],
        orchard_id: str,
        day_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create alert data structure from triggered rule
        
        Args:
            rule: Triggered alert rule
            orchard_id: UUID of the orchard
            day_data: Weather data that triggered the alert
        
        Returns:
            Alert data ready to be inserted into database
        """
        return {
            "orchard_id": orchard_id,
            "alert_type": rule["alert_type"],
            "severity": rule["severity"],
            "message": rule["message_en"],
            "recommendation": rule["recommendation_en"],
            "is_active": True,
            "triggered_at": datetime.utcnow().isoformat()
        }
    
    def _alert_already_exists(
        self,
        orchard_id: str,
        rule_code: str,
        hours: int = 24
    ) -> bool:
        """
        Check if similar alert already exists (to avoid spam)
        
        Args:
            orchard_id: UUID of the orchard
            rule_code: Alert rule code
            hours: Look back period in hours (default: 24)
        
        Returns:
            True if alert exists, False otherwise
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            response = supabase.table("weather_alerts")\
                .select("id")\
                .eq("orchard_id", orchard_id)\
                .eq("is_active", True)\
                .gte("triggered_at", cutoff_time.isoformat())\
                .execute()
            
            # Check if any existing alert matches this rule type
            # (Simple check - could be enhanced with rule_code storage)
            return len(response.data) > 0 if response.data else False
        
        except Exception as e:
            logger.error(f"Error checking existing alerts: {str(e)}")
            return False
    
    async def create_alert(
        self, 
        alert_data: Dict[str, Any],
        orchard_data: Optional[Dict[str, Any]] = None,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new weather alert in the database and send email notification
        
        Args:
            alert_data: Alert information
            orchard_data: Orchard details (for email context)
            user_data: User details (for email recipient)
        
        Returns:
            Created alert or None if failed
        """
        try:
            # Create alert in database
            response = supabase.table("weather_alerts")\
                .insert(alert_data)\
                .execute()
            
            if not response.data:
                logger.error("Failed to create alert in database")
                return None
            
            created_alert = response.data[0]
            logger.info(f"✅ Alert created: {created_alert['id']} ({alert_data.get('severity', 'unknown').upper()})")
            
            # Send email notification (async, non-blocking)
            try:
                await self._send_alert_email_notification(
                    alert=created_alert,
                    orchard_data=orchard_data,
                    user_data=user_data
                )
            except Exception as email_error:
                # Log error but don't fail alert creation
                logger.error(f"⚠️ Email notification failed (alert still created): {str(email_error)}")
            
            return created_alert
        
        except Exception as e:
            logger.error(f"❌ Error creating alert: {str(e)}")
            return None
    
    async def _send_alert_email_notification(
        self,
        alert: Dict[str, Any],
        orchard_data: Optional[Dict[str, Any]] = None,
        user_data: Optional[Dict[str, Any]] = None
    ):
        """
        Send email notification for a newly created alert
        
        Args:
            alert: Created alert data from database
            orchard_data: Orchard information (optional, will fetch if not provided)
            user_data: User information (optional, will fetch if not provided)
        """
        try:
            orchard_id = alert.get("orchard_id")
            
            # Fetch orchard data if not provided
            if not orchard_data:
                orchard_response = supabase.table("orchards")\
                    .select("*")\
                    .eq("id", orchard_id)\
                    .single()\
                    .execute()
                
                if not orchard_response.data:
                    logger.error(f"Orchard not found: {orchard_id}")
                    return
                
                orchard_data = orchard_response.data
            
            # Fetch user data if not provided
            if not user_data:
                user_id = orchard_data.get("user_id")
                user_response = supabase.table("users")\
                    .select("id, email, full_name")\
                    .eq("id", user_id)\
                    .single()\
                    .execute()
                
                if not user_response.data:
                    logger.error(f"User not found: {user_id}")
                    return
                
                user_data = user_response.data
            
            # Extract email details
            to_email = user_data.get("email")
            to_name = user_data.get("full_name", "Farmer")
            
            if not to_email:
                logger.error("User email not found - cannot send alert email")
                return
            
            # Build location string
            location = None
            if orchard_data.get("latitude") and orchard_data.get("longitude"):
                location = f"{orchard_data['latitude']:.4f}, {orchard_data['longitude']:.4f}"
            
            # Send email
            success = await email_service.send_alert_email(
                to_email=to_email,
                to_name=to_name,
                orchard_name=orchard_data.get("name", "Unknown Orchard"),
                alert_type=alert.get("alert_type", "Weather Alert"),
                severity=alert.get("severity", "medium"),
                message=alert.get("message", "Weather conditions require attention"),
                recommendation=alert.get("recommendation", "Monitor your orchard closely"),
                diseases_at_risk=alert.get("diseases_at_risk", []),
                triggered_at=datetime.fromisoformat(alert["triggered_at"].replace('Z', '+00:00')) if alert.get("triggered_at") else datetime.utcnow(),
                location=location
            )
            
            if success:
                logger.info(f"📧 Email notification sent to {to_email} for alert {alert['id']}")
            else:
                logger.warning(f"⚠️ Email notification failed for alert {alert['id']}")
        
        except Exception as e:
            logger.error(f"❌ Error sending alert email notification: {str(e)}")
            # Don't raise - email failure shouldn't break alert creation
    
    async def evaluate_all_orchards(self) -> Dict[str, Any]:
        """
        Evaluate alert rules for ALL orchards in the system
        Used by background scheduler
        
        Returns:
            Summary of evaluation results
        """
        try:
            # Get all orchards
            orchards_response = supabase.table("orchards")\
                .select("*")\
                .execute()
            
            if not orchards_response.data:
                logger.info("No orchards found")
                return {"total_orchards": 0, "alerts_created": 0}
            
            total_alerts = 0
            emails_sent = 0
            
            for orchard in orchards_response.data:
                # Evaluate alerts for this orchard
                alerts = await self.evaluate_orchard_alerts(
                    orchard_id=orchard["id"],
                    orchard_data=orchard
                )
                
                # Create alerts in database and send email notifications
                for alert_data in alerts:
                    created = await self.create_alert(
                        alert_data=alert_data,
                        orchard_data=orchard,
                        user_data=None  # Will be fetched automatically
                    )
                    if created:
                        total_alerts += 1
                        # Email sending is handled in create_alert
                        emails_sent += 1
            
            logger.info(
                f"✅ Alert evaluation complete: {len(orchards_response.data)} orchards, "
                f"{total_alerts} alerts created, {emails_sent} email notifications sent"
            )
            
            return {
                "total_orchards": len(orchards_response.data),
                "alerts_created": total_alerts,
                "emails_sent": emails_sent,
                "evaluated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error evaluating all orchards: {str(e)}")
            return {"error": str(e)}
        
        except Exception as e:
            logger.error(f"Error evaluating all orchards: {str(e)}")
            return {"error": str(e)}


# Global instance
alert_service = AlertService()
