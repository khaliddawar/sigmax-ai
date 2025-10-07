"""
TranscriptProcessor
• Accepts str, Path (.txt) or JSON payload (future Fireflies webhook)
• Splits into paragraphs
• Tags each paragraph with domain-specific topics loaded from configuration
• Exposes helper: `bucketed_text()` for summary prompt
"""
from pathlib import Path
import json, re, typing as T, collections
import os
from config.domain_loader import get_domain_loader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Cache anchor keywords to avoid repeated domain loader calls
_CACHED_ANCHOR_KEYWORDS = None

# Mapping of embedding models to context length
_MODEL_CTX_MAP = {
    "text-embedding-ada-002": 8192,
    "text-embedding-3-small": 8192,
    "text-embedding-3-large": 8192,
}

def _get_anchor_keywords() -> dict[str, list[str]]:
    """
    Get domain-specific anchor keywords from configuration.
    This replaces the hardcoded ANCHOR_KEYWORDS with dynamic loading.
    Uses caching to avoid repeated domain loader initialization.
    """
    global _CACHED_ANCHOR_KEYWORDS
    
    # Return cached keywords if available
    if _CACHED_ANCHOR_KEYWORDS is not None:
        return _CACHED_ANCHOR_KEYWORDS
    
    try:
        domain_loader = get_domain_loader()
        
        # Set domain from environment or default to generic
        domain_type = os.getenv("DOMAIN_TYPE", "generic")
        
        domain_loader.set_current_domain(domain_type)
        domain_config = domain_loader.get_current_config()
        
        # Extract domain-specific terms
        domain_terms = domain_loader.get_domain_specific_terms()
        
        # Convert domain configuration to anchor keywords format
        anchor_keywords = {}
        
        # Get entity types for general categorization
        entity_types = domain_loader.get_entity_types()
        
        if domain_type == "financial":
            # Financial domain structure
            financial_instruments = domain_terms.get('financial_instruments', {})
            
            # Flatten financial instruments into categories
            if 'indices' in financial_instruments:
                anchor_keywords['indices'] = [term.lower() for term in financial_instruments['indices']]
            if 'commodities' in financial_instruments:
                anchor_keywords['commodities'] = [term.lower() for term in financial_instruments['commodities']]
            if 'currencies' in financial_instruments:
                anchor_keywords['currencies'] = [term.lower() for term in financial_instruments['currencies']]
            if 'cryptocurrencies' in financial_instruments:
                anchor_keywords['crypto'] = [term.lower() for term in financial_instruments['cryptocurrencies']]
            if 'bonds' in financial_instruments:
                anchor_keywords['bonds'] = [term.lower() for term in financial_instruments['bonds']]
            
            # Add sentiment indicators as trading category
            sentiment_indicators = domain_loader.get_sentiment_indicators()
            trading_terms = []
            for sentiment_type, terms in sentiment_indicators.items():
                if isinstance(terms, dict):
                    for category, term_list in terms.items():
                        trading_terms.extend([term.lower() for term in term_list])
                elif isinstance(terms, list):
                    trading_terms.extend([term.lower() for term in terms])
            anchor_keywords['trading'] = trading_terms
            
        elif domain_type == "medical":
            # Medical domain structure
            medical_concepts = domain_terms.get('medical_concepts', {})
            
            # Convert medical concepts to anchor keywords
            for concept_type, terms in medical_concepts.items():
                anchor_keywords[concept_type] = [term.lower() for term in terms]
                
            # Add sentiment indicators
            sentiment_indicators = domain_loader.get_sentiment_indicators()
            assessment_terms = []
            for sentiment_type, terms in sentiment_indicators.items():
                if isinstance(terms, dict):
                    for category, term_list in terms.items():
                        assessment_terms.extend([term.lower() for term in term_list])
                elif isinstance(terms, list):
                    assessment_terms.extend([term.lower() for term in terms])
            anchor_keywords['assessment'] = assessment_terms
            
        else:
            # Generic domain - create categories based on available data
            for key, value in domain_terms.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, list):
                            anchor_keywords[sub_key] = [term.lower() for term in sub_value]
        
        # Add topic classification boundary indicators as discussion triggers
        topic_rules = domain_loader.get_topic_classification_rules()
        boundary_indicators = topic_rules.get('boundary_indicators', [])
        if boundary_indicators:
            anchor_keywords['discussion'] = [term.lower() for term in boundary_indicators]
        
        # Ensure we have at least some categories
        if not anchor_keywords:
            # Fallback to basic entity types
            anchor_keywords['general'] = [entity_type.lower() for entity_type in entity_types]
        
        # Cache the result
        _CACHED_ANCHOR_KEYWORDS = anchor_keywords
        return anchor_keywords
        
    except Exception as e:
        # Fallback to basic categorization if domain loading fails
        print(f"Warning: Could not load domain configuration ({e}), using basic categorization")
        fallback_keywords = {
            'general': ['discussion', 'analysis', 'topic', 'subject'],
            'entities': ['person', 'organization', 'location', 'date', 'money', 'percent']
        }
        # Cache the fallback result
        _CACHED_ANCHOR_KEYWORDS = fallback_keywords
        return fallback_keywords

def _load_raw(source: str | Path) -> str:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
    else:
        text = source
    # future Fireflies JSON support
    if text.lstrip().startswith("{"):
        try:
            payload = json.loads(text)
            text = "\n".join(u["text"] for u in payload.get("utterances", []))
        except json.JSONDecodeError:
            pass
    # strip any stray .srt time-stamps
    return re.sub(r"\d+\n\d\d:\d\d:\d\d.\d+ --> .*", "", text).strip()

def _tag_paragraph(p: str) -> set[str]:
    """
    Tag a paragraph with domain-specific topic categories.
    This replaces the hardcoded tagging with dynamic configuration-based tagging.
    """
    low = p.lower()
    anchor_keywords = _get_anchor_keywords()
    
    return {
        tag
        for tag, kw_list in anchor_keywords.items()
        if any(k in low for k in kw_list)
    } or {"misc"}

def _get_primary_tag(p: str) -> str:
    """
    Get the primary/best matching tag for a paragraph to avoid content duplication.
    Returns the tag with the most keyword matches, or the first match if tied.
    """
    low = p.lower()
    anchor_keywords = _get_anchor_keywords()
    
    # Count matches for each tag
    tag_scores = {}
    for tag, kw_list in anchor_keywords.items():
        matches = sum(1 for k in kw_list if k in low)
        if matches > 0:
            tag_scores[tag] = matches
    
    if not tag_scores:
        return "misc"
    
    # Return tag with highest score (most matches)
    return max(tag_scores.items(), key=lambda x: x[1])[0]

def bucketed_text(source: str | Path) -> dict[str, str]:
    """Returns dict where key = topic tag, val = concatenated text."""
    raw = _load_raw(source)
    
    # Try paragraph splitting first
    paras = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]
    
    # If no paragraphs found (transcript has no line breaks), use sentence-based chunking
    if len(paras) <= 1 and len(raw) > 1000:
        print("Warning: No paragraph breaks found, using sentence-based chunking")
        
        # Split by sentences and group into logical chunks
        sentences = [s.strip() for s in re.split(r'[.!?]+', raw) if s.strip() and len(s.strip()) > 20]
        
        # Group sentences into chunks of reasonable size (3-5 sentences per chunk)
        chunk_size = 4
        paras = []
        for i in range(0, len(sentences), chunk_size):
            chunk = '. '.join(sentences[i:i+chunk_size])
            if chunk:
                paras.append(chunk + '.')
    
    buckets = collections.defaultdict(list)
    
    # Assign each paragraph/chunk to its PRIMARY category only (no duplication)
    for p in paras:
        primary_tag = _get_primary_tag(p)
        buckets[primary_tag].append(p)
    
    # concatenate & clip each bucket to 12000 chars for better content preservation
    return {k: "\n".join(v)[:12000] for k, v in buckets.items()}

# Add TranscriptProcessor class for backward compatibility
class TranscriptProcessor:
    """Domain-agnostic TranscriptProcessor class with configuration-based processing"""
    
    def process_transcript(self, text: str) -> dict:
        """Process transcript into chunks using token-aware chunking suitable for embeddings."""
        raw = _load_raw(text)

        # Compute dynamic chunk parameters once
        chunk_size, overlap = _default_chunk_params()

        # Build a RecursiveCharacterTextSplitter that stops splitting when token limit reached
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=_token_len,
            separators=["\n\n", ". ", "? ", "! ", " ", ""],
        )

        try:
            docs = splitter.create_documents([raw])
            chunks = [{"text": doc.page_content} for doc in docs if doc.page_content.strip()]
        except Exception as e:
            # Fallback to naive char splitting on error (highly unlikely)
            print(f"[TranscriptProcessor] Fallback chunking reason: {e}")
            chunks = []
            step = 0
            while step < len(raw):
                segment = raw[step: step + chunk_size]
                chunks.append({"text": segment})
                step = step + chunk_size - overlap

        return {"chunks": chunks, "success": True}

    def _chunk_by_sentences(self, text: str, max_chunk_size: int = 3000, overlap: int = 200) -> list[str]:
        """
        Split text into chunks by sentences, respecting character limits
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        # Split into sentences using multiple delimiters
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        if not sentences:
            # Fallback to character-based chunking if no sentences found
            return self._chunk_by_characters(text, max_chunk_size, overlap)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Add period back to sentence (except for the last one if it doesn't need it)
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            
            # Check if adding this sentence would exceed the limit
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= max_chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Start new chunk
                if len(sentence) <= max_chunk_size:
                    current_chunk = sentence
                else:
                    # Sentence itself is too long, split it by characters
                    char_chunks = self._chunk_by_characters(sentence, max_chunk_size, overlap)
                    chunks.extend(char_chunks[:-1])  # Add all but the last
                    current_chunk = char_chunks[-1] if char_chunks else ""
        
        # Add the final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _chunk_by_characters(self, text: str, max_chunk_size: int = 3000, overlap: int = 200) -> list[str]:
        """
        Split text into chunks by character count with overlap
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chunk_size
            
            if end >= len(text):
                # Last chunk
                chunks.append(text[start:])
                break
            
            # Try to break at a word boundary near the end
            chunk_text = text[start:end]
            
            # Find the last space to avoid breaking words
            last_space = chunk_text.rfind(' ')
            if last_space > max_chunk_size * 0.8:  # Only if we're not cutting too much
                end = start + last_space
            
            chunks.append(text[start:end])
            
            # Move start position with overlap
            start = end - overlap
            if start < 0:
                start = 0
        
        return chunks 

def _token_len(text: str, encoding_name: str = "cl100k_base") -> int:
    """Return token count for given text using tiktoken encoding."""
    import tiktoken  # Lazy import to reduce startup memory
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))

def _default_chunk_params() -> tuple[int, int]:
    """Derive chunk_size and chunk_overlap (tokens) based on model ctx and env overrides."""
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    model_ctx = _MODEL_CTX_MAP.get(model_name, 8192)

    safe_headroom = 512
    max_safe = max(256, model_ctx - safe_headroom)

    # Allow override via env var TRANSCRIPT_CHUNK_TOKENS
    try:
        user_size = int(os.getenv("TRANSCRIPT_CHUNK_TOKENS", "0"))
    except ValueError:
        user_size = 0

    chunk_size = user_size if 0 < user_size < max_safe else min(1000, max_safe)
    overlap = int(chunk_size * 0.2)
    return chunk_size, overlap 