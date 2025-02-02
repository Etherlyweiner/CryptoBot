"""
Security module for CryptoBot with advanced security features.
"""

import os
import jwt
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import aiohttp
from aiohttp import web
import ipaddress
from prometheus_client import Counter, Gauge
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

# Prometheus metrics
AUTH_FAILURES = Counter('auth_failures_total', 'Total number of authentication failures')
BLOCKED_REQUESTS = Counter('blocked_requests_total', 'Total number of blocked requests')
API_REQUESTS = Counter('api_requests_total', 'Total API requests', ['endpoint'])

@dataclass
class RateLimitRule:
    """Rate limiting configuration for an endpoint."""
    requests_per_second: float
    burst_size: int
    block_duration: int = 300  # 5 minutes

class SecurityManager:
    """Comprehensive security management system."""
    
    def __init__(self, config_path: str = "config/security.json"):
        self.config = self._load_config(config_path)
        self.rate_limiters: Dict[str, Dict] = {}
        self.blocked_ips: Dict[str, datetime] = {}
        self._setup_encryption()
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_blocked_ips())

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load security configuration."""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                # Create default config
                config = {
                    'jwt_secret': os.getenv('JWT_SECRET', secrets.token_hex(32)),
                    'jwt_expiry': 3600,  # 1 hour
                    'rate_limits': {
                        'default': {'requests_per_second': 5, 'burst_size': 10},
                        '/api/trade': {'requests_per_second': 2, 'burst_size': 5},
                        '/api/market': {'requests_per_second': 10, 'burst_size': 20}
                    },
                    'allowed_ips': [],
                    'blocked_ips': [],
                    'api_keys': {}
                }
                
                config_file.parent.mkdir(exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=4)
                
            with open(config_file) as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading security config: {str(e)}")
            return {}

    def _setup_encryption(self):
        """Setup encryption keys and Fernet instance."""
        try:
            # Generate or load encryption key
            key_file = Path("config/encryption.key")
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                key_file.parent.mkdir(exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(key)
            
            self.fernet = Fernet(key)
            
        except Exception as e:
            logger.error(f"Error setting up encryption: {str(e)}")
            raise

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise

    def generate_api_key(self, user_id: str) -> Tuple[str, str]:
        """Generate a new API key and secret."""
        try:
            api_key = f"cb_{secrets.token_hex(16)}"
            api_secret = secrets.token_hex(32)
            
            # Hash the secret before storing
            secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()
            
            self.config['api_keys'][api_key] = {
                'user_id': user_id,
                'secret_hash': secret_hash,
                'created_at': datetime.utcnow().isoformat(),
                'last_used': None,
                'enabled': True
            }
            
            # Save updated config
            with open("config/security.json", 'w') as f:
                json.dump(self.config, f, indent=4)
            
            return api_key, api_secret
            
        except Exception as e:
            logger.error(f"Error generating API key: {str(e)}")
            raise

    def validate_api_key(self, api_key: str, api_secret: str) -> bool:
        """Validate API key and secret."""
        try:
            key_data = self.config['api_keys'].get(api_key)
            if not key_data or not key_data['enabled']:
                return False
            
            # Check secret hash
            secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()
            if secret_hash != key_data['secret_hash']:
                return False
            
            # Update last used timestamp
            key_data['last_used'] = datetime.utcnow().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return False

    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """Create a JWT token."""
        try:
            payload = {
                **user_data,
                'exp': datetime.utcnow() + timedelta(seconds=self.config['jwt_expiry'])
            }
            return jwt.encode(payload, self.config['jwt_secret'], algorithm='HS256')
        except Exception as e:
            logger.error(f"JWT creation error: {str(e)}")
            raise

    def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token."""
        try:
            return jwt.decode(token, self.config['jwt_secret'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None

    def check_rate_limit(self, ip: str, endpoint: str) -> bool:
        """Check if request is within rate limits."""
        try:
            current_time = time.time()
            
            # Get rate limit rule
            rule = self.config['rate_limits'].get(
                endpoint,
                self.config['rate_limits']['default']
            )
            
            # Initialize rate limiter for IP if not exists
            if ip not in self.rate_limiters:
                self.rate_limiters[ip] = {
                    'tokens': rule['burst_size'],
                    'last_update': current_time
                }
            
            limiter = self.rate_limiters[ip]
            time_passed = current_time - limiter['last_update']
            
            # Replenish tokens
            limiter['tokens'] = min(
                rule['burst_size'],
                limiter['tokens'] + time_passed * rule['requests_per_second']
            )
            
            # Check if request can be processed
            if limiter['tokens'] >= 1:
                limiter['tokens'] -= 1
                limiter['last_update'] = current_time
                return True
            
            # Block IP if too many requests
            self.blocked_ips[ip] = datetime.utcnow() + timedelta(
                seconds=rule['block_duration']
            )
            BLOCKED_REQUESTS.inc()
            return False
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            return False

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked."""
        if ip in self.blocked_ips:
            if datetime.utcnow() < self.blocked_ips[ip]:
                return True
            del self.blocked_ips[ip]
        return False

    async def _cleanup_blocked_ips(self):
        """Periodically clean up expired IP blocks."""
        while True:
            try:
                current_time = datetime.utcnow()
                expired = [
                    ip for ip, block_until in self.blocked_ips.items()
                    if current_time >= block_until
                ]
                for ip in expired:
                    del self.blocked_ips[ip]
                    
            except Exception as e:
                logger.error(f"Error cleaning up blocked IPs: {str(e)}")
            
            await asyncio.sleep(60)  # Check every minute

    def validate_input(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate input data against schema."""
        try:
            for field, rules in schema.items():
                if field not in data:
                    if rules.get('required', True):
                        return False, f"Missing required field: {field}"
                    continue
                
                value = data[field]
                
                # Type validation
                if not isinstance(value, rules['type']):
                    return False, f"Invalid type for {field}"
                
                # Pattern validation
                if 'pattern' in rules and not re.match(rules['pattern'], str(value)):
                    return False, f"Invalid format for {field}"
                
                # Range validation
                if 'min' in rules and value < rules['min']:
                    return False, f"{field} below minimum value"
                if 'max' in rules and value > rules['max']:
                    return False, f"{field} above maximum value"
                
                # Custom validation
                if 'validator' in rules and not rules['validator'](value):
                    return False, f"Validation failed for {field}"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Input validation error: {str(e)}")
            return False, str(e)

def require_auth(f):
    """Decorator for requiring authentication."""
    @wraps(f)
    async def wrapper(request: web.Request, *args, **kwargs):
        try:
            # Get auth header
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                raise web.HTTPUnauthorized(reason="Missing authorization header")
            
            # Extract token
            auth_type, token = auth_header.split(' ', 1)
            if auth_type.lower() != 'bearer':
                raise web.HTTPUnauthorized(reason="Invalid authorization type")
            
            # Validate token
            security = request.app['security']
            user_data = security.validate_jwt_token(token)
            if not user_data:
                AUTH_FAILURES.inc()
                raise web.HTTPUnauthorized(reason="Invalid or expired token")
            
            # Add user data to request
            request['user'] = user_data
            
            # Track API request
            API_REQUESTS.labels(endpoint=request.path).inc()
            
            return await f(request, *args, **kwargs)
            
        except web.HTTPUnauthorized:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise web.HTTPInternalServerError()
    
    return wrapper

def require_api_key(f):
    """Decorator for requiring API key authentication."""
    @wraps(f)
    async def wrapper(request: web.Request, *args, **kwargs):
        try:
            # Get API key and secret
            api_key = request.headers.get('X-API-Key')
            api_secret = request.headers.get('X-API-Secret')
            
            if not api_key or not api_secret:
                raise web.HTTPUnauthorized(reason="Missing API credentials")
            
            # Validate credentials
            security = request.app['security']
            if not security.validate_api_key(api_key, api_secret):
                AUTH_FAILURES.inc()
                raise web.HTTPUnauthorized(reason="Invalid API credentials")
            
            # Track API request
            API_REQUESTS.labels(endpoint=request.path).inc()
            
            return await f(request, *args, **kwargs)
            
        except web.HTTPUnauthorized:
            raise
        except Exception as e:
            logger.error(f"API authentication error: {str(e)}")
            raise web.HTTPInternalServerError()
    
    return wrapper
