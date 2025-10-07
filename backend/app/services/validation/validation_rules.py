"""
Validation Rules Engine

Defines configurable validation rules for different types of LLM outputs.
Rules are designed to be domain-agnostic and configurable through metadata.
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger("bpt-validation-rules")

@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    field_name: str
    rule_name: str
    error_message: Optional[str] = None
    suggested_fix: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ValidationResult to JSON-serializable dictionary"""
        return {
            "is_valid": self.is_valid,
            "field_name": self.field_name,
            "rule_name": self.rule_name,
            "error_message": self.error_message,
            "suggested_fix": self.suggested_fix,
            "severity": self.severity
        }

class ValidationRule(ABC):
    """Abstract base class for validation rules"""
    
    def __init__(self, name: str, description: str, severity: str = "medium"):
        self.name = name
        self.description = description
        self.severity = severity
    
    @abstractmethod
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate a value and return result"""
        pass

class NotNullRule(ValidationRule):
    """Rule to check if a value is not null/empty"""
    
    def __init__(self, allow_empty_string: bool = False):
        super().__init__(
            name="not_null",
            description="Value must not be null or empty",
            severity="high"
        )
        self.allow_empty_string = allow_empty_string
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        field_name = context.get("field_name", "unknown") if context else "unknown"
        
        if value is None:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message=f"Field '{field_name}' is null",
                suggested_fix="Generate meaningful content or use 'Not available' instead of null",
                severity=self.severity
            )
        
        if not self.allow_empty_string and value == "":
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message=f"Field '{field_name}' is empty",
                suggested_fix="Provide descriptive content instead of empty string",
                severity=self.severity
            )
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            rule_name=self.name
        )

class TemplateValueRule(ValidationRule):
    """Rule to detect templated/placeholder values that should be replaced"""
    
    def __init__(self, forbidden_values: List[str] = None):
        super().__init__(
            name="no_template_values",
            description="Value must not contain template placeholders",
            severity="high"
        )
        self.forbidden_values = forbidden_values or [
            "null", "None", "N/A", "TBD", "TODO", "{{", "}}", 
            "Key Levels: null", "Not provided", "Not available"
        ]
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        field_name = context.get("field_name", "unknown") if context else "unknown"
        
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=True,
                field_name=field_name,
                rule_name=self.name
            )
        
        # Check for exact matches or contains forbidden values
        for forbidden in self.forbidden_values:
            if forbidden.lower() in value.lower():
                return ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    rule_name=self.name,
                    error_message=f"Field '{field_name}' contains template value: '{forbidden}'",
                    suggested_fix="Replace with actual content or meaningful description",
                    severity=self.severity
                )
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            rule_name=self.name
        )

class MinContentLengthRule(ValidationRule):
    """Rule to ensure content has minimum meaningful length"""
    
    def __init__(self, min_length: int = 10, min_words: int = 2):
        super().__init__(
            name="min_content_length",
            description=f"Content must have at least {min_length} characters and {min_words} words",
            severity="medium"
        )
        self.min_length = min_length
        self.min_words = min_words
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        field_name = context.get("field_name", "unknown") if context else "unknown"
        
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=True,
                field_name=field_name,
                rule_name=self.name
            )
        
        # Skip validation for certain field types
        if field_name.lower() in ["price", "target", "stop", "entry"]:
            return ValidationResult(
                is_valid=True,
                field_name=field_name,
                rule_name=self.name
            )
        
        # Check both length and word count - both must pass
        char_length_valid = len(value) >= self.min_length
        word_count = len(value.split())
        word_count_valid = word_count >= self.min_words
        
        if not char_length_valid and not word_count_valid:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message=f"Field '{field_name}' too short: {len(value)} characters (min: {self.min_length}) and too few words: {word_count} (min: {self.min_words})",
                suggested_fix="Provide more detailed and descriptive content",
                severity=self.severity
            )
        elif not char_length_valid:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message=f"Field '{field_name}' too short: {len(value)} characters (min: {self.min_length})",
                suggested_fix="Provide more detailed and descriptive content",
                severity=self.severity
            )
        elif not word_count_valid:
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message=f"Field '{field_name}' too few words: {word_count} (min: {self.min_words})",
                suggested_fix="Expand with more descriptive language",
                severity=self.severity
            )
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            rule_name=self.name
        )

class StructuralCompletenessRule(ValidationRule):
    """Rule to check if required fields in structured data are present and valid"""
    
    def __init__(self, required_fields: List[str], optional_fields: List[str] = None):
        super().__init__(
            name="structural_completeness",
            description="Required fields must be present and non-empty",
            severity="high"
        )
        self.required_fields = required_fields
        self.optional_fields = optional_fields or []
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        field_name = context.get("field_name", "unknown") if context else "unknown"
        
        if not isinstance(value, dict):
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message=f"Field '{field_name}' is not a structured object",
                suggested_fix="Ensure output is properly structured",
                severity=self.severity
            )
        
        missing_fields = []
        empty_fields = []
        
        for field in self.required_fields:
            if field not in value:
                missing_fields.append(field)
            elif value[field] is None or value[field] == "":
                empty_fields.append(field)
        
        if missing_fields or empty_fields:
            error_parts = []
            if missing_fields:
                error_parts.append(f"Missing required fields: {', '.join(missing_fields)}")
            if empty_fields:
                error_parts.append(f"Empty required fields: {', '.join(empty_fields)}")
            
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message="; ".join(error_parts),
                suggested_fix="Ensure all required fields are present and contain meaningful content",
                severity=self.severity
            )
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            rule_name=self.name
        )

class ContextualRelevanceRule(ValidationRule):
    """Rule to check if content is contextually relevant to expected content type"""
    
    def __init__(self, content_type: str, keywords: List[str] = None):
        super().__init__(
            name="contextual_relevance",
            description=f"Content must be relevant to {content_type}",
            severity="medium"
        )
        self.content_type = content_type
        self.keywords = keywords or []
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        field_name = context.get("field_name", "unknown") if context else "unknown"
        
        if not isinstance(value, str) or not self.keywords:
            return ValidationResult(
                is_valid=True,
                field_name=field_name,
                rule_name=self.name
            )
        
        # Check if any relevant keywords are present
        value_lower = value.lower()
        relevant_keywords_found = any(keyword.lower() in value_lower for keyword in self.keywords)
        
        if not relevant_keywords_found and len(value) > 20:  # Only validate substantial content
            return ValidationResult(
                is_valid=False,
                field_name=field_name,
                rule_name=self.name,
                error_message=f"Content in '{field_name}' may not be relevant to {self.content_type}",
                suggested_fix=f"Ensure content relates to {self.content_type} and includes relevant terminology",
                severity=self.severity
            )
        
        return ValidationResult(
            is_valid=True,
            field_name=field_name,
            rule_name=self.name
        )

class ValidationRuleEngine:
    """Engine for managing and applying validation rules"""
    
    def __init__(self):
        self.rules = {}
        self.field_rules = {}
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default validation rules for summary content"""
        
        # Summary-specific rules addressing the issues identified
        self.add_rule("summary_theme", [
            NotNullRule(),
            TemplateValueRule(),
            MinContentLengthRule(min_length=15, min_words=3)
        ])
        
        self.add_rule("trade_rationale", [
            NotNullRule(),
            TemplateValueRule(),
            MinContentLengthRule(min_length=20, min_words=4),
            ContextualRelevanceRule("trading", ["buy", "sell", "bullish", "bearish", "support", "resistance", "trend", "level"])
        ])
        
        self.add_rule("trade_idea", [
            StructuralCompletenessRule(
                required_fields=["asset", "strategy", "rationale"],
                optional_fields=["entry", "target", "stop"]
            ),
            TemplateValueRule()
        ])
        
        self.add_rule("qa_content", [
            NotNullRule(),
            MinContentLengthRule(min_length=10, min_words=2)
        ])
        
        self.add_rule("analyst_outlook", [
            NotNullRule(),
            TemplateValueRule(),
            MinContentLengthRule(min_length=15, min_words=3),
            ContextualRelevanceRule("market_analysis", ["market", "price", "trend", "analysis", "outlook", "expect"])
        ])
        
        # General content rules
        self.add_rule("general_content", [
            NotNullRule(),
            TemplateValueRule()
        ])
    
    def add_rule(self, field_type: str, rules: List[ValidationRule]):
        """Add validation rules for a specific field type"""
        self.field_rules[field_type] = rules
        logger.debug(f"Added {len(rules)} rules for field type: {field_type}")
    
    def get_rules_for_field(self, field_name: str, field_type: str = None) -> List[ValidationRule]:
        """Get applicable rules for a specific field"""
        
        # Use field_type if provided, otherwise infer from field_name
        if field_type:
            return self.field_rules.get(field_type, self.field_rules.get("general_content", []))
        
        # Infer field type from field name
        field_lower = field_name.lower()
        
        if "theme" in field_lower or "summary" in field_lower:
            return self.field_rules.get("summary_theme", [])
        elif "rationale" in field_lower or "reason" in field_lower:
            return self.field_rules.get("trade_rationale", [])
        elif "trade" in field_lower and any(x in field_lower for x in ["idea", "strategy", "action"]):
            return self.field_rules.get("trade_idea", [])
        elif "qa" in field_lower or "question" in field_lower or "answer" in field_lower:
            return self.field_rules.get("qa_content", [])
        elif any(x in field_lower for x in ["outlook", "direction", "analysis", "expected_move"]):
            return self.field_rules.get("analyst_outlook", [])
        else:
            return self.field_rules.get("general_content", [])
    
    def validate_field(self, field_name: str, value: Any, field_type: str = None, context: Dict[str, Any] = None) -> List[ValidationResult]:
        """Validate a single field using applicable rules"""
        
        rules = self.get_rules_for_field(field_name, field_type)
        results = []
        
        validation_context = {"field_name": field_name}
        if context:
            validation_context.update(context)
        
        for rule in rules:
            try:
                result = rule.validate(value, validation_context)
                results.append(result)
            except Exception as e:
                logger.error(f"Error applying rule {rule.name} to field {field_name}: {str(e)}")
                results.append(ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    rule_name=rule.name,
                    error_message=f"Validation rule error: {str(e)}",
                    severity="high"
                ))
        
        return results
    
    def validate_structure(self, data: Dict[str, Any], structure_type: str = "summary") -> Dict[str, List[ValidationResult]]:
        """Validate an entire structured object"""
        
        all_results = {}
        
        def validate_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Only validate non-array fields directly
                    if not isinstance(value, list):
                        field_results = self.validate_field(key, value, context={"path": current_path})
                        if field_results:
                            all_results[current_path] = field_results
                    
                    # Recursively validate nested structures
                    if isinstance(value, (dict, list)):
                        validate_recursive(value, current_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    
                    # If the item is a dict, validate it as a structured object
                    if isinstance(item, dict):
                        # For trade ideas and similar structures, apply structure validation
                        parent_field = path.split('.')[-1] if '.' in path else path
                        if parent_field == "trade_ideas":
                            # Apply trade_idea structure validation to each item
                            item_results = self.validate_field("trade_idea", item, "trade_idea", {"path": current_path})
                            if item_results:
                                all_results[current_path] = item_results
                        
                        # Continue recursive validation of the item's contents
                        validate_recursive(item, current_path)
                    else:
                        # For non-dict items in arrays, validate the item itself
                        field_results = self.validate_field(f"item_{i}", item, context={"path": current_path})
                        if field_results:
                            all_results[current_path] = field_results
        
        validate_recursive(data)
        return all_results
    
    def get_validation_summary(self, results: Dict[str, List[ValidationResult]]) -> Dict[str, Any]:
        """Generate a summary of validation results"""
        
        total_checks = sum(len(field_results) for field_results in results.values())
        failed_checks = sum(
            len([r for r in field_results if not r.is_valid]) 
            for field_results in results.values()
        )
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        failed_fields = []
        
        for field_name, field_results in results.items():
            field_failures = [r for r in field_results if not r.is_valid]
            if field_failures:
                failed_fields.append({
                    "field": field_name,
                    "failures": len(field_failures),
                    "errors": [r.error_message for r in field_failures if r.error_message]
                })
                
                for failure in field_failures:
                    severity_counts[failure.severity] += 1
        
        return {
            "total_checks": total_checks,
            "failed_checks": failed_checks,
            "success_rate": (total_checks - failed_checks) / total_checks if total_checks > 0 else 1.0,
            "severity_counts": severity_counts,
            "failed_fields": failed_fields,
            "is_valid": failed_checks == 0
        }

    def validate_all(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, List[ValidationResult]]:
        """
        Validate all fields in a data structure
        
        Args:
            data: Dictionary to validate
            context: Optional validation context
            
        Returns:
            Dictionary mapping field paths to validation results
        """
        return self.validate_structure(data, context.get("structure_type", "summary") if context else "summary") 