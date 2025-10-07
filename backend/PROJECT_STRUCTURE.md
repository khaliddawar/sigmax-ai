# Simply Project Structure

## Overview
Simply (TubeVibe) is a comprehensive YouTube video processing and AI-powered analysis platform featuring a FastAPI backend, Chrome extension integration, and advanced RAG capabilities for intelligent content summarization and analysis.

## Directory Structure

### **Root Level**
- `app/` - Main FastAPI application (BPT Pipeline API)
- `extension/` - Chrome extension source code (TubeVibe)
- `config/` - Configuration files and domain-specific settings
- `scripts/` - Utility scripts, database setup, and development tools
- `tests/` - Test files and integration testing infrastructure
- `deployment/` - Docker containers and deployment configurations
- `docs/` - Comprehensive documentation and implementation guides

### **app/** - Main Application (FastAPI Backend)
- `main.py` - FastAPI application entry point with lifespan management
- `settings.py` - Application configuration and environment management
- `routes/` - Modular API route definitions
- `services/` - Core business logic and service layer
- `middleware/` - Security, observability, and custom middleware
- `models/` - Pydantic data models and schemas
- `utils/` - Shared utility functions and helpers
- `web/` - Streamlit web interface components
- `templates/` - Email and HTML templates

### **app/routes/** - API Endpoints (8 route modules)
Modular REST API structure:
- `auth_routes.py` - Authentication and user management
- `youtube_routes.py` - YouTube video processing and ingestion
- `transcript_routes.py` - Transcript management and processing
- `qa_routes.py` - RAG-based question answering endpoints
- `payment_routes.py` - Paddle payment integration and webhooks
- `health_routes.py` - Health checks and system monitoring
- `admin.py` - Administrative functions and user management
- `debug_routes.py` - Development and debugging utilities

### **app/services/** - Core Business Logic (40+ services)
Comprehensive service layer with specialized components:

**Core Processing Services:**
- `transcript_processor.py` - Main transcript processing pipeline
- `ingestion_service.py` - Content ingestion and pipeline orchestration
- `summary_service.py` & `summary_service_v2.py` - AI-powered summarization
- `embedding_service.py` - Vector embedding generation and management
- `semantic_chunker.py` & `semantic_chunks_service.py` - Intelligent text segmentation

**Database & Storage:**
- `supabase_client.py` - Supabase database operations and queries
- `storage_adapters/supabase_adapter.py` - Storage abstraction layer
- `storage/` - Text and vector storage operations

**AI & Retrieval:**
- `retrieval_qa_service.py` - RAG-based question answering
- `retrieval/` - Advanced retrieval system (coordinator, reranking, validation)
- `summarization/generator.py` - Content summarization engine
- `validation/` - Content validation and error correction

**Authentication & Payments:**
- `auth_service.py` - User authentication and authorization
- `paddle_service.py` - Paddle payment processing and webhooks
- `quota_service.py` - Usage quota management and enforcement

**Communication & Integration:**
- `email_service.py` & `postmark_email_service.py` - Email delivery systems
- `queue_service.py` - Redis-based background job processing
- `slack_service.py` - Slack integration for notifications

**Infrastructure:**
- `dependency_container.py` - Dependency injection and service management
- `webhook_security.py` - Webhook validation and security

### **extension/** - Chrome Extension (TubeVibe v1.0.4)
Production-ready Chrome extension with Manifest V3:

- `simply/` - Main extension source code
  - `background.js` - Service worker for extension lifecycle
  - `content.js` - Main content script for YouTube integration
  - `manifest.json` - Extension configuration and permissions
  - `contents/` - Specialized content scripts (embedded popup, transcript handling)
  - `utils/` - Security, storage, and utility modules (13 files)
  - `assets/` - Icons and static resources
  - `styles/` - CSS styling and design tokens
  - `scripts/` - Build and deployment automation
  - `package.json` - NPM dependencies and build scripts

**Extension Features:**
- OAuth2 authentication with Google
- YouTube video metadata extraction
- Real-time transcript processing
- AI summary generation
- Secure storage and token management
- Payment integration with Paddle

### **config/** - Configuration Management
Domain-specific configurations and AI prompts:
- `config.py` & `domain_loader.py` - Configuration loading and management
- `domains/` - Domain-specific settings
  - `financial.yaml` - Financial content analysis prompts
  - `medical.yaml` - Medical content processing rules
  - `generic.yaml` - General-purpose content settings
- `prompts/` - AI prompt templates
  - `content_synthesis.yaml` - Content generation prompts
  - `section_discovery.yaml` - Section analysis and extraction
  - `validation_prompts.yaml` - Content validation templates

### **scripts/** - Utility Scripts & Development Tools (80+ files)
Comprehensive tooling for development and operations:

**Database & Infrastructure:**
- `setup_database.py` & `setup_pgvector.py` - Database initialization
- `migration/` - Database schema migrations and updates
- `check_database_structure.py` - Database health monitoring

**Development Servers:**
- `servers/` - Development server runners and configurations
- `start_server.py`, `start_streamlit.py` - Application startup scripts

**Testing & Validation:**
- `test_*.py` (20+ files) - Comprehensive testing utilities
- `validate_environment.py` - Environment validation

**Processing & Analysis:**
- `processing/` - Data processing and transcript analysis tools
- Various PowerShell scripts for Windows development

### **tests/** - Testing Infrastructure (24 test files)
Comprehensive testing coverage:
- `test_extension_integration.py` - Chrome extension integration tests
- `test_full_pipeline.py` - End-to-end pipeline testing
- `test_youtube_api.py` - YouTube API integration tests
- `test_simple_curl.py` - Basic API endpoint tests
- `test_paddle_webhook.py` - Payment webhook testing
- `test_auth_*.py` - Authentication system tests
- Multiple PowerShell and JavaScript test files

### **docs/** - Documentation (45+ documents)
Centralized documentation and guides:
- Implementation guides and technical documentation
- Deployment and configuration guides
- Authentication and payment integration docs
- Email templates and formatting examples
- Architecture summaries and improvement plans

### **deployment/** - Production Deployment
Docker and cloud deployment configurations:
- `Dockerfile` - Main application container
- `docker-compose.yml` - Multi-service orchestration
- `render.yaml` & `render-with-worker.yaml` - Render.com configurations
- `railway.json` - Railway deployment settings
- Environment templates and CLI tools

## Key Features & Capabilities

### **YouTube Integration**
- Chrome extension with seamless YouTube integration
- Automatic transcript extraction and enhancement
- Real-time video processing with job status tracking
- OAuth2 authentication and secure user management

### **AI-Powered Analysis**
- Advanced RAG (Retrieval-Augmented Generation) system
- Multi-domain content analysis (financial, medical, generic)
- Intelligent summarization with multiple strategies
- Question answering with source attribution and validation

### **Production Architecture**
- Microservices-based design with dependency injection
- Async/await throughout for high performance
- Redis-based background job processing
- Comprehensive error handling and structured logging
- Circuit breaker patterns and observability middleware

### **Payment & Subscription System**
- Paddle payment processing integration
- Quota management and usage enforcement
- Subscription lifecycle management
- Webhook security and validation

### **Security & Compliance**
- OAuth2 authentication with Google
- Secure token management and storage
- CSP (Content Security Policy) enforcement
- Input validation and sanitization
- Webhook signature verification

## Development Workflow

1. **Environment Setup**: Configure environment variables and run `scripts/setup_database.py`
2. **Development**: Use development servers in `scripts/servers/`
3. **Testing**: Execute comprehensive test suites in `tests/`
4. **Extension Development**: Build with `cd extension/simply && npm run build:prod`
5. **Deployment**: Use Docker configurations in `deployment/`

## Technology Stack

- **Backend**: FastAPI 0.115+, Python 3.11+, Uvicorn
- **Database**: Supabase (PostgreSQL + pgvector for embeddings)
- **Queue System**: Redis + Celery for background processing
- **AI/ML**: OpenAI GPT models, Anthropic Claude, custom embedding pipeline
- **Frontend**: Streamlit web interface + Chrome Extension
- **Extension**: Manifest V3, Vanilla JavaScript (no framework)
- **Deployment**: Docker, Render.com, Railway
- **Monitoring**: Structured logging, health checks, metrics collection

This architecture supports a complete YouTube video processing pipeline from browser-based content capture to AI-powered analysis and user interaction, designed for production scale and reliability. 