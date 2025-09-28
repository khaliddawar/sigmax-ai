"""
Pydantic models for request/response schemas
"""
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


# Enums
class MessagePriority(str, Enum):
    """Message priority levels"""
    REALTIME = "realtime"
    STANDARD = "standard"
    ARCHIVE = "archive"


class ReportType(str, Enum):
    """Report types"""
    ALERT = "alert"
    HOURLY = "hourly"
    DAILY = "daily"


class SentimentType(str, Enum):
    """Sentiment classifications"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class TradingAction(str, Enum):
    """Trading signal actions"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# Message Intelligence Models
class TradingSignal(BaseModel):
    """Trading signal extracted from message"""
    action: TradingAction
    tickers: List[str]
    strength: str = Field(default="moderate")


class Sentiment(BaseModel):
    """Sentiment analysis result"""
    score: float = Field(ge=-1, le=1)
    sentiment: SentimentType
    confidence: float = Field(ge=0, le=1)


class Entities(BaseModel):
    """Extracted entities from message"""
    tickers: List[str] = Field(default_factory=list)
    prices: List[str] = Field(default_factory=list)
    percentages: List[str] = Field(default_factory=list)
    quantities: List[str] = Field(default_factory=list)


class Intelligence(BaseModel):
    """Complete intelligence analysis of a message"""
    entities: Entities
    sentiment: Sentiment
    tradingSignal: Optional[TradingSignal] = None
    importance: int = Field(ge=0, le=10)


# Attachment Models
class Attachment(BaseModel):
    """Message attachment (image, link, etc.)"""
    type: str  # "image", "link", "file", etc.
    url: Optional[str] = None
    data: Optional[str] = None  # base64 data for images
    title: Optional[str] = None
    context: Optional[str] = None
    alt: Optional[str] = None


# Message Models
class Message(BaseModel):
    """Individual message from Chrome Extension"""
    id: str
    platform: str
    author: str
    content: str
    timestamp: datetime
    url: str
    intelligence: Intelligence
    capturedAt: Optional[datetime] = None
    channel: Optional[str] = None  # Channel/room name
    attachments: List[Attachment] = Field(default_factory=list)  # Message attachments
    
    @validator("timestamp", "capturedAt", pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class WebhookPayload(BaseModel):
    """Webhook payload from Chrome Extension"""
    messages: List[Message]
    client: Optional[Dict[str, Any]] = None
    source: Optional[Union[Dict[str, Any], str]] = None  # Accept both dict and string
    timestamp: Optional[str] = None  # Extension sends this
    version: Optional[str] = None    # Extension sends this


# Batch Models
class MessageBatch(BaseModel):
    """Batch of messages for processing"""
    id: str
    priority: MessagePriority
    messages: List[Message]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    total_importance: int = 0
    
    @validator("message_count", always=True)
    def set_message_count(cls, v, values):
        if "messages" in values:
            return len(values["messages"])
        return v
    
    @validator("total_importance", always=True)
    def calculate_total_importance(cls, v, values):
        if "messages" in values:
            return sum(msg.intelligence.importance for msg in values["messages"])
        return v


# Report Models
class ReportInsight(BaseModel):
    """Individual insight from a report"""
    ticker: Optional[str] = None
    insight: str
    confidence: float = Field(ge=0, le=1)
    source_messages: List[str] = Field(default_factory=list)


class TradingIdea(BaseModel):
    """Trading idea from report"""
    asset: str
    strategy: str
    rationale: str
    entry: Optional[str] = None
    target: Optional[str] = None
    stop: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


class RiskAlert(BaseModel):
    """Risk alert from report"""
    event: str
    impact: str
    severity: str = Field(pattern="^(high|medium|low)$")
    affected_tickers: List[str] = Field(default_factory=list)


class Report(BaseModel):
    """Generated intelligence report"""
    id: str
    batch_id: str
    report_type: ReportType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Core report data
    market_overview: Optional[Dict[str, Any]] = None
    key_insights: List[ReportInsight] = Field(default_factory=list)
    trading_ideas: List[TradingIdea] = Field(default_factory=list)
    risk_alerts: List[RiskAlert] = Field(default_factory=list)
    
    # Metadata
    mentioned_tickers: List[str] = Field(default_factory=list)
    overall_sentiment: Optional[SentimentType] = None
    confidence_score: float = Field(ge=0, le=1, default=0.5)
    
    # Processing metadata
    messages_analyzed: int = 0
    processing_time_seconds: Optional[float] = None
    llm_tokens_used: Optional[int] = None
    llm_model_used: Optional[str] = None


# Response Models
class WebhookResponse(BaseModel):
    """Response for webhook endpoint"""
    success: bool
    received: int
    message: Optional[str] = None
    batch_id: Optional[str] = None


class ReportResponse(BaseModel):
    """Response for report endpoints"""
    success: bool
    report: Optional[Report] = None
    message: Optional[str] = None


class ReportListResponse(BaseModel):
    """Response for report list endpoints"""
    success: bool
    reports: List[Report] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 20


# Queue Status Models
class QueueStatus(BaseModel):
    """Queue status information"""
    priority: MessagePriority
    depth: int
    oldest_message_age_seconds: Optional[float] = None
    newest_message_age_seconds: Optional[float] = None
    processing_rate_per_minute: float = 0


class SystemStatus(BaseModel):
    """Overall system status"""
    queues: List[QueueStatus]
    active_batches: int = 0
    reports_generated_today: int = 0
    messages_processed_today: int = 0
    average_processing_time: float = 0
    system_health: str = "healthy"