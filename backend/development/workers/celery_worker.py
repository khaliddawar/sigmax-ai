#!/usr/bin/env python3
"""
Celery Worker for YouTube Transcript Processing
Run this script to start processing queued YouTube transcript jobs

Usage:
    python workers/celery_worker.py

Environment Variables:
    REDIS_HOST: Redis server host (default: localhost)
    REDIS_PORT: Redis server port (default: 6379)
    REDIS_PASSWORD: Redis password (optional)
    LOG_LEVEL: Logging level (default: INFO)
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.queue_service import celery_app
from app.settings import REDIS_HOST, REDIS_PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Start the Celery worker"""
    logger.info("Starting Celery worker for YouTube transcript processing")
    logger.info(f"Redis connection: {REDIS_HOST}:{REDIS_PORT}")
    
    # Start Celery worker
    # The worker will process both high and normal priority queues
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--queues=high,normal',
        '--concurrency=2',
        '--prefetch-multiplier=1'
    ])

if __name__ == "__main__":
    main() 