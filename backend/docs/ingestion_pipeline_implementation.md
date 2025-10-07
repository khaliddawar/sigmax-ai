# Transcript Processing Pipeline Implementation

## Overview

This document describes the implementation of the complete transcript processing pipeline for BPT (Big Picture Trading). The pipeline processes transcripts from Fireflies.ai, generates summaries, extracts trade information, and delivers the results via email.

## Architecture

The ingestion pipeline consists of the following components:

1. **Webhook Handler**: Receives notifications from Fireflies.ai when a new transcript is available
2. **Transcript Processor**: Downloads and processes the transcript into manageable chunks
3. **Embedding Service**: Generates vector embeddings for transcript chunks
4. **Summary Service**: Uses LLM to generate concise summaries of the transcript
5. **Trade Extraction Service**: Extracts trading information (tickers, prices, etc.)
6. **Email Service**: Formats and sends email notifications to subscribers

## Storage Options

The system supports two storage options for transcripts and related data:

1. **Supabase with pgvector** (Primary): When properly configured, Supabase provides vector search capabilities for efficient similarity search of transcript chunks.

2. **Local File Storage** (Fallback): If Supabase is not configured, the system automatically falls back to a simple file-based storage system. This stores:
   - Transcripts as JSON files in `data/transcripts/`
   - Chunks as JSON files in `data/chunks/{transcript_id}/`
   - Embeddings as JSON files in `data/embeddings/{transcript_id}/`
   - Trades as JSON files in `data/trades/{transcript_id}/`

The system automatically selects the appropriate storage method, prioritizing Supabase when available.

## Implementation Details

### Webhook Handler

The webhook handler is implemented in `app/main.py` and provides an endpoint at `/webhook/fireflies` to receive notifications from Fireflies.ai. When a notification is received, it validates the payload and queues a background task to process the transcript.

### Ingestion Service

The core of the pipeline is the `IngestionService` class in `app/services/ingestion_service.py`. This service orchestrates the entire process, tracking progress and handling errors. It follows these steps:

1. Download the transcript from the provided URL
2. Process the transcript into semantic chunks
3. Generate embeddings for the chunks using OpenAI
4. Store the transcript and embeddings in Supabase or local file storage
5. Generate a summary of the transcript
6. Extract trade information from the transcript
7. Send email notifications to subscribers

### Mock Mode

All services support a "mock mode" that can be enabled by setting environment variables:
- `USE_MOCK_OPENAI=true`
- `USE_MOCK_SUPABASE=true`
- `USE_MOCK_EMAIL=true`

This allows testing the pipeline without requiring external services.

## Configuration

The pipeline requires several environment variables to be set:

### Required
- `OPENAI_API_KEY`: For embedding and summary generation

### Optional (for Supabase)
- `SUPABASE_URL`: For Supabase database access
- `SUPABASE_KEY`: For Supabase database access

### Optional (for email)
- `SMTP_SERVER`: SMTP server for sending emails (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP port (default: 587)
- `SMTP_USERNAME`: SMTP username for authentication
- `SMTP_PASSWORD`: SMTP password for authentication
- `SENDER_EMAIL`: Email address to send from
- `ADMIN_EMAIL`: Default recipient if no subscribers are found

## Usage

### Running the Server

To run the server with the ingestion pipeline enabled:

```bash
# Run with real services
python run_with_ingestion.py

# Run in mock mode
python run_with_ingestion.py --mock

# Run with specific environment file
python run_with_ingestion.py --env .env.local
```

### Testing the Pipeline

To test the ingestion pipeline with the sample webhook data:

```bash
# Test with real services
python scripts/test_ingestion_pipeline.py

# Test in mock mode
python scripts/test_ingestion_pipeline.py --mock
```

## Testing the Webhook

You can test the webhook endpoint by sending a POST request to the `/webhook/fireflies` endpoint with sample data:

### Using PowerShell

```powershell
$payload = Get-Content -Raw -Path sample_fireflies_webhook.json
Invoke-RestMethod -Uri 'http://localhost:8000/webhook/fireflies' -Method Post -Body $payload -ContentType 'application/json'
```

### Using curl (Linux/Mac)

```bash
curl -X POST http://localhost:8000/webhook/fireflies \
  -H "Content-Type: application/json" \
  -d @sample_fireflies_webhook.json
```

### Expected Response

```json
{
  "status": "success",
  "message": "Webhook received and processing started",
  "transcript_id": "ff_sample_12345"
}
```

### Verifying Results

After the webhook is processed, you can check:

1. **File Storage (when using --file-storage)**:
   ```
   data/
   ├── transcripts/
   │   └── ff_sample_12345.json  # Transcript metadata and summary
   ├── chunks/
   │   └── ff_sample_12345/      # Text chunks with context
   ├── embeddings/
   │   └── ff_sample_12345/      # Vector embeddings
   └── trades/
       └── ff_sample_12345/      # Extracted trades
   ```

2. **Supabase (when using Supabase storage)**:
   - Check the `transcripts` table for the transcript metadata
   - Check the `transcript_chunks` table for the chunks with embeddings
   - Check the `trades` table for extracted trades

3. **Email Delivery**:
   - When not in mock mode and SMTP is configured, an email is sent to subscribers

## Search Capabilities

The system supports two methods for searching transcript content:

1. **Vector Similarity Search** (with Supabase): When Supabase is configured with pgvector, the system uses embedding-based similarity search for highly accurate retrieval of relevant content.

2. **Keyword Search** (with File Storage): When using file storage, the system falls back to a basic keyword-based search that extracts important terms from the query and matches them against transcript chunks.

## Extending the Pipeline

The pipeline is designed to be modular and extensible. To add new features:

1. Create a new service in `app/services/`
2. Add the service to the `IngestionService` class
3. Update the `start_ingestion_pipeline` function to include the new service

## Troubleshooting

If the pipeline fails, check the logs for error messages. Common issues include:

- Missing API keys or environment variables
- Network connectivity issues
- Rate limiting from external services

In development, you can use mock mode to isolate and test individual components.

## Future Improvements

Potential improvements to the pipeline include:

1. Add support for additional transcript sources beyond Fireflies.ai
2. Implement caching to avoid regenerating embeddings for unchanged content
3. Add support for multiple LLM providers
4. Improve error recovery and retry mechanisms
5. Add monitoring and alerting for pipeline health
6. Enhance the file storage system with better indexing and search capabilities 