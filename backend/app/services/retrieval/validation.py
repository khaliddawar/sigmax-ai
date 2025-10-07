"""Validation Module for Retrieval Responses

Handles validation of QA responses to prevent hallucination and ensure quality.
Extracted from the monolithic retrieval_qa_service.py for better maintainability.

Key responsibilities:
- Response validation against context
- Hallucination detection
- Numeric consistency checking
- Quote accuracy validation
- Grounding verification
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger("retrieval-validation")


@dataclass
class ValidationResult:
    """Result of response validation."""
    is_valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    validation_details: Dict[str, Any]


class BaseValidator(ABC):
    """Abstract base class for response validators."""
    
    @abstractmethod
    async def validate(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Validate a response against context and question."""
        pass
    
    @abstractmethod
    def get_validator_name(self) -> str:
        """Get the name of this validator."""
        pass


class NumericConsistencyValidator(BaseValidator):
    """Validates numeric consistency between response and context."""
    
    def __init__(self):
        self.numeric_pattern = re.compile(r'[\d,]+\.?\d*%?|\$[\d,]+\.?\d*|[\d,]+\.?\d*[KMB]?')
    
    async def validate(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Validate numeric consistency."""
        try:
            # Extract numbers from response and context
            response_numbers = self.numeric_pattern.findall(response)
            context_numbers = self.numeric_pattern.findall(context)
            
            # Normalize numbers for comparison
            normalized_context = [self._normalize_number(num) for num in context_numbers]
            
            invalid_numbers = []
            for num in response_numbers:
                normalized_num = self._normalize_number(num)
                if normalized_num not in normalized_context:
                    invalid_numbers.append(num)
            
            is_valid = len(invalid_numbers) == 0
            confidence = 1.0 if is_valid else 0.3
            
            issues = [f"Ungrounded number: {num}" for num in invalid_numbers] if invalid_numbers else []
            suggestions = ["Ensure all numbers come from the source context"] if invalid_numbers else []
            
            return ValidationResult(
                is_valid=is_valid,
                confidence=confidence,
                issues=issues,
                suggestions=suggestions,
                validation_details={
                    "response_numbers": response_numbers,
                    "context_numbers": context_numbers,
                    "invalid_numbers": invalid_numbers
                }
            )
            
        except Exception as e:
            logger.error(f"Numeric validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"Validation error: {str(e)}"],
                suggestions=["Check numeric validation configuration"],
                validation_details={"error": str(e)}
            )
    
    def _normalize_number(self, num_str: str) -> str:
        """Normalize number string for comparison."""
        return re.sub(r'[,$]', '', num_str.lower())
    
    def get_validator_name(self) -> str:
        return "numeric_consistency"


class QuoteAccuracyValidator(BaseValidator):
    """Validates accuracy of quoted text against source context."""
    
    def __init__(self, min_quote_length: int = 6):
        self.min_quote_length = min_quote_length
        self.quote_patterns = [
            re.compile(r'"([^"]{' + str(min_quote_length) + r',})"'),  # Double quotes
            re.compile(r"'([^']{" + str(min_quote_length) + r",})'"),   # Single quotes
            re.compile(r'«([^»]{' + str(min_quote_length) + r',})»'),   # Guillemets
        ]
    
    async def validate(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Validate quote accuracy."""
        try:
            # Extract quotes from response
            quotes = []
            for pattern in self.quote_patterns:
                quotes.extend(pattern.findall(response))
            
            # Check each quote against context
            invalid_quotes = []
            for quote in quotes:
                if not self._is_quote_in_context(quote, context):
                    invalid_quotes.append(quote)
            
            is_valid = len(invalid_quotes) == 0
            confidence = 1.0 if is_valid else 0.2
            
            issues = [f"Invalid quote: {quote[:50]}..." for quote in invalid_quotes] if invalid_quotes else []
            suggestions = ["Ensure all quotes are exact matches from the source"] if invalid_quotes else []
            
            return ValidationResult(
                is_valid=is_valid,
                confidence=confidence,
                issues=issues,
                suggestions=suggestions,
                validation_details={
                    "total_quotes": len(quotes),
                    "invalid_quotes": invalid_quotes,
                    "valid_quotes": len(quotes) - len(invalid_quotes)
                }
            )
            
        except Exception as e:
            logger.error(f"Quote validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"Quote validation error: {str(e)}"],
                suggestions=["Check quote validation configuration"],
                validation_details={"error": str(e)}
            )
    
    def _is_quote_in_context(self, quote: str, context: str) -> bool:
        """Check if quote exists in context with some fuzzy matching."""
        # Direct match
        if quote in context:
            return True
        
        # Fuzzy match (allowing for minor differences in whitespace/punctuation)
        normalized_quote = re.sub(r'\s+', ' ', quote.strip().lower())
        normalized_context = re.sub(r'\s+', ' ', context.lower())
        
        return normalized_quote in normalized_context
    
    def get_validator_name(self) -> str:
        return "quote_accuracy"


class ContextGroundingValidator(BaseValidator):
    """Validates that response is grounded in the provided context."""
    
    def __init__(self, grounding_threshold: float = 0.4):
        self.grounding_threshold = grounding_threshold
        self.common_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }
    
    async def validate(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Validate context grounding."""
        try:
            issues = []
            
            # Check question relevance
            question_relevance = self._check_question_relevance(response, question)
            if question_relevance < 0.3:
                issues.append("Response may not address the question adequately")
            
            # Check context grounding
            grounding_ratio = self._calculate_grounding_ratio(response, context)
            if grounding_ratio < self.grounding_threshold:
                issues.append(f"Response may not be sufficiently grounded in context (ratio: {grounding_ratio:.2f})")
            
            is_valid = len(issues) == 0
            confidence = min(question_relevance, grounding_ratio)
            
            suggestions = []
            if grounding_ratio < self.grounding_threshold:
                suggestions.append("Improve grounding of response concepts in the provided context")
            if question_relevance < 0.3:
                suggestions.append("Ensure response directly addresses the question")
            
            return ValidationResult(
                is_valid=is_valid,
                confidence=confidence,
                issues=issues,
                suggestions=suggestions,
                validation_details={
                    "question_relevance": question_relevance,
                    "grounding_ratio": grounding_ratio,
                    "grounding_threshold": self.grounding_threshold
                }
            )
            
        except Exception as e:
            logger.error(f"Context grounding validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"Grounding validation error: {str(e)}"],
                suggestions=["Check grounding validation configuration"],
                validation_details={"error": str(e)}
            )
    
    def _check_question_relevance(self, response: str, question: str) -> float:
        """Check how well the response addresses the question."""
        question_keywords = [
            word.lower() for word in question.split() 
            if len(word) > 3 and word.lower() not in self.common_words
        ]
        
        if not question_keywords:
            return 1.0  # No meaningful keywords to check
        
        response_lower = response.lower()
        keyword_matches = sum(1 for keyword in question_keywords if keyword in response_lower)
        
        return keyword_matches / len(question_keywords)
    
    def _calculate_grounding_ratio(self, response: str, context: str) -> float:
        """Calculate how well the response is grounded in context."""
        response_words = [
            word.lower() for word in response.split()
            if len(word) > 4 and word.lower() not in self.common_words
        ]
        
        if not response_words:
            return 1.0  # No meaningful words to check
        
        context_lower = context.lower()
        grounded_words = sum(1 for word in response_words if word in context_lower)
        
        return grounded_words / len(response_words)
    
    def get_validator_name(self) -> str:
        return "context_grounding"


class CompositeValidator(BaseValidator):
    """Combines multiple validators for comprehensive validation."""
    
    def __init__(self, validators: List[BaseValidator], weights: Optional[Dict[str, float]] = None):
        self.validators = validators
        self.weights = weights or {}
        
        # Default weights if not specified
        default_weights = {
            "numeric_consistency": 0.3,
            "quote_accuracy": 0.3,
            "context_grounding": 0.4
        }
        
        for validator in validators:
            name = validator.get_validator_name()
            if name not in self.weights:
                self.weights[name] = default_weights.get(name, 1.0 / len(validators))
    
    async def validate(
        self,
        response: str,
        context: str,
        question: str,
        **kwargs
    ) -> ValidationResult:
        """Run all validators and combine results."""
        try:
            # Run all validators
            validation_results = []
            for validator in self.validators:
                result = await validator.validate(response, context, question, **kwargs)
                validation_results.append((validator.get_validator_name(), result))
            
            # Combine results
            all_issues = []
            all_suggestions = []
            validation_details = {}
            
            total_weight = 0.0
            weighted_confidence = 0.0
            all_valid = True
            
            for validator_name, result in validation_results:
                weight = self.weights.get(validator_name, 1.0)
                total_weight += weight
                weighted_confidence += result.confidence * weight
                
                if not result.is_valid:
                    all_valid = False
                
                all_issues.extend(result.issues)
                all_suggestions.extend(result.suggestions)
                validation_details[validator_name] = result.validation_details
            
            # Calculate overall confidence
            overall_confidence = weighted_confidence / total_weight if total_weight > 0 else 0.0
            
            # Remove duplicate suggestions
            unique_suggestions = list(set(all_suggestions))
            
            return ValidationResult(
                is_valid=all_valid,
                confidence=overall_confidence,
                issues=all_issues,
                suggestions=unique_suggestions,
                validation_details={
                    "individual_validations": validation_details,
                    "weights_used": self.weights,
                    "overall_confidence": overall_confidence
                }
            )
            
        except Exception as e:
            logger.error(f"Composite validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"Composite validation error: {str(e)}"],
                suggestions=["Check composite validator configuration"],
                validation_details={"error": str(e)}
            )
    
    def get_validator_name(self) -> str:
        return "composite_validator"


# Factory function for creating default validator
def create_default_validator() -> CompositeValidator:
    """Create a default composite validator with standard validators."""
    validators = [
        NumericConsistencyValidator(),
        QuoteAccuracyValidator(),
        ContextGroundingValidator()
    ]
    
    return CompositeValidator(validators)


# Factory function for creating strict validator
def create_strict_validator() -> CompositeValidator:
    """Create a strict validator with higher thresholds."""
    validators = [
        NumericConsistencyValidator(),
        QuoteAccuracyValidator(min_quote_length=4),  # Stricter quote length
        ContextGroundingValidator(grounding_threshold=0.6)  # Higher grounding threshold
    ]
    
    weights = {
        "numeric_consistency": 0.4,
        "quote_accuracy": 0.4,
        "context_grounding": 0.2
    }
    
    return CompositeValidator(validators, weights) 