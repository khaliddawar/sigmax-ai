# SignalScope Message Stacking Architecture

## Executive Summary
This document outlines the message stacking architecture for SignalScope, designed to efficiently batch trading chat messages for LLM processing and report generation. The architecture follows industry best practices for message queuing, batching, and processing at scale.

## Architecture Overview

### Data Flow
```
Chrome Extension → Webhook → Backend API → Redis Queue → Batch Processor → LLM → Supabase
```

### Key Components

1. **Message Ingestion Layer**
   - Webhook receiver (FastAPI endpoint)
   - Message validation and normalization
   - Immediate acknowledgment to extension

2. **Message Stacking System**
   - Redis Streams for real-time ingestion
   - Time-series storage for historical data
   - Configurable batching strategies

3. **Batch Processing Pipeline**
   - Celery workers for async processing
   - Smart batching based on multiple criteria
   - LLM orchestration for report generation

4. **Storage & Reporting**
   - Supabase for persistent storage
   - Generated reports and insights
   - User dashboard access

## Message Stacking Strategy

### Industry Best Practices Applied

#### 1. **Redis Streams for Message Queue**
Based on the existing backend's queue_service.py pattern:

```python
class MessageStackingService:
    """Service for stacking trading messages before LLM processing"""
    
    # Stream names for different priority levels
    REALTIME_STREAM = "signalscope_realtime"      # High-importance signals (score >= 8)
    STANDARD_STREAM = "signalscope_standard"      # Normal messages (score 5-7)
    ARCHIVE_STREAM = "signalscope_archive"        # Low importance (score < 5)
    
    def stack_message(self, message_data: Dict, importance_score: int):
        """Stack message in appropriate stream based on importance"""
        
        # Determine stream based on importance
        if importance_score >= 8:
            stream = self.REALTIME_STREAM
            ttl = 300  # 5 minutes - process quickly
        elif importance_score >= 5:
            stream = self.STANDARD_STREAM
            ttl = 900  # 15 minutes - standard batch
        else:
            stream = self.ARCHIVE_STREAM
            ttl = 3600  # 1 hour - batch for analysis
        
        # Add to Redis stream with metadata
        self.redis.xadd(stream, {
            'message_id': message_data['id'],
            'content': json.dumps(message_data),
            'importance': importance_score,
            'timestamp': message_data['timestamp'],
            'platform': message_data['platform'],
            'tickers': json.dumps(message_data['intelligence']['entities']['tickers']),
            'sentiment': message_data['intelligence']['sentiment']['sentiment'],
            'trading_signal': json.dumps(message_data['intelligence'].get('tradingSignal'))
        })
```

#### 2. **Batching Strategies**

**Time-Based Batching**
- Real-time: Every 5 minutes or 20 messages
- Standard: Every 15 minutes or 50 messages
- Archive: Every hour or 200 messages

**Context-Based Batching**
- Group by ticker symbols
- Group by time windows (market hours)
- Group by sentiment clusters
- Group by author/influencer

**Volume-Based Batching**
- Token limits (4000 tokens per batch for GPT-4)
- Message count limits
- Importance score thresholds

### Implementation Pattern

```python
class BatchingStrategy:
    """Smart batching for LLM processing"""
    
    def __init__(self):
        self.batch_configs = {
            'realtime': {
                'max_messages': 20,
                'max_wait_seconds': 300,
                'max_tokens': 3000,
                'min_importance': 8
            },
            'standard': {
                'max_messages': 50,
                'max_wait_seconds': 900,
                'max_tokens': 4000,
                'min_importance': 5
            },
            'archive': {
                'max_messages': 200,
                'max_wait_seconds': 3600,
                'max_tokens': 8000,
                'min_importance': 0
            }
        }
    
    async def should_process_batch(self, stream_type: str, batch: List[Dict]) -> bool:
        """Determine if batch is ready for processing"""
        config = self.batch_configs[stream_type]
        
        # Check multiple conditions
        if len(batch) >= config['max_messages']:
            return True
            
        if self.get_batch_age(batch) >= config['max_wait_seconds']:
            return True
            
        if self.estimate_tokens(batch) >= config['max_tokens']:
            return True
            
        # Special case: urgent trading signal
        if any(msg.get('importance', 0) >= 10 for msg in batch):
            return True
            
        return False
```

## LLM Report Generation Pipeline

### Report Types

1. **Real-Time Alerts** (5-minute batches)
   - Critical trading signals
   - Major sentiment shifts
   - Unusual volume on specific tickers
   - Influencer activity

2. **Hourly Summaries**
   - Top mentioned tickers
   - Sentiment trends
   - Key trading ideas
   - Risk alerts

3. **Daily Reports**
   - Comprehensive market sentiment
   - Trading signal performance
   - Pattern recognition
   - Predictive insights

### LLM Processing Architecture

```python
class LLMReportGenerator:
    """Generate trading reports from message batches"""
    
    async def generate_report(self, messages: List[Dict], report_type: str) -> Dict:
        """Generate report using LLM based on message batch"""
        
        # Prepare context based on report type
        if report_type == 'realtime_alert':
            context = self.prepare_alert_context(messages)
            prompt = REALTIME_ALERT_PROMPT
        elif report_type == 'hourly_summary':
            context = self.prepare_hourly_context(messages)
            prompt = HOURLY_SUMMARY_PROMPT
        else:
            context = self.prepare_daily_context(messages)
            prompt = DAILY_REPORT_PROMPT
        
        # Generate report using existing summary service pattern
        report_data = await self.llm_service.generate_structured_report(
            context=context,
            prompt=prompt,
            schema=REPORT_SCHEMAS[report_type]
        )
        
        # Validate and store
        validated_report = self.validate_report(report_data, messages)
        await self.store_report(validated_report)
        
        return validated_report
```

## Database Schema (Supabase)

### Tables Design

```sql
-- Raw messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id TEXT UNIQUE NOT NULL,
    platform TEXT NOT NULL,
    author TEXT,
    content TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    importance_score INTEGER,
    tickers TEXT[],
    sentiment TEXT,
    trading_signal JSONB,
    batch_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message batches
CREATE TABLE message_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_type TEXT NOT NULL, -- 'realtime', 'standard', 'archive'
    message_count INTEGER NOT NULL,
    total_importance INTEGER,
    processing_status TEXT DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    llm_tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID REFERENCES message_batches(id),
    report_type TEXT NOT NULL, -- 'alert', 'hourly', 'daily'
    report_data JSONB NOT NULL,
    key_insights TEXT[],
    mentioned_tickers TEXT[],
    overall_sentiment TEXT,
    trading_signals JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Report subscriptions
CREATE TABLE report_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    report_type TEXT NOT NULL,
    delivery_method TEXT NOT NULL, -- 'email', 'webhook', 'dashboard'
    configuration JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_messages_tickers ON messages USING GIN(tickers);
CREATE INDEX idx_messages_captured_at ON messages(captured_at);
CREATE INDEX idx_messages_batch_id ON messages(batch_id);
CREATE INDEX idx_reports_created_at ON reports(created_at);
CREATE INDEX idx_reports_tickers ON reports USING GIN(mentioned_tickers);
```

## Integration with Existing Backend

### Webhook Receiver Endpoint

```python
# app/routes/webhook_routes.py
@router.post("/api/webhooks/signalscope")
async def receive_signalscope_messages(
    request: Request,
    background_tasks: BackgroundTasks,
    supabase: SupabaseClient = Depends(get_supabase)
):
    """Receive messages from SignalScope Chrome Extension"""
    
    # Verify HMAC signature
    signature = request.headers.get('X-SignalScope-Signature')
    if not verify_webhook_signature(await request.body(), signature):
        raise HTTPException(401, "Invalid signature")
    
    # Parse message batch
    data = await request.json()
    messages = data.get('messages', [])
    
    # Quick acknowledgment
    background_tasks.add_task(process_messages_async, messages)
    
    return {"success": True, "received": len(messages)}

async def process_messages_async(messages: List[Dict]):
    """Process messages asynchronously"""
    stacking_service = MessageStackingService()
    
    for message in messages:
        # Extract importance from intelligence data
        importance = message.get('intelligence', {}).get('importance', 0)
        
        # Stack message based on importance
        await stacking_service.stack_message(message, importance)
    
    # Trigger batch processing if thresholds met
    await check_and_trigger_batch_processing()
```

### Celery Worker for Batch Processing

```python
# app/services/batch_processor.py
@celery_app.task(bind=True)
def process_message_batch(self, batch_id: str, stream_type: str):
    """Process a batch of messages through LLM"""
    
    try:
        # Retrieve messages from Redis
        messages = retrieve_batch_messages(batch_id, stream_type)
        
        # Generate report based on stream type
        report_generator = LLMReportGenerator()
        report = loop.run_until_complete(
            report_generator.generate_report(
                messages=messages,
                report_type=get_report_type(stream_type)
            )
        )
        
        # Store in Supabase
        store_report_in_supabase(report, batch_id)
        
        # Notify subscribers
        notify_report_subscribers(report)
        
        return {"success": True, "report_id": report['id']}
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise
```

## Monitoring and Observability

### Key Metrics

1. **Ingestion Metrics**
   - Messages per second
   - Webhook success rate
   - Extension connectivity

2. **Stacking Metrics**
   - Queue depths by priority
   - Average message age
   - Batch fill rates

3. **Processing Metrics**
   - Batch processing time
   - LLM token usage
   - Report generation success rate

4. **Business Metrics**
   - Unique tickers tracked
   - Trading signals detected
   - Report engagement rates

### Implementation

```python
class MetricsCollector:
    """Collect and export metrics for monitoring"""
    
    def __init__(self):
        self.redis = redis_client
        self.prometheus_client = PrometheusClient()
    
    async def collect_metrics(self):
        """Collect current system metrics"""
        
        metrics = {
            'queue_depth_realtime': self.redis.xlen('signalscope_realtime'),
            'queue_depth_standard': self.redis.xlen('signalscope_standard'),
            'queue_depth_archive': self.redis.xlen('signalscope_archive'),
            'messages_processed_today': await self.get_daily_processed(),
            'reports_generated_today': await self.get_daily_reports(),
            'active_tickers': await self.get_active_tickers()
        }
        
        # Export to monitoring system
        for metric_name, value in metrics.items():
            self.prometheus_client.gauge(f'signalscope_{metric_name}', value)
        
        return metrics
```

## Scalability Considerations

### Horizontal Scaling
- Multiple Redis instances with sharding
- Celery worker auto-scaling
- Load-balanced webhook endpoints

### Performance Optimization
- Message compression in Redis
- Batch processing parallelization
- LLM response caching
- Database query optimization

### Cost Management
- Tiered processing based on user plans
- Token usage optimization
- Storage retention policies
- CDN for report delivery

## Security Measures

1. **Data Protection**
   - Encryption at rest (Redis, Supabase)
   - TLS for all communications
   - PII anonymization

2. **Access Control**
   - API key authentication
   - HMAC webhook signatures
   - Rate limiting per user

3. **Compliance**
   - GDPR data retention
   - Right to deletion
   - Audit logging

## Implementation Timeline

### Phase 1: Core Infrastructure (Week 1)
- Set up Redis streams
- Implement webhook receiver
- Basic message stacking
- Supabase schema

### Phase 2: Batch Processing (Week 2)
- Batching strategies
- Celery worker setup
- LLM integration
- Report generation

### Phase 3: Optimization (Week 3)
- Performance tuning
- Monitoring setup
- Alert system
- Dashboard integration

### Phase 4: Advanced Features (Week 4)
- ML-based batching
- Predictive insights
- Custom report templates
- API for third-party access

## Next Steps

1. **Immediate Actions**
   - Review and approve architecture
   - Set up development environment
   - Begin webhook receiver implementation

2. **Technical Decisions**
   - Confirm Redis vs. RabbitMQ for queuing
   - Choose monitoring stack (Prometheus/Grafana vs. DataDog)
   - Decide on LLM provider (OpenAI vs. Anthropic)

3. **Resource Requirements**
   - Redis instance (minimum 2GB RAM)
   - Celery workers (2-4 instances)
   - Supabase project (Pro plan recommended)
   - LLM API budget ($500/month estimated)