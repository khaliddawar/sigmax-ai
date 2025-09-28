"""
Mock Redis service for development without Redis
"""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from collections import defaultdict, deque

from app.models.schemas import Message, MessagePriority
from app.settings import settings

logger = structlog.get_logger()


class MockRedisService:
    """Mock Redis service that stores data in memory for testing"""
    
    # Stream names for different priority levels
    REALTIME_STREAM = "signalscope:messages:realtime"
    STANDARD_STREAM = "signalscope:messages:standard"
    ARCHIVE_STREAM = "signalscope:messages:archive"
    
    # Consumer group name
    CONSUMER_GROUP = "signalscope:processors"
    
    def __init__(self):
        # In-memory storage
        self.streams = {
            self.REALTIME_STREAM: deque(maxlen=1000),
            self.STANDARD_STREAM: deque(maxlen=1000),
            self.ARCHIVE_STREAM: deque(maxlen=1000),
        }
        self.cache = {}
        self.metrics = defaultdict(int)
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize mock Redis service"""
        logger.info("Mock Redis service initialized (in-memory storage)")
        self.initialized = True
    
    async def close(self) -> None:
        """Close mock Redis service"""
        logger.info("Mock Redis service closed")
    
    async def ping(self) -> bool:
        """Check mock Redis service"""
        return True
    
    def get_stream_for_priority(self, importance_score: int) -> str:
        """Determine which stream to use based on importance score"""
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
        """Add a message to the appropriate stream"""
        # Determine stream based on importance
        importance = message.intelligence.importance
        stream = self.get_stream_for_priority(importance)
        
        # Create entry ID
        entry_id = f"{int(datetime.utcnow().timestamp() * 1000)}-0"
        
        # Prepare message data
        message_data = {
            "id": entry_id,
            "message_id": message.id,
            "content": message.model_dump(mode="json"),
            "importance": importance,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to stream
        self.streams[stream].append(message_data)
        
        logger.info(
            "Message added to mock stream",
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
        """Get a batch of messages from a stream"""
        if stream not in self.streams:
            return []
        
        # Get messages from the stream
        messages = list(self.streams[stream])[:count]
        
        # Remove fetched messages from stream (simulating consumption)
        for _ in range(min(count, len(self.streams[stream]))):
            if self.streams[stream]:
                self.streams[stream].popleft()
        
        result = []
        for msg_data in messages:
            result.append({
                "id": msg_data["id"],
                "stream": stream,
                "message": msg_data["content"]
            })
        
        return result
    
    async def ack_messages(self, stream: str, message_ids: List[str]) -> int:
        """Acknowledge processed messages (no-op for mock)"""
        logger.info(f"Mock: Acknowledged {len(message_ids)} messages from {stream}")
        return len(message_ids)
    
    async def get_stream_info(self, stream: str) -> Dict[str, Any]:
        """Get information about a stream"""
        if stream not in self.streams:
            return {}
        
        stream_data = self.streams[stream]
        return {
            "length": len(stream_data),
            "first_entry": stream_data[0] if stream_data else None,
            "last_entry": stream_data[-1] if stream_data else None,
            "consumer_groups": 1,
            "pending_messages": 0
        }
    
    async def get_queue_depths(self) -> Dict[str, int]:
        """Get the depth of all queues"""
        return {
            "realtime": len(self.streams[self.REALTIME_STREAM]),
            "standard": len(self.streams[self.STANDARD_STREAM]),
            "archive": len(self.streams[self.ARCHIVE_STREAM])
        }
    
    async def increment_metric(self, key: str, amount: int = 1) -> None:
        """Increment a metric counter"""
        self.metrics[key] += amount
    
    async def get_metrics(self) -> Dict[str, int]:
        """Get all metrics"""
        return dict(self.metrics)
    
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600
    ) -> None:
        """Set a cache value with TTL (ignores TTL in mock)"""
        cache_key = f"signalscope:cache:{key}"
        self.cache[cache_key] = value
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cache value"""
        cache_key = f"signalscope:cache:{key}"
        return self.cache.get(cache_key)