#!/usr/bin/env python3
"""
Minimal Celery Worker for YouTube Transcript Processing
Only loads essential components - no web UI, templates, or email services

Usage:
    python development/workers/minimal_celery_worker.py

Environment Variables Required:
    REDIS_URL: Redis connection string
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY: Database access
    ANTHROPIC_API_KEY: For AI processing
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure minimal logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_minimal_celery_app():
    """Create Celery app with minimal dependencies"""
    from celery import Celery
    
    # Get Redis URL from environment
    redis_url = os.getenv('REDIS_URL')
    if not redis_url:
        logger.error("REDIS_URL environment variable not set")
        sys.exit(1)
    
    # Create minimal Celery app
    app = Celery('minimal_yt_processor', broker=redis_url, backend=redis_url)
    
    # Minimal configuration
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_routes={
            'transcript_processing.*': {'queue': 'normal'},
            'priority_transcript_processing.*': {'queue': 'high'},
        },
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_disable_rate_limits=False,
        task_compression='gzip',
        result_compression='gzip',
    )
    
    logger.info("✅ Minimal Celery app created successfully")
    return app

# Create the minimal app
celery_app = create_minimal_celery_app()

@celery_app.task(bind=True, name='app.services.queue_service.process_transcript_normal')
def process_transcript_normal(self, job_data):
    """Minimal transcript processing task - matches backend task name"""
    
    job_id = job_data.get('job_id', 'unknown')
    
    try:
        logger.info(f"🔄 Processing job: {job_id}")
        
        # Import only what we need, when we need it (same as original)
        import asyncio
        from app.services.ingestion_service import IngestionService
        from app.services.summary_service_v2 import SummaryServiceRouter
        
        # Extract transcript data from the job structure
        transcript_data = job_data.get('transcript_data', {})
        video_id = transcript_data.get('video_id')
        transcript_content = transcript_data.get('transcript', '')
        title = transcript_data.get('title', 'Unknown Title')
        metadata = transcript_data.get('metadata', {})
        
        if not video_id or not transcript_content:
            logger.error("Missing required job data: video_id or transcript content")
            return {'success': False, 'error': 'Missing required data'}
        
        logger.info(f"📝 Processing transcript for video: {video_id} ({len(transcript_content)} chars)")
        
        # Generate transcript_id using the same pattern as backend routes
        # This should match what the extension expects: yt_Tx008mYAqa4_e52dae78
        import uuid
        unique_id = str(uuid.uuid4())[:8]  # Generate 8-char ID like backend does
        transcript_id = f"yt_{video_id}_{unique_id}"
        
        logger.info(f"🆔 Generated transcript_id: {transcript_id}")
        
        # Step 1: Ingest transcript - pass transcript_id to ensure consistency  
        ingestion_service = IngestionService()
        
        # Run async method in Celery sync context (same as original)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Call the ingestion service with the correct transcript_id
        # We'll modify the call to pass the generated transcript_id
        ingestion_result = loop.run_until_complete(
            ingestion_service.process_transcript_direct(
                transcript_text=transcript_content,
                video_id=video_id,
                title=title,
                metadata=metadata
            )
        )
        
        # Override the transcript_id in the ingestion result to ensure consistency
        if isinstance(ingestion_result, dict):
            ingestion_result['transcript_id'] = transcript_id
        
        loop.close()
        
        # Step 2: Generate summary (corrected for async method and proper parameters)
        summary_service = SummaryServiceRouter()
        
        # Get duration from metadata or default to 0
        duration_seconds = int(metadata.get('duration', 0))
        
        # Call async generate_summary method in same loop pattern as ingestion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        summary_result = loop.run_until_complete(
            summary_service.generate_summary(
                transcript_id=transcript_id,  # Use our generated transcript_id
                transcript_text=transcript_content,
                duration_seconds=duration_seconds
            )
        )
        loop.close()
        
        # Step 3: Save transcript data directly to database with correct ID
        # Import Supabase adapter to save with our specific transcript_id
        from app.services.storage_adapters.supabase_adapter import SupabaseAdapter
        supabase = SupabaseAdapter()
        
        # Save transcript with our generated transcript_id
        save_result = supabase.save_transcript(
            transcript_id=transcript_id,
            video_id=video_id,
            title=title,
            content=transcript_content,
            summary=summary_result.get('summary', '') if isinstance(summary_result, dict) else '',
            detailed_summary=summary_result.get('detailed_summary', '') if isinstance(summary_result, dict) else ''
        )
        
        # Prepare result (same as original)
        from datetime import datetime
        result = {
            'ingestion': ingestion_result,
            'summary': summary_result,
            'save': save_result,
            'transcript_id': transcript_id,  # Include the generated transcript_id
            'processed_at': datetime.utcnow().isoformat()
        }
        
        # Check if save was successful
        if isinstance(save_result, dict) and save_result.get('success'):
            logger.info(f"✅ Job completed successfully: {transcript_id}")
            return result
        else:
            logger.error(f"❌ Database save failed for {transcript_id}: {save_result}")
            return {'success': False, 'error': 'Database save failed', 'transcript_id': transcript_id}
            
    except Exception as e:
        logger.error(f"❌ Job processing failed: {str(e)}")
        return {'success': False, 'error': str(e)}

@celery_app.task(bind=True, name='app.services.queue_service.process_transcript_high')  
def process_transcript_high(self, job_data):
    """High priority transcript processing - same logic as normal"""
    return process_transcript_normal(self, job_data)

def main():
    """Start the minimal Celery worker"""
    logger.info("🚀 Starting minimal Celery worker for YouTube transcript processing")
    
    # Verify environment variables
    required_vars = ['REDIS_URL', 'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("✅ All required environment variables present")
    
    # Start worker with minimal configuration
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--queues=high,normal',
        '--concurrency=1',  # Reduced concurrency to save memory
        '--prefetch-multiplier=1',
        '--max-memory-per-child=200000'  # Restart worker after 200MB
    ])

if __name__ == "__main__":
    main() 