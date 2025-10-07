#!/usr/bin/env python3
"""
Resource Monitoring Script for Simply YouTube Extension
Monitors backend and worker memory usage, queue depth, and processing metrics.
"""

import psutil
import redis
import requests
import time
import logging
from datetime import datetime
import os
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("resource-monitor")

class ResourceMonitor:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.backend_url = os.getenv('BACKEND_URL', 'https://simply-firy.onrender.com')
        
        # Connect to Redis
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_connected = True
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_connected = False
    
    def get_system_metrics(self):
        """Get current system resource metrics"""
        try:
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'memory': {
                    'total_mb': memory.total / 1024 / 1024,
                    'used_mb': memory.used / 1024 / 1024,
                    'available_mb': memory.available / 1024 / 1024,
                    'percent': memory.percent
                },
                'cpu_percent': cpu,
                'disk': {
                    'total_gb': disk.total / 1024 / 1024 / 1024,
                    'used_gb': disk.used / 1024 / 1024 / 1024,
                    'free_gb': disk.free / 1024 / 1024 / 1024,
                    'percent': (disk.used / disk.total) * 100
                }
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return None
    
    def get_queue_metrics(self):
        """Get Redis queue metrics"""
        if not self.redis_connected:
            return None
        
        try:
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'queues': {}
            }
            
            # Check different queue streams
            queue_names = ['yt_ingest_stream', 'yt_ingest_high']
            
            for queue_name in queue_names:
                try:
                    length = self.redis_client.xlen(queue_name)
                    metrics['queues'][queue_name] = {
                        'length': length,
                        'pending_jobs': length
                    }
                except Exception as e:
                    logger.warning(f"Could not get metrics for queue {queue_name}: {e}")
                    metrics['queues'][queue_name] = {'length': 0, 'error': str(e)}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting queue metrics: {e}")
            return None
    
    def check_backend_health(self):
        """Check backend service health and performance"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status_code': response.status_code,
                'response_time_ms': response_time * 1000,
                'healthy': response.status_code == 200,
                'response_data': response.json() if response.status_code == 200 else None
            }
            
        except Exception as e:
            logger.error(f"Backend health check failed: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'healthy': False,
                'error': str(e)
            }
    
    def analyze_memory_trends(self, metrics_history):
        """Analyze memory usage trends and provide recommendations"""
        if len(metrics_history) < 2:
            return None
        
        recent_metrics = metrics_history[-10:]  # Last 10 measurements
        memory_usage = [m['memory']['percent'] for m in recent_metrics if 'memory' in m]
        
        if not memory_usage:
            return None
        
        avg_memory = sum(memory_usage) / len(memory_usage)
        max_memory = max(memory_usage)
        
        recommendations = []
        
        if avg_memory > 80:
            recommendations.append("HIGH MEMORY USAGE: Consider upgrading instance size")
        elif avg_memory > 60:
            recommendations.append("MODERATE MEMORY USAGE: Monitor closely")
        
        if max_memory > 90:
            recommendations.append("CRITICAL: Memory spikes detected - check for memory leaks")
        
        return {
            'average_memory_percent': avg_memory,
            'max_memory_percent': max_memory,
            'recommendations': recommendations
        }
    
    def monitor_continuously(self, duration_minutes=60, interval_seconds=30):
        """Run continuous monitoring for specified duration"""
        logger.info(f"Starting continuous monitoring for {duration_minutes} minutes")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        metrics_history = []
        
        while time.time() < end_time:
            try:
                # Collect all metrics
                system_metrics = self.get_system_metrics()
                queue_metrics = self.get_queue_metrics()
                backend_health = self.check_backend_health()
                
                # Combine metrics
                combined_metrics = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'system': system_metrics,
                    'queues': queue_metrics,
                    'backend': backend_health
                }
                
                metrics_history.append(combined_metrics)
                
                # Log current status
                if system_metrics:
                    memory_percent = system_metrics['memory']['percent']
                    cpu_percent = system_metrics.get('cpu_percent', 0)
                    
                    logger.info(f"System Status - Memory: {memory_percent:.1f}%, CPU: {cpu_percent:.1f}%")
                
                if queue_metrics:
                    total_queue_length = sum(
                        q.get('length', 0) for q in queue_metrics['queues'].values() 
                        if isinstance(q, dict)
                    )
                    logger.info(f"Queue Status - Total pending jobs: {total_queue_length}")
                
                if backend_health:
                    status = "✅ Healthy" if backend_health['healthy'] else "❌ Unhealthy"
                    response_time = backend_health.get('response_time_ms', 0)
                    logger.info(f"Backend Status - {status}, Response time: {response_time:.0f}ms")
                
                # Analyze trends every 10 measurements
                if len(metrics_history) % 10 == 0:
                    trends = self.analyze_memory_trends(metrics_history)
                    if trends and trends['recommendations']:
                        logger.warning("Memory Analysis Recommendations:")
                        for rec in trends['recommendations']:
                            logger.warning(f"  - {rec}")
                
                # Wait before next measurement
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval_seconds)
        
        # Save metrics history
        self.save_metrics_report(metrics_history)
        
        return metrics_history
    
    def save_metrics_report(self, metrics_history):
        """Save metrics to a report file"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"resource_metrics_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(metrics_history, f, indent=2)
            
            logger.info(f"Metrics report saved to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save metrics report: {e}")

def main():
    """Main monitoring function"""
    monitor = ResourceMonitor()
    
    # Run monitoring
    try:
        # Monitor for 1 hour by default, check every 30 seconds
        monitor.monitor_continuously(duration_minutes=60, interval_seconds=30)
    except KeyboardInterrupt:
        logger.info("Monitoring stopped")

if __name__ == "__main__":
    main() 