from datetime import datetime, timedelta
import os
import json
import hashlib
import secrets
from typing import Dict, List, Optional

class SecurityManager:
    def __init__(self):
        self.rate_limits: Dict[str, List[datetime]] = {}
        self.api_keys: Dict[str, dict] = {}
        self.whitelisted_ips: set = set()
        self.max_requests_per_minute = 60
        self.key_rotation_days = 30
        
    def load_config(self):
        """Load security configuration from environment or config file"""
        try:
            # Load whitelisted IPs
            whitelist = os.getenv('WHITELISTED_IPS', '127.0.0.1').split(',')
            self.whitelisted_ips = set(ip.strip() for ip in whitelist)
            
            # Load API keys with expiration
            self.load_api_keys()
            
            return True
        except Exception as e:
            print(f"Error loading security config: {e}")
            return False
    
    def load_api_keys(self):
        """Load API keys from secure storage"""
        keys = {
            'helius': os.getenv('HELIUS_KEY', ''),
            'quicknode': os.getenv('QUICKNODE_KEY', ''),
            'birdeye': os.getenv('BIRDEYE_KEY', ''),
            'jupiter': os.getenv('JUPITER_KEY', '')
        }
        
        for service, key in keys.items():
            if key:
                self.api_keys[service] = {
                    'key': key,
                    'created_at': datetime.now(),
                    'expires_at': datetime.now() + timedelta(days=self.key_rotation_days)
                }
    
    def check_rate_limit(self, ip: str) -> bool:
        """Check if IP has exceeded rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests
        if ip in self.rate_limits:
            self.rate_limits[ip] = [t for t in self.rate_limits[ip] if t > minute_ago]
        else:
            self.rate_limits[ip] = []
        
        # Check limit
        if len(self.rate_limits[ip]) >= self.max_requests_per_minute:
            return False
        
        # Add new request
        self.rate_limits[ip].append(now)
        return True
    
    def is_ip_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        return ip in self.whitelisted_ips
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for service if valid"""
        if service not in self.api_keys:
            return None
            
        key_data = self.api_keys[service]
        if datetime.now() > key_data['expires_at']:
            # Key has expired
            return None
            
        return key_data['key']
    
    def rotate_key(self, service: str) -> bool:
        """Rotate API key for service"""
        try:
            # In a real implementation, this would integrate with the API provider
            # to generate new keys. For now, we'll just update the expiration.
            if service in self.api_keys:
                self.api_keys[service]['created_at'] = datetime.now()
                self.api_keys[service]['expires_at'] = datetime.now() + timedelta(days=self.key_rotation_days)
            return True
        except Exception:
            return False
    
    def generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for logging"""
        return hashlib.sha256(data.encode()).hexdigest()[:8]
