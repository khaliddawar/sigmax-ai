# Field Name Reference Guide

This document provides a definitive reference for field names used across BPT services to prevent field name mismatches that can cause processing failures.

## 🎯 Critical Issue Context

**Recently Fixed Issue**: The transcript handler was using incorrect field names (`transcript_text` instead of `text` and `character_count` instead of calculating from `text`), causing the unified processing pipeline to retrieve empty text and fail.

**Symptoms**: 
- Webhook logs showed successful transcript fetching (e.g., "34,297 characters")
- Immediately followed by "Retrieved transcript text for X: 0 characters"
- Unified processing failed with "None" error

## 📋 SupabaseService Response Field Reference

### `get_transcript_text()` Response

**Correct Structure:**
```typescript
{
  "success": boolean,
  "transcript_id": string,
  "text": string,           // ✅ CORRECT: Full concatenated transcript text
  "chunk_count": number    // ✅ CORRECT: Number of chunks that were concatenated
}
```

**Common Mistakes:**
```typescript
{
  "transcript_text": string,  // ❌ WRONG: This field does NOT exist
  "character_count": number   // ❌ WRONG: This field does NOT exist
}
```

**Safe Access Pattern:**
```python
# ✅ CORRECT
text_result = await supabase.get_transcript_text(transcript_id)
if text_result.get("success"):
    transcript_text = text_result.get("text", "")
    character_count = len(transcript_text)
    chunk_count = text_result.get("chunk_count", 0)

# ❌ WRONG - These fields don't exist
transcript_text = text_result.get("transcript_text")  # Returns None!
character_count = text_result.get("character_count", 0)  # Returns 0!
```

### `store_transcript()` Response

**Structure:**
```typescript
{
  "success": boolean,
  "transcript_id": string,
  "chunks_stored": number,
  "processing_time": number
}
```

### `get_transcript_by_id()` Response

**Structure:**
```typescript
{
  "success": boolean,
  "data": {
    "transcript_id": string,
    "title": string,
    "source": string,
    "created_at": string,
    "metadata": object
  }
}
```

## 🔧 Service-Specific Field Patterns

### TranscriptHandler Service

The `TranscriptHandler` should use these patterns:

```python
# ✅ CORRECT logging pattern
async def get_transcript_text(self, transcript_id: str) -> Dict[str, Any]:
    result = await self.supabase_service.get_transcript_text(transcript_id)
    text_length = len(result.get("text", "")) if result.get("success") else 0
    logger.info(f"Retrieved transcript text for {transcript_id}: {text_length} characters")
    return result

# ✅ CORRECT text extraction in pipelines
text_result = await self.get_transcript_text(transcript_id)
transcript_text = text_result.get("text")  # NOT "transcript_text"
```

### IngestionService Patterns

```python
# ✅ CORRECT webhook processing
transcript_text = download_result.get("text", "")
metadata = {
    "word_count": len(transcript_text.split()),
    "character_count": len(transcript_text)  # Calculate, don't expect this field
}
```

### FirefliesClient Patterns

```python
# ✅ CORRECT Fireflies API response handling
transcript_data = data.get("data", {}).get("transcript")
text = sentence.get("raw_text", "").strip()
```

## 🛡️ Safe Field Access Patterns

### Using the FieldValidator Utility

```python
from app.services.field_validator import TranscriptFieldHelper, FieldValidator

# ✅ SAFE transcript text access
text_result = await supabase.get_transcript_text(transcript_id)
transcript_text = TranscriptFieldHelper.get_transcript_text(text_result)
character_count = TranscriptFieldHelper.get_transcript_length(text_result)

# ✅ SAFE logging
TranscriptFieldHelper.log_transcript_retrieval(transcript_id, text_result)

# ✅ SAFE general field access
value = FieldValidator.safe_get(
    data=response,
    field_name="text",
    expected_type=str,
    default="",
    required=True,
    context="transcript response"
)
```

### Without FieldValidator (Manual Safety)

```python
# ✅ SAFE manual pattern
def safe_get_transcript_text(response: Dict[str, Any]) -> str:
    if not response.get("success", False):
        logger.error(f"Response indicates failure: {response.get('error', 'Unknown error')}")
        return ""
    
    text = response.get("text")
    if not isinstance(text, str):
        logger.error(f"Expected string for 'text' field, got {type(text)}")
        return ""
    
    return text
```

## 📊 Database Schema Field Names

### `transcripts` Table
- `transcript_id` (TEXT PRIMARY KEY)
- `title` (TEXT)
- `source` (TEXT)  
- `created_at` (TIMESTAMPTZ)
- `metadata` (JSONB)

### `transcript_chunks` Table
- `id` (BIGSERIAL PRIMARY KEY)
- `transcript_id` (TEXT REFERENCES transcripts)
- `chunk_index` (INTEGER)
- `text` (TEXT) - ✅ This is the field that gets concatenated
- `metadata` (JSONB)
- `embedding` (VECTOR) - if pgvector enabled

### `semantic_chunks` Table
- `id` (BIGSERIAL PRIMARY KEY)
- `transcript_id` (TEXT)
- `chunk_index` (INTEGER)
- `text` (TEXT)
- `embedding` (VECTOR)
- `metadata` (JSONB)

## 🚨 Common Pitfalls

### 1. Assuming Field Names
```python
# ❌ DON'T assume field names without checking service implementation
result = service.get_data()
value = result["expected_field"]  # Might not exist!

# ✅ DO check service code or use safe accessors
value = result.get("expected_field", default_value)
```

### 2. Not Validating Response Structure
```python
# ❌ DON'T trust response structure
text = response["text"]  # Might throw KeyError

# ✅ DO validate responses
if response.get("success") and "text" in response:
    text = response["text"]
else:
    logger.error(f"Invalid response: {response}")
    text = ""
```

### 3. Mixing Old and New Field Names
```python
# ❌ DON'T mix deprecated field names
if "transcript_text" in response:  # Old field name
    text = response["transcript_text"]
else:
    text = response.get("text", "")  # New field name

# ✅ DO use consistent field names
text = response.get("text", "")  # Always use the correct current field name
```

## 🔄 Migration Strategy

### For Existing Code

1. **Identify Risky Patterns**: Search for `.get("transcript_text")` and `.get("character_count")`
2. **Gradual Adoption**: Start using `TranscriptFieldHelper` in new code
3. **Update Logging**: Replace manual logging with `TranscriptFieldHelper.log_transcript_retrieval()`
4. **Test Thoroughly**: Ensure changes don't break existing functionality

### Code Search Commands

```bash
# Find potential field name issues
grep -r "transcript_text" app/services/
grep -r "character_count" app/services/
grep -r "\.get(" app/services/ | grep -E "(transcript|text|count)"

# Find services that might need validation
grep -r "get_transcript_text" app/services/
```

## 📝 Code Review Checklist

When reviewing transcript-related code, check:

- [ ] Uses `text_result.get("text")` not `text_result.get("transcript_text")`
- [ ] Calculates character count from text length, doesn't assume `character_count` field
- [ ] Validates response success before accessing fields
- [ ] Uses type hints for response structures
- [ ] Includes proper error handling for missing fields
- [ ] Logs field access issues appropriately
- [ ] Uses consistent field names across the service

## 🎯 Quick Reference

| **Context** | **Correct Field** | **Wrong Field** |
|-------------|------------------|-----------------|
| Transcript text content | `text` | `transcript_text` |
| Text length calculation | `len(text)` | `character_count` |
| Chunk count | `chunk_count` | `chunks_count` |
| Success status | `success` | `status` |
| Error message | `error` | `message` |

---

**Remember**: When in doubt, check the actual service implementation rather than assuming field names. The `SupabaseService.get_transcript_text()` method is the source of truth for transcript text response structure. 