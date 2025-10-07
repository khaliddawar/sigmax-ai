"""
YouTube Transcript Ingestion API Routes
Handles Chrome extension requests for YouTube video processing
"""

from fastapi import APIRouter, HTTPException, Header, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Tuple, List
import hashlib
import json
import uuid
from datetime import datetime, timedelta
import redis
import logging
import gc
import psutil

from app.services.supabase_client import get_supabase_client
from app.middleware.auth_middleware import get_current_user
from app.services.file_storage import FileStorageService
from app.services.queue_service import queue_service
from app.services.quota_service import quota_service
from app.services.email_router import email_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["youtube"])

# Redis connection using environment configuration
import os
from dotenv import load_dotenv

load_dotenv()

# Import Redis configuration from settings
redis_client = None
try:
    import redis
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        logger.info(f"Connected to Redis: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
    else:
        logger.warning("REDIS_URL not found in environment variables")
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_client = None

class YouTubeIngestRequest(BaseModel):
    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    channel_name: str = Field(..., description="Channel name")
    duration: float = Field(..., description="Video duration in seconds")
    transcript: str = Field(..., description="Full video transcript")
    user_id: str = Field(..., description="User ID from extension")
    source: str = Field(default="chrome_extension", description="Source of the request")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class YouTubeIngestResponse(BaseModel):
    success: bool
    job_id: str
    message: str
    duplicate: bool = False
    estimated_tokens: int
    video_id: str
    data: Optional[Dict[str, Any]] = Field(default=None, description="Processing results and summary data")

# Use Redis for idempotency store if available, otherwise fallback to in-memory
idempotency_store: Dict[str, Dict] = {}

def store_idempotency_result(key: str, result: Dict[str, Any], ttl: int = 3600):
    """Store idempotency result in Redis or memory"""
    try:
        if redis_client:
            redis_client.setex(f"idempotency:{key}", ttl, json.dumps(result))
        else:
            idempotency_store[key] = result
    except Exception as e:
        logger.error(f"Failed to store idempotency result: {e}")
        idempotency_store[key] = result

def get_idempotency_result(key: str) -> Optional[Dict[str, Any]]:
    """Get idempotency result from Redis or memory"""
    try:
        if redis_client:
            result = redis_client.get(f"idempotency:{key}")
            return json.loads(result) if result else None
        else:
            return idempotency_store.get(key)
    except Exception as e:
        logger.error(f"Failed to get idempotency result: {e}")
        return idempotency_store.get(key)

def estimate_tokens(text: str) -> int:
    """
    Estimate tokens using the specified formula: len(text)/3.8*1.05
    This provides a pessimistic estimate for token usage.
    """
    return int((len(text) / 3.8) * 1.05)

def generate_idempotency_key(video_id: str, user_id: str, transcript_hash: str) -> str:
    """Generate a consistent idempotency key for the same video/user/transcript combination"""
    combined = f"{video_id}:{user_id}:{transcript_hash}"
    return hashlib.md5(combined.encode()).hexdigest()

def get_transcript_hash(transcript: str) -> str:
    """Generate a hash of the transcript content for duplicate detection"""
    return hashlib.sha256(transcript.encode()).hexdigest()[:16]

async def check_weekly_video_limit(user_id: str) -> bool:
    """
    Check if user has exceeded their video limit
    For free users: 10 videos total (lifetime)
    For premium/enterprise users: unlimited monthly
    """
    return await check_total_video_limit(user_id)

async def check_total_video_limit(user_id: str) -> bool:
    """
    Check if user has exceeded their video limit based on their plan
    - Free users: 10 videos total (lifetime)
    - Premium/Enterprise users: unlimited per month
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's plan and limits
        profile_resp = supabase.table("user_profiles").select("plan_type, plan_limits").eq("user_id", user_id).single().execute()
        plan_type = profile_resp.data.get("plan_type", "free") if profile_resp.data else "free"
        plan_limits = profile_resp.data.get("plan_limits", {}) if profile_resp.data else {}

        # Check if unlimited plan (premium/enterprise)
        if plan_type in ["premium", "enterprise"]:
            logger.info(f"User {user_id} has unlimited access ({plan_type} plan)")
            return True

        # For free users, check total video limit (lifetime)
        total_videos_limit = plan_limits.get("total_videos", 10)  # Default: 10 videos
        
        # Count all video_processing records for this user (lifetime)
        response = supabase.table("usage_ledger").select("id").eq("user_id", user_id).eq("resource_type", "video_processing").execute()
        
        total_videos_used = len(response.data) if response.data else 0
        
        logger.info(f"Free user {user_id} has used {total_videos_used}/{total_videos_limit} total videos")
        
        return total_videos_used < total_videos_limit
        
    except Exception as e:
        logger.error(f"Error checking total video limit for user {user_id}: {e}")
        return False  # Fail safe - deny access if we can't check

async def record_video_usage(user_id: str, video_id: str, estimated_tokens: int) -> bool:
    """
    Record video processing in usage ledger for weekly limit tracking
    """
    try:
        supabase = get_supabase_client()
        
        # Avoid duplicate entries for same video within the same week
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

        existing = supabase.table("usage_ledger")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("metadata->>video_id", video_id)\
            .gte("created_at", week_start.isoformat())\
            .limit(1).execute()

        if existing.data:
            logger.info(f"Usage for video {video_id} already recorded this week – skipping duplicate entry")
            return True

        response = supabase.table("usage_ledger").insert({
            "user_id": user_id,
            "resource_type": "video_processing",
            "amount": 1,
            "metadata": {
                "video_id": video_id,
                "estimated_tokens": estimated_tokens,
                "source": "youtube_extension"
            }
        }).execute()
        
        if response.data:
            logger.info(f"✅ Recorded video usage for user {user_id}, video {video_id}")
            return True
        else:
            logger.error(f"❌ Failed to record video usage: {response}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error recording video usage for user {user_id}: {e}")
        return False

async def check_quota_limits(user_id: str, estimated_tokens: int, video_duration: Optional[float] = None) -> Tuple[bool, str]:
    """
    Check if user can consume the estimated tokens
    """
    try:
        can_proceed, message, quota_info = await quota_service.check_quota_and_consume(
            user_id=user_id,
            estimated_tokens=estimated_tokens,
            video_duration=video_duration
        )
        
        return can_proceed, message
        
    except Exception as e:
        logger.error(f"Error checking quota for user {user_id}: {e}")
        return False, f"Quota check failed: {str(e)}"

async def save_transcript_to_storage(request: YouTubeIngestRequest, job_id: str) -> str:
    """Save transcript to file storage and return the storage path"""
    try:
        file_storage = FileStorageService()
        
        # Create transcript data
        transcript_data = {
            "video_id": request.video_id,
            "title": request.title,
            "channel_name": request.channel_name,
            "duration": request.duration,
            "transcript": request.transcript,
            "user_id": request.user_id,
            "source": request.source,
            "metadata": request.metadata or {},
            "job_id": job_id,
            "created_at": datetime.utcnow().isoformat(),
            "estimated_tokens": estimate_tokens(request.transcript)
        }
        
        # Save to storage
        filename = f"yt_transcript_{request.video_id}_{job_id}.json"
        storage_path = await file_storage.save_json(filename, transcript_data)
        
        logger.info(f"Transcript saved to storage: {storage_path}")
        return storage_path
        
    except Exception as e:
        logger.error(f"Failed to save transcript to storage: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")

async def queue_processing_job(request: YouTubeIngestRequest, job_id: str, transcript_id: str, storage_path: str, user_tier: str = "free", user_email: str = None) -> str:
    """
    Queue the transcript for processing using existing BPT ingestion pipeline
    """
    try:
        # Prepare transcript data for processing with YouTube-specific metadata
        transcript_data = {
            "video_id": request.video_id,
            "title": request.title,
            "channel_name": request.channel_name,
            "duration": request.duration,
            "transcript": request.transcript,
            "user_id": request.user_id,
            "storage_path": storage_path,
            "metadata": {
                **(request.metadata or {}),
                "source": "youtube_extension",
                "job_id": job_id,
                "user_tier": user_tier,
                "user_id": request.user_id,  # Ensure user_id is in metadata
                "user_email": user_email,    # Include authenticated user's email
                "video_url": f"https://youtube.com/watch?v={request.video_id}",
                "processing_type": "youtube_transcript"
            }
        }
        
        # Use the queue service to enqueue for processing
        if queue_service and queue_service.redis:
            queued_job_id = queue_service.enqueue_transcript_job(
                transcript_data=transcript_data,
                user_tier=user_tier,
                idempotency_key=None  # We handle idempotency at the API level
            )
            logger.info(f"Job {queued_job_id} queued for processing (user_tier: {user_tier})")
            return queued_job_id
        else:
            # Fallback: Process directly using ingestion service (for development/testing)
            logger.warning("Queue service not available, processing directly")
            from app.services.ingestion_service import IngestionService
            
            ingestion_service = IngestionService()
            
            # Process using the existing ingestion pipeline
            result = await ingestion_service.start_ingestion_pipeline_with_text(
                transcript_id=transcript_id,
                transcript_text=request.transcript,
                meeting_title=request.title,
                meeting_date=datetime.utcnow().isoformat(),
                metadata=transcript_data["metadata"]
            )
            
            if result.get("success"):
                logger.info(f"Direct processing completed for job {job_id}")
                return job_id
            else:
                raise Exception(f"Direct processing failed: {result.get('error')}")
        
    except Exception as e:
        logger.error(f"Failed to queue processing job: {e}")
        raise HTTPException(status_code=500, detail=f"Queue error: {str(e)}")

async def get_user_plan_from_database(user_id: str) -> tuple[str, dict]:
    """
    Get user plan and limits from the database user_profiles table.
    
    Returns:
        tuple: (plan_type, plan_limits)
    """
    try:
        supabase = get_supabase_client()
        
        # Get user profile from database
        response = supabase.table("user_profiles").select("plan_type, plan_limits").eq("user_id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            profile = response.data[0]
            plan_type = profile.get("plan_type", "free")
            plan_limits = profile.get("plan_limits", {})
            
            # Determine plan based on plan_limits tier if plan_type is inconsistent
            tier = plan_limits.get("tier", "free")
            if tier != "free" and plan_type == "free":
                logger.warning(f"Plan type inconsistency for user {user_id}: plan_type={plan_type}, tier={tier}. Using tier.")
                plan_type = tier
            
            logger.info(f"Retrieved user plan from database: {plan_type} (limits: {plan_limits})")
            return plan_type, plan_limits
        else:
            logger.warning(f"No user profile found for user {user_id}, defaulting to free plan")
            return "free", {}
            
    except Exception as e:
        logger.error(f"Error retrieving user plan from database: {e}")
        return "free", {}

# Add utility functions before the endpoint definitions
def calculate_tokens(text: str) -> int:
    """Calculate estimated tokens using the same formula as worker"""
    return int((len(text) / 3.8) * 1.05)

def get_transcript_hash(transcript: str) -> str:
    """Generate hash for transcript deduplication"""
    return hashlib.md5(transcript.encode()).hexdigest()[:16]

async def get_current_queue_depth() -> int:
    """Get current queue depth from Redis"""
    try:
        from app.services.queue_service import queue_service
        if queue_service and queue_service.redis:
            # Get approximate queue depth from Redis streams
            high_depth = queue_service.redis.xlen(queue_service.HIGH_PRIORITY_STREAM) or 0
            normal_depth = queue_service.redis.xlen(queue_service.NORMAL_STREAM) or 0
            return high_depth + normal_depth
    except Exception as e:
        logger.warning(f"Could not get queue depth: {e}")
    return 0

async def decide_processing_strategy(transcript_size_mb: float, estimated_tokens: int, user_plan: str, current_queue_depth: int) -> bool:
    """
    Decide whether to process directly in backend or queue to worker.
    
    Returns True for direct processing, False for worker queue.
    """
    # Memory-aware processing decision
    try:
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # Current backend memory in MB
    except:
        current_memory = 0
    
    # 🆕 CORRECTED Decision matrix for proper Redis/Worker usage:
    # 1. Backend memory pressure (> 1.5GB) -> Always queue to worker
    # 2. Large transcripts (> 10MB) -> Always queue to worker  
    # 3. Very high queue depth (> 20) -> Process directly (emergency overflow)
    # 4. Small transcripts (< 1MB) AND low queue (< 3) -> Direct processing (efficiency)
    # 5. Default: Queue to worker (proper architecture)
    
    if current_memory > 1500:  # Backend memory pressure
        logger.info(f"Backend memory pressure ({current_memory:.1f}MB), queuing to worker")
        return False
    
    if transcript_size_mb > 10:  # Very large transcripts
        logger.info(f"Large transcript ({transcript_size_mb:.1f}MB), queuing to worker")
        return False
    
    if current_queue_depth > 20:  # Emergency overflow only
        logger.info(f"EMERGENCY: Very high queue depth ({current_queue_depth}), processing directly to prevent system overload")
        return True
    
    if transcript_size_mb < 1.0 and current_queue_depth < 3:  # Efficiency for tiny transcripts
        logger.info(f"Small transcript ({transcript_size_mb:.1f}MB) with low queue ({current_queue_depth}), processing directly for efficiency")
        return True
    
    # 🎯 DEFAULT: Queue to worker (proper architecture)
    logger.info(f"Queuing to worker (size: {transcript_size_mb:.1f}MB, plan: {user_plan}, queue: {current_queue_depth}) - this is the correct flow!")
    return False

async def process_transcript_directly_in_backend(
    request: YouTubeIngestRequest, 
    transcript_id: str, 
    user_id: str, 
    user_email: str, 
    user_plan: str, 
    estimated_tokens: int
) -> Dict[str, Any]:
    """
    Process a transcript directly in the backend using the ingestion service.
    """
    logger.info(f"Starting direct backend processing for transcript {transcript_id}")
    
    try:
        from app.services.ingestion_service import IngestionService
        ingestion_service = IngestionService()
        
        # Prepare metadata for the pipeline
        pipeline_metadata = {
            "source": "youtube",
            "job_id": transcript_id.split('_')[-1],  # Extract job portion
            "video_url": f"https://youtube.com/watch?v={request.video_id}",
            "processing_type": "youtube_transcript",
            "channel_name": request.channel_name,
            "duration": request.duration,
            "user_id": user_id,
            "user_email": user_email,
            "user_plan": user_plan,
            "processing_location": "backend_direct",
            "ingestion_timestamp": datetime.utcnow().isoformat()
        }
        
        # Add any additional metadata from the request
        if request.metadata:
            pipeline_metadata.update(request.metadata)
        
        # Process using the existing ingestion pipeline
        result = await ingestion_service.start_ingestion_pipeline_with_text(
            transcript_id=transcript_id,
            transcript_text=request.transcript,
            meeting_title=request.title,
            meeting_date=datetime.utcnow().isoformat(),
            metadata=pipeline_metadata
        )
        
        # Extract processing details and summary
        processing_details = {
            "transcript_id": transcript_id,
            "chunks_created": result.get("chunk_count", 0),
            "embeddings_generated": result.get("embeddings_count", 0),
            "summary_generated": "generate_summary" in result.get("steps_completed", []),
            "processing_time": result.get("total_time", 0),
            "steps_completed": result.get("steps_completed", []),
            "summary": result.get("summary_html", ""),
            "processing_method": "backend_direct"
        }
        
        # Record usage for the user
        await record_video_usage(user_id, request.video_id, estimated_tokens)
        
        # Force garbage collection after direct processing
        gc.collect()
        
        logger.info(f"Direct backend processing completed for transcript {transcript_id}")
        return processing_details
        
    except Exception as e:
        logger.error(f"Error in direct backend processing: {e}")
        # Clean up on error
        gc.collect()
        raise

async def record_video_usage(user_id: str, video_id: str, tokens_used: int):
    """Record video processing usage for the user"""
    try:
        from app.services.quota_service import quota_service
        await quota_service.consume_quota(
            user_id=user_id,
            tokens_consumed=tokens_used,
            video_processed=True
        )
        logger.info(f"Recorded usage for user {user_id}: {tokens_used} tokens")
    except Exception as e:
        logger.warning(f"Failed to record usage: {e}")

@router.post("/yt_ingest", response_model=YouTubeIngestResponse)
async def ingest_youtube_transcript(
    request: YouTubeIngestRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: Dict = Depends(get_current_user)  # Now required, not optional
):
    """
    Ingest YouTube transcript from Chrome extension (requires authentication)
    
    Features:
    - User authentication required
    - Weekly video limit for free users
    - Quota validation and enforcement
    - Automatic email delivery to authenticated user
    - Idempotency key handling for duplicate requests
    - Token estimation using len(text)/3.8*1.05 formula
    - File storage for transcripts
    - Job queuing for processing
    - 🆕 Hybrid processing: small transcripts processed directly, large ones queued
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Generate transcript ID for database storage and summary fetching
        transcript_id = f"yt_{request.video_id}_{job_id[:8]}"
        
        # Use authenticated user's ID instead of request user_id
        user_id = current_user["id"]
        user_email = current_user["email"]
        
        # 🔧 FIXED: Get user plan from database instead of auth metadata
        user_plan, user_plan_limits = await get_user_plan_from_database(user_id)
        
        logger.info(f"Processing request for authenticated user: {user_email} (Plan: {user_plan})")
        
        # Check weekly video limit based on plan limits
        weekly_limit = user_plan_limits.get("weekly_videos", 1 if user_plan == "free" else 999)
        
        if weekly_limit < 999:  # Only check limit if not unlimited
            can_process_weekly = await check_weekly_video_limit(user_id)
            if not can_process_weekly:
                raise HTTPException(
                    status_code=402,
                    detail=f"Weekly video limit reached. You can process {weekly_limit} video(s) per week on the {user_plan} plan. Upgrade to Premium for unlimited videos."
                )
        
        # Calculate transcript hash for duplicate detection
        transcript_hash = get_transcript_hash(request.transcript)
        
        # Check for existing transcript with same hash
        from app.services.file_storage import FileStorageService
        storage_service = FileStorageService()
        existing_transcript = await storage_service.get_transcript_by_hash(transcript_hash)
        if existing_transcript:
            logger.info(f"Found existing transcript with hash {transcript_hash}, returning cached result")
            return YouTubeIngestResponse(
                success=True,
                job_id=job_id,
                message="Transcript already processed",
                duplicate=True,  # 🔧 FIXED: This is a duplicate/cached response
                estimated_tokens=existing_transcript.get("estimated_tokens", 0),
                video_id=request.video_id,  # 🔧 FIXED: Include required video_id field
                data=existing_transcript
            )
        
        # Calculate estimated tokens for processing cost
        estimated_tokens = estimate_tokens(request.transcript)
        logger.info(
            f"📏 Incoming transcript length: {len(request.transcript):,} chars  (est. {estimated_tokens:,} tokens)"
        )
        
        logger.info(f"Estimated tokens for transcript: {estimated_tokens}")
        
        # 🆕 SMART LOAD DISTRIBUTION: Decide processing strategy based on transcript size and system load
        transcript_size_mb = len(request.transcript) / 1024 / 1024
        
        should_process_directly = await decide_processing_strategy(
            transcript_size_mb=transcript_size_mb,
            estimated_tokens=estimated_tokens,
            user_plan=user_plan,
            current_queue_depth=await get_current_queue_depth()
        )
        
        if should_process_directly:
            logger.info(f"Processing transcript directly in backend (size: {transcript_size_mb:.1f}MB, tokens: {estimated_tokens})")
            
            # Process directly in backend to avoid worker memory pressure
            result = await process_transcript_directly_in_backend(
                request=request,
                transcript_id=transcript_id,
                user_id=user_id,
                user_email=user_email,
                user_plan=user_plan,
                estimated_tokens=estimated_tokens
            )
            
            # Return immediate response with summary
            return YouTubeIngestResponse(
                success=True,
                job_id=job_id,
                message="Transcript processed successfully (direct processing)",
                duplicate=False,
                estimated_tokens=estimated_tokens,
                video_id=request.video_id,  # 🔧 FIXED: Include required video_id field
                data=result
            )
        
        else:
            logger.info(f"Queuing transcript for worker processing (size: {transcript_size_mb:.1f}MB, tokens: {estimated_tokens})")
            
            # Use existing queue processing for larger transcripts
            queued_job_id = await queue_processing_job(
                request=request,
                job_id=job_id,
                transcript_id=transcript_id,
                storage_path="",  # Will be handled in queue
                user_tier=user_plan,
                user_email=user_email
            )
            
            return YouTubeIngestResponse(
                success=True,
                job_id=queued_job_id,
                message="Transcript queued for processing",
                duplicate=False,
                estimated_tokens=estimated_tokens,
                video_id=request.video_id,  # 🔧 FIXED: Include required video_id field
                data=None
            )
        
    except Exception as e:
        logger.error(f"Error in YouTube transcript ingestion: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def cleanup_old_idempotency_entries():
    """Clean up idempotency entries older than 24 hours"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        keys_to_remove = []
        
        for key, data in idempotency_store.items():
            created_at = datetime.fromisoformat(data["created_at"])
            if created_at < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del idempotency_store[key]
            
        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} old idempotency entries")
            
    except Exception as e:
        logger.error(f"Error cleaning up idempotency entries: {e}")

@router.get("/yt_job/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: Dict = Depends(get_current_user)  # Now required
):
    """
    Get the status of a YouTube processing job
    """
    try:
        # Get job status from queue service
        job_status = queue_service.get_job_status(job_id)
        
        if "error" in job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "job_id": job_id,
            "status": job_status.get("status", "unknown"),
            "created_at": job_status.get("created_at"),
            "updated_at": job_status.get("updated_at"),
            "result": job_status.get("result")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving job status: {str(e)}")

@router.get("/quota/{user_id}")
async def get_user_quota(
    user_id: str,
    current_user: Dict = Depends(get_current_user)  # Now required
):
    """
    Get user's quota information including limits, usage, and remaining quota
    """
    try:
        # Verify user can access this quota info (either their own or admin)
        if current_user and current_user.get("id") != user_id:
            # Check if user is admin (implement admin check as needed)
            if current_user.get("role") != "admin":
                raise HTTPException(status_code=403, detail="Access denied")
        
        quota_summary = await quota_service.get_quota_summary(user_id)
        
        if "error" in quota_summary:
            raise HTTPException(status_code=500, detail=quota_summary["error"])
        
        return quota_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quota for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving quota: {str(e)}")

@router.post("/yt_email_summary")
async def email_summary(
    request: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)  # Now required
):
    """
    Send a YouTube video summary via email with enhanced formatting
    """
    try:
        # Validate required fields - recipient_email is now optional, defaults to authenticated user's email
        if "video_id" not in request:
            raise HTTPException(status_code=400, detail="Missing required field: video_id")
        
        video_id = request["video_id"]
        recipient_email = request.get("recipient_email", current_user["email"])  # Default to authenticated user's email
        
        logger.info(f"Sending summary for video {video_id} to {recipient_email} (user: {current_user['email']})")
        
        # Prepare video data
        video_data = {
            "title": request.get("title", "YouTube Video"),
            "channel_name": request.get("channel_name", ""),
            "duration": request.get("duration", "Unknown"),  # Keep as string for email display
            "transcript_length": request.get("transcript_length", ""),
            "url": f"https://youtube.com/watch?v={video_id}",
            "video_id": video_id
        }
        
        # Get the transcript to generate a fresh JSON summary for enhanced email formatting
        transcript_text = request.get("transcript", "")
        summary_data = None
        
        if transcript_text:
            try:
                # Generate fresh JSON summary using the enhanced SummaryService
                from app.services.summary_service import SummaryService
                summary_service = SummaryService()
                
                logger.info("Generating fresh JSON summary for enhanced email formatting")
                summary_result = await summary_service.generate_session_summary(transcript_text)
                
                if summary_result.get("success"):
                    summary_data = summary_result.get("summary_data", {})
                    logger.info(f"Generated fresh summary with {len(summary_data)} sections")
                else:
                    logger.warning("Failed to generate fresh summary, falling back to provided summary")
                    
            except Exception as e:
                logger.warning(f"Error generating fresh summary: {e}, falling back to provided summary")
        
        # If we couldn't generate fresh summary data, use the provided summary as fallback
        if not summary_data:
            fallback_summary = request.get("summary", "")
            logger.info("Using provided summary as fallback")
            
            # If the fallback is HTML (old format), wrap it in the new structure
            if isinstance(fallback_summary, str) and fallback_summary.strip():
                # Check if it looks like HTML or plain text
                if "<" in fallback_summary or fallback_summary.count("\n") > 3:
                    # Treat as legacy HTML content
                    summary_data = {
                        "legacy_html": fallback_summary,
                        "key_takeaways": [],
                        "hero_numbers": [],
                        "step_by_step": [],
                        "notable_quotes": []
                    }
                    logger.info("Wrapped fallback summary in new JSON structure for enhanced email")
                else:
                    # Treat as plain text and put in legacy_html
                    summary_data = {
                        "legacy_html": f"<p>{fallback_summary}</p>",
                        "key_takeaways": [],
                        "hero_numbers": [],
                        "step_by_step": [],
                        "notable_quotes": []
                    }
            else:
                # No summary data available
                summary_data = {
                    "legacy_html": "<p>No summary available</p>",
                    "key_takeaways": [],
                    "hero_numbers": [],
                    "step_by_step": [],
                    "notable_quotes": []
                }
        
        # Email sending is handled by the ingestion pipeline, not here
        # This endpoint is now only for returning summary data to the frontend
        logger.info("Summary email will be sent by the ingestion pipeline, not this endpoint")
        
        # Return success without sending duplicate email
        return {
            "success": True,
            "message": f"Summary data prepared for {recipient_email} - email will be sent by ingestion pipeline",
            "video_id": video_id,
            "summary_type": "json" if isinstance(summary_data, dict) else "html",
            "summary_data": summary_data  # Return the summary data for frontend use
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending summary email: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending email: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for the YouTube ingestion service"""
    return {
        "service": "youtube_ingestion",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_client is not None,
        "idempotency_entries": len(idempotency_store),
        "email_services": email_router.get_service_status()
    }

@router.get("/yt_summary/{transcript_id}")
async def get_youtube_summary(transcript_id: str):
    """
    Public endpoint to fetch YouTube transcript summary (no authentication required)
    Used by Chrome extension to retrieve summaries after processing
    """
    try:
        logger.info(f"Fetching summary for transcript: {transcript_id}")
        
        from app.services.supabase_client import SupabaseService
        supabase_service = SupabaseService()
        
        if not supabase_service.is_connected():
            raise HTTPException(status_code=500, detail="Database service unavailable")
        
        # Add retry logic to handle database transaction timing
        max_retries = 5
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                transcript_data = await supabase_service.get_transcript_by_id(transcript_id)
                
                if transcript_data.get("success") and transcript_data.get("transcript"):
                    transcript_record = transcript_data["transcript"]
                    
                    # Check both summary fields
                    summary_content = transcript_record.get("detailed_summary") or transcript_record.get("summary")
                    
                    if summary_content:
                        logger.info(f"✅ Found summary for {transcript_id} (attempt {attempt + 1}): {len(summary_content)} chars")
                        return {
                            "success": True,
                            "transcript_id": transcript_id,
                            "summary": summary_content,
                            "title": transcript_record.get("title", ""),
                            "source": transcript_record.get("source", ""),
                            "created_at": transcript_record.get("created_at", "")
                        }
                    else:
                        logger.warning(f"⚠️ No summary content found for {transcript_id} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {retry_delay}s...")
                            import asyncio
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 1.5  # Increase delay
                            continue
                else:
                    logger.warning(f"⚠️ Transcript not found or unsuccessful: {transcript_data.get('error', 'Unknown error')} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 1.5
                        continue
                        
            except Exception as e:
                logger.error(f"❌ Error fetching transcript data (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
        
        # All retries failed
        logger.error(f"❌ Failed to retrieve summary after {max_retries} attempts")
        raise HTTPException(
            status_code=404, 
            detail=f"Summary not found for transcript {transcript_id} after {max_retries} attempts"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching summary for {transcript_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving summary: {str(e)}")

@router.post("/yt_test_ingest", response_model=YouTubeIngestResponse)
async def test_ingest_youtube_transcript(request: YouTubeIngestRequest):
    """
    Test endpoint for YouTube ingestion without authentication (for development/testing only)
    """
    try:
        logger.info(f"🧪 Test ingestion for video: {request.video_id}")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Estimate tokens
        estimated_tokens = estimate_tokens(request.transcript)
        logger.info(f"Estimated tokens: {estimated_tokens}")
        
        # Use the full BPT ingestion pipeline
        logger.info(f"🚀 Starting full BPT pipeline for job {job_id}")
        
        from app.services.ingestion_service import IngestionService
        
        ingestion_service = IngestionService()
        
        # Generate a unique transcript ID for YouTube content
        transcript_id = f"yt_{request.video_id}_{job_id[:8]}"
        
        # Prepare metadata for the pipeline
        pipeline_metadata = {
            "source": "youtube",  # Fixed: use database-allowed value
            "job_id": job_id,
            "video_url": f"https://youtube.com/watch?v={request.video_id}",
            "processing_type": "youtube_transcript",
            "channel_name": request.channel_name,
            "duration": request.duration,
            "user_id": request.user_id,
            "original_source": request.source,
            "ingestion_timestamp": datetime.utcnow().isoformat()
        }
        
        # 🔧 CRITICAL FIX: Add user_email to test endpoint metadata 
        # If user_id provided, try to look up user_email from database
        if request.user_id and request.user_id != 'extension_user':
            try:
                from app.services.supabase_client import get_supabase_client
                supabase = get_supabase_client()
                
                user_response = supabase.table("user_profiles").select("email").eq("user_id", request.user_id).execute()
                
                if user_response.data and len(user_response.data) > 0:
                    user_email = user_response.data[0]["email"]
                    pipeline_metadata["user_email"] = user_email
                    logger.info(f"🔧 Added user_email to test endpoint metadata: {user_email}")
                else:
                    logger.warning(f"🔧 No user found for user_id: {request.user_id}")
                    
            except Exception as e:
                logger.warning(f"🔧 Error looking up user email for test endpoint: {e}")
        else:
            logger.info(f"🔧 Test endpoint: No valid user_id provided ({request.user_id})")
        
        # Add any additional metadata from the request
        if request.metadata:
            pipeline_metadata.update(request.metadata)
        
        # Process using the existing BPT ingestion pipeline
        result = await ingestion_service.start_ingestion_pipeline_with_text(
            transcript_id=transcript_id,
            transcript_text=request.transcript,
            meeting_title=request.title,
            meeting_date=datetime.utcnow().isoformat(),
            metadata=pipeline_metadata
        )
        
        # -----------------------------------------------------------
        # 🆕  Prefer summary from pipeline result if available first
        # -----------------------------------------------------------
        summary_html = result.get("summary_html") if isinstance(result, dict) else None
        
        # If pipeline did not return summary_html, try database fetch
        if not summary_html and result.get("success"):
            logger.info("Pipeline did not return summary_html, falling back to DB fetch")
            
            # Add retry logic to handle database transaction timing issues
            max_retries = 3
            retry_delay = 0.5
            
            for attempt in range(max_retries):
                try:
                    from app.services.supabase_client import SupabaseService
                    supabase_service = SupabaseService()
                    if supabase_service.is_connected():
                        transcript_data = await supabase_service.get_transcript_by_id(transcript_id)
                        if transcript_data.get("success") and transcript_data.get("transcript"):
                            # Check both summary and detailed_summary fields
                            summary_html = transcript_data["transcript"].get("detailed_summary") or transcript_data["transcript"].get("summary")
                            if summary_html:
                                logger.info(f"Retrieved summary from database (attempt {attempt + 1}): {len(summary_html)} chars")
                                break
                            else:
                                logger.warning(f"No summary found in database for transcript {transcript_id} (attempt {attempt + 1})")
                        else:
                            logger.warning(f"Failed to get transcript data (attempt {attempt + 1}): {transcript_data}")
                except Exception as e:
                    logger.warning(f"Error retrieving summary from database (attempt {attempt + 1}): {e}")
                
                # Wait before retry (except on last attempt)
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        # Extract processing details from result
        processing_details = {
            "transcript_id": transcript_id,
            "chunks_created": result.get("chunk_count", 0),
            "embeddings_generated": result.get("embeddings_count", 0),
            "summary_generated": "generate_summary" in result.get("steps_completed", []),
            "processing_time": result.get("total_time", 0),
            "steps_completed": result.get("steps_completed", []),
            "summary": summary_html  # Include the actual summary
        }
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"YouTube transcript fully processed! Transcript ID: {transcript_id}. Pipeline completed: {', '.join(result.get('steps_completed', []))}",
            "duplicate": False,
            "estimated_tokens": estimated_tokens,
            "video_id": request.video_id,
            "data": processing_details  # Include processing details with summary
        }
        
    except Exception as e:
        logger.error(f"❌ Test ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"Test ingestion failed: {str(e)}") 

@router.post("/yt_worker_fallback", response_model=YouTubeIngestResponse)
async def worker_fallback_processing(
    job_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Fallback endpoint for when worker fails due to memory constraints.
    Processes the job directly in the backend.
    """
    try:
        job_id = job_data.get("job_id")
        transcript_data = job_data.get("transcript_data", {})
        
        logger.info(f"Worker fallback processing for job {job_id}")
        
        # Extract data from transcript_data
        video_id = transcript_data.get("video_id")
        transcript_text = transcript_data.get("transcript", "")
        title = transcript_data.get("title", "Unknown Title")
        
        if not transcript_text:
            raise HTTPException(status_code=400, detail="No transcript data in fallback request")
        
        # Generate new transcript ID for fallback processing
        transcript_id = f"yt_{video_id}_{job_id[:8]}_fallback"
        
        # Get user info
        user_id = current_user["id"]
        user_email = current_user["email"]
        
        # 🔧 FIXED: Get user plan from database instead of auth metadata
        user_plan, _ = await get_user_plan_from_database(user_id)
        
        # Calculate tokens
        estimated_tokens = calculate_tokens(transcript_text)
        
        # Create request object for processing
        from app.routes.youtube_routes import YouTubeIngestRequest
        fallback_request = YouTubeIngestRequest(
            video_id=video_id,
            title=title,
            transcript=transcript_text,
            channel_name=transcript_data.get("channel_name", ""),
            duration=transcript_data.get("duration", 0),
            source="worker_fallback",
            metadata=transcript_data.get("metadata", {})
        )
        
        # Process directly in backend
        result = await process_transcript_directly_in_backend(
            request=fallback_request,
            transcript_id=transcript_id,
            user_id=user_id,
            user_email=user_email,
            user_plan=user_plan,
            estimated_tokens=estimated_tokens
        )
        
        # Update original job status in queue to completed
        try:
            from app.services.queue_service import queue_service
            if queue_service:
                queue_service.update_job_status(job_id, "completed_fallback", {
                    **result,
                    "fallback_processed": True,
                    "original_worker_failed": True
                })
        except Exception as e:
            logger.warning(f"Could not update original job status: {e}")
        
        return YouTubeIngestResponse(
            success=True,
            job_id=job_id,
            message="Transcript processed successfully (worker fallback)",
            duplicate=False,
            estimated_tokens=estimated_tokens,
            video_id=video_id,  # 🔧 FIXED: Include required video_id field
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error in worker fallback processing: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Fallback processing failed: {str(e)}") 