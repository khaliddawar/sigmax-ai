# SignalScope Backend

Trading Intelligence Processing Pipeline for SignalScope Chrome Extension

## Overview

This backend service receives trading chat messages from the SignalScope Chrome Extension, processes them through an intelligent batching system, generates AI-powered reports using LLMs, and stores the results in Supabase.

## Architecture

```
Chrome Extension → Webhook → FastAPI → Redis Queue → Batch Processor → LLM → Supabase → Reports
```

### Key Components

1. **FastAPI Application** - RESTful API for webhook reception and report access
2. **Redis Streams** - Message queuing with 3-tier priority system
3. **Celery Workers** - Async batch processing and LLM orchestration
4. **Supabase** - PostgreSQL database for persistent storage
5. **LLM Integration** - OpenAI/Anthropic for report generation

## Features

- **Real-time Message Processing**: HMAC-verified webhook endpoint
- **Smart Batching**: Time, volume, and context-based message grouping
- **3-Tier Priority System**:
  - Realtime (importance ≥ 8): 5-minute batches
  - Standard (importance 5-7): 15-minute batches
  - Archive (importance < 5): 60-minute batches
- **AI Report Generation**:
  - Real-time alerts for urgent signals
  - Hourly market summaries
  - Daily comprehensive reports
- **Token Optimization**: Intelligent context reduction for cost efficiency
- **Monitoring**: Prometheus metrics and structured logging

## Installation

### Prerequisites

- Python 3.11+
- Redis 7+
- Docker & Docker Compose (optional)
- Supabase account (for database)
- OpenAI/Anthropic API keys

### Local Setup

1. Clone the repository:
```bash
cd signalscope-backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run Redis (using Docker):
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

6. Start the application:
```bash
uvicorn app.main:app --reload
```

### Docker Setup

1. Build and run with Docker Compose:
```bash
docker-compose up -d
```

This starts:
- Redis (port 6379)
- FastAPI backend (port 8000)
- Celery worker
- Celery beat scheduler
- Flower monitoring (port 5555)

## API Endpoints

### Webhooks
- `POST /api/webhooks/signalscope` - Receive messages from Chrome Extension
- `GET /api/webhooks/status` - Webhook service status

### Reports
- `GET /api/reports/latest` - Get latest reports
- `GET /api/reports/{report_id}` - Get specific report
- `POST /api/reports/generate` - Trigger manual report generation
- `GET /api/reports/ticker/{ticker}` - Reports by ticker
- `GET /api/reports/stats/summary` - Report statistics

### System
- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus metrics
- `GET /docs` - Interactive API documentation

## Configuration

### Environment Variables

Key configuration in `.env`:

```env
# Security
WEBHOOK_SECRET=your-webhook-hmac-secret

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM Providers
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# Batch Processing
REALTIME_BATCH_SECONDS=300
STANDARD_BATCH_SECONDS=900
ARCHIVE_BATCH_SECONDS=3600
```

## Database Schema

### Tables (Supabase)

```sql
-- messages: Raw captured data
-- message_batches: Batch tracking
-- reports: Generated intelligence
-- report_subscriptions: Distribution config
```

See `MESSAGE_STACKING_ARCHITECTURE.md` for complete schema.

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black app/
ruff check app/
```

### Monitoring

- **Flower UI**: http://localhost:5555 (Celery monitoring)
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

## Deployment

### Production Checklist

1. Set secure `SECRET_KEY` and `WEBHOOK_SECRET`
2. Configure production database (Supabase)
3. Set up Redis cluster or managed Redis
4. Configure SSL/TLS certificates
5. Set up monitoring (Prometheus/Grafana)
6. Configure rate limiting
7. Set up backup strategy

### Scaling

- Horizontal scaling with multiple Celery workers
- Redis Cluster for high availability
- Load balancer for API endpoints
- CDN for report distribution

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## License

MIT

## Support

For issues and questions, please open a GitHub issue.