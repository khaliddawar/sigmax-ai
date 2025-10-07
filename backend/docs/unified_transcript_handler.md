# Unified Transcript Handler

The Unified Transcript Handler provides a single interface for processing stored transcripts for both Q&A (Streamlit) and email pipeline purposes.

## Overview

Previously, BPT had two separate processing paths:
1. **Streamlit Upload** → Q&A pipeline (vector search, semantic chunking)
2. **Webhook Ingestion** → Email pipeline (summary, trades, email notifications)

The new **Unified Transcript Handler** allows any stored transcript to be processed through both pipelines, enabling:
- **Dual processing**: Vector search capability + Email notifications
- **Consistent storage**: All transcripts stored the same way
- **Flexible routing**: Choose Q&A, Email, or both pipelines

## Architecture

```
Transcript Source (Upload/Webhook)
       ↓
   Store in Database
       ↓
TranscriptHandler.process_dual_pipeline()
       ↓                    ↓
   Q&A Pipeline      Email Pipeline
   (Vector Search)   (Summary + Email)
```

## Features

### Safe Integration
- **Feature flag controlled**: `USE_UNIFIED_TRANSCRIPT_HANDLER=true/false`
- **Backward compatible**: Falls back to original pipeline if new handler fails
- **No existing code modified**: All original functionality preserved

### Processing Options
- `process_for_qa_pipeline()`: Semantic chunking + vector storage for Streamlit
- `process_for_email_pipeline()`: Summary + trades + email notifications  
- `process_dual_pipeline()`: Both pipelines in sequence

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Enable unified transcript handler (default: false)
USE_UNIFIED_TRANSCRIPT_HANDLER=true

# Required for full functionality
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Optional for email pipeline
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
ADMIN_EMAIL=admin@yourcompany.com
```

### MCP Configuration

For Cursor/MCP integration, add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bpt": {
      "env": {
        "USE_UNIFIED_TRANSCRIPT_HANDLER": "true",
        "OPENAI_API_KEY": "your_openai_key",
        "SUPABASE_URL": "your_supabase_url",
        "SUPABASE_KEY": "your_supabase_key"
      }
    }
  }
}
```

## Usage

### 1. Webhook Processing (Fireflies)

When `USE_UNIFIED_TRANSCRIPT_HANDLER=true`:

```python
# Webhook receives Fireflies notification
# → Fetches transcript text from Fireflies API  
# → Stores transcript in database
# → Processes with unified handler:
#   - Creates semantic chunks for Q&A
#   - Generates summary and extracts trades
#   - Sends email notifications
```

**Benefits:**
- Webhook transcripts become searchable in Streamlit
- Maintains email notifications
- Single processing path for consistency

### 2. Manual Processing

```python
from app.services.transcript_handler import TranscriptHandler

# Initialize handler
handler = TranscriptHandler(
    supabase_service=supabase_service,
    embedding_service=embedding_service, 
    semantic_service=semantic_service
)

# Process for Q&A only
qa_result = await handler.process_for_qa_pipeline(transcript_id)

# Process for email only  
email_result = await handler.process_for_email_pipeline(
    transcript_id, 
    meeting_title="Custom Title",
    metadata={"custom": "data"}
)

# Process for both
dual_result = await handler.process_dual_pipeline(transcript_id)
```

### 3. Testing

```bash
# Safe dry-run test (read-only)
python scripts/test_transcript_handler.py

# Test actual processing (modifies database, sends emails)
python scripts/test_transcript_handler.py --run-all
```

## Benefits

### For End Users
- **Streamlit**: Can search ALL transcripts (uploaded + webhook)  
- **Email**: Continues to work as before
- **Consistency**: Same processing quality for all transcript sources

### For Developers
- **DRY**: Single codebase for transcript processing
- **Maintainable**: Updates apply to both pipelines
- **Extensible**: Easy to add new processing types

## Migration Path

### Phase 1: Enable Safely (Current)
```bash
USE_UNIFIED_TRANSCRIPT_HANDLER=false  # Default, original behavior
```

### Phase 2: Test New Handler  
```bash
USE_UNIFIED_TRANSCRIPT_HANDLER=true   # Test with new transcripts
```

### Phase 3: Full Adoption
```bash
# Process existing transcripts through unified handler
python scripts/migrate_existing_transcripts.py
```

## Monitoring

### Logs
The unified handler provides detailed logging:

```
INFO - Using unified transcript handler for meeting 123
INFO - Stored transcript 123 in database for unified processing  
INFO - 🎉 Unified processing completed successfully for meeting 123
INFO -    Q&A pipeline: ✅
INFO -    Email pipeline: ✅
INFO -    Total time: 45.2s
```

### Fallback Behavior
If unified processing fails, automatically falls back to original pipeline:

```
WARNING - TranscriptHandler not available: ImportError
INFO - Falling back to original processing pipeline
INFO - ✅ Original pipeline completed successfully
```

## Database Impact

### New Tables Used
- `semantic_chunks`: For Q&A vector search
- `transcripts`: Metadata storage (existing)
- `transcript_chunks`: Fallback chunk storage (existing)

### Data Flow
1. Transcript stored in `transcripts` + `transcript_chunks`
2. Q&A pipeline creates `semantic_chunks` with embeddings
3. Email pipeline reads from `transcripts` for summary/trades

## Troubleshooting

### Common Issues

**Issue**: `TranscriptHandler not available`
**Solution**: Ensure `app/services/transcript_handler.py` exists and imports work

**Issue**: `semantic_service not initialized`  
**Solution**: Check `SUPABASE_URL` and `SUPABASE_KEY` environment variables

**Issue**: `Failed to generate embeddings`
**Solution**: Verify `OPENAI_API_KEY` is set and valid

**Issue**: Email pipeline fails
**Solution**: Check SMTP configuration and `ADMIN_EMAIL` setting

### Force Original Pipeline
```bash
USE_UNIFIED_TRANSCRIPT_HANDLER=false
```

### Debug Mode
```bash
LOG_LEVEL=DEBUG
python scripts/test_transcript_handler.py --run-all
```

## Future Enhancements

- **Batch processing**: Process multiple transcripts in parallel
- **Custom pipelines**: Define custom processing workflows  
- **Analytics**: Track processing performance and success rates
- **Streaming**: Real-time processing for live transcripts 