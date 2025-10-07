# Load environment variables first
from app import settings

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import logging
import httpx
import uuid
import os
import traceback
import json
from datetime import datetime, timezone
import sys
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
import signal
import uvicorn

from app.models.transcript import FirefliesWebhookPayload, ProcessedTranscript, TranscriptMetadata
from app.services.transcript_processor import TranscriptProcessor
from app.services.supabase_client import SupabaseService, get_supabase_client
from app.services.embedding_service import EmbeddingService
from app.services.semantic_chunks_service import SemanticChunksService
from app.services.auth_service import AuthService
from app.routes import api_router  # Import the combined router
from app.middleware.security_middleware import setup_security_middleware, security_exception_handler
from app.settings import get_settings
from typing import Optional, Dict, Any, List

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bpt-api")

# Import observability components
try:
    from app.middleware.observability_middleware import (
        observability_middleware, 
        circuit_breaker_middleware,
        get_health_status,
        get_metrics,
        get_prometheus_metrics
    )
    from app.utils.structured_logging import get_logger
    OBSERVABILITY_AVAILABLE = True
    structured_logger = get_logger("bpt-api", "main")
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    structured_logger = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with proper dependency injection"""
    logger.info("Starting BPT Pipeline API")
    
    # Initialize dependency container
    from app.services.dependency_container import get_application_container
    container = await get_application_container()
    
    # Verify core services are working
    try:
        supabase_service = await container.get("supabase_service")
        connection_check = supabase_service.check_connection()
        if connection_check.get("success"):
            logger.info("✅ Supabase connection verified")
        else:
            logger.warning(f"⚠️ Supabase connection issue: {connection_check}")
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise
    
    # 🔧 DEBUG: Initialize queue service to check Redis connection
    try:
        from app.services.queue_service import queue_service, redis_client
        if redis_client:
            redis_client.ping()
            logger.info("✅ Queue service Redis connection verified")
        else:
            logger.error("❌ Queue service Redis client is None")
    except Exception as e:
        logger.error(f"❌ Queue service Redis connection failed: {e}")
    
    yield
    
    logger.info("Shutting down BPT Pipeline API")
    
    # Cleanup all services through dependency container
    try:
        await cleanup_application_container()
        logger.info("✅ All services cleaned up successfully")
    except Exception as e:
        logger.warning(f"Error during service cleanup: {e}")
    
    logger.info("✅ Application shutdown completed")

# Create FastAPI app with security-focused configuration
app = FastAPI(
    title="BPT Pipeline API",
    description="Bullish/Bearish/Pullback Trader Pipeline with YouTube Extension Support",
    version="1.0.0",
    lifespan=lifespan,
    # Security headers
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") == "development" else None,
)

# Setup comprehensive security middleware
setup_security_middleware(app)

# Add observability middleware if available
if OBSERVABILITY_AVAILABLE:
    app.middleware("http")(observability_middleware)
    app.middleware("http")(circuit_breaker_middleware)

# Register body size limit middleware (5MB)
from app.middleware.body_size_limit import BodySizeLimitMiddleware
app.add_middleware(BodySizeLimitMiddleware, max_body_size=5*1024*1024)

from app.services.dependency_container import cleanup_application_container  

# Include all API routes with /api prefix
app.include_router(api_router, prefix="/api")

# ---------------------------------------------------------------------------
# Expose Paddle webhook endpoint at root (no /api prefix) to match Paddle's
# configured webhook URL `/payments/notifications`. The existing handler lives
# in `app.routes.payment_routes` as `handle_paddle_notification`, but that
# route is namespaced under `/api`. Here we expose the SAME handler directly
# so that incoming Paddle webhooks (which cannot easily be changed to include
# the `/api` prefix) are processed correctly without altering other payment
# routes.
# ---------------------------------------------------------------------------
from app.routes.payment_routes import handle_paddle_notification as paddle_webhook_handler
app.add_api_route(
    "/payments/notifications",
    paddle_webhook_handler,
    methods=["POST"],
    include_in_schema=False,
)

@app.get("/")
def read_root():
    return {"message": "BPT API is running with Enhanced RAG System!"}

async def process_transcript_background(payload: Dict[str, Any]):
    """
    Process a transcript in the background
    This includes:
    - Downloading the transcript
    - Chunking the text
    - Generating embeddings
    - Storing in the database
    - Generating summary
    - Extracting trades
    - Sending email to subscribers
    """
    try:
        logger.info(f"Starting background processing for transcript ID: {payload.get('transcript_id')}")
        
        # Extract data from payload
        transcript_id = payload.get("transcript_id")
        transcript_url = payload.get("transcript_url")
        meeting_title = payload.get("title")
        meeting_date = payload.get("created_at") or payload.get("date")
        
        if not transcript_id or not transcript_url:
            logger.error("Missing required fields in payload")
            return
            
        # Extract metadata from payload
        metadata = {}
        if "metadata" in payload and isinstance(payload["metadata"], dict):
            metadata = payload["metadata"]
        else:
            # Try to extract common fields into metadata
            for field in ["meeting_id", "organizer_email", "duration_seconds", "word_count", "participants"]:
                if field in payload:
                    metadata[field] = payload[field]
        
        # Import the ingestion service
        from app.services.ingestion_service import IngestionService
        
        # Fix timestamp handling - convert Unix timestamp to ISO format if needed
        corrected_meeting_date = meeting_date
        if meeting_date:
            try:
                # Check if it's a Unix timestamp (string of digits)
                if isinstance(meeting_date, str) and meeting_date.isdigit():
                    # Convert from milliseconds to seconds if needed
                    timestamp = int(meeting_date)
                    if timestamp > 1e10:  # Likely milliseconds
                        timestamp = timestamp / 1000
                    
                    # Validate timestamp is reasonable (between 1970 and 2050 to be safer)
                    min_timestamp = 0  # 1970-01-01
                    max_timestamp = 2524608000  # 2050-01-01 (safer than 2100)
                    
                    if timestamp < min_timestamp or timestamp > max_timestamp:
                        logger.warning(f"Invalid timestamp {timestamp} (outside 1970-2050 range), using current time")
                        corrected_meeting_date = datetime.now(timezone.utc).isoformat()
                    else:
                        # Convert to datetime and then ISO format with better error handling
                        try:
                            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                            corrected_meeting_date = dt.isoformat()
                            logger.info(f"Converted timestamp {timestamp} to date: {corrected_meeting_date}")
                        except (ValueError, OSError) as e:
                            logger.warning(f"Failed to convert timestamp {timestamp}: {e}, using current time")
                            corrected_meeting_date = datetime.now(timezone.utc).isoformat()
                elif isinstance(meeting_date, str):
                    # Try to parse as ISO string directly
                    try:
                        parsed_dt = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
                        # Ensure it's in UTC and properly formatted
                        if parsed_dt.tzinfo is None:
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        corrected_meeting_date = parsed_dt.isoformat()
                        logger.info(f"Parsed ISO date: {corrected_meeting_date}")
                    except ValueError as e:
                        logger.warning(f"Could not parse ISO date '{meeting_date}': {e}, using current time")
                        corrected_meeting_date = datetime.now(timezone.utc).isoformat()
                else:
                    logger.warning(f"Unexpected date format: {type(meeting_date)}, using current time")
                    corrected_meeting_date = datetime.now(timezone.utc).isoformat()
            except (ValueError, TypeError, OSError) as e:
                logger.warning(f"Could not parse date '{meeting_date}': {e}, using current time")
                corrected_meeting_date = datetime.now(timezone.utc).isoformat()
        else:
            corrected_meeting_date = datetime.now(timezone.utc).isoformat()
        
        # Start the complete ingestion pipeline with the CORRECTED timestamp
        ingestion_service = IngestionService()
        result = await ingestion_service.start_ingestion_pipeline_with_text(
            transcript_id=transcript_id,
            transcript_text=payload.get("transcript_text", ""),
            meeting_title=meeting_title,
            meeting_date=corrected_meeting_date,  # Use corrected timestamp
            metadata=metadata
        )
        
        if result["success"]:
            logger.info(f"Ingestion pipeline completed successfully for transcript ID: {transcript_id}")
            logger.info(f"Pipeline summary: {len(result.get('steps_completed', []))} steps completed in {result.get('total_time', 0):.2f} seconds")
        else:
            logger.error(f"Ingestion pipeline failed for transcript ID: {transcript_id}")
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")
        logger.error(traceback.format_exc())

@app.post("/webhook/fireflies")
async def fireflies_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Enhanced Fireflies webhook handler with security validation.
    
    Based on insights from Firefly III webhook implementation:
    - Timestamp extraction from signature headers
    - Comprehensive security validation
    - Detailed logging for debugging
    - No fallback arrangements - explicit failures only
    """
    try:
        # Get raw request body for signature validation
        raw_body = await request.body()
        raw_body_str = raw_body.decode('utf-8')
        
        # Parse JSON payload
        try:
            payload = json.loads(raw_body_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        logger.info(f"Received Fireflies webhook with keys: {list(payload.keys())}")
        
        # Enhanced header logging for debugging
        headers_info = {
            "content-type": request.headers.get("content-type"),
            "user-agent": request.headers.get("user-agent"),
            "x-hub-signature": request.headers.get("x-hub-signature"),
            "x-hub-signature-256": request.headers.get("x-hub-signature-256"),
            "signature": request.headers.get("signature"),
            "x-fireflies-signature": request.headers.get("x-fireflies-signature"),
        }
        logger.info(f"Webhook headers: {headers_info}")
        
        # Initialize webhook timestamp variables
        webhook_received_at = datetime.now(timezone.utc)
        signature_timestamp = None
        
        # Enhanced signature validation with timestamp extraction
        webhook_secret = os.getenv("FIREFLIES_WEBHOOK_SECRET")
        if os.getenv("WEBHOOK_VERIFY_SIGNATURES", "false").lower() == "true":
            if not webhook_secret:
                logger.error("Webhook signature verification enabled but FIREFLIES_WEBHOOK_SECRET not set")
                raise HTTPException(status_code=500, detail="Webhook signature verification misconfigured")
            
            # Import the new security service
            from app.services.webhook_security import create_webhook_validator
            
            validator = create_webhook_validator(webhook_secret)
            if not validator:
                logger.error("Failed to create webhook validator")
                raise HTTPException(status_code=500, detail="Webhook validation setup failed")
            
            # Try multiple signature header formats
            signature_headers = [
                request.headers.get("signature"),  # Firefly III style
                request.headers.get("x-hub-signature-256"),  # GitHub style
                request.headers.get("x-hub-signature"),  # GitHub legacy
                request.headers.get("x-fireflies-signature"),  # Fireflies custom (if exists)
            ]
            
            validation_result = None
            for sig_header in signature_headers:
                if sig_header:
                    logger.info(f"Attempting signature validation with header: {sig_header[:20]}...")
                    validation_result = validator.validate_signature(sig_header, raw_body_str)
                    
                    if validation_result["valid"]:
                        logger.info("Signature validation successful")
                        # Extract timestamp from signature if available
                        signature_timestamp = validator.get_webhook_timestamp(sig_header)
                        if signature_timestamp:
                            logger.info(f"Extracted timestamp from signature: {signature_timestamp}")
                        break
                    else:
                        logger.warning(f"Signature validation failed: {validation_result['error']}")
            
            if not validation_result or not validation_result["valid"]:
                logger.error("All signature validation attempts failed")
                logger.error(f"Available headers: {[h for h in signature_headers if h]}")
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Check if this is a test payload with transcript_text included
        is_test_payload = payload.get("transcript_text") is not None or request.headers.get("X-Test-Upload") == "true"
        
        if is_test_payload:
            # Handle test payload with direct transcript text
            transcript_id = payload.get("transcript_id") or payload.get("meetingId")
            if not transcript_id:
                logger.error("Missing transcript_id or meetingId in test payload")
                raise HTTPException(status_code=400, detail="Missing transcript_id or meetingId field")
            
            logger.info(f"Processing test webhook payload - Transcript ID: {transcript_id}")
            
            # Process directly with the included transcript text
            background_tasks.add_task(process_transcript_background, payload)
            
            return {
                "status": "success",
                "message": "Test webhook received and processing started",
                "transcript_id": transcript_id,
                "processing": "background",
                "webhook_received_at": webhook_received_at.isoformat(),
                "signature_timestamp": signature_timestamp.isoformat() if signature_timestamp else None
            }
        
        # Handle actual Fireflies webhook format
        meeting_id = payload.get("meetingId")
        event_type = payload.get("eventType")
        client_reference_id = payload.get("clientReferenceId")
        
        # Validate required fields for actual Fireflies webhook
        if not meeting_id:
            logger.error("Missing meetingId in webhook payload")
            raise HTTPException(status_code=400, detail="Missing meetingId field")
        
        if not event_type:
            logger.error("Missing eventType in webhook payload") 
            raise HTTPException(status_code=400, detail="Missing eventType field")
        
        logger.info(f"Processing Fireflies webhook - Meeting ID: {meeting_id}, Event: {event_type}")
        
        # Check if this is a transcription completion event
        if event_type != "Transcription completed":
            logger.info(f"Ignoring event type: {event_type} (not a transcription completion)")
            return {
                "status": "success",
                "message": f"Event {event_type} acknowledged but not processed",
                "meeting_id": meeting_id,
                "webhook_received_at": webhook_received_at.isoformat(),
                "signature_timestamp": signature_timestamp.isoformat() if signature_timestamp else None
            }
        
        # Create a normalized payload for our internal processing
        normalized_payload = {
            "transcript_id": meeting_id,  # Use meetingId as transcript_id
            "meeting_id": meeting_id,
            "event_type": event_type,
            "client_reference_id": client_reference_id,
            "raw_json": raw_body_str,
            "source": "fireflies",
            "webhook_received_at": webhook_received_at.isoformat(),
            "signature_timestamp": signature_timestamp.isoformat() if signature_timestamp else None
        }
        
        # Check if there's a FIREFLIES_API_KEY to fetch transcript data
        fireflies_api_key = os.getenv("FIREFLIES_API_KEY")
        if fireflies_api_key:
            # Add task to fetch transcript data from Fireflies API and then process
            background_tasks.add_task(process_fireflies_webhook_background, normalized_payload)
        else:
            logger.error("No FIREFLIES_API_KEY found - cannot fetch transcript data from Fireflies API")
            logger.error("To enable full processing, set FIREFLIES_API_KEY environment variable")
            
            # Explicit failure - no fallback arrangements
            raise HTTPException(
                status_code=500, 
                detail="Fireflies API key not configured - cannot process webhook"
            )
        
        # Return immediate success response with enhanced timestamp information
        return {
            "status": "success", 
            "message": "Webhook received and processing started",
            "meeting_id": meeting_id,
            "event_type": event_type,
            "webhook_received_at": webhook_received_at.isoformat(),
            "signature_timestamp": signature_timestamp.isoformat() if signature_timestamp else None,
            "timestamp_source": "signature_header" if signature_timestamp else "server_generated"
        }
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/process-transcript")
async def test_process_transcript(request: Request, background_tasks: BackgroundTasks):
    """
    Test endpoint for direct transcript processing.
    
    This endpoint bypasses the webhook and directly processes a transcript
    with the provided text. Useful for testing the anti-hallucination system
    with local test files.
    """
    try:
        # Parse the payload
        payload = await request.json()
        logger.info(f"Received test transcript processing request with keys: {list(payload.keys())}")
        
        # Validate required fields
        transcript_id = payload.get("transcript_id")
        transcript_text = payload.get("transcript_text")
        
        if not transcript_id:
            raise HTTPException(status_code=400, detail="Missing transcript_id field")
        
        if not transcript_text:
            raise HTTPException(status_code=400, detail="Missing transcript_text field")
        
        logger.info(f"Processing test transcript - ID: {transcript_id}")
        logger.info(f"Transcript length: {len(transcript_text)} characters")
        
        # Add background task for processing
        background_tasks.add_task(process_transcript_background, payload)
        
        # Return immediate success response
        return {
            "status": "success",
            "message": "Test transcript received and processing started",
            "transcript_id": transcript_id,
            "processing": "background"
        }
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing test transcript: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test/webhook-signature")
async def test_webhook_signature(request: Request):
    """
    Test endpoint for webhook signature validation.
    
    Based on Firefly III webhook repository patterns:
    https://github.com/akyrey/firefly-iii-webhooks
    
    This endpoint allows testing our webhook signature validation
    with various signature formats and payloads.
    """
    try:
        # Get raw request body
        raw_body = await request.body()
        raw_body_str = raw_body.decode('utf-8')
        
        # Parse JSON payload
        try:
            payload = json.loads(raw_body_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        logger.info(f"Testing webhook signature validation with payload: {payload}")
        
        # Get webhook secret from environment or payload
        webhook_secret = payload.get("webhook_secret") or os.getenv("FIREFLIES_WEBHOOK_SECRET", "abcdef")
        
        # Collect all signature headers
        signature_headers = {
            "signature": request.headers.get("signature"),
            "x-hub-signature": request.headers.get("x-hub-signature"),
            "x-hub-signature-256": request.headers.get("x-hub-signature-256"),
            "x-fireflies-signature": request.headers.get("x-fireflies-signature"),
        }
        
        logger.info(f"Received signature headers: {signature_headers}")
        
        # Import webhook security validator
        from app.services.webhook_security import create_webhook_validator
        
        validator = create_webhook_validator(webhook_secret)
        if not validator:
            raise HTTPException(status_code=500, detail="Failed to create webhook validator")
        
        # Test each signature header
        validation_results = {}
        signature_timestamp = None
        
        for header_name, header_value in signature_headers.items():
            if header_value:
                logger.info(f"Testing signature header '{header_name}': {header_value[:30]}...")
                
                result = validator.validate_signature(header_value, raw_body_str)
                validation_results[header_name] = result
                
                # Extract timestamp if available and valid
                if result["valid"] and not signature_timestamp:
                    signature_timestamp = validator.get_webhook_timestamp(header_value)
        
        # Generate test signatures for comparison
        from app.utils.webhook_test_utils import generate_firefly_signature, generate_github_signature
        
        test_signatures = {
            "firefly_style": generate_firefly_signature(raw_body_str, webhook_secret),
            "github_style": generate_github_signature(raw_body_str, webhook_secret)
        }
        
        # Determine overall validation status
        any_valid = any(result["valid"] for result in validation_results.values())
        
        response = {
            "status": "success" if any_valid else "validation_failed",
            "message": "Webhook signature validation test completed",
            "payload_received": payload,
            "webhook_secret_used": webhook_secret[:6] + "..." if len(webhook_secret) > 6 else webhook_secret,
            "signature_headers_received": {k: v[:30] + "..." if v and len(v) > 30 else v for k, v in signature_headers.items()},
            "validation_results": validation_results,
            "test_signatures_generated": test_signatures,
            "signature_timestamp": signature_timestamp.isoformat() if signature_timestamp else None,
            "overall_valid": any_valid,
            "webhook_received_at": datetime.now(timezone.utc).isoformat()
        }
        
        if any_valid:
            logger.info("✅ Webhook signature validation test PASSED")
        else:
            logger.warning("❌ Webhook signature validation test FAILED")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in webhook signature test: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

async def process_fireflies_webhook_background(payload: Dict[str, Any]):
    """
    Process a Fireflies webhook in the background by fetching transcript data
    and then running the appropriate processing pipeline.
    
    NEW: Supports unified transcript handler for dual Q&A + Email processing
    """
    try:
        meeting_id = payload.get("meeting_id")
        logger.info(f"Starting Fireflies webhook background processing for meeting ID: {meeting_id}")
        
        # Feature flag for new unified processing (default: False for safety)
        use_unified_handler = os.getenv("USE_UNIFIED_TRANSCRIPT_HANDLER", "false").lower() == "true"
        
        # Import Fireflies API client (we'll need to create this)
        try:
            from app.services.fireflies_client import FirefliesClient
            
            fireflies_client = FirefliesClient()
            
            # Fetch transcript data from Fireflies
            transcript_data = await fireflies_client.get_transcript_by_meeting_id(meeting_id)
            
            if not transcript_data or not transcript_data.get("success"):
                logger.error(f"Failed to fetch transcript data from Fireflies for meeting {meeting_id}")
                return
            
            # Extract the transcript info
            transcript_info = transcript_data.get("data", {})
            transcript_text = transcript_info.get("transcript_text", "")
            
            if not transcript_text:
                logger.error(f"No transcript text found for meeting {meeting_id}")
                return
            
            # Store transcript in database first (for unified handler to retrieve)
            metadata = {
                "source": "fireflies",
                "meeting_id": meeting_id,
                "organizer_email": transcript_info.get("organizer_email", ""),
                "duration": transcript_info.get("duration", 0),
                "participants": transcript_info.get("participants", []),
                "speakers": transcript_info.get("speakers", []),
                "original_payload": payload,
                "word_count": len(transcript_text.split()),
                "received_at": datetime.now().isoformat()
            }
            
            title = transcript_info.get("title", f"Fireflies Transcript {meeting_id}")
            raw_date = transcript_info.get("date", "")
            
            # Fix timestamp handling - convert Unix timestamp to ISO format if needed
            created_at = ""
            if raw_date:
                try:
                    # Check if it's a Unix timestamp (string of digits)
                    if isinstance(raw_date, str) and raw_date.isdigit():
                        # Convert from milliseconds to seconds if needed
                        timestamp = int(raw_date)
                        if timestamp > 1e10:  # Likely milliseconds
                            timestamp = timestamp / 1000
                        
                        # Validate timestamp is reasonable (between 1970 and 2050 to be safer)
                        min_timestamp = 0  # 1970-01-01
                        max_timestamp = 2524608000  # 2050-01-01 (safer than 2100)
                        
                        if timestamp < min_timestamp or timestamp > max_timestamp:
                            logger.warning(f"Invalid timestamp {timestamp} (outside 1970-2050 range), using current time")
                            created_at = datetime.now(timezone.utc).isoformat()
                        else:
                            # Convert to datetime and then ISO format with better error handling
                            try:
                                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                                created_at = dt.isoformat()
                                logger.info(f"Converted timestamp {timestamp} to date: {created_at}")
                            except (ValueError, OSError) as e:
                                logger.warning(f"Failed to convert timestamp {timestamp}: {e}, using current time")
                                created_at = datetime.now(timezone.utc).isoformat()
                    elif isinstance(raw_date, str):
                        # Try to parse as ISO string directly
                        try:
                            parsed_dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                            # Ensure it's in UTC and properly formatted
                            if parsed_dt.tzinfo is None:
                                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                            created_at = parsed_dt.isoformat()
                            logger.info(f"Parsed ISO date: {created_at}")
                        except ValueError as e:
                            logger.warning(f"Could not parse ISO date '{raw_date}': {e}, using current time")
                            created_at = datetime.now(timezone.utc).isoformat()
                    else:
                        logger.warning(f"Unexpected date format: {type(raw_date)}, using current time")
                        created_at = datetime.now(timezone.utc).isoformat()
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"Could not parse date '{raw_date}': {e}")
                    created_at = datetime.now(timezone.utc).isoformat()
            else:
                created_at = datetime.now(timezone.utc).isoformat()
            
            # Add the corrected date to metadata BEFORE using it (CRITICAL FIX)
            metadata["date"] = created_at
            metadata["created_at"] = created_at
            metadata["title"] = title
            
            # NEW: Use unified transcript handler if enabled
            if use_unified_handler:
                logger.info(f"Using unified transcript handler for meeting {meeting_id}")
                
                try:
                    # Initialize the unified transcript handler
                    from app.services.transcript_handler import TranscriptHandler
                    
                    handler = TranscriptHandler(
                        supabase_service=supabase_service,
                        embedding_service=embedding_service,
                        semantic_service=semantic_chunks_service
                    )
                    
                    # Store transcript first using existing logic to ensure it's in database
                    from app.services.transcript_processor import TranscriptProcessor
                    processor = TranscriptProcessor()
                    processed_data = processor.process_transcript(transcript_text)
                    
                    if processed_data.get("success"):
                        # Store transcript and chunks so unified handler can retrieve them
                        chunks = processed_data["chunks"]
                        for i, chunk in enumerate(chunks):
                            chunk.update({
                                "transcript_id": meeting_id,
                                "chunk_index": i,
                                "position": i,
                                "is_first": i == 0,
                                "is_last": i == len(chunks) - 1,
                                "metadata": {}
                            })
                        
                        store_result = await supabase_service.store_transcript(meeting_id, metadata, chunks)
                        
                        if store_result.get("success"):
                            logger.info(f"Stored transcript {meeting_id} in database for unified processing")
                            
                            # Process with dual pipeline (Q&A + Email)
                            result = await handler.process_dual_pipeline(
                                transcript_id=meeting_id,
                                meeting_title=title,
                                meeting_date=created_at,
                                metadata=metadata
                            )
                            
                            if result.get("success"):
                                logger.info(f"🎉 Unified processing completed successfully for meeting {meeting_id}")
                                logger.info(f"   Q&A pipeline: {'✅' if result.get('qa_success') else '❌'}")
                                logger.info(f"   Email pipeline: {'✅' if result.get('email_success') else '❌'}")
                                logger.info(f"   Total time: {result.get('total_time', 0):.2f}s")
                            else:
                                logger.error(f"❌ Unified processing failed for meeting {meeting_id}: {result.get('error')}")
                        else:
                            logger.error(f"Failed to store transcript for unified processing: {store_result.get('error')}")
                            # Fall back to original processing
                            use_unified_handler = False
                    else:
                        logger.error(f"Failed to process transcript text: {processed_data.get('error')}")
                        # Fall back to original processing
                        use_unified_handler = False
                        
                except ImportError as e:
                    logger.warning(f"TranscriptHandler not available: {e}")
                    logger.info("Falling back to original processing pipeline")
                    use_unified_handler = False
                except Exception as e:
                    logger.error(f"Error in unified processing: {e}")
                    logger.info("Falling back to original processing pipeline")
                    use_unified_handler = False
            
            # ORIGINAL: Use existing email-only pipeline (backward compatible)
            if not use_unified_handler:
                logger.info(f"Using original email-only pipeline for meeting {meeting_id}")
                
                # Create payload for ingestion pipeline
                ingestion_payload = {
                    "transcript_id": meeting_id,
                    "transcript_text": transcript_text,
                    "title": title,
                    "created_at": created_at,
                    "metadata": metadata
                }
                
                # Start the ingestion pipeline with the fetched data
                from app.services.ingestion_service import IngestionService
                
                ingestion_service = IngestionService()
                result = await ingestion_service.start_ingestion_pipeline_with_text(
                    transcript_id=meeting_id,
                    transcript_text=ingestion_payload["transcript_text"],
                    meeting_title=ingestion_payload["title"],
                    meeting_date=ingestion_payload["created_at"],
                    metadata=ingestion_payload["metadata"]
                )
                
                if result["success"]:
                    logger.info(f"✅ Original pipeline completed successfully for meeting ID: {meeting_id}")
                    logger.info(f"Pipeline summary: {len(result.get('steps_completed', []))} steps completed in {result.get('total_time', 0):.2f} seconds")
                else:
                    logger.error(f"❌ Original pipeline failed for meeting ID: {meeting_id}")
                    logger.error(f"Error: {result.get('error', 'Unknown error')}")
                
        except ImportError:
            logger.error("FirefliesClient not found - cannot fetch transcript data")
            logger.info("Please implement app/services/fireflies_client.py to enable full webhook processing")
        except Exception as e:
            logger.error(f"Error fetching transcript from Fireflies API: {str(e)}")
            logger.error(traceback.format_exc())
            
    except Exception as e:
        logger.error(f"Error in Fireflies webhook background processing: {str(e)}")
        logger.error(traceback.format_exc())

@app.get("/transcripts/{transcript_id}/key-points")
async def get_transcript_key_points(transcript_id: str):
    """Extract key points from a specific transcript"""
    if not transcript_id:
        raise HTTPException(status_code=400, detail="Transcript ID is required")
        
    response = await semantic_chunks_service.extract_key_points(transcript_id)
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail=response.get("error", "Failed to extract key points"))
        
    return response

@app.get("/transcripts/{transcript_id}")
async def get_transcript(transcript_id: str):
    """Get a transcript and its chunks"""
    if not transcript_id:
        raise HTTPException(status_code=400, detail="Transcript ID is required")
        
    if not supabase_service.is_connected():
        raise HTTPException(status_code=500, detail="Database not connected")
        
    response = await supabase_service.get_transcript_by_id(transcript_id)
    
    if not response["success"]:
        raise HTTPException(status_code=404, detail=response.get("error", "Transcript not found"))
        
    return response

@app.delete("/transcripts/{transcript_id}")
async def delete_transcript(transcript_id: str):
    """
    Delete a transcript and all its related data.
    
    This endpoint safely removes:
    - The transcript record
    - All transcript chunks
    - All semantic chunks
    - Key points analysis
    - Transcript sharing permissions
    
    This action cannot be undone.
    """
    if not transcript_id:
        raise HTTPException(status_code=400, detail="Transcript ID is required")
        
    if not supabase_service.is_connected():
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # Log the deletion attempt
    logger.info(f"DELETE request received for transcript {transcript_id}")
        
    response = await supabase_service.delete_transcript(transcript_id)
    
    if not response["success"]:
        error_message = response.get("error", "Failed to delete transcript")
        logger.error(f"Failed to delete transcript {transcript_id}: {error_message}")
        
        # Return appropriate HTTP status codes
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=500, detail=error_message)
    
    # Log successful deletion
    logger.info(f"✅ Successfully deleted transcript {transcript_id}")
    logger.info(f"   Total items deleted: {response.get('total_deleted', 0)}")
    logger.info(f"   Processing time: {response.get('processing_time', 0):.2f}s")
        
    return response

@app.delete("/transcript-delete/{transcript_id}")
async def delete_transcript_alt(transcript_id: str):
    """
    Alternative DELETE endpoint for testing - Delete a transcript and all its related data.
    
    This endpoint safely removes:
    - The transcript record
    - All transcript chunks
    - All semantic chunks
    - Key points analysis
    - Transcript sharing permissions
    
    This action cannot be undone.
    """
    if not transcript_id:
        raise HTTPException(status_code=400, detail="Transcript ID is required")
        
    if not supabase_service.is_connected():
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # Log the deletion attempt
    logger.info(f"[ALT] DELETE request received for transcript {transcript_id}")
        
    response = await supabase_service.delete_transcript(transcript_id)
    
    if not response["success"]:
        error_message = response.get("error", "Failed to delete transcript")
        logger.error(f"[ALT] Failed to delete transcript {transcript_id}: {error_message}")
        
        # Return appropriate HTTP status codes
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=500, detail=error_message)
    
    # Log successful deletion
    logger.info(f"[ALT] ✅ Successfully deleted transcript {transcript_id}")
    logger.info(f"[ALT]    Total items deleted: {response.get('total_deleted', 0)}")
    logger.info(f"[ALT]    Processing time: {response.get('processing_time', 0):.2f}s")
        
    return response

@app.get("/health")
async def health_check():
    """Enhanced API health check endpoint with observability"""
    health_data = {
        "status": "healthy",
        "version": "2.0.0-enhanced",
        "services": {
            "supabase": supabase_service.is_connected(),
            "embedding": True,  # embedding_service exists
            "auth": True,       # auth_service exists  
            "semantic_chunks": semantic_chunks_service.is_initialized(),  # ENHANCED: semantic chunks service
            "enhanced_rag": True  # ENHANCED: enhanced RAG system active
        },
        "enhancements": {
            "semantic_chunking": True,
            "vector_search": True,
            "domain_agnostic": True,
            "entity_extraction": True,
            "sentiment_analysis": True
        }
    }
    
    # Add observability data if available
    try:
        from app.middleware.observability_middleware import get_health_status
        observability_status = get_health_status()
        health_data["observability"] = observability_status
    except ImportError:
        health_data["observability"] = {"status": "not_available"}
    
    return health_data

@app.get("/metrics")
async def metrics_endpoint():
    """Metrics endpoint for monitoring"""
    try:
        from app.middleware.observability_middleware import get_metrics
        return get_metrics()
    except ImportError:
        return {"error": "Observability not available"}

@app.get("/metrics/prometheus")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    try:
        from app.middleware.observability_middleware import get_prometheus_metrics
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(get_prometheus_metrics(), media_type="text/plain")
    except ImportError:
        return {"error": "Observability not available"}

@app.get("/setup/user-management")
async def setup_user_management(admin_secret: str):
    """Set up user management tables"""
    # Check admin secret
    expected_secret = os.getenv("ADMIN_SECRET", "change-me-in-production")
    if admin_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid admin secret")
    
    # Import setup script
    sys.path.append(str(Path(__file__).parent.parent / "scripts"))
    from scripts.setup_user_management import check_user_management_setup, setup_user_management as run_setup
    
    # Check if already set up
    already_setup = await check_user_management_setup()
    if already_setup:
        return {
            "success": True,
            "message": "User management tables are already set up."
        }
    
    # Set up tables
    result = await run_setup()
    if result:
        return {
            "success": True,
            "message": "User management tables have been set up successfully."
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail="Failed to set up user management tables."
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for security and logging"""
    return await security_exception_handler(request, exc)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 