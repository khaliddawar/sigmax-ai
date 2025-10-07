"""
Prompt Validation System

This module provides domain-agnostic prompt engineering and validation capabilities
for ensuring structured, evidence-based LLM responses across all domains.

Key features:
- Universal evidence citation format with {{ }} braces
- Configurable response structure validation
- Domain-agnostic retry logic for missing evidence
- Numeric value and sentiment validation
- Consistency checking across multiple runs
- Structured prompt templates that work across domains
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum

# Import our hybrid retrieval system
from .hybrid_retriever import HybridRetriever, RetrievalResult
from .semantic_chunker import ChunkMetadata
from config.domain_loader import get_domain_loader
from config.settings import get_validation_config

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types of responses requiring different validation"""
    FACTUAL = "factual"          # Direct factual questions
    NUMERIC = "numeric"          # Questions requiring numeric values
    SENTIMENT = "sentiment"      # Questions about opinions/sentiment
    INVENTORY = "inventory"      # Questions about topics/entities count
    COMPARISON = "comparison"    # Comparative questions

@dataclass
class ValidationResult:
    """Result of response validation with detailed feedback"""
    is_valid: bool
    has_evidence: bool
    has_required_numeric: bool
    sentiment_matches: bool
    missing_elements: List[str]
    validation_errors: List[str]
    evidence_count: int
    retry_recommended: bool

@dataclass
class PromptTemplate:
    """Domain-agnostic prompt template structure"""
    system_prompt: str
    user_prompt: str
    response_format: str
    validation_rules: Dict[str, Any]
    retry_prompt: str

class PromptValidator:
    """
    Domain-agnostic prompt validation system.
    
    This class implements sophisticated prompt engineering and validation
    that works across financial, medical, legal, technical, and other domains
    without hardcoded assumptions.
    """
    
    def __init__(self, retriever: HybridRetriever):
        """
        Initialize the prompt validator.
        
        Args:
            retriever: Hybrid retrieval system for evidence gathering
        """
        self.retriever = retriever
        self.domain_loader = get_domain_loader()
        
        # Load validation configuration
        validation_config = get_validation_config()
        self.max_retries = validation_config.get('max_retries', 3)
        self.evidence_required = validation_config.get('evidence_required', True)
        self.numeric_validation = validation_config.get('numeric_validation', True)
        self.sentiment_validation = validation_config.get('sentiment_validation', True)
        
        # Evidence patterns
        self.evidence_pattern = re.compile(r'\{\{([^}]+)\}\}')
        
        # Initialize prompt templates
        self._init_prompt_templates()
        
        logger.info("PromptValidator initialized with domain-agnostic validation")
    
    def _init_prompt_templates(self) -> None:
        """Initialize domain-agnostic prompt templates"""
        
        # Base system prompt that works across all domains
        base_system_prompt = """You are a precise information extraction assistant. Your role is to provide accurate, evidence-based answers using only the provided context.

Key Instructions:
1. Always cite evidence using {{ }} braces around direct quotes
2. Only include information that can be found in the provided context
3. If information is missing or unclear, say "insufficient data"
4. Be precise with numeric values when they appear in context
5. Maintain consistent sentiment interpretation based on source material
6. Focus on factual accuracy over speculation"""

        # Universal response format
        base_response_format = """Answer in max 2 sentences:
1) Direct answer to the user question.
2) Cite the relevant evidence inside {{ }} braces.

If unsure, say "insufficient data"."""

        # Prompt templates for different response types
        self.prompt_templates = {
            ResponseType.FACTUAL: PromptTemplate(
                system_prompt=base_system_prompt,
                user_prompt="Context:\n{context}\n\nQuestion: {question}\n\n" + base_response_format,
                response_format=base_response_format,
                validation_rules={"evidence_required": True, "numeric_check": False},
                retry_prompt="The previous response lacked proper evidence citations. Please provide a response with evidence in {{ }} braces from the context."
            ),
            
            ResponseType.NUMERIC: PromptTemplate(
                system_prompt=base_system_prompt + "\n\nSpecial attention: Include specific numeric values from the context when answering quantitative questions.",
                user_prompt="Context:\n{context}\n\nQuestion: {question}\n\nFocus on including any numeric values, measurements, or quantities mentioned in the context.\n\n" + base_response_format,
                response_format=base_response_format,
                validation_rules={"evidence_required": True, "numeric_check": True},
                retry_prompt="The previous response was missing numeric values. Please include ONLY the specific numbers, measurements, or quantities that are explicitly mentioned in the context above with evidence in {{ }} braces. If no numbers are mentioned in the context, state 'no specific numbers provided in source material'."
            ),
            
            ResponseType.SENTIMENT: PromptTemplate(
                system_prompt=base_system_prompt + "\n\nSpecial attention: When discussing opinions or sentiment, cite the exact phrases that indicate the sentiment.",
                user_prompt="Context:\n{context}\n\nQuestion: {question}\n\nFocus on sentiment-indicating phrases and quote them directly.\n\n" + base_response_format,
                response_format=base_response_format,
                validation_rules={"evidence_required": True, "sentiment_check": True},
                retry_prompt="The previous response needs clearer sentiment evidence. Please cite the exact phrases that indicate the sentiment using {{ }} braces."
            ),
            
            ResponseType.INVENTORY: PromptTemplate(
                system_prompt=base_system_prompt + "\n\nSpecial attention: When counting topics or entities, be comprehensive and specific.",
                user_prompt="Context:\n{context}\n\nQuestion: {question}\n\nProvide a complete count and list specific items mentioned in the context.\n\n" + base_response_format,
                response_format=base_response_format,
                validation_rules={"evidence_required": True, "comprehensive_list": True},
                retry_prompt="The previous response may have missed some items. Please provide a comprehensive count with specific examples in {{ }} braces."
            ),
            
            ResponseType.COMPARISON: PromptTemplate(
                system_prompt=base_system_prompt + "\n\nSpecial attention: When comparing entities, cite evidence for each comparison point.",
                user_prompt="Context:\n{context}\n\nQuestion: {question}\n\nCompare using specific evidence for each entity mentioned.\n\n" + base_response_format,
                response_format=base_response_format,
                validation_rules={"evidence_required": True, "balanced_comparison": True},
                retry_prompt="The previous response needs more balanced evidence. Please cite evidence for each entity being compared using {{ }} braces."
            )
        }
    
    def classify_response_type(self, question: str) -> ResponseType:
        """
        Classify the question to determine appropriate prompt template.
        
        Args:
            question: User's question
            
        Returns:
            Response type for template selection
        """
        question_lower = question.lower()
        
        # Inventory patterns (how many, list all, what topics)
        inventory_patterns = [
            r'how many', r'list all', r'what topics', r'which.*discussed',
            r'topics.*covered', r'count.*', r'enumerate', r'identify all'
        ]
        
        # Numeric patterns (price, target, value, percentage)
        numeric_patterns = [
            r'price', r'target', r'value', r'percentage', r'percent', r'level',
            r'amount', r'size', r'quantity', r'measure', r'rate', r'cost'
        ]
        
        # Sentiment patterns (opinion, view, sentiment, bullish, bearish)
        sentiment_patterns = [
            r'view', r'opinion', r'sentiment', r'think', r'feel', r'believe',
            r'positive', r'negative', r'optimistic', r'pessimistic', r'outlook'
        ]
        
        # Comparison patterns (versus, compared to, better, worse)
        comparison_patterns = [
            r'versus', r'vs', r'compared to', r'compare', r'better', r'worse',
            r'more.*than', r'less.*than', r'against', r'relative to'
        ]
        
        # Check patterns in order of specificity
        for pattern in inventory_patterns:
            if re.search(pattern, question_lower):
                return ResponseType.INVENTORY
        
        for pattern in comparison_patterns:
            if re.search(pattern, question_lower):
                return ResponseType.COMPARISON
        
        for pattern in sentiment_patterns:
            if re.search(pattern, question_lower):
                return ResponseType.SENTIMENT
        
        for pattern in numeric_patterns:
            if re.search(pattern, question_lower):
                return ResponseType.NUMERIC
        
        # Default to factual
        return ResponseType.FACTUAL
    
    async def generate_validated_response(self, question: str, 
                                        llm_service, 
                                        k: Optional[int] = None) -> Tuple[str, ValidationResult]:
        """
        Generate a validated response using structured prompts and validation.
        
        Args:
            question: User's question
            llm_service: LLM service for response generation
            k: Number of chunks to retrieve (optional)
            
        Returns:
            Tuple of (response, validation_result)
        """
        # Step 1: Classify question and get appropriate template
        response_type = self.classify_response_type(question)
        template = self.prompt_templates[response_type]
        
        logger.info(f"Classified question as {response_type.value}")
        
        # Step 2: Retrieve relevant chunks
        retrieval_results = await self.retriever.retrieve(question, k=k)
        
        if not retrieval_results:
            return "insufficient data", ValidationResult(
                is_valid=True, has_evidence=False, has_required_numeric=False,
                sentiment_matches=True, missing_elements=["context"],
                validation_errors=["No relevant context found"], evidence_count=0,
                retry_recommended=False
            )
        
        # Step 3: Build context from retrieval results
        context = self._build_context_from_results(retrieval_results)
        
        # Step 4: Generate initial response
        response = await self._generate_response_with_template(
            question, context, template, llm_service
        )
        
        # Step 5: Validate response
        validation_result = self._validate_response(
            response, retrieval_results, template.validation_rules
        )
        
        # Step 6: Retry if validation fails
        retry_count = 0
        while (not validation_result.is_valid and 
               validation_result.retry_recommended and 
               retry_count < self.max_retries):
            
            logger.info(f"Retrying response generation (attempt {retry_count + 1})")
            
            # Generate retry prompt with specific feedback
            retry_prompt = self._build_retry_prompt(
                question, context, template, validation_result
            )
            
            response = await llm_service.generate_response(retry_prompt)
            validation_result = self._validate_response(
                response, retrieval_results, template.validation_rules
            )
            
            retry_count += 1
        
        return response, validation_result
    
    def _build_context_from_results(self, results: List[RetrievalResult]) -> str:
        """
        Build context string from retrieval results with source tracking.
        
        Args:
            results: List of retrieval results
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, result in enumerate(results, 1):
            chunk = result.chunk
            context_parts.append(f"[{i}] {chunk.text}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_response_with_template(self, question: str, context: str,
                                             template: PromptTemplate,
                                             llm_service) -> str:
        """
        Generate response using the specified template.
        
        Args:
            question: User's question
            context: Retrieved context
            template: Prompt template to use
            llm_service: LLM service for generation
            
        Returns:
            Generated response
        """
        try:
            # Format the prompt
            formatted_prompt = template.user_prompt.format(
                context=context,
                question=question
            )
            
            # Generate response
            response = await llm_service.generate_response(
                prompt=formatted_prompt,
                system_prompt=template.system_prompt
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "insufficient data"
    
    def _validate_response(self, response: str, 
                         retrieval_results: List[RetrievalResult],
                         validation_rules: Dict[str, Any]) -> ValidationResult:
        """
        Validate response against domain-agnostic rules.
        
        Args:
            response: Generated response
            retrieval_results: Context used for generation
            validation_rules: Validation rules for this response type
            
        Returns:
            Validation result with detailed feedback
        """
        # Initialize validation state
        is_valid = True
        missing_elements = []
        validation_errors = []
        
        # Check for evidence citations
        evidence_matches = self.evidence_pattern.findall(response)
        has_evidence = len(evidence_matches) > 0
        
        if validation_rules.get("evidence_required", True) and not has_evidence:
            is_valid = False
            missing_elements.append("evidence_citations")
            validation_errors.append("Response lacks evidence citations in {{ }} braces")
        
        # Check for numeric values if required
        has_required_numeric = True
        if validation_rules.get("numeric_check", False):
            has_required_numeric = self._has_numeric_values(response, retrieval_results)
            if not has_required_numeric:
                is_valid = False
                missing_elements.append("numeric_values")
                validation_errors.append("Response missing required numeric values")
        
        # Check sentiment consistency if required
        sentiment_matches = True
        if validation_rules.get("sentiment_check", False):
            sentiment_matches = self._validate_sentiment_consistency(
                response, retrieval_results
            )
            if not sentiment_matches:
                is_valid = False
                missing_elements.append("sentiment_consistency")
                validation_errors.append("Response sentiment inconsistent with source")
        
        # Determine if retry is recommended
        retry_recommended = (
            not is_valid and 
            len(missing_elements) > 0 and
            "insufficient data" not in response.lower()
        )
        
        return ValidationResult(
            is_valid=is_valid,
            has_evidence=has_evidence,
            has_required_numeric=has_required_numeric,
            sentiment_matches=sentiment_matches,
            missing_elements=missing_elements,
            validation_errors=validation_errors,
            evidence_count=len(evidence_matches),
            retry_recommended=retry_recommended
        )
    
    def _has_numeric_values(self, response: str, 
                           retrieval_results: List[RetrievalResult]) -> bool:
        """
        Check if response contains numeric values when they're available in context.
        
        Args:
            response: Generated response
            retrieval_results: Context that was used
            
        Returns:
            True if numeric requirements are met
        """
        # Look for numeric patterns in response
        numeric_pattern = re.compile(r'\d+(?:\.\d+)?(?:\s*%|percent|dollars?|points?)?')
        response_numbers = numeric_pattern.findall(response)
        
        # Look for numeric patterns in context
        context_numbers = []
        for result in retrieval_results:
            context_numbers.extend(numeric_pattern.findall(result.chunk.text))
        
        # If context has numbers but response doesn't, validation fails
        if context_numbers and not response_numbers:
            return False
        
        return True
    
    def _validate_sentiment_consistency(self, response: str,
                                      retrieval_results: List[RetrievalResult]) -> bool:
        """
        Validate that response sentiment matches source chunk sentiment.
        
        Args:
            response: Generated response
            retrieval_results: Context chunks with sentiment metadata
            
        Returns:
            True if sentiment is consistent
        """
        # Get sentiment indicators from domain configuration
        try:
            domain_config = self.domain_loader.get_sentiment_indicators()
            positive_terms = domain_config.get('positive', [])
            negative_terms = domain_config.get('negative', [])
        except:
            # Fallback to basic sentiment detection
            positive_terms = ['positive', 'good', 'excellent', 'strong', 'bullish']
            negative_terms = ['negative', 'bad', 'poor', 'weak', 'bearish']
        
        response_lower = response.lower()
        
        # Determine response sentiment
        response_sentiment = "neutral"
        if any(term in response_lower for term in positive_terms):
            response_sentiment = "positive"
        elif any(term in response_lower for term in negative_terms):
            response_sentiment = "negative"
        
        # Check against source chunk sentiments
        source_sentiments = [result.chunk.sentiment for result in retrieval_results 
                           if result.chunk.sentiment]
        
        if not source_sentiments:
            return True  # No sentiment to validate against
        
        # Allow response sentiment if it matches any source sentiment
        return response_sentiment in source_sentiments or response_sentiment == "neutral"
    
    def _build_retry_prompt(self, question: str, context: str,
                          template: PromptTemplate, 
                          validation_result: ValidationResult) -> str:
        """
        Build retry prompt with specific feedback about validation failures.
        
        Args:
            question: Original question
            context: Retrieved context
            template: Current template
            validation_result: Failed validation result
            
        Returns:
            Retry prompt with specific guidance
        """
        # Start with base retry prompt
        retry_prompt = template.retry_prompt
        
        # Add specific feedback based on missing elements
        if "evidence_citations" in validation_result.missing_elements:
            retry_prompt += "\n\nMake sure to include direct quotes from the context using {{ }} braces."
        
        if "numeric_values" in validation_result.missing_elements:
            retry_prompt += "\n\nInclude specific numeric values that appear in the context."
        
        if "sentiment_consistency" in validation_result.missing_elements:
            retry_prompt += "\n\nEnsure sentiment interpretation matches the tone in the source material."
        
        # Build full retry prompt
        full_retry_prompt = f"""{template.system_prompt}

Context:
{context}

Question: {question}

Previous attempt had these issues: {', '.join(validation_result.validation_errors)}

{retry_prompt}

{template.response_format}"""
        
        return full_retry_prompt
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics and configuration"""
        return {
            "max_retries": self.max_retries,
            "evidence_required": self.evidence_required,
            "numeric_validation": self.numeric_validation,
            "sentiment_validation": self.sentiment_validation,
            "available_response_types": [rt.value for rt in ResponseType],
            "evidence_pattern": self.evidence_pattern.pattern
        } 