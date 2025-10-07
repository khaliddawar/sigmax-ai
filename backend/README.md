# BPT (Business Process Transcription)

<!-- Auto-deployment test: 2025-01-09 -->

A sophisticated AI-powered platform for transcribing, processing, and analyzing business conversations and meetings with **advanced anti-hallucination validation**, **webhook security**, and **Fireflies-style formatting**. Built for production-scale financial transcript analysis with comprehensive Q&A capabilities.

> **📋 For detailed project structure, see [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)**

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key
- Supabase account
- Fireflies API key (for webhook integration)

### Installation

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd BPT
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   # Production API (Railway deployment)
   python app/main.py

   # Local development with Streamlit
   streamlit run app/web/streamlit_app.py

   # With specific features
   python development/runners/run_with_ingestion.py
python development/runners/run_with_auth.py
   ```

## 🏗️ System Overview

### Current Architecture (v3.0.0-production) ⚡ ENHANCED!

#### 🎯 **Core Features**
- **🔒 Anti-Hallucination System**: Advanced LLM validation with boundary checking and confidence scoring
- **🔐 Webhook Security**: Timestamp-based signature validation for Fireflies integration
- **📧 Email Pipeline**: Automated summary delivery with professional Fireflies-style formatting
- **🔍 Q&A System**: Semantic search with hybrid retrieval and context-aware responses
- **⚡ Real-time Processing**: Webhook-triggered transcript ingestion and analysis

#### 🛡️ **Security & Validation**
- **Boundary Validation**: Prevents AI hallucination with timestamp and content verification
- **Webhook Authentication**: Secure signature validation with replay attack prevention
- **Duplicate Handling**: Robust transcript deduplication with constraint violation prevention
- **Error Recovery**: Explicit failure handling without fallback arrangements

#### 🎨 **Enhanced Formatting**
- **Fireflies-Style Output**: Professional bullet points and section organization
- **Markdown Processing**: Automatic conversion to HTML with proper spacing
- **Email Optimization**: CSS styling for cross-client compatibility
- **Responsive Design**: Mobile-friendly email templates

## 📊 System Components

### 🔧 **Core Services**

#### **Summary Generation (Enhanced v2)**
- `summary_service_v2.py` - Advanced summary generation with validation
- `enhanced_prompt_engine.py` - Dynamic prompt management
- `dynamic_section_analyzer.py` - AI-powered section discovery
- `validation/llm_validator.py` - Anti-hallucination validation

#### **Ingestion Pipeline**
- `ingestion_service.py` - Unified transcript processing
- `transcript_handler.py` - Fireflies webhook handling
- `webhook_security.py` - Signature validation and security
- `fireflies_client.py` - API integration

#### **Data & Storage**
- `supabase_client.py` - Database operations with duplicate handling
- `embedding_service.py` - Vector embeddings for semantic search
- `semantic_chunker.py` - Intelligent text segmentation

#### **Communication**
- `email_service.py` - Professional email delivery
- `slack_service.py` - Slack integration
- `trade_service.py` - Financial trade extraction

### 🌐 **API Endpoints**

#### **Transcript Processing**
- `POST /webhook/fireflies` - Secure webhook endpoint
- `POST /transcripts/upload` - Manual transcript upload
- `GET /transcripts/{id}` - Retrieve transcript details

#### **Q&A System**
- `POST /qa/ask` - Semantic question answering
- `GET /qa/history` - Query history
- `POST /qa/feedback` - Response feedback

#### **Administration**
- `GET /health` - System health check
- `POST /admin/reprocess` - Reprocess transcripts
- `GET /admin/stats` - System statistics

## 🔧 Configuration

### Environment Variables

#### **Required API Keys**
```bash
# AI Services
OPENAI_API_KEY=sk-...
FIREFLIES_API_KEY=387d9f8c-...

# Database
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...

# Email Service
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
```

#### **System Configuration**
```bash
# Anti-Hallucination System
ENABLE_ANTI_HALLUCINATION=true
VALIDATION_ROLLOUT_PERCENT=100
ALLOW_NO_TIMESTAMPS=true
DEFAULT_TRANSCRIPT_DURATION=3600

# Processing Limits
MAX_SAFE_TOKENS=64000
MAX_DISCOVERY_CHARS=0
MAX_SYNTHESIS_CHARS=0

# Domain Configuration
DOMAIN_TYPE=financial
SERVICE_TYPE=fastapi
```

## 🚀 Deployment

### Railway Deployment (Production)

**⚠️ CRITICAL DEPLOYMENT RULE**: Never deploy directly using `railway up`. Always follow this workflow:

1. **Make changes locally**
2. **Commit to git**: `git add -A && git commit -m "your changes"`
3. **Push to GitHub**: `git push origin master`
4. **Let Railway auto-deploy** from GitHub

This prevents dangerous sync issues between local, GitHub, and Railway environments.

### Local Development

```bash
# Start backend
python app/main.py

# Start frontend (separate terminal)
streamlit run app/web/streamlit_app.py

# Run with specific configurations
ENABLE_ANTI_HALLUCINATION=true python app/main.py
```

## 📈 Recent Enhancements

### ✅ **Anti-Hallucination System (v3.0)**
- **Boundary Validation**: Prevents timestamps exceeding transcript duration
- **Content Verification**: Validates AI-generated content against source material
- **Confidence Scoring**: Provides reliability metrics for generated summaries
- **Circuit Breaker**: Limits regeneration attempts to prevent infinite loops

### ✅ **Webhook Security Enhancement**
- **Signature Validation**: Timestamp-based security with replay attack prevention
- **Multiple Format Support**: Compatible with Stripe, GitHub, and Fireflies webhooks
- **Test Utilities**: Comprehensive testing tools for webhook validation

### ✅ **Fireflies-Style Formatting**
- **Professional Output**: Organized bullet points and section headings
- **Markdown Processing**: Automatic HTML conversion with proper spacing
- **Email Optimization**: Cross-client CSS styling for beautiful emails

### ✅ **Project Cleanup**
- **Removed 50+ test files** from root and scripts directories
- **Cleaned up obsolete** documentation and sample data
- **Organized codebase** while maintaining full functionality

## 🔍 Monitoring & Debugging

### Health Checks
```bash
# System health
curl https://bpt-production.up.railway.app/health

# Database connectivity
curl https://bpt-production.up.railway.app/health/db

# Service status
curl https://bpt-production.up.railway.app/admin/stats
```

### Logs & Debugging
- **Railway Logs**: Monitor via Railway dashboard
- **Validation Logs**: Anti-hallucination system provides detailed error reporting
- **Webhook Logs**: Comprehensive security and processing logs

## 📚 Documentation

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Complete codebase structure
- **[docs/](docs/)** - Technical documentation and guides
- **[config/prompts/](config/prompts/)** - AI prompt configurations

## 🤝 Contributing

1. Follow the deployment workflow (no direct Railway deployment)
2. Maintain anti-fallback principles (explicit failures over silent degradation)
3. Add comprehensive tests for new features
4. Update documentation for significant changes

## 📄 License

This project is proprietary software for Big Picture Trading analysis and processing.

---

**Built with ❤️ for professional financial transcript analysis** 