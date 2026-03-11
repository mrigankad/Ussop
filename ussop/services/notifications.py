"""
Notification Service for Ussop
Sends alerts via email, webhooks, and Slack
"""
import json
import logging
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False


class NotificationChannel(Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


@dataclass
class NotificationMessage:
    """Notification message structure."""
    title: str
    body: str
    severity: str  # info, warning, error, critical
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class NotificationService:
    """
    Multi-channel notification service.
    
    Supports:
    - Email (SMTP)
    - Webhook (HTTP POST)
    - Slack
    """
    
    def __init__(self):
        self.email_config: Optional[Dict] = None
        self.webhook_urls: List[str] = []
        self.slack_webhook: Optional[str] = None
        self.enabled_channels: List[NotificationChannel] = []
    
    def configure_email(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        use_tls: bool = True
    ):
        """Configure email notifications."""
        self.email_config = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "from_addr": from_addr,
            "to_addrs": to_addrs,
            "use_tls": use_tls
        }
        
        if SMTP_AVAILABLE:
            self.enabled_channels.append(NotificationChannel.EMAIL)
            logger.info("Email configured: %s -> %s", from_addr, ', '.join(to_addrs))
        else:
            logger.warning("SMTP not available. Install aiosmtplib: pip install aiosmtplib")
    
    def configure_webhook(self, urls: List[str]):
        """Configure webhook notifications."""
        self.webhook_urls = urls
        
        if AIOHTTP_AVAILABLE and urls:
            self.enabled_channels.append(NotificationChannel.WEBHOOK)
            logger.info("Webhook configured: %d URLs", len(urls))
        elif urls:
            logger.warning("aiohttp not available. Install: pip install aiohttp")
    
    def configure_slack(self, webhook_url: str):
        """Configure Slack notifications."""
        self.slack_webhook = webhook_url
        
        if AIOHTTP_AVAILABLE and webhook_url:
            self.enabled_channels.append(NotificationChannel.SLACK)
            logger.info("Slack configured")
        elif webhook_url:
            logger.warning("aiohttp not available. Install: pip install aiohttp")
    
    async def send(self, message: NotificationMessage):
        """Send notification through all enabled channels."""
        tasks = []
        
        if NotificationChannel.EMAIL in self.enabled_channels:
            tasks.append(self._send_email(message))
        
        if NotificationChannel.WEBHOOK in self.enabled_channels:
            tasks.append(self._send_webhook(message))
        
        if NotificationChannel.SLACK in self.enabled_channels:
            tasks.append(self._send_slack(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_email(self, message: NotificationMessage):
        """Send email notification."""
        if not self.email_config or not SMTP_AVAILABLE:
            return
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_addr']
            msg['To'] = ', '.join(self.email_config['to_addrs'])
            msg['Subject'] = f"[Ussop {message.severity.upper()}] {message.title}"
            
            # Body
            body = f"""
Ussop Alert Notification
=======================

Severity: {message.severity.upper()}
Time: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

{message.body}

---
Sent by Ussop Visual Inspector
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send
            await aiosmtplib.send(
                msg,
                hostname=self.email_config['host'],
                port=self.email_config['port'],
                username=self.email_config['username'],
                password=self.email_config['password'],
                use_tls=self.email_config['use_tls']
            )
            
            logger.info("Email sent: %s", message.title)
            
        except Exception as e:
            logger.error("Email failed: %s", e)
    
    async def _send_webhook(self, message: NotificationMessage):
        """Send webhook notification."""
        if not self.webhook_urls or not AIOHTTP_AVAILABLE:
            return
        
        payload = {
            "source": "ussop",
            "timestamp": message.timestamp.isoformat(),
            "severity": message.severity,
            "title": message.title,
            "message": message.body,
            "metadata": message.metadata or {}
        }
        
        async with aiohttp.ClientSession() as session:
            for url in self.webhook_urls:
                try:
                    async with session.post(
                        url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            logger.info("Webhook sent: %s", url)
                        else:
                            logger.warning("Webhook failed: %s (%d)", url, response.status)
                except Exception as e:
                    logger.error("Webhook error: %s - %s", url, e)
    
    async def _send_slack(self, message: NotificationMessage):
        """Send Slack notification."""
        if not self.slack_webhook or not AIOHTTP_AVAILABLE:
            return
        
        # Color based on severity
        colors = {
            "info": "#36a64f",
            "warning": "#ff9900",
            "error": "#ff0000",
            "critical": "#990000"
        }
        
        payload = {
            "attachments": [{
                "color": colors.get(message.severity, "#808080"),
                "title": f"[Ussop] {message.title}",
                "text": message.body,
                "fields": [
                    {
                        "title": "Severity",
                        "value": message.severity.upper(),
                        "short": True
                    },
                    {
                        "title": "Time",
                        "value": message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        "short": True
                    }
                ],
                "footer": "Ussop Visual Inspector",
                "ts": int(message.timestamp.timestamp())
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.slack_webhook,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info("Slack sent")
                    else:
                        logger.warning("Slack failed: %d", response.status)
        except Exception as e:
            logger.error("Slack error: %s", e)
    
    # Convenience methods for specific alert types
    
    async def send_defect_alert(
        self,
        station_id: str,
        part_id: Optional[str],
        defect_count: int,
        image_path: Optional[str] = None
    ):
        """Send defect detection alert."""
        message = NotificationMessage(
            title=f"Defects Detected - {station_id}",
            body=f"{defect_count} defect(s) detected on part {part_id or 'unknown'}",
            severity="warning" if defect_count < 3 else "error",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            metadata={
                "station_id": station_id,
                "part_id": part_id,
                "defect_count": defect_count,
                "image_path": image_path
            }
        )
        await self.send(message)
    
    async def send_system_alert(self, title: str, message: str, severity: str = "error"):
        """Send system alert."""
        notification = NotificationMessage(
            title=title,
            body=message,
            severity=severity,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        await self.send(notification)
    
    async def send_daily_report(
        self,
        recipient: str,
        stats: Dict[str, Any]
    ):
        """Send daily inspection report."""
        message = NotificationMessage(
            title="Daily Inspection Report",
            body=f"""
Daily Summary ({stats.get('date', 'Today')}):
- Total Inspections: {stats.get('total', 0)}
- Pass Rate: {stats.get('pass_rate', 0):.1%}
- Defects Found: {stats.get('defects', 0)}
- Avg Processing Time: {stats.get('avg_time_ms', 0):.0f}ms
            """,
            severity="info",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            metadata=stats
        )
        await self.send(message)


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
