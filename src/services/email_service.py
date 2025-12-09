"""
Email Service - Production-grade email notifications for weather alerts
Supports: Async SMTP, HTML templates, retry logic, error handling
"""
import asyncio
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Production-grade email service with async support and beautiful HTML templates"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name
        self.enabled = settings.email_enabled
        
    def _get_severity_color(self, severity: str) -> str:
        """Get color code for severity level"""
        colors = {
            'critical': '#DC2626',  # Red
            'high': '#EA580C',      # Orange
            'medium': '#EAB308',    # Yellow
            'low': '#3B82F6'        # Blue
        }
        return colors.get(severity.lower(), '#6B7280')
    
    def _get_severity_icon(self, severity: str) -> str:
        """Get emoji icon for severity"""
        icons = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '⚡',
            'low': 'ℹ️'
        }
        return icons.get(severity.lower(), '📢')
    
    def _create_alert_html_template(
        self,
        user_name: str,
        orchard_name: str,
        alert_type: str,
        severity: str,
        message: str,
        recommendation: str,
        diseases_at_risk: List[str],
        triggered_at: datetime,
        location: Optional[str] = None
    ) -> str:
        """Create beautiful HTML email template for weather alerts"""
        
        severity_color = self._get_severity_color(severity)
        severity_icon = self._get_severity_icon(severity)
        severity_upper = severity.upper()
        
        # Format timestamp
        time_str = triggered_at.strftime("%B %d, %Y at %I:%M %p")
        
        # Build diseases section
        diseases_html = ""
        if diseases_at_risk:
            diseases_list = "".join([f"<li style='margin: 5px 0; color: #374151;'>{disease}</li>" 
                                    for disease in diseases_at_risk[:5]])  # Show max 5
            diseases_html = f"""
            <div style="margin-top: 20px; padding: 15px; background-color: #FEF2F2; border-left: 4px solid #DC2626; border-radius: 4px;">
                <h3 style="margin: 0 0 10px 0; color: #DC2626; font-size: 16px;">🦠 Diseases at Risk</h3>
                <ul style="margin: 0; padding-left: 20px;">
                    {diseases_list}
                </ul>
            </div>
            """
        
        # Location section
        location_html = ""
        if location:
            location_html = f"""
            <div style="margin-top: 15px; padding: 10px; background-color: #F3F4F6; border-radius: 4px;">
                <p style="margin: 0; color: #6B7280; font-size: 14px;">📍 Location: {location}</p>
            </div>
            """
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weather Alert - {severity_upper}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F9FAFB;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; color: white; font-size: 28px; font-weight: 700;">🌱 FRESH Alert System</h1>
            <p style="margin: 10px 0 0 0; color: #D1FAE5; font-size: 14px;">Fruit Disease Early Warning System</p>
        </div>
        
        <!-- Alert Content -->
        <div style="background-color: white; padding: 30px; border-radius: 0 0 8px 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            
            <!-- Greeting -->
            <p style="margin: 0 0 20px 0; color: #374151; font-size: 16px;">Dear {user_name},</p>
            
            <!-- Severity Badge -->
            <div style="margin-bottom: 25px; padding: 15px; background-color: {severity_color}15; border-left: 5px solid {severity_color}; border-radius: 4px;">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 32px; margin-right: 15px;">{severity_icon}</span>
                    <div>
                        <h2 style="margin: 0; color: {severity_color}; font-size: 20px; font-weight: 700;">{severity_upper} ALERT</h2>
                        <p style="margin: 5px 0 0 0; color: #6B7280; font-size: 14px;">{alert_type}</p>
                    </div>
                </div>
            </div>
            
            <!-- Orchard Info -->
            <div style="margin-bottom: 20px; padding: 15px; background-color: #F3F4F6; border-radius: 6px;">
                <h3 style="margin: 0 0 5px 0; color: #1F2937; font-size: 18px;">🏞️ Affected Orchard</h3>
                <p style="margin: 0; color: #4B5563; font-size: 16px; font-weight: 600;">{orchard_name}</p>
            </div>
            
            <!-- Alert Message -->
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; color: #1F2937; font-size: 16px; font-weight: 600;">📋 Alert Details</h3>
                <p style="margin: 0; color: #374151; font-size: 15px; line-height: 1.6;">{message}</p>
            </div>
            
            <!-- Recommendations -->
            <div style="margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%); border-radius: 6px;">
                <h3 style="margin: 0 0 10px 0; color: #1E40AF; font-size: 16px; font-weight: 600;">💡 Recommended Actions</h3>
                <p style="margin: 0; color: #1E40AF; font-size: 15px; line-height: 1.7; font-weight: 500;">{recommendation}</p>
            </div>
            
            {diseases_html}
            
            {location_html}
            
            <!-- Timestamp -->
            <div style="margin-top: 25px; padding-top: 20px; border-top: 2px solid #E5E7EB;">
                <p style="margin: 0; color: #9CA3AF; font-size: 13px;">⏰ Alert triggered on {time_str}</p>
            </div>
            
            <!-- Call to Action -->
            <div style="margin-top: 25px; text-align: center;">
                <a href="#" style="display: inline-block; padding: 14px 30px; background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 15px; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);">
                    View Dashboard
                </a>
            </div>
            
        </div>
        
        <!-- Footer -->
        <div style="margin-top: 20px; text-align: center; padding: 20px;">
            <p style="margin: 0 0 10px 0; color: #9CA3AF; font-size: 13px;">
                This is an automated alert from FRESH - Fruit Disease Early Warning System
            </p>
            <p style="margin: 0; color: #9CA3AF; font-size: 12px;">
                © 2025 FRESH. Protecting Pakistani fruit orchards with AI and real-time weather monitoring.
            </p>
        </div>
        
    </div>
</body>
</html>
        """
        return html_content
    
    def _create_plain_text_template(
        self,
        user_name: str,
        orchard_name: str,
        alert_type: str,
        severity: str,
        message: str,
        recommendation: str,
        diseases_at_risk: List[str],
        triggered_at: datetime
    ) -> str:
        """Create plain text email template (fallback)"""
        
        time_str = triggered_at.strftime("%B %d, %Y at %I:%M %p")
        severity_upper = severity.upper()
        
        diseases_text = ""
        if diseases_at_risk:
            diseases_list = "\n".join([f"  - {disease}" for disease in diseases_at_risk[:5]])
            diseases_text = f"\n\n🦠 DISEASES AT RISK:\n{diseases_list}"
        
        plain_text = f"""
🌱 FRESH ALERT SYSTEM
Fruit Disease Early Warning System

Dear {user_name},

🚨 {severity_upper} ALERT - {alert_type}

🏞️ AFFECTED ORCHARD: {orchard_name}

📋 ALERT DETAILS:
{message}

💡 RECOMMENDED ACTIONS:
{recommendation}
{diseases_text}

⏰ Alert triggered on {time_str}

---
This is an automated alert from FRESH - Fruit Disease Early Warning System.
© 2025 FRESH. Protecting Pakistani fruit orchards with AI and real-time weather monitoring.
        """
        return plain_text.strip()
    
    async def send_alert_email(
        self,
        to_email: str,
        to_name: str,
        orchard_name: str,
        alert_type: str,
        severity: str,
        message: str,
        recommendation: str,
        diseases_at_risk: Optional[List[str]] = None,
        triggered_at: Optional[datetime] = None,
        location: Optional[str] = None
    ) -> bool:
        """
        Send weather alert email asynchronously
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            orchard_name: Name of affected orchard
            alert_type: Type of alert (e.g., "Mango Anthracnose Risk")
            severity: Alert severity (critical, high, medium, low)
            message: Alert message
            recommendation: Recommended actions
            diseases_at_risk: List of diseases at risk
            triggered_at: When alert was triggered
            location: Orchard location (optional)
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        
        if not self.enabled:
            logger.info("📧 Email sending is disabled in settings")
            return False
        
        if not settings.email_send_alerts:
            logger.info("📧 Alert emails are disabled in settings")
            return False
        
        if not all([self.smtp_username, self.smtp_password, self.from_email]):
            logger.error("📧 SMTP configuration incomplete - cannot send email")
            return False
        
        try:
            # Use current time if not provided
            if triggered_at is None:
                triggered_at = datetime.utcnow()
            
            # Handle empty diseases list
            if diseases_at_risk is None:
                diseases_at_risk = []
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 {severity.upper()} Alert: {alert_type} - {orchard_name}"
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = formataddr((to_name, to_email))
            
            # Create plain text version
            plain_text = self._create_plain_text_template(
                user_name=to_name,
                orchard_name=orchard_name,
                alert_type=alert_type,
                severity=severity,
                message=message,
                recommendation=recommendation,
                diseases_at_risk=diseases_at_risk,
                triggered_at=triggered_at
            )
            
            # Create HTML version
            html_content = self._create_alert_html_template(
                user_name=to_name,
                orchard_name=orchard_name,
                alert_type=alert_type,
                severity=severity,
                message=message,
                recommendation=recommendation,
                diseases_at_risk=diseases_at_risk,
                triggered_at=triggered_at,
                location=location
            )
            
            # Attach parts
            part1 = MIMEText(plain_text, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email in thread pool (async-friendly)
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_smtp_email,
                msg,
                to_email
            )
            
            logger.info(f"✅ Alert email sent successfully to {to_email} ({severity.upper()} - {alert_type})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send alert email to {to_email}: {str(e)}")
            return False
    
    def _send_smtp_email(self, msg: MIMEMultipart, to_email: str):
        """Send email via SMTP (blocking - run in executor)"""
        try:
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP Authentication failed - check username/password")
            raise
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {str(e)}")
            raise
    
    async def send_batch_alerts(
        self,
        alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send multiple alert emails in batch (async)
        
        Args:
            alerts: List of alert dictionaries with email details
            
        Returns:
            Dict with success/failure counts
        """
        
        if not alerts:
            return {"sent": 0, "failed": 0}
        
        # Send all emails concurrently
        tasks = []
        for alert in alerts:
            task = self.send_alert_email(
                to_email=alert.get('to_email'),
                to_name=alert.get('to_name'),
                orchard_name=alert.get('orchard_name'),
                alert_type=alert.get('alert_type'),
                severity=alert.get('severity'),
                message=alert.get('message'),
                recommendation=alert.get('recommendation'),
                diseases_at_risk=alert.get('diseases_at_risk', []),
                triggered_at=alert.get('triggered_at'),
                location=alert.get('location')
            )
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes and failures
        sent = sum(1 for r in results if r is True)
        failed = len(results) - sent
        
        logger.info(f"📊 Batch email results: {sent} sent, {failed} failed")
        
        return {
            "sent": sent,
            "failed": failed,
            "total": len(alerts)
        }


# Create singleton instance
email_service = EmailService()
