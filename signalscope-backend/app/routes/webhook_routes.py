"""
Webhook routes for receiving messages from Chrome Extension
"""
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional
import structlog
from datetime import datetime

from app.models.schemas import (
    WebhookPayload,
    WebhookResponse,
    Message
)
from app.utils.security import (
    verify_webhook_signature,
    is_request_expired,
    hash_message_id
)
from app.services.redis_service import RedisService
from app.services.telegram_service import TelegramService

logger = structlog.get_logger()

router = APIRouter()


@router.post("/signalscope/test")
async def test_webhook(request: Request):
    """Simple test endpoint for webhook connectivity"""
    try:
        body = await request.json()
        logger.info("Test webhook received", body=body)
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Test webhook received successfully"}
        )
    except Exception as e:
        logger.error("Test webhook failed", error=str(e))
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@router.post("/signalscope", response_model=WebhookResponse)
async def receive_signalscope_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signalscope_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None)
):
    """
    Receive messages from SignalScope Chrome Extension
    
    This endpoint:
    1. Verifies HMAC signature
    2. Validates message format
    3. Queues messages for processing
    4. Returns immediate acknowledgment
    """
    try:
        # Get request body
        body = await request.body()
        
        # Parse JSON manually to handle validation errors better
        import json
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in webhook request", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Try to validate as WebhookPayload
        try:
            payload = WebhookPayload(**data)
        except Exception as e:
            logger.error("Webhook validation failed", error=str(e), data=data)
            # Log the first message to see its structure
            if data.get('messages') and len(data['messages']) > 0:
                logger.error("First message structure", message=data['messages'][0])
            raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
        
        # Verify HMAC signature if provided
        if x_signalscope_signature:
            if not verify_webhook_signature(body, x_signalscope_signature):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Check timestamp to prevent replay attacks
        if x_timestamp:
            if is_request_expired(x_timestamp, max_age_seconds=300):
                logger.warning("Webhook request expired", timestamp=x_timestamp)
                raise HTTPException(status_code=400, detail="Request expired")
        
        # Get Redis service
        redis_service: RedisService = request.app.state.redis
        
        # Process messages
        messages = payload.messages
        message_count = len(messages)
        
        logger.info(
            "Webhook received",
            message_count=message_count,
            platform=messages[0].platform if messages else "unknown",
            client=payload.client
        )
        
        # Add background task to process messages (existing LLM flow)
        background_tasks.add_task(
            process_messages_async,
            redis_service,
            messages,
            payload.client,
            payload.source
        )
        
        # Add background task for Telegram bridge (parallel to LLM flow)
        background_tasks.add_task(
            telegram_bridge_async,
            messages
        )
        
        # Return immediate response
        return WebhookResponse(
            success=True,
            received=message_count,
            message=f"Received {message_count} messages for processing"
        )
        
    except ValueError as e:
        logger.error("Invalid webhook payload", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e), error_type=type(e).__name__)
        # For validation errors, return more details
        if "validation" in str(type(e)).lower():
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_messages_async(
    redis_service: RedisService,
    messages: list[Message],
    client_info: Optional[dict] = None,
    source_info: Optional[dict] = None
):
    """
    Process messages asynchronously in the background
    
    Args:
        redis_service: Redis service instance
        messages: List of messages to process
        client_info: Client metadata
        source_info: Source metadata
    """
    try:
        processed_count = 0
        high_importance_count = 0
        
        for message in messages:
            try:
                # Add deduplication check
                message_hash = hash_message_id(message.id)
                cache_key = f"msg_processed:{message_hash}"
                
                # Check if already processed
                if await redis_service.cache_get(cache_key):
                    logger.debug("Duplicate message skipped", message_id=message.id)
                    continue
                
                # Add message to appropriate queue based on importance
                await redis_service.add_message(message)
                
                # Mark as processed (cache for 1 hour)
                await redis_service.cache_set(cache_key, True, ttl_seconds=3600)
                
                processed_count += 1
                
                # Track high importance messages
                if message.intelligence.importance >= 8:
                    high_importance_count += 1
                
                # Log trading signals
                if message.intelligence.tradingSignal:
                    logger.info(
                        "Trading signal detected",
                        tickers=message.intelligence.entities.tickers,
                        action=message.intelligence.tradingSignal.action,
                        sentiment=message.intelligence.sentiment.sentiment,
                        importance=message.intelligence.importance
                    )
                
            except Exception as e:
                logger.error(
                    "Failed to process message",
                    message_id=message.id,
                    error=str(e)
                )
        
        # Check if batch processing should be triggered
        if high_importance_count > 0:
            await check_and_trigger_batch_processing(redis_service, "realtime")
        
        logger.info(
            "Message batch processed",
            total=len(messages),
            processed=processed_count,
            high_importance=high_importance_count
        )
        
    except Exception as e:
        logger.error("Background message processing failed", error=str(e))


async def telegram_bridge_async(messages: list[Message]):
    """
    Send messages directly to Telegram (parallel to LLM processing)
    
    Args:
        messages: List of messages to send to Telegram
    """
    try:
        # Initialize Telegram service
        telegram_service = TelegramService()
        
        if not telegram_service.enabled:
            logger.debug("Telegram bridge disabled, skipping")
            return
        
        # Convert Message objects to dict format for telegram service
        message_dicts = []
        for message in messages:
            # Convert attachments to dict format
            attachments_dict = []
            if hasattr(message, 'attachments') and message.attachments:
                for attachment in message.attachments:
                    if hasattr(attachment, 'dict'):
                        # Pydantic model
                        attachments_dict.append(attachment.dict())
                    else:
                        # Already a dict
                        attachments_dict.append(attachment)
            
            message_dict = {
                'id': message.id,
                'author': message.author,
                'content': message.content,
                'platform': message.platform,
                'timestamp': message.timestamp.isoformat(),
                'channel': message.channel or 'Live Chat',
                'url': message.url,
                'attachments': attachments_dict
            }
            message_dicts.append(message_dict)
        
        # Send messages to Telegram
        success = await telegram_service.send_message_batch(message_dicts)
        
        if success:
            logger.info(
                "Messages sent to Telegram successfully",
                message_count=len(messages)
            )
        else:
            logger.warning("Failed to send some messages to Telegram")
            
    except Exception as e:
        logger.error("Telegram bridge failed", error=str(e))


async def check_and_trigger_batch_processing(
    redis_service: RedisService,
    priority: str = None
):
    """
    Check if batch processing should be triggered based on queue depth
    
    Args:
        redis_service: Redis service instance
        priority: Specific priority to check (or check all)
    """
    try:
        from app.settings import settings
        
        # Get queue depths
        depths = await redis_service.get_queue_depths()
        
        # Check realtime queue (process if >= 10 messages or 5 minutes elapsed)
        if priority == "realtime" or priority is None:
            if depths.get("realtime", 0) >= 10:
                logger.info(
                    "Triggering realtime batch processing",
                    queue_depth=depths["realtime"]
                )
                # TODO: Trigger Celery task for batch processing
        
        # Check standard queue (process if >= 30 messages or 15 minutes elapsed)
        if priority == "standard" or priority is None:
            if depths.get("standard", 0) >= 30:
                logger.info(
                    "Triggering standard batch processing",
                    queue_depth=depths["standard"]
                )
                # TODO: Trigger Celery task for batch processing
        
        # Check archive queue (process if >= 100 messages or 60 minutes elapsed)
        if priority == "archive" or priority is None:
            if depths.get("archive", 0) >= 100:
                logger.info(
                    "Triggering archive batch processing",
                    queue_depth=depths["archive"]
                )
                # TODO: Trigger Celery task for batch processing
        
    except Exception as e:
        logger.error("Failed to check batch triggers", error=str(e))


@router.post("/telegram/test")
async def test_telegram_bridge(request: Request):
    """Test Telegram bridge with sample message"""
    try:
        # Create a test message
        from app.models.schemas import Message, Intelligence, Sentiment, Entities, Attachment
        
        test_message = Message(
            id="test-123",
            platform="circle",
            author="Julian Komar",
            content="Test message from SignalScope - Telegram bridge is working! 🚀",
            timestamp=datetime.utcnow(),
            url="https://members.julian-komar.com/c/community-chat/",
            intelligence=Intelligence(
                entities=Entities(),
                sentiment=Sentiment(score=0.5, sentiment="neutral", confidence=0.8),
                importance=5
            ),
            channel="Live Chat",
            attachments=[
                Attachment(
                    type="link",
                    url="https://signalscope.ai",
                    title="SignalScope AI"
                )
            ]
        )
        
        # Send to Telegram
        telegram_service = TelegramService()
        
        if not telegram_service.enabled:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Telegram not configured"}
            )
        
        # Test connection first
        connection_ok = await telegram_service.test_connection()
        if not connection_ok:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Telegram connection failed"}
            )
        
        # Send test message
        success = await telegram_service.send_raw_message({
            'id': test_message.id,
            'author': test_message.author,
            'content': test_message.content,
            'platform': test_message.platform,
            'timestamp': test_message.timestamp.isoformat(),
            'channel': test_message.channel,
            'url': test_message.url,
            'attachments': [att.dict() for att in test_message.attachments]
        })
        
        if success:
            return {"success": True, "message": "Test message sent to Telegram successfully"}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Failed to send test message"}
            )
            
    except Exception as e:
        logger.error("Telegram test failed", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )


@router.get("/status")
async def webhook_status(request: Request):
    """Get webhook service status"""
    try:
        redis_service: RedisService = request.app.state.redis
        
        # Get queue depths and metrics
        queue_depths = await redis_service.get_queue_depths()
        metrics = await redis_service.get_metrics()
        
        # Check Telegram status
        telegram_service = TelegramService()
        telegram_status = {
            "enabled": telegram_service.enabled,
            "configured": bool(telegram_service.bot_token and telegram_service.chat_id)
        }
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "queues": queue_depths,
            "telegram": telegram_status,
            "metrics": {
                "messages_received": metrics.get("messages_queued_total", 0),
                "messages_processed": metrics.get("messages_processed_total", 0),
                "reports_generated": metrics.get("reports_generated_total", 0)
            }
        }
    except Exception as e:
        logger.error("Failed to get webhook status", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": str(e)}
        )