"""Security management for CryptoBot."""

from typing import Dict, List, Optional, Set
import time
import logging
from datetime import datetime, timedelta
import jwt
import secrets
from dataclasses import dataclass
from functools import wraps
import ipaddress
import redis
from redis.connection import ConnectionPool
from prometheus_client import Counter

logger = logging.getLogger('SecurityManager')

@dataclass
class ApiKey:
    """API key details."""
    key_id: str
    secret: str
    created_at: datetime
    expires_at: datetime
    permissions: Set[str]
    rate_limit: int  # requests per minute

class SecurityManager:
    """Manages security features."""
    
    def __init__(self,
                 redis_url: Optional[str] = None,
                 jwt_secret: Optional[str] = None):
        """Initialize security manager."""
        self.jwt_secret = jwt_secret or secrets.token_hex(32)
        self._redis_pool = None
        if redis_url:
            self._redis_pool = ConnectionPool.from_url(redis_url)
            
        # Metrics
        self.blocked_requests = Counter(
            'cryptobot_blocked_requests_total',
            'Total number of blocked requests',
            ['reason']
        )
        
        # Load IP whitelist
        self.ip_whitelist: Set[ipaddress.IPv4Network] = set()
        self.load_ip_whitelist()
        
        # API key storage
        self.api_keys: Dict[str, ApiKey] = {}
        
    @property
    def redis(self) -> Optional[redis.Redis]:
        """Get Redis connection from pool."""
        if self._redis_pool:
            return redis.Redis(connection_pool=self._redis_pool)
        return None
        
    def load_ip_whitelist(self, filename: str = 'ip_whitelist.txt') -> None:
        """Load IP whitelist from file."""
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.ip_whitelist.add(ipaddress.IPv4Network(line))
        except FileNotFoundError:
            logger.warning(f"IP whitelist file {filename} not found")
            
    def check_ip(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        if not self.ip_whitelist:
            return True  # Allow all if no whitelist
            
        ip_addr = ipaddress.IPv4Address(ip)
        return any(ip_addr in network for network in self.ip_whitelist)
        
    def generate_api_key(self,
                        permissions: Set[str],
                        rate_limit: int = 60,
                        expires_in_days: int = 30) -> ApiKey:
        """Generate new API key."""
        key_id = secrets.token_hex(16)
        secret = secrets.token_hex(32)
        
        api_key = ApiKey(
            key_id=key_id,
            secret=secret,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=expires_in_days),
            permissions=permissions,
            rate_limit=rate_limit
        )
        
        self.api_keys[key_id] = api_key
        return api_key
        
    def rotate_api_key(self, key_id: str) -> Optional[ApiKey]:
        """Rotate existing API key."""
        if key_id not in self.api_keys:
            return None
            
        old_key = self.api_keys[key_id]
        new_key = self.generate_api_key(
            permissions=old_key.permissions,
            rate_limit=old_key.rate_limit,
            expires_in_days=30
        )
        
        # Keep old key valid for 24 hours
        old_key.expires_at = datetime.now() + timedelta(days=1)
        
        return new_key
        
    def validate_api_key(self, key_id: str, secret: str) -> bool:
        """Validate API key."""
        if key_id not in self.api_keys:
            return False
            
        api_key = self.api_keys[key_id]
        if api_key.expires_at < datetime.now():
            return False
            
        return api_key.secret == secret
        
    def check_rate_limit(self, key_id: str) -> bool:
        """Check if request is within rate limit."""
        if not self.redis or key_id not in self.api_keys:
            return True
            
        api_key = self.api_keys[key_id]
        redis_key = f"rate_limit:{key_id}"
        
        pipe = self.redis.pipeline()
        now = int(time.time())
        pipe.zadd(redis_key, {str(now): now})
        pipe.zremrangebyscore(redis_key, 0, now - 60)  # Remove older than 1 minute
        pipe.zcard(redis_key)
        pipe.expire(redis_key, 60)  # Set TTL
        _, _, request_count, _ = pipe.execute()
        
        return request_count <= api_key.rate_limit
        
    def generate_jwt(self, key_id: str, expires_in: int = 3600) -> str:
        """Generate JWT token."""
        if key_id not in self.api_keys:
            raise ValueError("Invalid API key")
            
        payload = {
            'key_id': key_id,
            'permissions': list(self.api_keys[key_id].permissions),
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
        
    def validate_jwt(self, token: str) -> Optional[Dict]:
        """Validate JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            if payload['key_id'] not in self.api_keys:
                return None
            return payload
        except jwt.InvalidTokenError:
            return None
            
    def require_auth(self, required_permissions: Optional[Set[str]] = None):
        """Decorator for requiring authentication."""
        def decorator(func):
            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                # Check IP whitelist
                client_ip = request.remote
                if not self.check_ip(client_ip):
                    self.blocked_requests.labels(reason='ip_blocked').inc()
                    return {'error': 'IP not whitelisted'}, 403
                    
                # Check API key
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    self.blocked_requests.labels(reason='no_auth').inc()
                    return {'error': 'Missing authentication'}, 401
                    
                token = auth_header.split(' ')[1]
                payload = self.validate_jwt(token)
                if not payload:
                    self.blocked_requests.labels(reason='invalid_token').inc()
                    return {'error': 'Invalid token'}, 401
                    
                # Check permissions
                if required_permissions:
                    user_permissions = set(payload['permissions'])
                    if not required_permissions.issubset(user_permissions):
                        self.blocked_requests.labels(reason='insufficient_permissions').inc()
                        return {'error': 'Insufficient permissions'}, 403
                        
                # Check rate limit
                if not self.check_rate_limit(payload['key_id']):
                    self.blocked_requests.labels(reason='rate_limit').inc()
                    return {'error': 'Rate limit exceeded'}, 429
                    
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator
        
# Global security manager instance
security_manager = SecurityManager(
    redis_url='redis://localhost:6379/1'
    if 'REDIS_URL' not in globals()
    else REDIS_URL
)
