"""
Redis Queue Service for YouTube Transcript Processing
Handles job queuing, priority management, and Celery integration
"""
import redis
import json
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from celery import Celery
from app.settings import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB

logger = logging.getLogger(__name__)

# Redis connection - Use REDIS_URL if available, fallback to individual settings
redis_client = None
try:
    import os
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        logger.info(f"Queue service connected to Redis: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
    else:
        # Fallback to individual settings
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        logger.info(f"Queue service connected to Redis: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.error(f"Queue service failed to connect to Redis: {e}")
    redis_client = None

# Celery app configuration
celery_app = None
try:
    if redis_client:
        # Use the same Redis URL as the main connection
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            celery_app = Celery('yt_processor', broker=redis_url, backend=redis_url)
        else:
            celery_app = Celery(
                'yt_processor',
                broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
                backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
            )
        logger.info("Celery app configured with Redis backend")
    else:
        logger.warning("Celery app not configured - Redis not available")
except Exception as e:
    logger.error(f"Failed to configure Celery: {e}")
    celery_app = None

# Configure Celery routing - only if celery_app is available
if celery_app:
    celery_app.conf.update(
        task_routes={
            'app.services.queue_service.process_transcript_high': {'queue': 'high'},
            'app.services.queue_service.process_transcript_normal': {'queue': 'normal'},
        },
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    logger.info("Celery routing configuration applied")
else:
    logger.warning("Celery routing not configured - Redis not available")

class QueueService:
    """Service for managing YouTube transcript processing queue"""
    
    NORMAL_STREAM = "yt_ingest_stream"
    HIGH_PRIORITY_STREAM = "yt_ingest_high"
    CONSUMER_GROUP = "yt_processors"
    
    def __init__(self):
        self.redis = redis_client
        if self.redis:
            self._ensure_streams()
        else:
            logger.warning("QueueService initialized without Redis connection")
    
    def _ensure_streams(self):
        """Ensure Redis streams and consumer groups exist"""
        try:
            # Create streams if they don't exist
            for stream in [self.NORMAL_STREAM, self.HIGH_PRIORITY_STREAM]:
                try:
                    self.redis.xgroup_create(stream, self.CONSUMER_GROUP, id='0', mkstream=True)
                except redis.exceptions.ResponseError as e:
                    if "BUSYGROUP" not in str(e):
                        logger.error(f"Error creating consumer group for {stream}: {e}")
            
            logger.info("Redis streams and consumer groups initialized")
        except Exception as e:
            logger.error(f"Error initializing Redis streams: {e}")
    
    def enqueue_transcript_job(
        self, 
        transcript_data: Dict[str, Any], 
        user_tier: str = "free",
        idempotency_key: Optional[str] = None
    ) -> str:
        """
        Enqueue a transcript processing job
        
        Args:
            transcript_data: The transcript data to process
            user_tier: User subscription tier (free, pro, team)
            idempotency_key: Optional idempotency key for duplicate prevention
            
        Returns:
            job_id: Unique job identifier
            
        Raises:
            Exception: If Redis is not available for queue operations
        """
        if not self.redis:
            raise Exception("Redis queue is not available - cannot enqueue job")
            
        job_id = str(uuid.uuid4())
        
        # Check for duplicate job if idempotency key provided
        if idempotency_key:
            existing_job = self._check_existing_job(idempotency_key)
            if existing_job:
                logger.info(f"Duplicate job detected for key {idempotency_key}")
                return existing_job
        
        # Prepare job data
        job_data = {
            'job_id': job_id,
            'transcript_data': transcript_data,
            'user_tier': user_tier,
            'created_at': datetime.utcnow().isoformat(),
            'idempotency_key': idempotency_key,
            'status': 'queued'
        }
        
        try:
            # Determine priority and stream
            if user_tier in ['pro', 'team']:
                stream = self.HIGH_PRIORITY_STREAM
                # Use Celery for high priority if available
                if celery_app:
                    process_transcript_high.delay(job_data)
            else:
                stream = self.NORMAL_STREAM
                # Use Celery for normal priority if available
                if celery_app:
                    process_transcript_normal.delay(job_data)
            
            # Add to Redis stream for monitoring (serialize complex data)
            redis_job_data = {
                'job_id': job_data['job_id'] or '',
                'transcript_data': json.dumps(job_data['transcript_data']) if job_data['transcript_data'] else '{}',
                'user_tier': job_data['user_tier'] or 'free',
                'created_at': job_data['created_at'] or datetime.utcnow().isoformat(),
                'idempotency_key': job_data.get('idempotency_key') or '',
                'status': job_data['status'] or 'queued'
            }
            
            # Filter out any remaining None values to prevent Redis errors
            redis_job_data = {k: v for k, v in redis_job_data.items() if v is not None}
            
            self.redis.xadd(stream, redis_job_data)
            
            # Store job metadata for idempotency checking
            if idempotency_key:
                self._store_job_metadata(idempotency_key, job_id)
            
            logger.info(f"Enqueued job {job_id} to {stream}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error enqueuing job {job_id}: {e}")
            raise
    
    def _check_existing_job(self, idempotency_key: str) -> Optional[str]:
        """Check if a job with the given idempotency key already exists"""
        try:
            existing_job_id = self.redis.get(f"idempotency:{idempotency_key}")
            if existing_job_id:
                # Check if job is still valid (not older than 24 hours)
                job_data = self.redis.get(f"job:{existing_job_id}")
                if job_data:
                    return existing_job_id
            return None
        except Exception as e:
            logger.error(f"Error checking existing job: {e}")
            return None
    
    def _store_job_metadata(self, idempotency_key: str, job_id: str):
        """Store job metadata for idempotency checking"""
        try:
            # Store idempotency mapping (expires in 24 hours)
            self.redis.setex(f"idempotency:{idempotency_key}", 86400, job_id)
            
            # Store job metadata (expires in 24 hours)
            job_metadata = {
                'job_id': job_id,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'queued'
            }
            self.redis.setex(f"job:{job_id}", 86400, json.dumps(job_metadata))
            
        except Exception as e:
            logger.error(f"Error storing job metadata: {e}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a job"""
        if not self.redis:
            return {"error": "Redis queue is not available"}
            
        try:
            job_data = self.redis.get(f"job:{job_id}")
            if job_data:
                return json.loads(job_data)
            return {"error": "Job not found"}
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {"error": str(e)}
    
    def update_job_status(self, job_id: str, status: str, result: Optional[Dict] = None):
        """Update job status and result"""
        if not self.redis:
            logger.warning(f"Cannot update job status for {job_id} - Redis not available")
            return
            
        try:
            job_data = self.redis.get(f"job:{job_id}")
            if job_data:
                job_info = json.loads(job_data)
                job_info['status'] = status
                job_info['updated_at'] = datetime.utcnow().isoformat()
                if result:
                    job_info['result'] = result
                
                self.redis.setex(f"job:{job_id}", 86400, json.dumps(job_info))
                logger.info(f"Updated job {job_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating job status: {e}")

# Celery tasks - only define if celery_app is available
if celery_app:
    @celery_app.task(bind=True)
    def process_transcript_high(self, job_data: Dict[str, Any]):
        """High priority transcript processing task"""
        return _process_transcript_task(self, job_data, priority="high")

    @celery_app.task(bind=True)
    def process_transcript_normal(self, job_data: Dict[str, Any]):
        """Normal priority transcript processing task"""
        return _process_transcript_task(self, job_data, priority="normal")
else:
    # Dummy functions when Celery is not available
    def process_transcript_high(job_data: Dict[str, Any]):
        logger.warning("Celery not available - cannot process high priority task")
        return None
    
    def process_transcript_normal(job_data: Dict[str, Any]):
        logger.warning("Celery not available - cannot process normal priority task")
        return None

async def call_backend_fallback(job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Call backend fallback endpoint when worker memory is constrained.
    """
    import httpx
    import os
    
    job_id = job_data.get('job_id', 'unknown')
    logger.info(f"Calling backend fallback for job {job_id}")
    
    try:
        # Get backend URL from environment or use default
        backend_url = os.getenv('BACKEND_FALLBACK_URL', 'http://localhost:8000')  # In production, this would be the internal backend URL
        fallback_endpoint = f"{backend_url}/api/yt_worker_fallback"
        
        # Get user access token or use service account
        # In a worker context, we'd need a service-to-service auth mechanism
        service_token = os.getenv('SERVICE_TO_SERVICE_TOKEN')  # Service account token
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        if service_token:
            headers['Authorization'] = f'Bearer {service_token}'
        
        # Make async HTTP request to backend fallback
        async with httpx.AsyncClient(timeout=300) as client:  # 5 minute timeout for processing
            response = await client.post(
                fallback_endpoint,
                json=job_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Backend fallback successful for job {job_id}")
                return result.get('data', result)
            else:
                logger.error(f"Backend fallback failed for job {job_id}: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Error calling backend fallback for job {job_id}: {e}")
        return None

def _process_transcript_task(task_instance, job_data: Dict[str, Any], priority: str):
    """Common transcript processing logic with memory optimization"""
    job_id = job_data['job_id']
    queue_service = QueueService()
    
    # 🆕 Memory monitoring
    import psutil
    import gc
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    logger.info(f"Processing {priority} priority job {job_id} - Initial memory: {initial_memory:.1f}MB")
    
    try:
        # Update job status to processing
        queue_service.update_job_status(job_id, "processing")
        
        # Import here to avoid circular imports
        from app.services.ingestion_service import IngestionService
        from app.services.summary_service_v2 import SummaryServiceV2
        
        # Process the transcript
        transcript_data = job_data['transcript_data']
        transcript_text = transcript_data['transcript']
        
        # 🆕 Memory check: Skip processing if transcript is too large for current memory
        transcript_size_mb = len(transcript_text) / 1024 / 1024
        current_memory = process.memory_info().rss / 1024 / 1024
        if transcript_size_mb > 10 or current_memory > 350:  # 350MB threshold
            logger.warning(f"Transcript too large ({transcript_size_mb:.1f}MB) or memory too high ({current_memory:.1f}MB), calling backend fallback")
            
            # Call backend fallback endpoint instead of failing
            try:
                # Use asyncio to run the async function in sync context
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    fallback_result = loop.run_until_complete(call_backend_fallback(job_data))
                    if fallback_result:
                        queue_service.update_job_status(job_id, "completed_via_fallback", fallback_result)
                        return fallback_result
                    else:
                        # Fallback failed, mark as deferred
                        queue_service.update_job_status(job_id, "deferred_to_backend", {"reason": "memory_constraint_fallback_failed"})
                        return {"deferred": True, "reason": "memory_constraint_fallback_failed"}
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"Backend fallback failed: {e}")
                queue_service.update_job_status(job_id, "failed", {"error": f"Memory constraint and fallback failed: {str(e)}"})
                raise
        
        # Step 1: Ingest transcript (chunking, embeddings, storage) with memory optimization
        logger.info(f"Step 1: Starting ingestion for job {job_id}")
        ingestion_service = IngestionService()
        
        # 🆕 Use existing event loop if available to reduce memory
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Loop is closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            ingestion_result = loop.run_until_complete(
                ingestion_service.process_transcript_direct(
                    transcript_text=transcript_text,
                    video_id=transcript_data.get('video_id'),
                    title=transcript_data.get('title'),
                    metadata=transcript_data.get('metadata', {})
                )
            )
        finally:
            # 🆕 Clean up after ingestion
            if hasattr(ingestion_service, 'cleanup'):
                ingestion_service.cleanup()
            del ingestion_service
            gc.collect()
        
        # 🆕 Memory check after ingestion
        memory_after_ingestion = process.memory_info().rss / 1024 / 1024
        logger.info(f"Memory after ingestion: {memory_after_ingestion:.1f}MB")
        
        # Step 2: Generate summary with memory optimization
        logger.info(f"Step 2: Starting summary generation for job {job_id}")
        summary_service = SummaryServiceV2()
        
        try:
            summary_result = summary_service.generate_summary(
                transcript_text=transcript_text,
                video_metadata=transcript_data.get('metadata', {})
            )
        finally:
            # 🆕 Clean up after summary
            if hasattr(summary_service, 'cleanup'):
                summary_service.cleanup()
            del summary_service
            gc.collect()
        
        # 🆕 Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        logger.info(f"Final memory usage: {final_memory:.1f}MB (delta: +{final_memory - initial_memory:.1f}MB)")
        
        # Prepare result
        result = {
            'ingestion': ingestion_result,
            'summary': summary_result,
            'processed_at': datetime.utcnow().isoformat(),
            'memory_stats': {
                'initial_mb': initial_memory,
                'final_mb': final_memory,
                'peak_delta_mb': final_memory - initial_memory
            }
        }
        
        # Update job status to completed
        queue_service.update_job_status(job_id, "completed", result)
        
        # Consume quota after successful processing
        try:
            from app.services.quota_service import quota_service as quota_svc
            estimated_tokens = int((len(transcript_text) / 3.8) * 1.05)
            
            try:
                quota_result = loop.run_until_complete(quota_svc.consume_quota(
                    user_id=transcript_data.get('user_id'),
                    tokens_consumed=estimated_tokens,
                    video_processed=True
                ))
            finally:
                # 🆕 Close loop if we created it
                if loop != asyncio.get_event_loop():
                    loop.close()
            
            logger.info(f"Quota consumed for job {job_id}: {estimated_tokens} tokens")
        except Exception as e:
            logger.warning(f"Failed to consume quota for job {job_id}: {e}")
        
        logger.info(f"Successfully processed job {job_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        queue_service.update_job_status(job_id, "failed", {"error": str(e)})
        raise
    finally:
        # 🆕 Force garbage collection after each job
        gc.collect()

# Initialize queue service instance
queue_service = QueueService() 