"""Service registry for microservices architecture."""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import json
import aiohttp
from dataclasses import dataclass
import redis
from redis.connection import ConnectionPool
from prometheus_client import Counter, Gauge

logger = logging.getLogger('ServiceRegistry')

@dataclass
class ServiceInstance:
    """Service instance information."""
    id: str
    name: str
    host: str
    port: int
    status: str
    last_heartbeat: datetime
    metadata: Dict
    
    @property
    def url(self) -> str:
        """Get service URL."""
        return f"http://{self.host}:{self.port}"
        
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'metadata': self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'ServiceInstance':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            host=data['host'],
            port=data['port'],
            status=data['status'],
            last_heartbeat=datetime.fromisoformat(data['last_heartbeat']),
            metadata=data['metadata']
        )

class ServiceRegistry:
    """Service registry for microservices."""
    
    def __init__(self,
                 redis_url: str,
                 heartbeat_interval: int = 30,
                 cleanup_interval: int = 60):
        """Initialize service registry."""
        self.redis_pool = ConnectionPool.from_url(redis_url)
        self.heartbeat_interval = heartbeat_interval
        self.cleanup_interval = cleanup_interval
        
        # Local cache
        self.services: Dict[str, Dict[str, ServiceInstance]] = {}
        
        # Prometheus metrics
        self.service_count = Gauge(
            'service_instances_total',
            'Total number of service instances',
            ['service_name']
        )
        self.instance_status = Gauge(
            'service_instance_status',
            'Status of service instances',
            ['service_name', 'instance_id']
        )
        self.registration_count = Counter(
            'service_registrations_total',
            'Total number of service registrations',
            ['service_name']
        )
        self.deregistration_count = Counter(
            'service_deregistrations_total',
            'Total number of service deregistrations',
            ['service_name']
        )
        
        # Start background tasks
        asyncio.create_task(self._cleanup_loop())
        
    @property
    def redis(self) -> redis.Redis:
        """Get Redis connection from pool."""
        return redis.Redis(connection_pool=self.redis_pool)
        
    async def register(self,
                      name: str,
                      host: str,
                      port: int,
                      metadata: Optional[Dict] = None) -> ServiceInstance:
        """Register a new service instance."""
        instance = ServiceInstance(
            id=f"{name}-{host}-{port}",
            name=name,
            host=host,
            port=port,
            status='starting',
            last_heartbeat=datetime.now(),
            metadata=metadata or {}
        )
        
        # Store in Redis
        self.redis.hset(
            f"services:{name}",
            instance.id,
            json.dumps(instance.to_dict())
        )
        
        # Update local cache
        if name not in self.services:
            self.services[name] = {}
        self.services[name][instance.id] = instance
        
        # Update metrics
        self.registration_count.labels(service_name=name).inc()
        self.service_count.labels(service_name=name).inc()
        self.instance_status.labels(
            service_name=name,
            instance_id=instance.id
        ).set(1)
        
        logger.info(f"Registered service instance: {instance.id}")
        return instance
        
    async def deregister(self, name: str, instance_id: str):
        """Deregister a service instance."""
        # Remove from Redis
        self.redis.hdel(f"services:{name}", instance_id)
        
        # Update local cache
        if name in self.services and instance_id in self.services[name]:
            del self.services[name][instance_id]
            if not self.services[name]:
                del self.services[name]
                
        # Update metrics
        self.deregistration_count.labels(service_name=name).inc()
        self.service_count.labels(service_name=name).dec()
        self.instance_status.labels(
            service_name=name,
            instance_id=instance_id
        ).set(0)
        
        logger.info(f"Deregistered service instance: {instance_id}")
        
    async def heartbeat(self, name: str, instance_id: str) -> bool:
        """Update service instance heartbeat."""
        instance_key = f"services:{name}"
        instance_data = self.redis.hget(instance_key, instance_id)
        
        if not instance_data:
            return False
            
        instance = ServiceInstance.from_dict(json.loads(instance_data))
        instance.last_heartbeat = datetime.now()
        instance.status = 'healthy'
        
        # Update Redis
        self.redis.hset(
            instance_key,
            instance_id,
            json.dumps(instance.to_dict())
        )
        
        # Update local cache
        if name in self.services:
            self.services[name][instance_id] = instance
            
        # Update metrics
        self.instance_status.labels(
            service_name=name,
            instance_id=instance_id
        ).set(1)
        
        return True
        
    async def get_instances(self, name: str) -> List[ServiceInstance]:
        """Get all instances of a service."""
        instances = []
        instance_data = self.redis.hgetall(f"services:{name}")
        
        for instance_id, data in instance_data.items():
            instance = ServiceInstance.from_dict(json.loads(data))
            instances.append(instance)
            
        return instances
        
    async def get_healthy_instances(self, name: str) -> List[ServiceInstance]:
        """Get healthy instances of a service."""
        all_instances = await self.get_instances(name)
        threshold = datetime.now() - timedelta(seconds=self.heartbeat_interval * 2)
        
        return [
            instance for instance in all_instances
            if instance.status == 'healthy'
            and instance.last_heartbeat >= threshold
        ]
        
    async def _cleanup_loop(self):
        """Periodically clean up dead instances."""
        while True:
            try:
                await self._cleanup_dead_instances()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(self.cleanup_interval)
                
    async def _cleanup_dead_instances(self):
        """Remove instances that haven't sent heartbeat."""
        threshold = datetime.now() - timedelta(seconds=self.heartbeat_interval * 3)
        
        for service_name in list(self.services.keys()):
            instances = await self.get_instances(service_name)
            
            for instance in instances:
                if instance.last_heartbeat < threshold:
                    await self.deregister(service_name, instance.id)
                    logger.warning(f"Removed dead instance: {instance.id}")
                    
    async def close(self):
        """Clean up resources."""
        self.redis.close()
        
# Example usage:
# registry = ServiceRegistry('redis://localhost:6379/0')
# 
# # Register service
# instance = await registry.register('auth-service', 'localhost', 8080)
# 
# # Update heartbeat
# await registry.heartbeat('auth-service', instance.id)
# 
# # Get healthy instances
# instances = await registry.get_healthy_instances('auth-service')
