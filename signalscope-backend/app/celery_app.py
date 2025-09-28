"""
Celery Application for Background Task Processing
"""
from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import structlog

load_dotenv()

logger = structlog.get_logger()

# Create Celery app
app = Celery(
    'signalscope',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
)

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'tasks.process_realtime_batch': {'queue': 'realtime'},
        'tasks.process_standard_batch': {'queue': 'standard'},
        'tasks.process_archive_batch': {'queue': 'archive'},
        'tasks.generate_report': {'queue': 'reports'},
        'tasks.cleanup_old_messages': {'queue': 'maintenance'}
    },
    
    # Task time limits
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=2,
    worker_max_tasks_per_child=100,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Process realtime messages every 5 minutes
        'process-realtime-batch': {
            'task': 'tasks.process_realtime_batch',
            'schedule': 300.0,  # 5 minutes
            'options': {'queue': 'realtime'}
        },
        
        # Process standard messages every 15 minutes
        'process-standard-batch': {
            'task': 'tasks.process_standard_batch',
            'schedule': 900.0,  # 15 minutes
            'options': {'queue': 'standard'}
        },
        
        # Process archive messages every hour
        'process-archive-batch': {
            'task': 'tasks.process_archive_batch',
            'schedule': 3600.0,  # 1 hour
            'options': {'queue': 'archive'}
        },
        
        # Generate daily summary report at 9 AM UTC
        'daily-summary-report': {
            'task': 'tasks.generate_daily_report',
            'schedule': crontab(hour=9, minute=0),
            'options': {'queue': 'reports'}
        },
        
        # Cleanup old messages daily at 2 AM UTC
        'cleanup-old-messages': {
            'task': 'tasks.cleanup_old_messages',
            'schedule': crontab(hour=2, minute=0),
            'options': {'queue': 'maintenance'}
        }
    }
)

# Import tasks
from app.tasks import *

if __name__ == '__main__':
    app.start()