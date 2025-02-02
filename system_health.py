"""System health monitoring for CryptoBot."""

import psutil
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
from prometheus_client import Gauge, Counter, Histogram
import os
import json

logger = logging.getLogger('SystemHealth')

@dataclass
class HealthMetrics:
    """System health metrics."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    process_count: int
    system_uptime: float
    load_average: List[float]

class SystemHealthChecker:
    """Monitors system health and resources."""
    
    def __init__(self, 
                 warning_threshold: float = 80.0,
                 critical_threshold: float = 90.0,
                 check_interval: int = 60):
        """Initialize health checker."""
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.check_interval = check_interval
        
        # Prometheus metrics
        self.cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('system_memory_usage_percent', 'Memory usage percentage')
        self.disk_usage = Gauge('system_disk_usage_percent', 'Disk usage percentage')
        self.process_count = Gauge('system_process_count', 'Number of running processes')
        self.system_load = Gauge('system_load_average', 'System load average', ['interval'])
        
        self.network_io_bytes = Counter('system_network_io_bytes_total',
                                      'Network I/O bytes',
                                      ['direction'])
        
        self.health_check_duration = Histogram('system_health_check_duration_seconds',
                                             'Time spent performing health check')
        
    async def get_health_metrics(self) -> HealthMetrics:
        """Collect current system health metrics."""
        with self.health_check_duration.time():
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            load_avg = psutil.getloadavg()
            
            metrics = HealthMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io={
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                },
                process_count=len(psutil.pids()),
                system_uptime=time.time() - psutil.boot_time(),
                load_average=list(load_avg)
            )
            
            # Update Prometheus metrics
            self.cpu_usage.set(metrics.cpu_percent)
            self.memory_usage.set(metrics.memory_percent)
            self.disk_usage.set(metrics.disk_usage_percent)
            self.process_count.set(metrics.process_count)
            
            for i, load in enumerate(metrics.load_average):
                self.system_load.labels(interval=f'{(i+1)*5}min').set(load)
                
            self.network_io_bytes.labels(direction='sent').inc(metrics.network_io['bytes_sent'])
            self.network_io_bytes.labels(direction='received').inc(metrics.network_io['bytes_recv'])
            
            return metrics
            
    def check_thresholds(self, metrics: HealthMetrics) -> List[str]:
        """Check if any metrics exceed thresholds."""
        warnings = []
        
        if metrics.cpu_percent > self.critical_threshold:
            warnings.append(f"CRITICAL: CPU usage at {metrics.cpu_percent}%")
        elif metrics.cpu_percent > self.warning_threshold:
            warnings.append(f"WARNING: CPU usage at {metrics.cpu_percent}%")
            
        if metrics.memory_percent > self.critical_threshold:
            warnings.append(f"CRITICAL: Memory usage at {metrics.memory_percent}%")
        elif metrics.memory_percent > self.warning_threshold:
            warnings.append(f"WARNING: Memory usage at {metrics.memory_percent}%")
            
        if metrics.disk_usage_percent > self.critical_threshold:
            warnings.append(f"CRITICAL: Disk usage at {metrics.disk_usage_percent}%")
        elif metrics.disk_usage_percent > self.warning_threshold:
            warnings.append(f"WARNING: Disk usage at {metrics.disk_usage_percent}%")
            
        return warnings
        
    async def monitor_health(self, callback=None):
        """Continuously monitor system health."""
        while True:
            try:
                metrics = await self.get_health_metrics()
                warnings = self.check_thresholds(metrics)
                
                if warnings:
                    for warning in warnings:
                        logger.warning(warning)
                        if callback:
                            await callback(warning)
                            
                # Log metrics to file
                self.log_metrics(metrics)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring system health: {e}")
                await asyncio.sleep(self.check_interval)
                
    def log_metrics(self, metrics: HealthMetrics):
        """Log metrics to file for historical analysis."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': metrics.cpu_percent,
            'memory_percent': metrics.memory_percent,
            'disk_usage_percent': metrics.disk_usage_percent,
            'network_io': metrics.network_io,
            'process_count': metrics.process_count,
            'system_uptime': metrics.system_uptime,
            'load_average': metrics.load_average
        }
        
        log_file = os.path.join('logs', 'system_health.json')
        os.makedirs('logs', exist_ok=True)
        
        try:
            with open(log_file, 'a') as f:
                json.dump(log_entry, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Error logging metrics: {e}")
            
    async def get_process_metrics(self) -> Dict:
        """Get detailed metrics for the current process."""
        process = psutil.Process()
        
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'threads': process.num_threads(),
            'open_files': len(process.open_files()),
            'connections': len(process.connections()),
            'io_counters': process.io_counters()._asdict() if hasattr(process, 'io_counters') else None
        }
        
# Global health checker instance
health_checker = SystemHealthChecker()
