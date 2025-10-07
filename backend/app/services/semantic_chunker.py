"""
Semantic Chunking Service

This module provides domain-agnostic semantic chunking capabilities for text documents.
It uses NLP techniques to identify natural semantic boundaries and extract metadata
without relying on hardcoded domain-specific assumptions.

Key features:
- spaCy NER for entity detection
- NLTK for sentence tokenization
- Configurable sentiment analysis
- Entity-based topic grouping
- Hash-based chunk IDs for reliable identification
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

# NLP libraries
try:
    import spacy
    import nltk
    from nltk.tokenize import sent_tokenize
    # Download required NLTK data if not present
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    except:
        pass
    
    # Load spaCy model
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = None
        
except ImportError:
    nlp = None
    sent_tokenize = None

# LangChain text splitter for better chunking
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    langchain_available = True
except ImportError:
    langchain_available = False

# Language detection
try:
    from langdetect import detect
    langdetect_available = True
except ImportError:
    langdetect_available = False

# Import domain configuration system
from config.domain_loader import get_domain_loader

logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Metadata schema for semantic chunks"""
    id: str
    text: str
    entities: List[Dict[str, Any]]
    language: str
    chunk_index: int
    sentence_count: int
    entity_types: List[str]
    start_position: int
    end_position: int
    # Removed sentiment field to prevent LLM overfitting
    # Sentiment should be analyzed by LLM in real-time based on query context

class SemanticChunker:
    """
    Domain-agnostic semantic chunking system.
    
    This class processes text documents into semantically coherent chunks
    using NLP techniques without hardcoded domain assumptions.
    """
    
    def __init__(self, domain_type: Optional[str] = None):
        """
        Initialize the semantic chunker.
        
        Args:
            domain_type: Domain type for configuration (e.g., 'financial', 'medical')
                        If None, will use DOMAIN_TYPE environment variable
        """
        self.domain_loader = get_domain_loader()
        self.domain_type = domain_type or os.getenv("DOMAIN_TYPE", "generic")
        
        # Load domain configuration
        try:
            self.domain_loader.set_current_domain(self.domain_type)
            self.domain_config = self.domain_loader.get_current_config()
            logger.info(f"Loaded domain configuration for: {self.domain_type}")
        except Exception as e:
            logger.warning(f"Could not load domain config for {self.domain_type}: {e}")
            self.domain_config = {}
        
        # NLP components availability
        self.spacy_available = nlp is not None
        self.nltk_available = sent_tokenize is not None
        self.langchain_available = langchain_available
        self.langdetect_available = langdetect_available
        
        if not self.spacy_available:
            logger.warning("spaCy not available, using fallback entity detection")
        if not self.nltk_available:
            logger.warning("NLTK not available, using basic sentence splitting")
        if not self.langchain_available:
            logger.warning("LangChain not available, using fallback chunking strategy")
        
        # Enhanced chunking parameters (FIXED based on second opinion)
        self.chunk_size = 500  # Target characters per chunk
        self.chunk_overlap = 100  # CRITICAL: Add overlap for context preservation
        self.min_chunk_size = 200  # Minimum viable chunk size
        self.max_chunk_size = 800  # Maximum chunk size
        
        # Initialize RecursiveCharacterTextSplitter with FIXED configuration
        if self.langchain_available:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,  # FIXED: Now includes overlap
                separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],  # FIXED: Better sentence boundaries
                length_function=len,
                is_separator_regex=False,
                keep_separator=True,  # FIXED: Keep separators to maintain sentence structure
            )
            logger.info(f"Initialized RecursiveCharacterTextSplitter with overlap={self.chunk_overlap}")
        else:
            self.text_splitter = None
            logger.warning("Using fallback sentence-based chunking")
        
    def chunk_text(self, text: str, source_id: Optional[str] = None) -> List[ChunkMetadata]:
        """
        Chunk text into semantically coherent segments with enhanced strategy.
        
        Uses RecursiveCharacterTextSplitter for better context preservation
        and proper chunk boundaries, following second opinion recommendations.
        
        Args:
            text: Input text to chunk
            source_id: Optional source identifier for chunk ID generation
            
        Returns:
            List of ChunkMetadata objects
        """
        if not text or not text.strip():
            return []
        
        # Clean and normalize text
        normalized_text = self._normalize_text(text)
        
        # Detect language with enhanced detection
        language = self._detect_language_enhanced(normalized_text)
        
        # Use enhanced chunking strategy
        if self.langchain_available and self.text_splitter:
            chunks = self._chunk_with_recursive_splitter(normalized_text)
        else:
            # Fallback to improved sentence-based chunking
            chunks = self._chunk_with_sentences_enhanced(normalized_text)
        
        # Create chunk metadata with enhanced processing
        chunk_metadata_list = []
        current_position = 0
        
        for chunk_index, chunk_text in enumerate(chunks):
            # Skip chunks that are too small
            if len(chunk_text.strip()) < self.min_chunk_size:
                logger.debug(f"Skipping chunk {chunk_index}: too small ({len(chunk_text)} chars)")
                continue
            
            # Create enhanced chunk metadata
            chunk_metadata = self._create_chunk_metadata_enhanced(
                text=chunk_text.strip(),
                chunk_index=chunk_index,
                source_id=source_id,
                language=language,
                start_position=current_position,
                end_position=current_position + len(chunk_text)
            )
            
            chunk_metadata_list.append(chunk_metadata)
            current_position += len(chunk_text)
        
        logger.info(f"Created {len(chunk_metadata_list)} enhanced semantic chunks from {len(normalized_text)} characters")
        return chunk_metadata_list
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing"""
        # Remove multiple whitespaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with processing
        text = re.sub(r'[^\w\s\.,!?;:()\-\$%]', ' ', text)
        
        # Clean up
        return text.strip()
    
    def _detect_language(self, text: str) -> str:
        """Detect text language (simple implementation)"""
        # Simple English detection - could be enhanced with proper language detection
        english_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = text.lower().split()
        english_count = sum(1 for word in words[:50] if word in english_words)
        
        return 'en' if english_count > 5 else 'unknown'
    
    def _detect_language_enhanced(self, text: str) -> str:
        """Enhanced language detection using langdetect if available"""
        if self.langdetect_available:
            try:
                # Only try langdetect if text is long enough
                if len(text.strip()) > 50:
                    detected = detect(text)
                    logger.debug(f"Detected language: {detected}")
                    return detected
                else:
                    # For short text, fall back to simple detection
                    return self._detect_language_simple(text)
            except Exception as e:
                logger.debug(f"Language detection failed: {e}, using fallback")
        
        # Fallback to improved simple detection
        return self._detect_language_simple(text)
    
    def _detect_language_simple(self, text: str) -> str:
        """Improved simple language detection for English content"""
        # Enhanced English detection with more comprehensive word list
        english_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may', 'might',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        # Clean and tokenize text
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        if not words:
            return 'en'  # Default to English for empty/non-word content
        
        # Count English words
        english_count = sum(1 for word in words[:100] if word in english_words)  # Check first 100 words
        english_ratio = english_count / min(len(words), 100)
        
        # If more than 20% are common English words, classify as English
        if english_ratio > 0.2:
            return 'en'
        
        # For transcripts and spoken content, be more lenient
        # Check for common English patterns
        text_lower = text.lower()
        english_patterns = [
            r'\bi\s+am\b', r'\byou\s+are\b', r'\bhe\s+is\b', r'\bshe\s+is\b',
            r'\bgoing\s+to\b', r'\bwant\s+to\b', r'\bhave\s+to\b',
            r'\bthink\s+that\b', r'\bknow\s+that\b', r'\bsay\s+that\b'
        ]
        
        pattern_matches = sum(1 for pattern in english_patterns if re.search(pattern, text_lower))
        
        if pattern_matches > 0 or english_ratio > 0.1:
            return 'en'
        
        return 'unknown'
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK or fallback"""
        if self.nltk_available:
            try:
                sentences = sent_tokenize(text)
                return [s.strip() for s in sentences if s.strip()]
            except Exception as e:
                logger.warning(f"NLTK sentence tokenization failed: {e}")
        
        # Fallback: simple sentence splitting
        sentences = re.split(r'[.!?]+\s*', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using spaCy or fallback.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        if self.spacy_available and nlp:
            try:
                doc = nlp(text)
                for ent in doc.ents:
                    entities.append({
                        'text': ent.text,
                        'label': ent.label_,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'confidence': 1.0  # spaCy doesn't provide confidence scores
                    })
            except Exception as e:
                logger.warning(f"spaCy entity extraction failed: {e}")
        
        # Fallback: use pattern-based extraction
        if not entities:
            entities = self._extract_pattern_entities(text)
        
        return entities
    
    def _extract_entities_enhanced(self, text: str) -> List[Dict[str, Any]]:
        """
        Enhanced entity extraction with better error handling and filtering.
        
        Provides more robust entity detection while avoiding domain-specific
        overfitting as recommended in the second opinion.
        """
        entities = []
        
        # Primary: Use spaCy for general entity detection
        if self.spacy_available and nlp:
            try:
                doc = nlp(text)
                for ent in doc.ents:
                    # Filter out very short or common entities that might be noise
                    if len(ent.text.strip()) > 1 and ent.text.strip().lower() not in {'the', 'and', 'or', 'but'}:
                        entities.append({
                            'text': ent.text.strip(),
                            'label': ent.label_,
                            'start': ent.start_char,
                            'end': ent.end_char,
                            'confidence': 1.0
                        })
            except Exception as e:
                logger.warning(f"Enhanced spaCy entity extraction failed: {e}")
        
        # Secondary: Add pattern-based entities for common types
        pattern_entities = self._extract_pattern_entities(text)
        entities.extend(pattern_entities)
        
        # Remove duplicates based on text and position
        unique_entities = []
        seen = set()
        for entity in entities:
            key = (entity['text'].lower(), entity['start'], entity['end'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        logger.debug(f"Extracted {len(unique_entities)} unique entities from text")
        return unique_entities
    
    def _extract_pattern_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities using general patterns (not domain-specific).
        
        Focuses on universal patterns like numbers, dates, money, etc.
        """
        entities = []
        
        # Universal patterns that work across domains
        patterns = {
            'MONEY': r'\$[\d,]+(?:\.\d{2})?|\d+(?:\.\d+)?\s*(?:dollars?|USD|cents?)',
            'PERCENT': r'\d+(?:\.\d+)?%',
            'NUMBER': r'\b\d+(?:,\d{3})*(?:\.\d+)?\b',
            'DATE': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
            'TIME': r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b',
        }
        
        for label, pattern in patterns.items():
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        'text': match.group().strip(),
                        'label': label,
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.9
                    })
            except Exception as e:
                logger.warning(f"Pattern matching failed for {label}: {e}")
        
        return entities
    
    def _generate_chunk_id(self, text: str, chunk_index: int, source_id: Optional[str] = None) -> str:
        """Generate unique hash-based ID for chunk"""
        # Create unique string for hashing
        id_string = f"{source_id or 'default'}_{chunk_index}_{text[:100]}"
        
        # Generate hash
        return hashlib.sha256(id_string.encode('utf-8')).hexdigest()[:16]
    
    def _create_chunk_metadata(self, text: str, chunk_index: int, source_id: Optional[str],
                              language: str, start_position: int, end_position: int) -> ChunkMetadata:
        """Create ChunkMetadata object"""
        # Extract entities
        entities = self._extract_entities(text)
        
        # Generate ID
        chunk_id = self._generate_chunk_id(text, chunk_index, source_id)
        
        # Count sentences
        sentences = self._split_into_sentences(text)
        sentence_count = len(sentences)
        
        # Extract entity types
        entity_types = list(set(e.get('label', '') for e in entities))
        
        return ChunkMetadata(
            id=chunk_id,
            text=text,
            entities=entities,
            language=language,
            chunk_index=chunk_index,
            sentence_count=sentence_count,
            entity_types=entity_types,
            start_position=start_position,
            end_position=end_position
        )
    
    def _create_chunk_metadata_enhanced(self, text: str, chunk_index: int, source_id: Optional[str],
                                       language: str, start_position: int, end_position: int) -> ChunkMetadata:
        """
        Create enhanced ChunkMetadata object with improved processing.
        
        This method provides better entity extraction and metadata
        while ensuring all required fields are properly populated.
        """
        # Extract entities with enhanced processing
        entities = self._extract_entities_enhanced(text)
        
        # Generate unique ID
        chunk_id = self._generate_chunk_id(text, chunk_index, source_id)
        
        # Count sentences for metadata
        sentences = self._split_into_sentences(text)
        sentence_count = len(sentences)
        
        # Extract unique entity types
        entity_types = list(set(e.get('label', '') for e in entities if e.get('label')))
        
        # Ensure we have meaningful entity types
        if not entity_types:
            entity_types = ['MISC']  # Default category for chunks without detected entities
        
        return ChunkMetadata(
            id=chunk_id,
            text=text,
            entities=entities,
            language=language,
            chunk_index=chunk_index,
            sentence_count=sentence_count,
            entity_types=entity_types,
            start_position=start_position,
            end_position=end_position
        )
    
    def _update_chunk_with_text(self, chunk: ChunkMetadata, new_text: str) -> ChunkMetadata:
        """Update existing chunk with new text and recalculate metadata"""
        return self._create_chunk_metadata(
            text=new_text,
            chunk_index=chunk.chunk_index,
            source_id=None,  # Will be regenerated
            language=chunk.language,
            start_position=chunk.start_position,
            end_position=chunk.start_position + len(new_text)
        )
    
    def bucket_by_entities(self, chunks: List[ChunkMetadata]) -> Dict[str, List[ChunkMetadata]]:
        """
        Group chunks by detected entities for topic-based organization.
        
        Args:
            chunks: List of chunk metadata
            
        Returns:
            Dictionary mapping entity types to chunks
        """
        buckets = defaultdict(list)
        
        for chunk in chunks:
            # Group by entity types
            if chunk.entity_types:
                for entity_type in chunk.entity_types:
                    buckets[entity_type].append(chunk)
            else:
                buckets['MISC'].append(chunk)
        
        return dict(buckets)
    
    def to_dict(self, chunks: List[ChunkMetadata]) -> List[Dict[str, Any]]:
        """Convert chunks to dictionary format for JSON serialization"""
        return [asdict(chunk) for chunk in chunks]
    
    def from_dict(self, data: List[Dict[str, Any]]) -> List[ChunkMetadata]:
        """Convert dictionary data back to ChunkMetadata objects"""
        return [ChunkMetadata(**item) for item in data]
    
    def _chunk_with_recursive_splitter(self, text: str) -> List[str]:
        """
        Use RecursiveCharacterTextSplitter for enhanced chunking.
        
        This method provides better context preservation and respects
        natural document boundaries as recommended in the second opinion.
        """
        try:
            chunks = self.text_splitter.split_text(text)
            logger.debug(f"RecursiveCharacterTextSplitter created {len(chunks)} chunks")
            
            # CRITICAL: Validate and fix chunk boundaries
            validated_chunks = self._validate_and_fix_chunks(chunks)
            logger.debug(f"After validation: {len(validated_chunks)} chunks")
            
            return validated_chunks
        except Exception as e:
            logger.error(f"RecursiveCharacterTextSplitter failed: {e}")
            # Fallback to sentence-based chunking
            return self._chunk_with_sentences_enhanced(text)
    
    def _validate_and_fix_chunks(self, chunks: List[str]) -> List[str]:
        """
        Validate chunk quality and fix common issues like mid-sentence starts.
        
        Addresses second opinion feedback about chunks starting with ". [any letter]"
        """
        if not chunks:
            return chunks
        
        fixed_chunks = []
        
        for i, chunk in enumerate(chunks):
            chunk = chunk.strip()
            if not chunk:
                continue
            
            # FIXED: Check for mid-sentence start (starts with ". " followed by ANY letter)
            if re.match(r'^\.\s*[a-zA-Z]', chunk):
                logger.debug(f"Detected mid-sentence start in chunk {i}: {chunk[:50]}...")
                
                # Try to fix by merging with previous chunk if available
                if fixed_chunks and len(fixed_chunks[-1]) + len(chunk) < self.max_chunk_size:
                    # Merge with previous chunk
                    fixed_chunks[-1] = fixed_chunks[-1] + " " + chunk
                    logger.debug(f"Merged chunk {i} with previous chunk")
                    continue
                else:
                    # Remove the leading period and ensure proper capitalization
                    chunk = chunk[1:].strip()  # Remove leading period
                    if chunk:
                        chunk = chunk[0].upper() + chunk[1:]  # Ensure first letter is capitalized
                        logger.debug(f"Fixed chunk {i} by removing period and ensuring capitalization")
            
            # Check for other problematic starts (any punctuation that shouldn't start a chunk)
            elif re.match(r'^[,;:]\s*', chunk):
                logger.debug(f"Detected punctuation start in chunk {i}: {chunk[:50]}...")
                # Try to merge with previous chunk
                if fixed_chunks and len(fixed_chunks[-1]) + len(chunk) < self.max_chunk_size:
                    fixed_chunks[-1] = fixed_chunks[-1] + chunk
                    continue
                else:
                    # Remove leading punctuation and capitalize
                    chunk = chunk[1:].strip()
                    if chunk:
                        chunk = chunk[0].upper() + chunk[1:]
            
            # ENHANCED: Check for sentence fragments (chunks that don't start with proper sentence structure)
            elif re.match(r'^(and|but|or|so|because|since|while|although|however|therefore|thus)\s+', chunk.lower()):
                logger.debug(f"Detected sentence fragment in chunk {i}: {chunk[:50]}...")
                # Try to merge with previous chunk
                if fixed_chunks and len(fixed_chunks[-1]) + len(chunk) < self.max_chunk_size:
                    fixed_chunks[-1] = fixed_chunks[-1] + " " + chunk
                    continue
                # If can't merge, keep as is but ensure proper capitalization
                chunk = chunk[0].upper() + chunk[1:] if chunk else chunk
            
            # Ensure chunk starts with capital letter (for sentence coherence)
            if chunk and chunk[0].islower():
                chunk = chunk[0].upper() + chunk[1:]
            
            # Only add non-empty chunks that meet minimum size
            if chunk and len(chunk) >= self.min_chunk_size:
                fixed_chunks.append(chunk)
            elif chunk:
                # Try to merge small chunks with previous chunk
                if fixed_chunks and len(fixed_chunks[-1]) + len(chunk) < self.max_chunk_size:
                    fixed_chunks[-1] = fixed_chunks[-1] + " " + chunk
                else:
                    # Keep small chunk if it's the only option
                    fixed_chunks.append(chunk)
        
        return fixed_chunks
    
    def _chunk_with_sentences_enhanced(self, text: str) -> List[str]:
        """
        Enhanced sentence-based chunking as fallback.
        
        Improved version that respects sentence boundaries and maintains
        better context than the original implementation.
        """
        sentences = self._split_into_sentences(text)
        if not sentences:
            return [text]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(chunk_text)
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and len(current_chunk) > 1:
                    # Keep last sentence for overlap
                    current_chunk = [current_chunk[-1], sentence]
                    current_length = len(current_chunk[-2]) + sentence_length
                else:
                    current_chunk = [sentence]
                    current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
        
        logger.debug(f"Enhanced sentence chunking created {len(chunks)} chunks")
        return chunks 