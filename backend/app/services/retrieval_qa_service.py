import os
import logging
import json
import time
import traceback
from typing import List, Dict, Any, Optional, Union, Tuple
import httpx
import asyncio
import numpy as np
import openai
import re
import spacy

from .embedding_service import EmbeddingService
from .supabase_client import SupabaseService
from .file_storage import FileStorageService

# Import domain configuration system
from config.domain_loader import get_domain_loader
from config.settings import get_retrieval_config, get_validation_config

# Import validation infrastructure
from .validation.llm_validator import LLMValidator, ValidationConfig

logger = logging.getLogger("bpt-qa-service")

class QAResponseValidator:
    """Specialized validation for QA responses to prevent hallucination"""
    
    def __init__(self):
        self.numeric_pattern = re.compile(r'[\d,]+\.?\d*%?|\$[\d,]+\.?\d*|[\d,]+\.?\d*[KMB]?')
        self.quote_min_words = 6
    
    def validate_qa_response(self, answer: str, context: str, question: str) -> Dict[str, Any]:
        """
        Validate QA response for hallucination prevention
        
        Args:
            answer: Generated answer text
            context: Retrieved context used for generation
            question: Original question
            
        Returns:
            Validation result with details
        """
        validation_results = {
            "overall_valid": True,
            "issues": [],
            "validations": {}
        }
        
        try:
            # 1. Numeric consistency validation
            numeric_result = self._validate_numeric_consistency(answer, context)
            validation_results["validations"]["numeric"] = numeric_result
            if not numeric_result["is_valid"]:
                validation_results["overall_valid"] = False
                validation_results["issues"].extend([f"Invalid number: {num}" for num in numeric_result.get("invalid_numbers", [])])
            
            # 2. Quote accuracy validation
            quote_result = self._validate_quote_accuracy(answer, context)
            validation_results["validations"]["quotes"] = quote_result
            if not quote_result["is_valid"]:
                validation_results["overall_valid"] = False
                validation_results["issues"].extend([f"Invalid quote: {q[:50]}..." for q in quote_result.get("invalid_quotes", [])])
            
            # 3. Context grounding validation
            grounding_result = self._validate_context_grounding(answer, context, question)
            validation_results["validations"]["grounding"] = grounding_result
            if not grounding_result["is_valid"]:
                validation_results["overall_valid"] = False
                validation_results["issues"].extend(grounding_result.get("issues", []))
            
            # 4. Source attribution validation
            attribution_result = self._validate_source_attribution(answer, context)
            validation_results["validations"]["attribution"] = attribution_result
            if not attribution_result["is_valid"]:
                # Source attribution is less critical, so we don't fail overall validation
                # but we log the issues
                logger.info(f"Source attribution issues: {attribution_result.get('issues', [])}")
            
        except Exception as e:
            logger.error(f"Error in QA response validation: {e}")
            validation_results["overall_valid"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def _validate_numeric_consistency(self, answer: str, context: str) -> Dict[str, Any]:
        """Validate that all numeric values in the answer exist in the context"""
        try:
            # Extract all numbers from answer
            answer_numbers = self.numeric_pattern.findall(answer)
            
            # Extract all numbers from context
            context_numbers = self.numeric_pattern.findall(context)
            
            # Normalize numbers for comparison
            def normalize_number(num_str):
                return re.sub(r'[,$]', '', num_str.lower())
            
            normalized_context = [normalize_number(num) for num in context_numbers]
            
            invalid_numbers = []
            for num in answer_numbers:
                normalized_num = normalize_number(num)
                if normalized_num not in normalized_context:
                    invalid_numbers.append(num)
            
            is_valid = len(invalid_numbers) == 0
            
            return {
                "is_valid": is_valid,
                "answer_numbers": answer_numbers,
                "context_numbers": context_numbers,
                "invalid_numbers": invalid_numbers,
                "validation_type": "numeric_consistency"
            }
            
        except Exception as e:
            logger.error(f"Error in QA numeric validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validation_type": "numeric_consistency"
            }
    
    def _validate_quote_accuracy(self, answer: str, context: str) -> Dict[str, Any]:
        """Validate that quotes in the answer appear in the context"""
        try:
            invalid_quotes = []
            all_quotes = []
            
            # Extract quotes from answer (text within quotes)
            quote_patterns = [
                r'"([^"]{20,})"',  # Text in double quotes (min 20 chars)
                r"'([^']{20,})'",  # Text in single quotes (min 20 chars)
                r'"([^"]+)"',      # Any text in double quotes
                r"'([^']+)'"       # Any text in single quotes
            ]
            
            for pattern in quote_patterns:
                matches = re.findall(pattern, answer)
                for quote_text in matches:
                    if len(quote_text.strip()) >= self.quote_min_words:
                        all_quotes.append(quote_text)
                        
                        # Check if quote appears in context (case-insensitive)
                        if quote_text.lower() not in context.lower():
                            # Try to find partial matches (at least 80% of words)
                            quote_words = quote_text.lower().split()
                            context_lower = context.lower()
                            
                            matching_words = sum(1 for word in quote_words if word in context_lower)
                            match_ratio = matching_words / len(quote_words) if quote_words else 0
                            
                            if match_ratio < 0.8:  # Less than 80% match
                                invalid_quotes.append(quote_text)
            
            is_valid = len(invalid_quotes) == 0
            
            return {
                "is_valid": is_valid,
                "all_quotes": all_quotes,
                "invalid_quotes": invalid_quotes,
                "validation_type": "quote_accuracy"
            }
            
        except Exception as e:
            logger.error(f"Error in QA quote validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validation_type": "quote_accuracy"
            }
    
    def _validate_context_grounding(self, answer: str, context: str, question: str) -> Dict[str, Any]:
        """Validate that the answer is grounded in the provided context"""
        try:
            issues = []
            
            # Check if the answer addresses the question
            question_keywords = [word for word in question.lower().split() if len(word) > 3]
            answer_lower = answer.lower()
            
            if question_keywords:
                keyword_matches = sum(1 for keyword in question_keywords if keyword in answer_lower)
                if keyword_matches / len(question_keywords) < 0.3:
                    issues.append("Answer may not address the question adequately")
            
            # Check if key concepts in answer appear in context
            # Extract meaningful words from answer (excluding common words)
            common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
            answer_words = [word for word in answer.lower().split() if len(word) > 4 and word not in common_words]
            
            if answer_words:
                context_lower = context.lower()
                grounded_words = sum(1 for word in answer_words if word in context_lower)
                grounding_ratio = grounded_words / len(answer_words)
                
                if grounding_ratio < 0.4:  # Less than 40% of meaningful words grounded
                    issues.append(f"Answer may not be sufficiently grounded in context (grounding ratio: {grounding_ratio:.2f})")
            
            # Check for impossible claims
            if "according to" in answer_lower and "source" not in context_lower:
                issues.append("Answer claims source attribution without sources in context")
            
            is_valid = len(issues) == 0
            
            return {
                "is_valid": is_valid,
                "issues": issues,
                "grounding_ratio": grounding_ratio if 'grounding_ratio' in locals() else None,
                "validation_type": "context_grounding"
            }
            
        except Exception as e:
            logger.error(f"Error in QA grounding validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validation_type": "context_grounding"
            }
    
    def _validate_source_attribution(self, answer: str, context: str) -> Dict[str, Any]:
        """Validate that source references in answer correspond to actual sources in context"""
        try:
            issues = []
            
            # Extract source references from answer (e.g., [1], [2], etc.)
            source_refs = re.findall(r'\[(\d+)\]', answer)
            
            # Extract source markers from context
            context_sources = re.findall(r'\[(\d+)\] Source:', context)
            
            # Check if all referenced sources exist in context
            for ref in source_refs:
                if ref not in context_sources:
                    issues.append(f"Answer references source [{ref}] which doesn't exist in context")
            
            is_valid = len(issues) == 0
            
            return {
                "is_valid": is_valid,
                "issues": issues,
                "referenced_sources": source_refs,
                "available_sources": context_sources,
                "validation_type": "source_attribution"
            }
            
        except Exception as e:
            logger.error(f"Error in QA source validation: {e}")
            return {
                "is_valid": False,
                "error": str(e),
                "validation_type": "source_attribution"
            }

class RetrievalQAService:
    """Service for answering questions based on retrieved transcript chunks"""
    
    def __init__(self, embedding_service: EmbeddingService, storage_service: Optional[SupabaseService] = None, file_storage_service: Optional[FileStorageService] = None):
        """Initialize the QA service with dependencies"""
        self.embedding_service = embedding_service
        self.storage_service = storage_service
        self.file_storage_service = file_storage_service or FileStorageService()
        
        # Load domain configuration
        self.domain_loader = get_domain_loader()
        domain_type = os.getenv("DOMAIN_TYPE", "generic")
        try:
            self.domain_loader.set_current_domain(domain_type)
            self.domain_config = self.domain_loader.get_current_config()
            logger.info(f"Loaded domain configuration for: {domain_type}")
        except Exception as e:
            logger.warning(f"Could not load domain config for {domain_type}: {e}")
            self.domain_config = {}
        
        # Initialize validation infrastructure
        validation_config = ValidationConfig()
        self.llm_validator = LLMValidator(validation_config)
        self.qa_response_validator = QAResponseValidator()
        
        # API keys for different providers
        self.api_key_openai = os.getenv("OPENAI_API_KEY")
        self.api_key_anthropic = os.getenv("ANTHROPIC_API_KEY")
        self.api_key_azure = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_key_cohere = os.getenv("COHERE_API_KEY")
        
        # Configuration
        self.qa_model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        self.provider = self._determine_provider()
        self.use_mock = os.getenv("USE_MOCK_RESPONSES", "false").lower() == "true"
        self.max_context_length = int(os.getenv("MAX_CONTEXT_LENGTH", "12000"))
        
        # Azure specific settings
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
        
        # HTTP client for API calls - will be properly managed
        self._http_client = None
        
        if self.use_mock:
            logger.info("Using mock responses for QA service")
        else:
            logger.info(f"QA service initialized with provider: {self.provider}, model: {self.qa_model}")
        
        if self.api_key_openai and not self.use_mock:
            openai.api_key = self.api_key_openai
            self.initialized = True
            logger.info(f"RetrievalQA service initialized with model: {self.qa_model} and enhanced validation")
        else:
            self.initialized = False
            if self.use_mock:
                logger.info("RetrievalQA service initialized in mock mode with validation")
            else:
                logger.warning("OpenAI API key not found, RetrievalQA service not fully initialized")
    
    @property
    def http_client(self):
        """Lazy initialization of HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self):
        """Properly close the HTTP client to prevent connection leaks"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _determine_provider(self) -> str:
        """Determine which provider to use based on available API keys and model name"""
        # Check model prefix to infer provider
        if self.qa_model.startswith(("gpt-", "text-davinci")):
            if self.api_key_openai:
                return "openai"
            elif self.api_key_azure and self.azure_endpoint:
                return "azure"
        elif self.qa_model.startswith(("claude-")):
            if self.api_key_anthropic:
                return "anthropic"
        elif self.qa_model.startswith(("command-")):
            if self.api_key_cohere:
                return "cohere"
                
        # Otherwise, use first available API key
        if self.api_key_openai:
            return "openai"
        elif self.api_key_anthropic:
            return "anthropic" 
        elif self.api_key_azure and self.azure_endpoint:
            return "azure"
        elif self.api_key_cohere:
            return "cohere"
        else:
            logger.warning("No API keys available. Using mock responses.")
            self.use_mock = True
            return "mock"
    
    async def answer_question(self, 
                           question: str, 
                           transcript_id: Optional[str] = None, 
                           top_k: int = 10,
                           similarity_threshold: float = 0.5) -> Dict[str, Any]:
        """
        Answer a question based on retrieved transcript chunks
        If transcript_id is provided, search only within that transcript
        Otherwise, search across all transcripts
        """
        try:
            start_time = time.time()
            logger.info(f"Processing question: '{question}' for transcript: {transcript_id or 'all'}")
            
            # Get domain-specific retrieval configuration
            retrieval_config = get_retrieval_config()
            
            # Use configured top_k if not explicitly provided
            if top_k == 10:  # Default value
                top_k = retrieval_config.get('final_k', 10)
            
            # Detect if this is a comprehensive question that needs more context
            is_comprehensive_question = any(phrase in question.lower() for phrase in [
                "how many topics", "topics", "covered", "session", "discussed"
            ])
            
            # Adjust top_k and context limits for comprehensive questions
            if is_comprehensive_question:
                top_k = min(top_k * 2, 20)  # Double the retrieval for comprehensive questions
                self.max_context_length = 12000  # Increase context limit for topic counting
            else:
                self.max_context_length = 8000  # Standard limit for other questions
            
            # Adjust top_k for comparative questions
            question_lower = question.lower()
            if any(word in question_lower for word in ["most bullish", "most bearish", "overall view"]):
                top_k = max(top_k, 12)  # Increase for comparative questions
                logger.info(f"Comparative question detected, increasing top_k to {top_k}")
            
            # Use mock response if configured
            if self.use_mock:
                logger.info("Using mock response for answer_question")
                return self._generate_mock_answer(question, transcript_id)
            
            if not self.initialized:
                logger.error("RetrievalQA service not initialized, cannot answer question")
                return {
                    "success": False,
                    "error": "RetrievalQA service not initialized"
                }
            
            # Generate embedding for the question
            question_embedding = await self.embedding_service.get_embedding(question)
            if not question_embedding:
                logger.error("Failed to generate question embedding")
                return {
                    "success": False,
                    "error": "Failed to generate question embedding"
                }
            
            embed_time = time.time()
            logger.info(f"Generated question embedding in {embed_time - start_time:.2f}s")
            
            # Search for relevant chunks
            logger.info(f"🔍 Searching for relevant chunks (top_k={top_k}, threshold={similarity_threshold})")
            relevant_chunks = await self._vector_search(question_embedding, transcript_id, top_k)
            
            if not relevant_chunks:
                logger.warning("No relevant chunks found to answer the question")
                return {
                    "success": True,
                    "answer": "I don't have enough information to answer this question based on the available transcripts.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            retrieval_time = time.time()
            logger.info(f"Retrieved chunks in {retrieval_time - embed_time:.2f}s")
            
            # Build context from chunks using domain-agnostic approach
            context, source_refs = self._build_context_from_chunks(relevant_chunks)
            
            logger.info(f"📝 Built context: {len(context)} characters from {len(source_refs)} sources")
            
            # Generate answer using LLM API with validation
            response, validation_results = await self._generate_validated_answer(question, context)
            
            # Map source numbers to actual source information
            sources = []
            for source_num in response["sources"]:
                if source_num <= len(source_refs):
                    sources.append(source_refs[source_num - 1])  # -1 because sources are 1-indexed in the response
            
            answer_time = time.time()
            logger.info(f"Generated answer in {answer_time - retrieval_time:.2f}s")
            logger.info(f"Answer validation results: {validation_results.get('overall_valid', False)}")
            logger.info(f"Total processing time: {answer_time - start_time:.2f}s")
            
            return {
                "success": True,
                "answer": response["answer"],
                "sources": sources,
                "confidence": response["confidence"],
                "validation": validation_results,
                "processing_time": answer_time - start_time
            }
                
        except Exception as e:
            logger.error(f"Error in answer_question: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_context_from_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Build a context string from retrieved chunks and return a mapping of sources
        Returns a tuple of (context_string, sources_map)
        """
        if not chunks:
            return "", []
        
        # Group chunks by topics for better organization
        topic_groups = self._group_chunks_by_topic(chunks)
        
        context_parts = []
        source_refs = []
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk['text']
            relevance_score = chunk.get('similarity_score', 0.0)
            chunk_index = chunk.get('chunk_index', i)
            
            # Process mixed-topic chunks using domain-agnostic approach
            processed_text = self._process_mixed_topic_chunk_enhanced(chunk_text, chunk_index, topic_groups)
            
            # Create source reference
            source_ref = {
                "chunk_index": chunk_index,
                "relevance_score": relevance_score,
                "preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
            }
            source_refs.append(source_ref)
            
            # Add to context with source marker
            context_parts.append(f"[{i+1}] Source: {chunk.get('source', 'Unknown')} | Relevance: {relevance_score:.3f}\n{processed_text}\n")
        
        return "\n".join(context_parts), source_refs
    
    def _group_chunks_by_topic(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """Group chunks by detected topics using domain-agnostic approach"""
        topic_groups = {}
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk['text']
            primary_topic = self._detect_primary_topic(chunk_text, i)
            
            if primary_topic:
                if primary_topic not in topic_groups:
                    topic_groups[primary_topic] = []
                topic_groups[primary_topic].append(i)
            else:
                # Fallback to generic topic
                if 'general' not in topic_groups:
                    topic_groups['general'] = []
                topic_groups['general'].append(i)
        
        return topic_groups
    
    def _detect_primary_topic(self, chunk_text: str, chunk_index: int) -> str:
        """
        Detect the primary topic of a chunk using domain-agnostic approach.
        
        Args:
            chunk_text: Text content of the chunk
            chunk_index: Index of the chunk
            
        Returns:
            Primary topic string or None if no clear topic
        """
        try:
            # Get domain-specific configuration
            domain_terms = self.domain_loader.get_domain_specific_terms()
            sentiment_indicators = self.domain_loader.get_sentiment_indicators()
            
            # Build topic indicators from configuration
            topic_indicators = self._build_topic_indicators_from_config(domain_terms, sentiment_indicators)
            
            if not topic_indicators:
                return None
            
            # Score each topic based on keyword matches
            topic_scores = {}
            text_lower = chunk_text.lower()
            
            for topic, config in topic_indicators.items():
                keywords = config.get("keywords", [])
                weight = config.get("weight_multiplier", 1.0)
                
                score = 0
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        score += weight
                
                if score > 0:
                    topic_scores[topic] = score
            
            # Return the highest scoring topic
            if topic_scores:
                primary_topic = max(topic_scores, key=topic_scores.get)
                logger.debug(f"Detected primary topic '{primary_topic}' for chunk {chunk_index}")
                return primary_topic
            
            return None
            
        except Exception as e:
            logger.warning(f"Error in topic detection: {e}")
            return None
    
    def _build_topic_indicators_from_config(self, domain_terms: Dict, sentiment_indicators: Dict) -> Dict[str, Dict]:
        """
        Build topic indicators dynamically from domain configuration.
        This replaces the hardcoded topic_indicators dictionary.
        """
        topic_indicators = {}
        
        # Get current domain to determine structure
        domain_type = os.getenv("DOMAIN_TYPE", "generic")
        
        # Build topic indicators from domain terms
        for category, terms_data in domain_terms.items():
            if isinstance(terms_data, dict):
                for subcategory, terms in terms_data.items():
                    if isinstance(terms, list):
                        topic_indicators[subcategory] = {
                            "keywords": terms,
                            "weight_multiplier": 1.0
                        }
        
        # Add sentiment-based topics
        for sentiment_type, terms in sentiment_indicators.items():
            if isinstance(terms, dict):
                all_terms = []
                for subtype, term_list in terms.items():
                    if isinstance(term_list, list):
                        all_terms.extend(term_list)
                if all_terms:
                    topic_indicators[f"{sentiment_type}_sentiment"] = {
                        "keywords": all_terms,
                        "weight_multiplier": 1.2  # Higher weight for sentiment
                    }
            elif isinstance(terms, list):
                topic_indicators[f"{sentiment_type}_sentiment"] = {
                    "keywords": terms,
                    "weight_multiplier": 1.2
                }
        
        # If no domain-specific terms, use entity types as topics
        if not topic_indicators:
            try:
                entity_types = self.domain_loader.get_entity_types()
                for entity_type in entity_types:
                    topic_indicators[entity_type.lower()] = {
                        "keywords": [entity_type.lower()],
                        "weight_multiplier": 1.0
                    }
            except Exception as e:
                logger.warning(f"Could not load entity types: {e}")
        
        return topic_indicators
    
    def _detect_secondary_topics(self, chunk_text: str, primary_topic: str) -> List[str]:
        """
        Detect secondary topics mentioned in a chunk using domain-agnostic approach.
        This replaces the hardcoded secondary topic detection.
        """
        secondary_topics = []
        
        # Only look for secondary topics if there's a primary topic
        if not primary_topic:
            return secondary_topics
        
        try:
            # Get all topic indicators
            domain_terms = self.domain_loader.get_domain_specific_terms()
            sentiment_indicators = self.domain_loader.get_sentiment_indicators()
            topic_indicators = self._build_topic_indicators_from_config(domain_terms, sentiment_indicators)
            
            chunk_text_lower = chunk_text.lower()
            
            for topic, config in topic_indicators.items():
                if topic != primary_topic:  # Don't include primary topic
                    keywords = config["keywords"]
                    if any(keyword.lower() in chunk_text_lower for keyword in keywords):
                        secondary_topics.append(topic)
            
            return secondary_topics
            
        except Exception as e:
            logger.warning(f"Error in secondary topic detection: {e}")
            return secondary_topics
    
    def _process_mixed_topic_chunk_enhanced(self, chunk_text: str, chunk_index: int, topic_context: dict) -> str:
        """
        Enhanced processing for chunks that may contain multiple topics using domain-agnostic approach.
        This replaces hardcoded topic transition detection with configurable NLP-based approach.
        """
        # Dynamic topic detection instead of hardcoded chunk checks
        lines = chunk_text.split('\n')
        processed_lines = []
        current_topic = None
        
        # Get domain-specific transition indicators from configuration
        topic_rules = self.domain_loader.get_topic_classification_rules()
        topic_transition_indicators = topic_rules.get('boundary_indicators', [
            # Fallback generic transition phrases
            "moving on", "let's talk about", "now looking at", "turning to",
            "next up", "also", "on the other hand", "meanwhile", "separately",
            "in contrast", "additionally", "furthermore", "shifting focus"
        ])
        
        # Look for abrupt context changes that might indicate topic shifts
        previous_entities = set()
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Detect potential topic transitions
            has_transition = any(indicator in line_lower for indicator in topic_transition_indicators)
            
            # Extract entities/topics from this line using domain-agnostic NER
            current_entities = self._extract_entities_from_line(line)
            
            # If we detect significant entity change or explicit transition, mark new topic section
            if has_transition or (current_entities and len(current_entities.intersection(previous_entities)) < 0.3 * len(previous_entities) and len(previous_entities) > 0):
                # Determine topic label dynamically
                topic_label = self._generate_dynamic_topic_label(current_entities, line)
                if topic_label != current_topic:
                    processed_lines.append(f"\n--- {topic_label.upper()} ---")
                    current_topic = topic_label
            
            processed_lines.append(line)
            previous_entities = current_entities
        
        return "\n".join(processed_lines)
    
    def _extract_entities_from_line(self, line: str) -> set:
        """
        Extract key entities from a line of text using domain-agnostic NLP approach.
        This replaces hardcoded entity patterns with spaCy NER and configurable patterns.
        """
        entities = set()
        line_lower = line.lower()
        
        # Use spaCy NER for general entity extraction if available
        try:
            # Try to load the language model
            try:
                nlp = spacy.load("en_core_web_sm")
                doc = nlp(line)
                
                # Extract entities based on domain configuration
                domain_config = self.domain_loader.get_current_config()
                entity_types = self.domain_loader.get_entity_types()
                
                for ent in doc.ents:
                    if ent.label_ in entity_types:
                        entities.add(ent.label_.lower())
                        
            except OSError:
                # Fallback if spaCy model not available
                logger.warning("spaCy model en_core_web_sm not found, using fallback entity detection")
                
        except ImportError:
            # Fallback if spaCy not available
            pass
        
        # Use domain-specific entity patterns as fallback/supplement
        try:
            domain_terms = self.domain_loader.get_domain_specific_terms()
            
            # Check against domain-specific terms
            for category, terms_data in domain_terms.items():
                if isinstance(terms_data, dict):
                    for subcategory, terms in terms_data.items():
                        if isinstance(terms, list):
                            if any(term.lower() in line_lower for term in terms):
                                entities.add(subcategory.lower())
                elif isinstance(terms_data, list):
                    if any(term.lower() in line_lower for term in terms_data):
                        entities.add(category.lower())
        
        except Exception as e:
            logger.warning(f"Error in domain-specific entity extraction: {e}")
        
        return entities
    
    def _generate_dynamic_topic_label(self, entities: set, line: str) -> str:
        """
        Generate a topic label based on detected entities and context using domain-agnostic approach.
        This replaces hardcoded topic labeling with configurable domain-specific labeling.
        """
        if not entities:
            return "GENERAL DISCUSSION"
        
        # Get domain-specific configuration
        domain_type = os.getenv("DOMAIN_TYPE", "generic")
        
        try:
            domain_config = self.domain_loader.get_current_config()
            domain_terms = self.domain_loader.get_domain_specific_terms()
            
            # Build entity priorities from domain configuration
            entity_priorities = {}
            priority_order = []
            
            # Extract categories from domain terms
            for category, terms_data in domain_terms.items():
                if isinstance(terms_data, dict):
                    for subcategory, terms in terms_data.items():
                        if isinstance(terms, list):
                            label = f"{subcategory.upper().replace('_', ' ')} DISCUSSION"
                            entity_priorities[subcategory] = label
                            priority_order.append(subcategory)
            
            # Return the highest priority entity found
            for entity in priority_order:
                if entity.lower() in [e.lower() for e in entities]:
                    return entity_priorities.get(entity, f"{entity.upper()} DISCUSSION")
            
            # Fallback based on entity types
            entity_list = list(entities)
            if entity_list:
                return f"{entity_list[0].upper()} DISCUSSION"
            
            return "TOPIC DISCUSSION"
            
        except Exception as e:
            logger.warning(f"Error generating topic label: {e}")
            return "GENERAL DISCUSSION"
    
    async def _generate_validated_answer(self, question: str, context: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate answer with comprehensive validation and retry logic
        
        Args:
            question: User question
            context: Retrieved context for generation
            
        Returns:
            Tuple of (answer_result, validation_results)
        """
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            is_strict_mode = attempt > 0  # Use strict mode for retries
            
            # Generate answer
            answer_result = await self._generate_answer(question, context, is_strict_mode)
            
            # Comprehensive validation
            validation_results = self.qa_response_validator.validate_qa_response(
                answer_result.get("answer", ""), context, question
            )
            
            if validation_results["overall_valid"]:
                logger.info(f"QA answer validation passed on attempt {attempt + 1}")
                return answer_result, validation_results
            
            if attempt < max_retries:
                logger.warning(f"QA answer validation failed on attempt {attempt + 1}, retrying with strict mode")
                logger.warning(f"Validation issues: {validation_results.get('issues', [])}")
            else:
                logger.error(f"QA answer validation failed after {max_retries + 1} attempts")
                # Return the last attempt even if validation failed
                return answer_result, validation_results
        
        return answer_result, validation_results
    
    async def _generate_answer(self, question: str, context: str, strict_mode: bool = False) -> Dict[str, Any]:
        """Generate an answer using LLM API based on the retrieved context"""
        try:
            # Trim context if it's too long
            original_length = len(context)
            if len(context) > self.max_context_length:
                logger.warning(f"Context is too long ({len(context)} chars), trimming to {self.max_context_length}")
                # Try to trim at paragraph breaks to maintain readability
                context = self._smart_trim_context(context, self.max_context_length)
                logger.info(f"Context trimmed from {original_length} to {len(context)} chars")
                
                # Debug: show what's in the trimmed context
                logger.debug(f"Trimmed context preview: {context[:500]}...")
            
            # Create strict mode instructions if enabled
            strict_instructions = ""
            if strict_mode:
                strict_instructions = """
**STRICT MODE ENABLED - CRITICAL ACCURACY REQUIREMENTS:**
- ONLY use numbers that appear EXACTLY in the context
- ONLY use quotes that appear VERBATIM in the context (minimum 6 words)
- ONLY reference concepts that are explicitly discussed in the provided context
- When in doubt, use phrases like "based on the available context" rather than making claims
- Double-check all factual claims against the source material
- If specific information is not available in the context, explicitly state this limitation

"""

            system_prompt = f"""You are an AI assistant helping users understand transcript content from discussions or presentations.

{strict_instructions}**CRITICAL INSTRUCTION FOR QUOTE ATTRIBUTION:**
- **ALWAYS** pay attention to section headers (e.g., "--- TOPIC A ANALYSIS ---", "--- TOPIC B DISCUSSION ---")
- **NEVER** attribute quotes or sentiment from one section to a different topic/subject
- When multiple topics appear in the same source, treat each section separately
- If a quote appears under "--- CURRENCY ANALYSIS ---", it refers ONLY to currency/financial instruments
- If a quote appears under "--- COMMODITIES ANALYSIS ---", it refers ONLY to commodities
- **SECTION BOUNDARIES ARE AUTHORITATIVE** - do not cross-reference quotes between different topic sections

**RESPONSE REQUIREMENTS:**
1. **DIRECT & PRECISE**: Answer exactly what was asked without unnecessary elaboration
2. **QUOTE ATTRIBUTION**: When citing quotes, explicitly mention which topic/subject they refer to
3. **COMPARATIVE ANALYSIS**: When asked about relative positions (most positive/negative, strongest/weakest):
   - Analyze the STRENGTH and CLARITY of language used
   - Look for explicit sentiment indicators (positive: "bullish", "optimistic", "upward trend"; negative: "bearish", "concerning", "downward trend")
   - Consider context and supporting evidence provided

4. **COMPREHENSIVE COVERAGE**: For topic counting or summary questions:
   - Scan ALL sources systematically for distinct topics/subjects
   - Don't miss topics mentioned briefly or in passing
   - Look for both direct mentions and indirect references
   - Provide organized, structured responses

5. **STRUCTURED ANSWERS**: 
   - Start with direct answer to the question
   - Support with specific quotes and source references
   - Use clear, organized formatting

**GENERAL GUIDELINES:**
- Base responses ONLY on the provided context
- If information isn't available, state so clearly
- Maintain objectivity and accuracy
- Respect topic boundaries established by section headers

Answer the user's question based on the transcript content provided."""

            user_prompt = f"""Context:
{context}

Question: {question}"""

            # Call the appropriate provider
            if self.provider == "openai":
                return await self._generate_openai_answer(system_prompt, user_prompt)
            elif self.provider == "anthropic":
                return await self._generate_anthropic_answer(system_prompt, user_prompt)
            elif self.provider == "azure":
                return await self._generate_azure_answer(system_prompt, user_prompt)
            elif self.provider == "cohere":
                return await self._generate_cohere_answer(system_prompt, user_prompt)
            else:
                # Fallback to mock answer
                logger.warning(f"Unsupported provider {self.provider}, using mock answer")
                return self._generate_mock_answer_text(question, context)
                
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "answer": "I encountered an error while trying to generate an answer.",
                "sources": [],
                "confidence": 0.0
            }
    
    def _smart_trim_context(self, context: str, max_length: int) -> str:
        """
        Trim context to max_length while trying to preserve complete sources and topic diversity.
        This uses domain-agnostic topic detection instead of hardcoded financial assumptions.
        """
        # If context is already short enough, return as is
        if len(context) <= max_length:
            return context
        
        # Split by source markers
        source_pattern = r'\[\d+\] Source:'
        import re
        parts = re.split(f"({source_pattern})", context)
        
        # Rebuild by prioritizing higher relevance scores and topic diversity
        source_blocks = []
        i = 0
        
        while i < len(parts):
            if i < len(parts) and re.match(source_pattern, parts[i]):
                source_marker = parts[i]
                content = parts[i+1] if i+1 < len(parts) else ""
                
                # Extract relevance score from source marker
                relevance_match = re.search(r'Relevance: ([\d.]+)', source_marker)
                relevance = float(relevance_match.group(1)) if relevance_match else 0.0
                
                # Extract topic hint using domain-agnostic approach
                topic_hint = self._extract_topic_from_content(content, source_marker)
                
                source_blocks.append({
                    'marker': source_marker,
                    'content': content,
                    'relevance': relevance,
                    'topic': topic_hint,
                    'length': len(source_marker) + len(content)
                })
                i += 2
            else:
                # Handle any content before the first source marker
                if i == 0 and parts[i].strip():
                    source_blocks.insert(0, {
                        'marker': '',
                        'content': parts[i],
                        'relevance': 999,  # High priority for intro content
                        'topic': 'intro',
                        'length': len(parts[i])
                    })
                i += 1
        
        # For topic diversity, prioritize one chunk per topic for comprehensive questions
        topics_seen = set()
        prioritized_blocks = []
        remaining_blocks = []
        
        # Sort by relevance first
        source_blocks.sort(key=lambda x: x['relevance'], reverse=True)
        
        for block in source_blocks:
            topic = block['topic']
            if topic and topic not in topics_seen and topic != 'intro':
                # First chunk of this topic - prioritize it
                topics_seen.add(topic)
                prioritized_blocks.append(block)
            else:
                # Additional chunks of same topic or no topic - lower priority
                remaining_blocks.append(block)
        
        # Combine prioritized (diverse topics) + remaining (same topics)
        all_blocks = prioritized_blocks + remaining_blocks
        
        # Build result by adding highest priority sources first
        result = ""
        for block in all_blocks:
            block_text = block['marker'] + block['content']
            if len(result) + block['length'] <= max_length:
                result += block_text
            else:
                # If we can't fit the whole block, try to fit part of it if it's high relevance or unique topic
                if block['relevance'] > 0.2 or block in prioritized_blocks:  # High relevance or unique topic
                    space_left = max_length - len(result)
                    if space_left > 100:  # Only if we have meaningful space left
                        partial_content = block['content'][:space_left - len(block['marker']) - 20] + "..."
                        result += block['marker'] + partial_content
                break
        
        return result
    
    def _extract_topic_from_content(self, content: str, source_marker: str) -> str:
        """
        Extract topic from content using domain-agnostic configuration-based approach.
        This replaces the hardcoded financial topic detection in context trimming.
        """
        # First check for explicit topic headers in the source marker or content
        topic_headers = [
            "ANALYSIS", "DISCUSSION", "CONDITIONS", "TREATMENTS", "SYMPTOMS",
            "MARKET", "INDICES", "COMMODITIES", "CURRENCY", "CRYPTO", "BONDS",
            "MEDICAL", "LEGAL", "TECHNICAL"
        ]
        
        for header in topic_headers:
            if header in source_marker.upper() or header in content.upper():
                return header.lower()
        
        # Use domain-agnostic entity detection to determine topic
        try:
            # Get domain-specific configuration
            domain_terms = self.domain_loader.get_domain_specific_terms()
            content_lower = content.lower()
            
            # Check against domain-specific terms to identify topic
            for category, terms_data in domain_terms.items():
                if isinstance(terms_data, dict):
                    for subcategory, terms in terms_data.items():
                        if isinstance(terms, list):
                            if any(term.lower() in content_lower for term in terms[:5]):  # Check first 5 terms for efficiency
                                return subcategory
                elif isinstance(terms_data, list):
                    if any(term.lower() in content_lower for term in terms_data[:5]):
                        return category
            
            # Fallback: use sentiment detection to categorize
            sentiment_indicators = self.domain_loader.get_sentiment_indicators()
            for sentiment_type, terms in sentiment_indicators.items():
                if isinstance(terms, dict):
                    for category, term_list in terms.items():
                        if isinstance(term_list, list) and any(term.lower() in content_lower for term in term_list[:3]):
                            return f"{sentiment_type}_{category}"
                elif isinstance(terms, list) and any(term.lower() in content_lower for term in terms[:3]):
                    return sentiment_type
            
            # Final fallback: generic topic
            return "general"
            
        except Exception as e:
            logger.warning(f"Error in topic extraction from content: {e}")
            return "general"
    
    async def _generate_openai_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate answer using OpenAI API"""
        if not self.api_key_openai:
            raise ValueError("OpenAI API key not set")
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key_openai}"
        }
        
        payload = {
            "model": self.qa_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3  # Lower for more factual responses
        }
        
        response = await self.http_client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code}, {response.text}")
        
        result = response.json()
        answer_text = result["choices"][0]["message"]["content"]
        
        # Extract source references
        source_refs = self._extract_source_references(answer_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(answer_text, source_refs)
        
        return {
            "answer": answer_text,
            "sources": source_refs,
            "confidence": confidence
        }
    
    async def _generate_anthropic_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate answer using Anthropic API"""
        if not self.api_key_anthropic:
            raise ValueError("Anthropic API key not set")
            
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key_anthropic,
            "anthropic-version": "2023-06-01"
        }
        
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        payload = {
            "model": self.qa_model,
            "prompt": f"\n\nHuman: {combined_prompt}\n\nAssistant:",
            "max_tokens_to_sample": 1000,
            "temperature": 0.3
        }
        
        response = await self.http_client.post(
            "https://api.anthropic.com/v1/complete",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API error: {response.status_code}, {response.text}")
        
        result = response.json()
        answer_text = result["completion"]
        
        # Extract source references
        source_refs = self._extract_source_references(answer_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(answer_text, source_refs)
        
        return {
            "answer": answer_text,
            "sources": source_refs,
            "confidence": confidence
        }
    
    async def _generate_azure_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate answer using Azure OpenAI API"""
        if not self.api_key_azure or not self.azure_endpoint:
            raise ValueError("Azure OpenAI API key or endpoint not set")
            
        # Extract deployment name from model name or use directly
        deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", self.qa_model)
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key_azure
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 800
        }
        
        response = await self.http_client.post(
            f"{self.azure_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={self.azure_api_version}",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Azure API error: {response.status_code}, {response.text}")
        
        result = response.json()
        answer_text = result["choices"][0]["message"]["content"]
        
        # Extract source references
        source_refs = self._extract_source_references(answer_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(answer_text, source_refs)
        
        return {
            "answer": answer_text,
            "sources": source_refs,
            "confidence": confidence
        }
    
    async def _generate_cohere_answer(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate answer using Cohere API"""
        if not self.api_key_cohere:
            raise ValueError("Cohere API key not set")
            
        headers = {
            "Authorization": f"Bearer {self.api_key_cohere}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.qa_model,
            "message": user_prompt,
            "preamble": system_prompt,
            "temperature": 0.3,
            "max_tokens": 800
        }
        
        response = await self.http_client.post(
            "https://api.cohere.ai/v1/chat",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Cohere API error: {response.status_code}, {response.text}")
        
        result = response.json()
        answer_text = result["text"]
        
        # Extract source references
        source_refs = self._extract_source_references(answer_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(answer_text, source_refs)
        
        return {
            "answer": answer_text,
            "sources": source_refs,
            "confidence": confidence
        }
    
    def _extract_source_references(self, text: str) -> List[int]:
        """Extract source references from answer text"""
        import re
        # Use regex to find references like [1], [2], etc.
        matches = re.findall(r'\[(\d+)\]', text)
        
        # Convert to integers and deduplicate
        source_refs = []
        for match in matches:
            try:
                num = int(match)
                if num not in source_refs:
                    source_refs.append(num)
            except ValueError:
                pass
                
        return sorted(source_refs)
    
    def _calculate_confidence(self, answer: str, sources: List[int]) -> float:
        """Calculate a confidence score based on answer and sources"""
        # Start with base confidence
        confidence = 0.5
        
        # Adjust based on number of sources
        source_factor = min(0.3, len(sources) * 0.05)
        confidence += source_factor
        
        # Lower confidence for "don't know" answers
        if any(phrase in answer.lower() for phrase in [
            "i don't have enough information",
            "cannot answer",
            "don't know",
            "no information",
            "not mentioned",
            "not provided"
        ]):
            confidence *= 0.5
        
        # Adjust based on answer length (too short or too long are suspect)
        length = len(answer)
        if length < 50:
            confidence *= 0.8
        elif length > 500:
            confidence *= 0.9
        
        # Cap at 0.95
        return min(confidence, 0.95)
    
    def _generate_mock_answer(self, question: str, transcript_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a mock answer for testing without API calls"""
        answer = f"This is a mock answer to the question: '{question}'. "
        
        if transcript_id:
            answer += f"Based on transcript {transcript_id}, "
        
        answer += "I found several relevant points in the transcript. [1] First, the meeting discussed market trends. [2] Second, there were action items assigned to the team."
        
        return {
            "success": True,
            "answer": answer,
            "sources": [1, 2],
            "confidence": 0.7,
            "processing_time": 0.5,
            "is_mock": True
        }
    
    def _generate_mock_answer_text(self, question: str, context: str) -> Dict[str, Any]:
        """Generate a mock answer text from the question and context"""
        # Very simple logic to extract sentences from context that contain words from the question
        question_words = set(question.lower().split())
        context_paragraphs = context.split('\n')
        
        relevant_lines = []
        source_refs = []
        
        for paragraph in context_paragraphs:
            # Look for source markers
            import re
            source_match = re.match(r'\[(\d+)\]', paragraph)
            current_source = int(source_match.group(1)) if source_match else None
            
            # If this paragraph contains question words, add it and its source
            paragraph_lower = paragraph.lower()
            if any(word in paragraph_lower for word in question_words if len(word) > 3):
                relevant_lines.append(paragraph)
                if current_source and current_source not in source_refs:
                    source_refs.append(current_source)
        
        if relevant_lines:
            answer = "Based on the transcript: " + " ".join(relevant_lines[:3])
            for source in source_refs:
                answer += f" [Source: {source}]"
            confidence = 0.7
        else:
            answer = "I don't have enough information in the transcript to answer this question."
            confidence = 0.3
        
        return {
            "answer": answer,
            "sources": source_refs,
            "confidence": confidence
        }
    
    async def extract_key_points(self, transcript_id: str) -> Dict[str, Any]:
        """Extract key points, action items, and insights from a transcript"""
        try:
            start_time = time.time()
            
            # Use mock response if configured
            if self.use_mock:
                logger.info("Using mock response for extract_key_points")
                return self._generate_mock_key_points(transcript_id)
                
            # Get the transcript
            transcript_result = await self.storage_service.get_transcript_by_id(transcript_id)
            if not transcript_result["success"]:
                logger.error(f"Failed to retrieve transcript: {transcript_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": transcript_result.get("error", "Failed to retrieve transcript")
                }
                
            # Combine chunks into a single text for analysis
            chunks = transcript_result.get("chunks", [])
            
            if not chunks:
                logger.warning(f"Transcript {transcript_id} has no chunks")
                return {
                    "success": False,
                    "error": "Transcript has no content"
                }
                
            # Sort chunks by index and combine
            full_text = ""
            for chunk in sorted(chunks, key=lambda x: x.get("chunk_index", 0)):
                full_text += chunk.get("text", "") + "\n\n"
                
            if not full_text:
                logger.warning(f"Transcript {transcript_id} has empty content")
                return {
                    "success": False,
                    "error": "Transcript has no content"
                }
                
            # Limit text length to avoid token limits
            if len(full_text) > self.max_context_length:
                logger.warning(f"Transcript too long ({len(full_text)} chars), trimming to {self.max_context_length}")
                # Trim to first portion - for key points, the beginning is often most important
                full_text = full_text[:self.max_context_length]
                
            # Use LLM to extract key points
            system_prompt = """You are an AI assistant analyzing meeting transcripts.
Extract the following from the transcript:
1. Key Discussion Points: Main topics discussed
2. Action Items: Tasks that were assigned or need to be done
3. Key Decisions: Any decisions made during the meeting
4. Important Insights: Analysis or observations about the topics discussed
5. Follow-up Questions: Potential questions that should be asked in the next meeting

Format each category as a bullet point list."""

            # Call the appropriate provider
            if self.provider == "openai":
                result = await self._extract_points_openai(system_prompt, full_text)
            elif self.provider == "anthropic":
                result = await self._extract_points_anthropic(system_prompt, full_text)
            elif self.provider == "azure":
                result = await self._extract_points_azure(system_prompt, full_text)
            elif self.provider == "cohere":
                result = await self._extract_points_cohere(system_prompt, full_text)
            else:
                # Fallback to mock analysis
                logger.warning(f"Unsupported provider {self.provider}, using mock key points")
                return self._generate_mock_key_points(transcript_id)
                
            # Store the analysis in the database for future reference
            store_result = await self.storage_service.store_key_points(transcript_id, result)
            
            end_time = time.time()
            logger.info(f"Extracted key points for transcript {transcript_id} in {end_time - start_time:.2f}s")
            
            return {
                "success": True,
                "transcript_id": transcript_id,
                "analysis": result,
                "processing_time": end_time - start_time
            }
                
        except Exception as e:
            logger.error(f"Error extracting key points: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _extract_points_openai(self, system_prompt: str, transcript_text: str) -> str:
        """Extract key points using OpenAI API"""
        if not self.api_key_openai:
            raise ValueError("OpenAI API key not set")
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key_openai}"
        }
        
        payload = {
            "model": self.qa_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript_text}
            ],
            "temperature": 0.3
        }
        
        response = await self.http_client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code}, {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    async def _extract_points_anthropic(self, system_prompt: str, transcript_text: str) -> str:
        """Extract key points using Anthropic API"""
        if not self.api_key_anthropic:
            raise ValueError("Anthropic API key not set")
            
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key_anthropic,
            "anthropic-version": "2023-06-01"
        }
        
        prompt = f"{system_prompt}\n\nAnalyze this transcript:\n{transcript_text}"
        
        payload = {
            "model": self.qa_model,
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": 1500,
            "temperature": 0.3
        }
        
        response = await self.http_client.post(
            "https://api.anthropic.com/v1/complete",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API error: {response.status_code}, {response.text}")
        
        result = response.json()
        return result["completion"]
    
    async def _extract_points_azure(self, system_prompt: str, transcript_text: str) -> str:
        """Extract key points using Azure OpenAI API"""
        if not self.api_key_azure or not self.azure_endpoint:
            raise ValueError("Azure OpenAI API key or endpoint not set")
            
        # Extract deployment name from model name or use directly
        deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", self.qa_model)
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key_azure
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript_text}
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        
        response = await self.http_client.post(
            f"{self.azure_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={self.azure_api_version}",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Azure API error: {response.status_code}, {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    async def _extract_points_cohere(self, system_prompt: str, transcript_text: str) -> str:
        """Extract key points using Cohere API"""
        if not self.api_key_cohere:
            raise ValueError("Cohere API key not set")
            
        headers = {
            "Authorization": f"Bearer {self.api_key_cohere}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.qa_model,
            "message": f"Analyze this transcript:\n{transcript_text}",
            "preamble": system_prompt,
            "temperature": 0.3,
            "max_tokens": 1500
        }
        
        response = await self.http_client.post(
            "https://api.cohere.ai/v1/chat",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Cohere API error: {response.status_code}, {response.text}")
        
        result = response.json()
        return result["text"]
    
    def _generate_mock_key_points(self, transcript_id: str) -> Dict[str, Any]:
        """Generate mock key points for testing"""
        analysis = """## Key Discussion Points:
* Quarterly financial performance review
* Market expansion strategy for Q3
* New product launch timeline
* Customer feedback analysis
* Competitor landscape updates

## Action Items:
* Schedule follow-up meeting with product team by Friday
* Complete market analysis report by next week
* Update customer dashboard with latest metrics
* Review budget allocation for Q3
* Contact key partners about upcoming changes

## Key Decisions:
* Approved budget for new marketing campaign
* Selected vendor for analytics platform
* Postponed international expansion until Q4
* Decided to hire three new developers

## Important Insights:
* Customer retention improved by 12% this quarter
* Mobile usage has surpassed desktop for the first time
* Western region showing strongest growth potential
* Price sensitivity increasing in mid-market segment

## Follow-up Questions:
* How will the new pricing structure affect existing customers?
* What specific metrics should we track for the new campaign?
* Should we prioritize feature A or feature B for the next release?
* What adjustments are needed for the Q3 sales targets?"""
        
        return {
            "success": True,
            "transcript_id": transcript_id,
            "analysis": analysis,
            "processing_time": 0.5,
            "is_mock": True
        }
    
    async def _vector_search(self, question_embedding: List[float], transcript_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search in Supabase
        
        Args:
            question_embedding: The embedding vector for the question
            transcript_id: Optional ID of specific transcript to search
            top_k: Number of results to return
            
        Returns:
            List of relevant chunks
        """
        try:
            similarity_threshold = 0.1  # Minimum similarity threshold (lowered for testing)
            
            logger.info(f"Calling vector search with threshold={similarity_threshold}, top_k={top_k}, transcript_id={transcript_id}")
            
            # Call Supabase stored procedure for vector search
            if transcript_id:
                # Search within specific transcript
                logger.info(f"Using match_transcript_semantic_chunks for transcript {transcript_id}")
                response = self.storage_service.client.rpc(
                    "match_transcript_semantic_chunks",
                    {
                        "query_embedding": question_embedding,
                        "transcript_id_param": transcript_id,
                        "match_threshold": similarity_threshold,
                        "match_count": top_k
                    }
                ).execute()
            else:
                # Search across all transcripts
                logger.info("Using match_semantic_chunks for all transcripts")
                response = self.storage_service.client.rpc(
                    "match_semantic_chunks",
                    {
                        "query_embedding": question_embedding,
                        "match_threshold": similarity_threshold,
                        "match_count": top_k
                    }
                ).execute()
            
            # Check for errors
            if hasattr(response, 'error') and response.error is not None:
                logger.error(f"Supabase RPC error: {response.error}")
                return []
            
            chunks = response.data if response.data else []
            logger.info(f"Vector search returned {len(chunks)} chunks")
            
            if chunks:
                logger.info(f"Sample result: {chunks[0] if chunks else 'None'}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []
    
    async def _keyword_search(self, question: str, transcript_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform enhanced keyword search in file storage with better relevance scoring
        
        Args:
            question: The question to search for
            transcript_id: Optional ID of specific transcript to search
            top_k: Number of results to return
            
        Returns:
            List of relevant chunks with similarity scores
        """
        try:
            # Enhanced keyword extraction with comprehensive financial terms and synonyms
            stop_words = {"a", "an", "the", "is", "are", "was", "were", "be", "been", "being", 
                        "in", "on", "at", "to", "for", "with", "about", "what", "when", "where",
                        "how", "why", "who", "which", "that", "do", "does", "did", "can", "could",
                        "will", "would", "should", "shall", "may", "might", "must", "of", "from",
                        "said", "say", "says", "mentioned", "mention", "mentions"}
            
            # Configurable domain-specific keyword expansion (could be loaded from config file)
            domain_config = self._get_domain_config()
            keyword_expansions = domain_config.get('keyword_expansions', {})
            
            # Question-specific keyword detection for comprehensive coverage
            if "how many topics" in question.lower() or "topics" in question.lower():
                # For topic counting questions, cast a wider net
                keywords = set()
                for category, terms in keyword_expansions.items():
                    keywords.update(terms)
                    
                # Add general discussion terms for broader coverage
                additional_terms = domain_config.get('general_terms', [
                    "discussion", "analysis", "session", "review", "update",
                    "trend", "outlook", "perspective", "view", "assessment"
                ])
                keywords.update(additional_terms)
                
            else:
                # For specific questions, use targeted keywords
                keywords = set(word.lower().strip() for word in re.split(r'[^\w\s$]', question.lower()) 
                             if word.strip() and word.lower() not in stop_words and len(word.strip()) > 2)
                
                # Expand based on keyword_expansions
                expanded_keywords = set(keywords)
                for main_term, synonyms in keyword_expansions.items():
                    if any(syn in question.lower() for syn in synonyms):
                        expanded_keywords.update(synonyms)
                
                keywords = expanded_keywords
            
            if not keywords:
                return []
            
            logger.info(f"Keyword search using: {', '.join(keywords)}")
            
            # Get all transcripts or specific transcript
            chunks = []
            
            if transcript_id:
                # Get chunks for specific transcript
                chunks_result = await self.file_storage_service.get_transcript_chunks(transcript_id)
                if chunks_result["success"]:
                    all_chunks = chunks_result["chunks"]
                else:
                    return []
            else:
                # Get all transcripts and their chunks (limit to most recent 5 transcripts)
                transcripts_result = await self.file_storage_service.get_transcripts(limit=5)
                
                if not transcripts_result["success"]:
                    return []
                    
                all_chunks = []
                for transcript in transcripts_result["transcripts"]:
                    transcript_id_loop = transcript.get("id")
                    if transcript_id_loop:
                        chunks_result = await self.file_storage_service.get_transcript_chunks(transcript_id_loop)
                        if chunks_result["success"]:
                            all_chunks.extend(chunks_result["chunks"])
            
            # Enhanced scoring with multiple factors + context continuation
            scored_chunks = []
            chunk_topic_map = {}  # Track which chunks discuss which topics
            
            for chunk in all_chunks:
                chunk_text = chunk.get("text", "").lower()
                chunk_index = chunk.get("chunk_index", 0)
                
                # Calculate multiple relevance scores
                keyword_score = 0
                exact_matches = 0
                phrase_matches = 0
                
                # Count keyword matches
                for keyword in keywords:
                    count = chunk_text.count(keyword.lower())
                    keyword_score += count
                    if count > 0:
                        exact_matches += 1
                
                # Check for phrase matches (higher weight)
                original_question = question.lower()
                question_words = original_question.split()
                for i in range(len(question_words) - 1):
                    phrase = " ".join(question_words[i:i+2])
                    if phrase in chunk_text:
                        phrase_matches += 1
                
                # Bonus for financial terms proximity
                financial_terms = ["points", "level", "average", "break", "support", "resistance", "trend"]
                proximity_bonus = sum(1 for term in financial_terms if term in chunk_text)
                
                # Topic detection for context continuation
                topics_found = []
                if any(word in chunk_text for word in ["gold", "$30", "30 quarter"]):
                    topics_found.append("gold")
                if any(word in chunk_text for word in ["bitcoin", "btc", "115000", "105000"]):
                    topics_found.append("bitcoin")
                if any(word in chunk_text for word in ["s&p", "sp500", "5700", "5500"]):
                    topics_found.append("sp500")
                if any(word in chunk_text for word in ["vix", "volatility", "20 level"]):
                    topics_found.append("volatility")
                if any(word in chunk_text for word in ["crude", "oil", "double bottom"]):
                    topics_found.append("crude")
                
                chunk_topic_map[chunk_index] = topics_found
                
                # Calculate final score
                final_score = (keyword_score * 1.0) + (exact_matches * 1.5) + (phrase_matches * 2.0) + (proximity_bonus * 0.5)
                
                # Add similarity score for compatibility
                similarity = min(final_score / 10.0, 1.0)  # Normalize to 0-1 range
                
                if final_score > 0:
                    # Add similarity to chunk data for consistent interface
                    chunk_with_similarity = dict(chunk)
                    chunk_with_similarity["similarity"] = similarity
                    scored_chunks.append((final_score, chunk_with_similarity))
            
            # Context continuation: if we found chunks about a topic, include adjacent chunks
            question_lower = question.lower()
            target_topic = None
            if "gold" in question_lower:
                target_topic = "gold"
            elif "bitcoin" in question_lower:
                target_topic = "bitcoin"
            elif "s&p" in question_lower or "sp500" in question_lower:
                target_topic = "sp500"
            elif "volatility" in question_lower or "vix" in question_lower:
                target_topic = "volatility"
            elif "crude" in question_lower or "oil" in question_lower:
                target_topic = "crude"
            
            if target_topic:
                # Find chunks that discuss the target topic
                topic_chunks = [idx for idx, topics in chunk_topic_map.items() if target_topic in topics]
                
                # Add adjacent chunks that might continue the discussion
                additional_chunks = []
                for topic_chunk_idx in topic_chunks:
                    # Check chunks immediately after (topic continuation)
                    for offset in [1, 2]:  # Check next 1-2 chunks
                        adjacent_idx = topic_chunk_idx + offset
                        adjacent_chunk = next((c for c in all_chunks if c.get("chunk_index") == adjacent_idx), None)
                        
                        if adjacent_chunk:
                            adjacent_text = adjacent_chunk.get("text", "").lower()
                            
                            # Check if adjacent chunk continues the topic discussion
                            continuation_indicators = [
                                "bulls", "bullish", "bearish", "trend", "upside", "downside",
                                "breakout", "resistance", "support", "momentum", "target",
                                "double top", "primary trend", "consolidate", "retest"
                            ]
                            
                            if any(indicator in adjacent_text for indicator in continuation_indicators):
                                # This looks like topic continuation - add with moderate score
                                continuation_score = 3.0  # Fixed score for continuation chunks
                                similarity = min(continuation_score / 10.0, 1.0)
                                
                                chunk_with_similarity = dict(adjacent_chunk)
                                chunk_with_similarity["similarity"] = similarity
                                additional_chunks.append((continuation_score, chunk_with_similarity))
                                
                                logger.info(f"Added continuation chunk {adjacent_idx} for {target_topic} topic")
                
                # Add continuation chunks to the scored chunks
                scored_chunks.extend(additional_chunks)
            
            # Sort by score and take top_k
            scored_chunks.sort(reverse=True, key=lambda x: x[0])
            result_chunks = [chunk for score, chunk in scored_chunks[:top_k]]
            
            logger.info(f"Enhanced keyword search returned {len(result_chunks)} chunks")
            if result_chunks:
                for i, chunk in enumerate(result_chunks[:3], 1):
                    similarity = chunk.get('similarity', 0)
                    text_preview = chunk.get('text', '')[:100]
                    logger.info(f"  Chunk {i}: similarity={similarity:.4f}, preview='{text_preview}...'")
            
            return result_chunks
            
        except Exception as e:
            logger.error(f"Error in enhanced keyword search: {str(e)}")
            return []
    
    def _get_domain_config(self) -> Dict[str, Any]:
        """
        Get domain-specific configuration for keyword expansions and entity detection.
        This loads configuration from domain files instead of hardcoded values.
        
        Returns:
            Dictionary containing domain-specific configuration
        """
        try:
            # Use domain loader to get current configuration
            domain_config = self.domain_loader.get_current_config()
            domain_terms = self.domain_loader.get_domain_specific_terms()
            
            # Convert domain configuration to the expected format
            config = {
                "keyword_expansions": {},
                "general_terms": [],
                "entity_categories": {}
            }
            
            # Extract terms from domain configuration
            for category, terms_data in domain_terms.items():
                if isinstance(terms_data, dict):
                    for subcategory, terms in terms_data.items():
                        if isinstance(terms, list):
                            # Add to keyword expansions
                            for term in terms:
                                config["keyword_expansions"][term.lower()] = [term.lower()]
                            
                            # Add to entity categories
                            config["entity_categories"][subcategory] = [t.lower() for t in terms]
            
            # Get sentiment indicators as general terms
            sentiment_indicators = self.domain_loader.get_sentiment_indicators()
            for sentiment_type, terms in sentiment_indicators.items():
                if isinstance(terms, dict):
                    for category, term_list in terms.items():
                        if isinstance(term_list, list):
                            config["general_terms"].extend([t.lower() for t in term_list])
                elif isinstance(terms, list):
                    config["general_terms"].extend([t.lower() for t in terms])
            
            return config
            
        except Exception as e:
            logger.warning(f"Could not load domain configuration: {e}")
            # Return minimal fallback configuration
            return {
                "keyword_expansions": {},
                "general_terms": ["good", "bad", "neutral", "positive", "negative"],
                "entity_categories": {
                    "general": ["entity", "item", "topic"]
                }
            } 