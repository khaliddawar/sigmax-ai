"""
Batch Processor for processing messages from Redis queues
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from supabase import create_client, Client
import os
from dotenv import load_dotenv

from app.services.redis_service import RedisService
from app.services.llm_service import LLMService
from app.services.telegram_service import TelegramService

load_dotenv()

logger = structlog.get_logger()

class BatchProcessor:
    """Process message batches from Redis and generate reports"""
    
    def __init__(self):
        self.redis_service = None
        self.llm_service = None
        self.supabase = None
        self.telegram_service = None
        self._initialize_services()
        
        # Batch settings from environment
        self.realtime_interval = int(os.getenv("REALTIME_BATCH_SECONDS", 300))  # 5 min
        self.standard_interval = int(os.getenv("STANDARD_BATCH_SECONDS", 900))  # 15 min
        self.archive_interval = int(os.getenv("ARCHIVE_BATCH_SECONDS", 3600))  # 1 hour
        self.max_batch_size = int(os.getenv("MAX_MESSAGES_PER_BATCH", 50))
        
        self.processing = False
        
    def _initialize_services(self):
        """Initialize required services"""
        try:
            # Initialize Redis
            self.redis_service = RedisService()
            # Note: Redis needs async initialization, done when actually used
            
            # Initialize LLM
            self.llm_service = LLMService()
            
            # Initialize Telegram
            try:
                self.telegram_service = TelegramService()
                logger.info("Telegram service initialized")
            except Exception as e:
                logger.warning(f"Telegram service not available: {e}")
                self.telegram_service = None
            
            # Initialize Supabase
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            if url and key:
                self.supabase = create_client(url, key)
                logger.info("Batch processor services initialized")
            else:
                logger.warning("Supabase not configured, will not persist reports")
                
        except Exception as e:
            logger.error(f"Failed to initialize batch processor: {e}")
            raise
    
    async def start_processing(self):
        """Start the batch processing loop"""
        if self.processing:
            logger.warning("Batch processor already running")
            return
        
        self.processing = True
        logger.info("Starting batch processor")
        
        # Start processing tasks for each priority level
        tasks = [
            asyncio.create_task(self._process_realtime_loop()),
            asyncio.create_task(self._process_standard_loop()),
            asyncio.create_task(self._process_archive_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Batch processor error: {e}")
        finally:
            self.processing = False
    
    async def stop_processing(self):
        """Stop the batch processing loop"""
        logger.info("Stopping batch processor")
        self.processing = False
    
    async def _process_realtime_loop(self):
        """Process realtime messages every 5 minutes"""
        while self.processing:
            try:
                await self._process_batch("realtime", "alert")
                await asyncio.sleep(self.realtime_interval)
            except Exception as e:
                logger.error(f"Realtime processing error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _process_standard_loop(self):
        """Process standard messages every 15 minutes"""
        while self.processing:
            try:
                await self._process_batch("standard", "hourly")
                await asyncio.sleep(self.standard_interval)
            except Exception as e:
                logger.error(f"Standard processing error: {e}")
                await asyncio.sleep(60)
    
    async def _process_archive_loop(self):
        """Process archive messages every hour"""
        while self.processing:
            try:
                await self._process_batch("archive", "daily")
                await asyncio.sleep(self.archive_interval)
            except Exception as e:
                logger.error(f"Archive processing error: {e}")
                await asyncio.sleep(60)
    
    async def _process_batch(self, priority: str, report_type: str):
        """
        Process a batch of messages from a specific priority queue
        
        Args:
            priority: Queue priority (realtime, standard, archive)
            report_type: Type of report to generate (alert, hourly, daily)
        """
        try:
            # Get messages from Redis
            messages = await self._get_messages_from_queue(priority)
            
            if not messages:
                logger.debug(f"No messages in {priority} queue")
                return
            
            logger.info(f"Processing {len(messages)} messages from {priority} queue")
            
            # Create batch record
            batch_id = await self._create_batch_record(priority, len(messages))
            
            # Generate report using LLM
            report = await self.llm_service.generate_report(messages, report_type)
            
            # Save messages to database
            await self._save_messages_to_db(messages, batch_id)
            
            # Save report to database
            await self._save_report_to_db(report, batch_id)
            
            # Update batch status
            await self._update_batch_status(batch_id, "completed", report.get("llm_tokens_used"))
            
            # Send alerts if needed
            if report_type == "alert" and report.get("trading_signals"):
                await self._send_alerts(report)
            
            # Send to Telegram if enabled
            if self.telegram_service and self.telegram_service.enabled:
                try:
                    if report_type == "alert":
                        await self.telegram_service.send_alert_report(report)
                        logger.info("Alert sent to Telegram")
                    elif report_type == "hourly":
                        await self.telegram_service.send_hourly_report(report)
                        logger.info("Hourly report sent to Telegram")
                    elif report_type == "daily":
                        await self.telegram_service.send_daily_report(report)
                        logger.info("Daily report sent to Telegram")
                except Exception as e:
                    logger.error(f"Failed to send Telegram notification: {e}")
            
            logger.info(
                f"Batch processed successfully",
                batch_id=batch_id,
                priority=priority,
                messages_count=len(messages),
                tickers_found=len(report.get("mentioned_tickers", []))
            )
            
        except Exception as e:
            logger.error(f"Failed to process {priority} batch: {e}")
            if 'batch_id' in locals():
                await self._update_batch_status(batch_id, "failed", error_message=str(e))
    
    async def _get_messages_from_queue(self, priority: str) -> List[Dict[str, Any]]:
        """Get messages from Redis queue"""
        try:
            # Ensure Redis is initialized
            if not self.redis_service.initialized:
                await self.redis_service.initialize()
            
            stream_map = {
                "realtime": "signalscope:messages:realtime",
                "standard": "signalscope:messages:standard",
                "archive": "signalscope:messages:archive"
            }
            
            stream_key = stream_map.get(priority)
            if not stream_key:
                return []
            
            # Read messages from stream (async)
            messages = []
            stream_messages = await self.redis_service.redis.xrange(
                stream_key, 
                count=self.max_batch_size
            )
            
            message_ids = []
            for msg_id, data in stream_messages:
                try:
                    # Parse message content
                    content = json.loads(data.get('content', '{}'))
                    
                    # Add additional fields
                    message = {
                        **content,
                        "redis_id": msg_id,
                        "importance_score": int(data.get('importance', 5)),
                        "tickers": json.loads(data.get('tickers', '[]')),
                        "sentiment": data.get('sentiment'),
                        "stream": stream_key
                    }
                    
                    messages.append(message)
                    message_ids.append(msg_id)
                    
                except Exception as e:
                    logger.error(f"Failed to parse message {msg_id}: {e}")
            
            # Remove processed messages from stream (async)
            if message_ids:
                await self.redis_service.redis.xdel(stream_key, *message_ids)
                logger.info(f"Removed {len(message_ids)} messages from {stream_key}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get messages from queue: {e}")
            return []
    
    async def _create_batch_record(self, batch_type: str, message_count: int) -> str:
        """Create a batch record in the database"""
        try:
            if not self.supabase:
                return f"mock_batch_{datetime.utcnow().timestamp()}"
            
            result = self.supabase.table("message_batches").insert({
                "batch_type": batch_type,
                "message_count": message_count,
                "processing_status": "processing",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }).execute()
            
            return result.data[0]["id"]
            
        except Exception as e:
            logger.error(f"Failed to create batch record: {e}")
            return f"error_batch_{datetime.utcnow().timestamp()}"
    
    async def _save_messages_to_db(self, messages: List[Dict[str, Any]], batch_id: str):
        """Save messages to the database"""
        try:
            if not self.supabase:
                return
            
            # Prepare messages for insertion
            db_messages = []
            for msg in messages:
                db_messages.append({
                    "message_id": msg.get("id", msg.get("redis_id", "")),
                    "platform": msg.get("platform", "unknown"),
                    "author": msg.get("author"),
                    "content": msg.get("content", ""),
                    "captured_at": msg.get("captured_at", msg.get("timestamp", datetime.utcnow().isoformat() + "Z")),
                    "importance_score": msg.get("importance_score", 5),
                    "tickers": msg.get("tickers", []),
                    "sentiment": msg.get("sentiment"),
                    "trading_signal": msg.get("intelligence", {}).get("tradingSignal") if msg.get("intelligence") else None,
                    "batch_id": batch_id,
                    "url": msg.get("url"),
                    "intelligence": msg.get("intelligence"),
                    "created_at": datetime.utcnow().isoformat() + "Z"
                })
            
            # Batch insert messages
            if db_messages:
                self.supabase.table("messages").insert(db_messages).execute()
                logger.info(f"Saved {len(db_messages)} messages to database")
                
        except Exception as e:
            logger.error(f"Failed to save messages to database: {e}")
    
    async def _save_report_to_db(self, report: Dict[str, Any], batch_id: str):
        """Save report to the database"""
        try:
            if not self.supabase:
                return
            
            # Prepare report for insertion
            db_report = {
                "batch_id": batch_id,
                "report_type": report.get("report_type", "standard"),
                "report_data": report.get("report_data", {}),
                "key_insights": report.get("key_insights", []),
                "mentioned_tickers": report.get("mentioned_tickers", []),
                "overall_sentiment": report.get("overall_sentiment"),
                "trading_signals": report.get("trading_signals", []),
                "confidence_score": report.get("confidence_score", 0.5),
                "messages_analyzed": report.get("messages_analyzed", 0),
                "llm_tokens_used": report.get("llm_tokens_used"),
                "llm_model_used": report.get("llm_model_used"),
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            result = self.supabase.table("reports").insert(db_report).execute()
            logger.info(f"Report saved to database", report_id=result.data[0]["id"])
            
        except Exception as e:
            logger.error(f"Failed to save report to database: {e}")
    
    async def _update_batch_status(self, batch_id: str, status: str, tokens_used: Optional[int] = None, error_message: Optional[str] = None):
        """Update batch processing status"""
        try:
            if not self.supabase or batch_id.startswith("mock_") or batch_id.startswith("error_"):
                return
            
            update_data = {
                "processing_status": status,
                "processed_at": datetime.utcnow().isoformat() + "Z"
            }
            
            if tokens_used:
                update_data["llm_tokens_used"] = tokens_used
            
            if error_message:
                update_data["error_message"] = error_message
            
            self.supabase.table("message_batches").update(update_data).eq("id", batch_id).execute()
            logger.info(f"Batch {batch_id} status updated to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update batch status: {e}")
    
    async def _send_alerts(self, report: Dict[str, Any]):
        """Send alerts for high-priority trading signals"""
        try:
            # For now, just log the alerts
            # In production, this would send emails, webhooks, etc.
            for signal in report.get("trading_signals", []):
                if signal.get("strength") == "strong":
                    logger.warning(
                        f"TRADING ALERT: {signal.get('action')} {signal.get('ticker')} - {signal.get('reasoning')}",
                        signal=signal
                    )
            
            # TODO: Implement email/webhook notifications
            
        except Exception as e:
            logger.error(f"Failed to send alerts: {e}")
    
    async def process_single_batch(self, priority: str = "standard") -> Dict[str, Any]:
        """
        Process a single batch immediately (for testing)
        
        Args:
            priority: Queue priority to process
            
        Returns:
            Processing result
        """
        report_type_map = {
            "realtime": "alert",
            "standard": "hourly",
            "archive": "daily"
        }
        
        report_type = report_type_map.get(priority, "hourly")
        
        logger.info(f"Processing single batch from {priority} queue")
        await self._process_batch(priority, report_type)
        
        return {
            "status": "completed",
            "priority": priority,
            "report_type": report_type,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }