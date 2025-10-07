# Summary Enhancement Plan - Oversummarization Mitigation (Revised)

## Critical Discovery
After deep analysis, the codebase is using `summary_service_v2.py` (EnhancedSummaryService), NOT `summary_service.py`. The original plan targeted the wrong service. This document has been revised to address the actual implementation.

## Problem Overview
Users report that long (> 45-min) transcripts suffer from:
1. Shallow, executive-only summaries
2. Missing late sections (everything after ~30 mins gets dropped)

## Root Cause Analysis (Updated)

### What We Initially Thought:
- 12,000-character hard cap in `bucketed_text()` causing truncation
- Single-prompt approach hitting model limits
- No usage of semantic chunks

### What's Actually Happening:
The active `summary_service_v2.py` uses a 5-stage AI pipeline:
1. **Stage 1**: Content flow analysis
2. **Stage 2**: Dynamic section discovery
3. **Stage 3**: Context-aware content extraction
4. **Stage 4**: Synthesis with `max_tokens=min(4000, total_content_length * 2)`
5. **Stage 5**: Action item extraction

The oversummarization occurs because:
- **Token output cap**: Line 923 limits output to 4000 tokens max
- **Low temperature**: 0.1 encourages extreme compression
- **Section synthesis prompt**: Explicitly asks for "brief summary" and "Quality over quantity"
- **No semantic chunks**: The pipeline doesn't leverage the existing semantic chunks table

## Implementation Strategy - Three Phase Approach (Revised)

### Phase 1: Immediate Fixes (Week 1)
Fix the most obvious limiters in the synthesis stage.

### Phase 2: Enhanced Section Processing (Week 2)
Implement sliding window approach within the existing 5-stage pipeline.

### Phase 3: Semantic Chunk Integration (Week 3)
Leverage existing semantic chunks for better coverage.

## Detailed Implementation Guide

### **Phase 1: Immediate Fixes**

#### 1. Environment Variables (.env)
```bash
# Add these new variables
SUMMARY_MAX_TOKENS=8000          # Increase from hardcoded 4000
SUMMARY_TEMPERATURE=0.35         # Increase from 0.1
SUMMARY_MIN_TOKENS=2000          # Minimum output length
ENABLE_SECTION_BATCHING=false    # For Phase 2
USE_SEMANTIC_CHUNKS=false        # For Phase 3
SYNTHESIS_PROMPT_STYLE=detailed  # Switch from 'brief' to 'detailed'
```

#### 2. Update `app/services/summary_service_v2.py`

##### Fix 1: Synthesis Token Limit (Line ~923)
```python
# Current code around line 923:
chat_params = {
    "model": self.model,
    "messages": [{"role": "system", "content": synthesis_prompt}],
    "temperature": 0.1,  # Lower temperature to reduce hallucination
    "max_tokens": min(4000, total_content_length * 2)  # Limit tokens based on actual content
}

# CHANGE TO:
temperature = float(os.getenv("SUMMARY_TEMPERATURE", "0.35"))
max_tokens = int(os.getenv("SUMMARY_MAX_TOKENS", "8000"))
min_tokens = int(os.getenv("SUMMARY_MIN_TOKENS", "2000"))

chat_params = {
    "model": self.model,
    "messages": [{"role": "system", "content": synthesis_prompt}],
    "temperature": temperature,  # Higher for more detail
    "max_tokens": max(min_tokens, min(max_tokens, total_content_length * 3))  # More generous limit
}
```

##### Fix 2: Synthesis Prompt (Line ~850-920)
```python
# Modify the synthesis prompt generation to be less restrictive
# Around line 883, change:
synthesis_prompt = f"""...
⚠️ CRITICAL: If the provided content is limited, generate a proportionally brief summary. Quality and accuracy over quantity.
"""

# TO:
prompt_style = os.getenv("SYNTHESIS_PROMPT_STYLE", "detailed")

if prompt_style == "detailed":
    synthesis_prompt = f"""
You are a comprehensive content synthesizer. Your goal is to create a DETAILED and THOROUGH summary that preserves important information.

CONTENT TO SYNTHESIZE:
{chr(10).join(section_summaries)}

Generate a comprehensive summary with:

1. **EXECUTIVE OVERVIEW** - 2-3 paragraphs capturing ALL main themes and key points

2. **DETAILED SECTIONS** - For each section, provide:
   - Complete coverage of main points
   - Specific examples and details mentioned
   - Important quotes or statistics
   {chr(10).join([f"   - {s.split('SECTION: ')[1].split(chr(10))[0] if 'SECTION: ' in s else 'Unknown'}" for s in section_summaries])}

3. **KEY INSIGHTS & TAKEAWAYS** - Comprehensive list of all important insights

FORMAT:
<h3>Executive Overview</h3>
<p>[First paragraph with main themes]</p>
<p>[Second paragraph with supporting points]</p>

<h3>[Section Name]</h3>
<p>[Detailed coverage of this section's content]</p>
<p>[Additional important points from this section]</p>

[Continue for ALL sections...]

<h3>Key Insights & Takeaways</h3>
<ul>
<li>[Detailed insight with context]</li>
<li>[Another comprehensive point]</li>
[Include ALL significant insights]
</ul>

⚠️ IMPORTANT: Provide COMPREHENSIVE coverage. Include specific details, examples, and quotes. This is a detailed summary, not a brief overview.
"""
```

##### Fix 3: Content Extraction Enhancement (Line ~497)
```python
# In _extract_section_content method, increase the extraction window
# Current: Extracts limited content per section
# Add more context around each section

async def _extract_section_content(self, transcript_text: str, discovered_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract comprehensive content for each discovered section."""
    
    # Add configuration
    context_expansion = int(os.getenv("SECTION_CONTEXT_EXPANSION", "500"))  # chars before/after
    
    # ... existing code ...
    
    # When extracting content for each section, expand the window
    for section in discovered_sections:
        start_pos = max(0, section['start_position'] - context_expansion)
        end_pos = min(len(transcript_text), section['end_position'] + context_expansion)
        
        # Extract expanded content
        section_text = transcript_text[start_pos:end_pos]
        # ... rest of extraction logic
```

### **Phase 2: Enhanced Section Processing**

#### 3. Create Section Batching System

##### Add new method in `summary_service_v2.py`:
```python
async def _synthesize_comprehensive_summary_batched(self, section_content: List[Dict[str, Any]], 
                                                   discovered_sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process sections in batches to avoid token limits and ensure complete coverage."""
    
    if not os.getenv("ENABLE_SECTION_BATCHING", "false").lower() == "true":
        # Fall back to original method
        return await self._synthesize_comprehensive_summary(section_content, discovered_sections)
    
    batch_size = int(os.getenv("SECTION_BATCH_SIZE", "5"))
    all_summaries = []
    
    # Process sections in batches
    for i in range(0, len(section_content), batch_size):
        batch = section_content[i:i + batch_size]
        batch_sections = discovered_sections[i:i + batch_size]
        
        # Synthesize this batch
        batch_result = await self._synthesize_comprehensive_summary(batch, batch_sections)
        all_summaries.append(batch_result)
    
    # Merge all batch summaries
    if len(all_summaries) == 1:
        return all_summaries[0]
    
    # Final synthesis pass to merge
    return await self._merge_batch_summaries(all_summaries)

async def _merge_batch_summaries(self, batch_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple batch summaries into final comprehensive summary."""
    
    merge_prompt = f"""
Merge the following {len(batch_summaries)} partial summaries into one comprehensive summary.
Maintain all important details and ensure no information is lost.

PARTIAL SUMMARIES:
{chr(10).join([f"PART {i+1}:\n{s.get('summary_html', '')}" for i, s in enumerate(batch_summaries)])}

Create a unified, comprehensive summary that includes ALL information from ALL parts.
"""
    
    # Call LLM to merge
    response = await self._call_openai_api(merge_prompt, temperature=0.3)
    
    return {
        "summary_html": response.get("content", ""),
        "segments_processed": sum(s.get("segments_processed", 0) for s in batch_summaries),
        "processing_metadata": {
            "method": "batched_synthesis",
            "batches": len(batch_summaries)
        }
    }
```

### **Phase 3: Semantic Chunk Integration**

#### 4. Integrate Semantic Chunks into Content Extraction

##### Update `app/services/summary_service_v2.py`:
```python
# Add import at top
from app.services.storage_adapters.supabase_adapter import SupabaseAdapter

# Modify the __init__ method to include storage adapter
def __init__(self):
    # ... existing code ...
    self.storage_adapter = SupabaseAdapter() if os.getenv("USE_SEMANTIC_CHUNKS", "false").lower() == "true" else None

# Enhance _extract_section_content method
async def _extract_section_content(self, transcript_text: str, discovered_sections: List[Dict[str, Any]], 
                                 transcript_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extract content with optional semantic chunk enhancement."""
    
    # Original extraction
    section_content = await self._original_extract_section_content(transcript_text, discovered_sections)
    
    # Enhance with semantic chunks if available
    if self.storage_adapter and transcript_id and os.getenv("USE_SEMANTIC_CHUNKS", "false").lower() == "true":
        logger.info(f"Enhancing extraction with semantic chunks for {transcript_id}")
        
        # Check availability
        availability = await self.storage_adapter.check_semantic_chunks_availability(transcript_id)
        
        if availability.get("available"):
            # Get relevant chunks
            semantic_chunks = await self.storage_adapter.get_semantic_chunks_for_summary(transcript_id, limit=100)
            
            if semantic_chunks:
                # Enhance each section with relevant semantic chunks
                for section in section_content:
                    section_start = section.get("start_position", 0)
                    section_end = section.get("end_position", len(transcript_text))
                    
                    # Find chunks that overlap with this section
                    relevant_chunks = [
                        chunk for chunk in semantic_chunks
                        if chunk.get("start_position", 0) >= section_start - 500 and
                           chunk.get("end_position", 0) <= section_end + 500
                    ]
                    
                    if relevant_chunks:
                        # Append high-relevance chunk content
                        additional_content = "\n\n[SEMANTIC CONTEXT]\n" + \
                                           "\n---\n".join([c["text"] for c in relevant_chunks[:5]])
                        section["enhanced_content"] = section.get("content", "") + additional_content
                        section["semantic_chunks_used"] = len(relevant_chunks)
    
    return section_content
```

#### 5. Update Ingestion Pipeline to Pass transcript_id

##### Modify `app/services/ingestion_service.py`:
```python
# Around line 1153, update the generate_summary call:
summary_result = await self.summary_service.generate_summary(
    transcript_id=transcript_id,
    transcript_text=transcript_text,
    duration_seconds=derived_duration
)

# The router already passes transcript_id, but we need to ensure
# generate_enhanced_summary receives it properly
```

##### Update `app/services/summary_service_v2.py` router:
```python
# In SummaryServiceRouter.generate_summary method (line ~1682):
if use_enhanced:
    logger.info(f"📈 Using enhanced summary for {transcript_id}")
    return await self.service.synthesize_summary_enhanced(
        transcript_id, transcript_text, duration_seconds, **kwargs
    )
else:
    logger.info(f"📋 Using standard summary for {transcript_id}")
    # Pass transcript_id to generate_enhanced_summary
    result = await self.service.generate_enhanced_summary(transcript_text, transcript_id)
    return self.service._add_metadata(result, {'method': 'standard'})
```

### Configuration Updates

#### Update `.env.example`
```bash
# Summary Enhancement Settings
SUMMARY_MAX_TOKENS=8000             # Max tokens for synthesis output
SUMMARY_TEMPERATURE=0.35            # LLM temperature (0.1-1.0)
SUMMARY_MIN_TOKENS=2000             # Minimum output tokens
SYNTHESIS_PROMPT_STYLE=detailed     # 'brief' or 'detailed'
SECTION_CONTEXT_EXPANSION=500       # Extra chars around sections
ENABLE_SECTION_BATCHING=false       # Process sections in batches
SECTION_BATCH_SIZE=5                # Sections per batch
USE_SEMANTIC_CHUNKS=false           # Enhance with semantic chunks
```

### Testing Plan

1. **Unit Tests** (`tests/test_summary_v2_enhancement.py`)
```python
async def test_synthesis_respects_token_limits():
    """Ensure synthesis uses configured token limits."""
    
async def test_detailed_prompt_generation():
    """Test that detailed prompts are generated correctly."""
    
async def test_section_batching():
    """Test section batching for long transcripts."""
    
async def test_semantic_chunk_enhancement():
    """Test semantic chunk integration when available."""
```

2. **Integration Tests**
- Test with actual long transcripts (45min, 2hr)
- Verify no content is dropped
- Compare output length before/after changes

### Rollout Plan

**Week 1**: Phase 1
- Deploy with env var changes only
- Monitor summary length and quality

**Week 2**: Phase 2
- Enable `ENABLE_SECTION_BATCHING=true` for long transcripts
- A/B test batched vs non-batched

**Week 3**: Phase 3
- Enable `USE_SEMANTIC_CHUNKS=true` for premium users
- Measure impact on coverage and quality

### Success Metrics

1. **Coverage**: Average summary length increases by 80%+ for 1hr+ videos
2. **Completeness**: User complaints about missing sections drop to 0
3. **Quality**: No increase in hallucination reports
4. **Performance**: P95 generation time remains under 20 seconds

### Risk Mitigation

1. **Token Costs**: Increased output = higher costs. Monitor usage closely.
2. **Hallucination**: Higher temperature may increase hallucination. Keep validation.
3. **Breaking Changes**: All changes are behind env vars for easy rollback.
4. **Memory**: Batch processing may increase memory usage. Monitor closely.

> **Next Review**: After Phase 1 deployment

