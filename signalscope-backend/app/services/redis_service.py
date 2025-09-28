"""
Redis service for message queuing and caching
"""
import redis.asyncio as redis
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
import asyncio

from app.settings import settings
from app.models.schemas import Message, MessagePriority

logger = structlog.get_logger()


class RedisService:
    """Service for Redis operations"""
    
    # Stream names for different priority levels
    REALTIME_STREAM = "signalscope:messages:realtime"
    STANDARD_STREAM = "signalscope:messages:standard"
    ARCHIVE_STREAM = "signalscope:messages:archive"
    
    # Consumer group name
    CONSUMER_GROUP = "signalscope:processors"
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize Redis connection and create streams"""
        try:
            # Create Redis connection
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis.ping()
            logger.info("Redis connection established", url=settings.redis_url)
            
            # Create consumer groups for streams
            for stream in [self.REALTIME_STREAM, self.STANDARD_STREAM, self.ARCHIVE_STREAM]:
                try:
                    await self.redis.xgroup_create(
                        stream,
                        self.CONSUMER_GROUP,
                        id="0",
                        mkstream=True
                    )
                    logger.info(f"Created consumer group for stream", stream=stream)
                except redis.ResponseError as e:
                    if "BUSYGROUP" in str(e):
                        logger.debug(f"Consumer group already exists", stream=stream)
                    else:
                        raise
            
            self.initialized = True
            
        except Exception as e:
            logger.error("Failed to initialize Redis", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def ping(self) -> bool:
        """Check Redis connection"""
        try:
            if self.redis:
                await self.redis.ping()
                return True
        except:
            return False
        return False
    
    def get_stream_for_priority(self, importance_score: int) -> str:
        """
        Determine which stream to use based on importance score
        
        Args:
            importance_score: Message importance (0-10)
        
        Returns:
            Stream name
        """
        if importance_score >= settings.realtime_importance_threshold:
            return self.REALTIME_STREAM
        elif importance_score >= settings.standard_importance_threshold:
            return self.STANDARD_STREAM
        else:
            return self.ARCHIVE_STREAM
    
    def get_priority_for_score(self, importance_score: int) -> MessagePriority:
        """Get priority enum for importance score"""
        if importance_score >= settings.realtime_importance_threshold:
            return MessagePriority.REALTIME
        elif importance_score >= settings.standard_importance_threshold:
            return MessagePriority.STANDARD
        else:
            return MessagePriority.ARCHIVE
    
    async def add_message(self, message: Message) -> str:
        """
        Add a message to the appropriate stream
        
        Args:
            message: Message to add
        
        Returns:
            Stream entry ID
        """
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        
        # Determine stream based on importance
        importance = message.intelligence.importance
        stream = self.get_stream_for_priority(importance)
        
        # Prepare message data for Redis
        message_data = {
            "message_id": message.id,
            "content": json.dumps(message.model_dump(mode="json")),
            "importance": str(importance),
            "platform": message.platform,
            "author": message.author,
            "timestamp": message.timestamp.isoformat(),
            "tickers": json.dumps(message.intelligence.entities.tickers),
            "sentiment": message.intelligence.sentiment.sentiment,
            "trading_signal": json.dumps(
                message.intelligence.tradingSignal.model_dump() 
                if message.intelligence.tradingSignal else None
            )
        }
        
        # Add to stream
        entry_id = await self.redis.xadd(stream, message_data)
        
        logger.info(
            "Message added to stream",
            stream=stream,
            entry_id=entry_id,
            importance=importance,
            tickers=message.intelligence.entities.tickers
        )
        
        # Update metrics
        await self.increment_metric("messages_queued_total")
        await self.increment_metric(f"messages_queued_{stream.split(':')[-1]}")
        
        return entry_id
    
    async def get_messages_batch(
        self,
        stream: str,
        count: int = 50,
        block: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get a batch of messages from a stream
        
        Args:
            stream: Stream name
            count: Maximum number of messages
            block: Block timeout in milliseconds (0 = don't block)
        
        Returns:
            List of messages with their IDs
        """
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            # Read from stream using consumer group
            messages = await self.redis.xreadgroup(
                self.CONSUMER_GROUP,
                "worker-1",  # Consumer name
                {stream: ">"},  # Read new messages
                count=count,
                block=block
            )
            
            if not messages:
                return []
            
            # Parse messages
            result = []
            for stream_name, stream_messages in messages:
                for msg_id, data in stream_messages:
                    try:
                        # Parse the message content
                        content = json.loads(data.get("content", "{}"))
                        result.append({
                            "id": msg_id,
                            "stream": stream_name,
                            "message": content
                        })
                    except json.JSONDecodeError:
                        logger.error("Failed to parse message", msg_id=msg_id)
            
            return result
            
        except Exception as e:
            logger.error("Failed to get message batch", error=str(e))
            return []
    
    async def ack_messages(self, stream: str, message_ids: List[str]) -> int:
        """
        Acknowledge processed messages
        
        Args:
            stream: Stream name
            message_ids: List of message IDs to acknowledge
        
        Returns:
            Number of acknowledged messages
        """
        if not self.redis or not message_ids:
            return 0
        
        try:
            count = await self.redis.xack(stream, self.CONSUMER_GROUP, *message_ids)
            logger.info(f"Acknowledged messages", stream=stream, count=count)
            return count
        except Exception as e:
            logger.error("Failed to acknowledge messages", error=str(e))
            return 0
    
    async def get_stream_info(self, stream: str) -> Dict[str, Any]:
        """
        Get information about a stream
        
        Args:
            stream: Stream name
        
        Returns:
            Stream information
        """
        if not self.redis:
            return {}
        
        try:
            # Get stream info
            info = await self.redis.xinfo_stream(stream)
            
            # Get consumer group info
            groups = await self.redis.xinfo_groups(stream)
            
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "consumer_groups": len(groups),
                "pending_messages": sum(g.get("pending", 0) for g in groups)
            }
        except Exception as e:
            logger.error("Failed to get stream info", error=str(e))
            return {}
    
    async def get_queue_depths(self) -> Dict[str, int]:
        """Get the depth of all queues"""
        depths = {}
        for stream_name, priority in [
            (self.REALTIME_STREAM, "realtime"),
            (self.STANDARD_STREAM, "standard"),
            (self.ARCHIVE_STREAM, "archive")
        ]:
            info = await self.get_stream_info(stream_name)
            depths[priority] = info.get("length", 0)
        return depths
    
    # Metrics and monitoring
    async def increment_metric(self, key: str, amount: int = 1) -> None:
        """Increment a metric counter"""
        if self.redis:
            await self.redis.hincrby("signalscope:metrics", key, amount)
    
    async def get_metrics(self) -> Dict[str, int]:
        """Get all metrics"""
        if not self.redis:
            return {}
        
        metrics = await self.redis.hgetall("signalscope:metrics")
        return {k: int(v) for k, v in metrics.items()}
    
    # Caching
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600
    ) -> None:
        """Set a cache value with TTL"""
        if self.redis:
            cache_key = f"signalscope:cache:{key}"
            await self.redis.setex(
                cache_key,
                ttl_seconds,
                json.dumps(value) if not isinstance(value, str) else value
            )
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cache value"""
        if not self.redis:
            return None
        
        cache_key = f"signalscope:cache:{key}"
        value = await self.redis.get(cache_key)
        
        if value:
            try:
                return json.loads(value)
            except:
                return value
        return None