"""
Error monitoring and alerting system for CryptoBot.
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from prometheus_client import Counter, Gauge, Histogram
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from pathlib import Path
import traceback
import socket
from functools import wraps

logger = logging.getLogger(__name__)

# Prometheus metrics
ERROR_COUNT = Counter('error_total', 'Total number of errors', ['type', 'severity'])
ALERT_COUNT = Counter('alerts_total', 'Total number of alerts sent', ['type'])
SYSTEM_HEALTH = Gauge('system_health', 'Overall system health score (0-100)')
RESPONSE_TIME = Histogram('response_time_seconds', 'Response time in seconds', ['endpoint'])

@dataclass
class Alert:
    """Alert configuration."""
    severity: str
    message: str
    timestamp: datetime
    error_type: str
    details: Dict[str, Any]
    resolved: bool = False

class MonitoringSystem:
    """Comprehensive monitoring and alerting system."""
    
    def __init__(self, 
                 config_path: str = "config/monitoring.json",
                 alert_interval: int = 300):  # 5 minutes
        self.config = self._load_config(config_path)
        self.alert_interval = alert_interval
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_handlers: Dict[str, List[Callable]] = {
            'critical': [],
            'error': [],
            'warning': []
        }
        
        # Initialize alert channels
        self._setup_alert_channels()
        
        # Start background tasks
        asyncio.create_task(self._periodic_health_check())
        asyncio.create_task(self._alert_processor())

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load monitoring configuration."""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                # Create default config
                config = {
                    'alert_thresholds': {
                        'error_rate': 0.1,
                        'response_time': 2.0,
                        'memory_usage': 0.9
                    },
                    'email_settings': {
                        'smtp_server': os.getenv('SMTP_SERVER', ''),
                        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                        'sender_email': os.getenv('ALERT_EMAIL', ''),
                        'sender_password': os.getenv('ALERT_EMAIL_PASSWORD', '')
                    },
                    'slack_webhook': os.getenv('SLACK_WEBHOOK', ''),
                    'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
                    'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
                }
                
                config_file.parent.mkdir(exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
                
            with open(config_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading monitoring config: {str(e)}")
            return {}

    def _setup_alert_channels(self):
        """Setup alert notification channels."""
        # Email alerts
        if all(self.config.get('email_settings', {}).values()):
            self.alert_handlers['critical'].append(self._send_email_alert)
            self.alert_handlers['error'].append(self._send_email_alert)
        
        # Slack alerts
        if self.config.get('slack_webhook'):
            self.alert_handlers['critical'].append(self._send_slack_alert)
            self.alert_handlers['error'].append(self._send_slack_alert)
        
        # Telegram alerts
        if self.config.get('telegram_token') and self.config.get('telegram_chat_id'):
            self.alert_handlers['critical'].append(self._send_telegram_alert)
            self.alert_handlers['error'].append(self._send_telegram_alert)
            self.alert_handlers['warning'].append(self._send_telegram_alert)

    async def _send_email_alert(self, alert: Alert):
        """Send alert via email."""
        try:
            settings = self.config['email_settings']
            msg = MIMEMultipart()
            msg['From'] = settings['sender_email']
            msg['To'] = settings['sender_email']  # Send to self
            msg['Subject'] = f"CryptoBot Alert: {alert.severity.upper()} - {alert.error_type}"
            
            body = f"""
            Severity: {alert.severity}
            Type: {alert.error_type}
            Time: {alert.timestamp}
            Message: {alert.message}
            Details: {json.dumps(alert.details, indent=2)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(settings['smtp_server'], settings['smtp_port']) as server:
                server.starttls()
                server.login(settings['sender_email'], settings['sender_password'])
                server.send_message(msg)
            
            ALERT_COUNT.labels(type='email').inc()
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")

    async def _send_slack_alert(self, alert: Alert):
        """Send alert to Slack."""
        try:
            webhook_url = self.config['slack_webhook']
            
            message = {
                "text": f"*CryptoBot Alert*",
                "attachments": [{
                    "color": {
                        "critical": "#FF0000",
                        "error": "#FFA500",
                        "warning": "#FFFF00"
                    }.get(alert.severity, "#808080"),
                    "fields": [
                        {"title": "Severity", "value": alert.severity, "short": True},
                        {"title": "Type", "value": alert.error_type, "short": True},
                        {"title": "Message", "value": alert.message},
                        {"title": "Details", "value": f"```{json.dumps(alert.details, indent=2)}```"}
                    ]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=message) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack alert: {await response.text()}")
                    else:
                        ALERT_COUNT.labels(type='slack').inc()
                        
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")

    async def _send_telegram_alert(self, alert: Alert):
        """Send alert via Telegram."""
        try:
            token = self.config['telegram_token']
            chat_id = self.config['telegram_chat_id']
            
            message = f"""
🚨 *CryptoBot Alert*
*Severity:* {alert.severity}
*Type:* {alert.error_type}
*Time:* {alert.timestamp}
*Message:* {alert.message}
*Details:* ```{json.dumps(alert.details, indent=2)}```
            """
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            params = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Telegram alert: {await response.text()}")
                    else:
                        ALERT_COUNT.labels(type='telegram').inc()
                        
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {str(e)}")

    def monitor(self, error_type: str = "general"):
        """Decorator for monitoring function execution."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = datetime.utcnow()
                try:
                    result = await func(*args, **kwargs)
                    RESPONSE_TIME.labels(endpoint=func.__name__).observe(
                        (datetime.utcnow() - start_time).total_seconds()
                    )
                    return result
                except Exception as e:
                    self.record_error(
                        error_type=error_type,
                        message=str(e),
                        details={
                            'function': func.__name__,
                            'args': str(args),
                            'kwargs': str(kwargs),
                            'traceback': traceback.format_exc()
                        }
                    )
                    raise
            return wrapper
        return decorator

    def record_error(self, 
                    error_type: str,
                    message: str,
                    details: Dict[str, Any] = None,
                    severity: str = "error"):
        """Record an error and potentially trigger alerts."""
        try:
            ERROR_COUNT.labels(type=error_type, severity=severity).inc()
            
            alert = Alert(
                severity=severity,
                message=message,
                timestamp=datetime.utcnow(),
                error_type=error_type,
                details=details or {}
            )
            
            alert_key = f"{error_type}_{message}"
            if alert_key not in self.active_alerts:
                self.active_alerts[alert_key] = alert
                asyncio.create_task(self._process_alert(alert))
                
        except Exception as e:
            logger.error(f"Failed to record error: {str(e)}")

    async def _process_alert(self, alert: Alert):
        """Process and send alerts based on severity."""
        try:
            handlers = self.alert_handlers.get(alert.severity, [])
            for handler in handlers:
                await handler(alert)
                
        except Exception as e:
            logger.error(f"Failed to process alert: {str(e)}")

    async def _periodic_health_check(self):
        """Perform periodic health checks."""
        while True:
            try:
                # Check system metrics
                memory_usage = self._get_memory_usage()
                error_rate = self._get_error_rate()
                avg_response_time = self._get_avg_response_time()
                
                # Calculate health score (0-100)
                health_score = 100
                
                if memory_usage > self.config['alert_thresholds']['memory_usage']:
                    health_score -= 30
                    self.record_error(
                        "system",
                        "High memory usage",
                        {"usage": memory_usage},
                        "warning"
                    )
                
                if error_rate > self.config['alert_thresholds']['error_rate']:
                    health_score -= 40
                    self.record_error(
                        "system",
                        "High error rate",
                        {"rate": error_rate},
                        "error"
                    )
                
                if avg_response_time > self.config['alert_thresholds']['response_time']:
                    health_score -= 30
                    self.record_error(
                        "system",
                        "Slow response time",
                        {"time": avg_response_time},
                        "warning"
                    )
                
                SYSTEM_HEALTH.set(health_score)
                
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
            
            await asyncio.sleep(60)  # Check every minute

    async def _alert_processor(self):
        """Process and clean up alerts."""
        while True:
            try:
                current_time = datetime.utcnow()
                resolved_alerts = []
                
                for key, alert in self.active_alerts.items():
                    if (current_time - alert.timestamp) > timedelta(minutes=5):
                        alert.resolved = True
                        resolved_alerts.append(key)
                
                for key in resolved_alerts:
                    self.active_alerts.pop(key)
                    
            except Exception as e:
                logger.error(f"Alert processor error: {str(e)}")
            
            await asyncio.sleep(self.alert_interval)

    def _get_memory_usage(self) -> float:
        """Get current memory usage."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_percent()
        except:
            return 0.0

    def _get_error_rate(self) -> float:
        """Calculate error rate from recent errors."""
        total_requests = sum(RESPONSE_TIME.collect()[0].samples[0].value)
        if total_requests == 0:
            return 0.0
        total_errors = sum(ERROR_COUNT.collect()[0].samples[0].value)
        return total_errors / total_requests

    def _get_avg_response_time(self) -> float:
        """Get average response time from histogram."""
        samples = RESPONSE_TIME.collect()[0].samples
        if not samples:
            return 0.0
        return sum(s.value for s in samples) / len(samples)
