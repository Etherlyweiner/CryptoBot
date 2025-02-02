"""
Notification system for CryptoBot alerts
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from typing import Dict, List, Optional
from datetime import datetime
from config import config
from logging_config import get_logger, log_with_context

logger = get_logger('Notifications')

class NotificationManager:
    def __init__(self):
        """Initialize notification manager"""
        self.telegram_enabled = config.ENABLE_TELEGRAM
        self.email_enabled = config.ENABLE_EMAIL
        
        if self.telegram_enabled and not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
            logger.warning("Telegram notifications enabled but missing bot token or chat ID")
            self.telegram_enabled = False
        
        if self.email_enabled and not all([
            config.EMAIL_SMTP_SERVER,
            config.EMAIL_SMTP_PORT,
            config.EMAIL_USERNAME,
            config.EMAIL_PASSWORD,
            config.EMAIL_RECIPIENTS
        ]):
            logger.warning("Email notifications enabled but missing configuration")
            self.email_enabled = False
    
    def send_notification(self, alert_data: Dict) -> None:
        """Send notification through all enabled channels"""
        try:
            if self.telegram_enabled:
                self._send_telegram(alert_data)
            
            if self.email_enabled:
                self._send_email(alert_data)
                
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                "Error sending notifications",
                {
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'alert': alert_data
                }
            )
    
    def _send_telegram(self, alert_data: Dict) -> None:
        """Send notification via Telegram"""
        try:
            message = self._format_telegram_message(alert_data)
            
            response = requests.post(
                f'https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage',
                json={
                    'chat_id': config.TELEGRAM_CHAT_ID,
                    'text': message,
                    'parse_mode': 'HTML'
                },
                timeout=10
            )
            
            response.raise_for_status()
            
            log_with_context(
                logger,
                logging.INFO,
                "Telegram notification sent",
                {'alert_symbol': alert_data['symbol']}
            )
            
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                "Error sending Telegram notification",
                {
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'alert': alert_data
                }
            )
            raise
    
    def _send_email(self, alert_data: Dict) -> None:
        """Send notification via email"""
        try:
            subject, body = self._format_email_message(alert_data)
            
            msg = MIMEMultipart()
            msg['From'] = config.EMAIL_USERNAME
            msg['To'] = ', '.join(config.EMAIL_RECIPIENTS)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(config.EMAIL_SMTP_SERVER, config.EMAIL_SMTP_PORT) as server:
                server.starttls()
                server.login(config.EMAIL_USERNAME, config.EMAIL_PASSWORD)
                server.send_message(msg)
            
            log_with_context(
                logger,
                logging.INFO,
                "Email notification sent",
                {
                    'alert_symbol': alert_data['symbol'],
                    'recipients': len(config.EMAIL_RECIPIENTS)
                }
            )
            
        except Exception as e:
            log_with_context(
                logger,
                logging.ERROR,
                "Error sending email notification",
                {
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'alert': alert_data
                }
            )
            raise
    
    def _format_telegram_message(self, alert_data: Dict) -> str:
        """Format alert data for Telegram message"""
        return f"""
🚨 <b>New High-Opportunity Token Alert!</b>

<b>Token:</b> {alert_data['symbol']} ({alert_data['name']})
<b>Opportunity Score:</b> {alert_data['opportunity_score']:.2f}

<b>Analysis:</b>
• Momentum Score: {alert_data['momentum_score']:.2f}
• Social Score: {alert_data['social_score']:.2f}
• Risk Score: {alert_data['risk_score']:.2f}

<b>Time:</b> {alert_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
    
    def _format_email_message(self, alert_data: Dict) -> tuple[str, str]:
        """Format alert data for email message"""
        subject = f"🚨 CryptoBot Alert: High-Opportunity Token {alert_data['symbol']}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #1a73e8;">New High-Opportunity Token Alert!</h2>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
                <h3 style="margin: 0;">Token Information</h3>
                <p>
                    <strong>Symbol:</strong> {alert_data['symbol']}<br>
                    <strong>Name:</strong> {alert_data['name']}<br>
                    <strong>Opportunity Score:</strong> {alert_data['opportunity_score']:.2f}
                </p>
                
                <h3>Analysis</h3>
                <ul>
                    <li>Momentum Score: {alert_data['momentum_score']:.2f}</li>
                    <li>Social Score: {alert_data['social_score']:.2f}</li>
                    <li>Risk Score: {alert_data['risk_score']:.2f}</li>
                </ul>
                
                <p style="color: #666;">
                    Alert generated at: {alert_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}
                </p>
            </div>
            
            <p style="font-size: 12px; color: #666;">
                This is an automated alert from your CryptoBot monitoring system.
            </p>
        </body>
        </html>
        """
        
        return subject, body

# Initialize notification manager
notifications = NotificationManager()
