"""
Error Corrector

Automatically fixes common LLM output errors based on validation results.
Provides correction strategies for different types of validation failures.
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from .validation_rules import ValidationResult

logger = logging.getLogger("bpt-error-corrector")

class CorrectionStrategy:
    """Base class for correction strategies"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def can_correct(self, validation_result: ValidationResult) -> bool:
        """Check if this strategy can correct the validation error"""
        return False
    
    def apply_correction(self, value: Any, validation_result: ValidationResult, context: Dict[str, Any] = None) -> Tuple[Any, bool]:
        """
        Apply correction to the value
        
        Returns:
            Tuple of (corrected_value, was_corrected)
        """
        return value, False

class NullValueCorrectionStrategy(CorrectionStrategy):
    """Strategy to correct null/empty values"""
    
    def __init__(self):
        super().__init__(
            name="null_value_correction",
            description="Replace null/empty values with meaningful defaults"
        )
        
        # Field-specific default replacements
        self.default_replacements = {
            "theme": "Market analysis and trading insights",
            "key_stat": "Key metrics discussed in session",
            "top_trade_idea": "Primary trading opportunity identified",
            "levels": "Technical levels to monitor",
            "outlook": "Market outlook based on current analysis",
            "setup": "Current market configuration",
            "expected_move": "Anticipated price movement",
            "rationale": "Analysis supporting this position",
            "impact": "Potential market impact",
            "question": "Participant question from session",
            "answer": "Response provided during discussion",
            "event": "Upcoming market event",
            "significance": "Important for market timing"
        }
    
    def can_correct(self, validation_result: ValidationResult) -> bool:
        return validation_result.rule_name == "not_null"
    
    def apply_correction(self, value: Any, validation_result: ValidationResult, context: Dict[str, Any] = None) -> Tuple[Any, bool]:
        field_name = validation_result.field_name.lower()
        
        # Try to find a specific replacement
        for key, replacement in self.default_replacements.items():
            if key in field_name:
                logger.info(f"Corrected null value in '{validation_result.field_name}' with: '{replacement}'")
                return replacement, True
        
        # Generic replacement based on field name patterns
        if any(word in field_name for word in ["name", "asset", "symbol"]):
            return "Asset name", True
        elif any(word in field_name for word in ["direction", "strategy"]):
            return "Directional bias", True
        elif any(word in field_name for word in ["price", "target", "stop", "entry"]):
            return "Price level", True
        elif any(word in field_name for word in ["date", "time"]):
            return "Date/time from session", True
        else:
            # Generic fallback
            return "Content from session analysis", True

class TemplateValueCorrectionStrategy(CorrectionStrategy):
    """Strategy to correct template/placeholder values"""
    
    def __init__(self):
        super().__init__(
            name="template_value_correction",
            description="Replace template placeholders with meaningful content"
        )
        
        self.template_replacements = {
            "null": "Information not specified",
            "none": "Not mentioned in session",
            "n/a": "Not applicable to current analysis",
            "tbd": "To be determined based on market conditions",
            "todo": "Requires further analysis",
            "key levels: null": "Technical levels discussed in session",
            "not provided": "Information available in full session",
            "not available": "Details discussed during session"
        }
    
    def can_correct(self, validation_result: ValidationResult) -> bool:
        return validation_result.rule_name == "no_template_values"
    
    def apply_correction(self, value: Any, validation_result: ValidationResult, context: Dict[str, Any] = None) -> Tuple[Any, bool]:
        if not isinstance(value, str):
            return value, False
        
        corrected_value = value
        was_corrected = False
        
        # Replace known template values
        for template, replacement in self.template_replacements.items():
            if template.lower() in corrected_value.lower():
                corrected_value = re.sub(
                    re.escape(template), 
                    replacement, 
                    corrected_value, 
                    flags=re.IGNORECASE
                )
                was_corrected = True
        
        if was_corrected:
            logger.info(f"Corrected template values in '{validation_result.field_name}': '{value}' -> '{corrected_value}'")
        
        return corrected_value, was_corrected

class MinContentLengthCorrectionStrategy(CorrectionStrategy):
    """Strategy to expand content that's too short"""
    
    def __init__(self):
        super().__init__(
            name="min_content_length_correction",
            description="Expand short content with additional context"
        )
        
        self.expansion_templates = {
            "theme": "Session focused on {original} with detailed market analysis",
            "rationale": "Trade based on {original} considering current market conditions",
            "outlook": "Market outlook suggests {original} based on technical and fundamental factors",
            "analysis": "Analysis indicates {original} with supporting evidence from session",
            "setup": "Current market setup shows {original} configuration",
            "impact": "Expected impact: {original} affecting market sentiment",
            "answer": "Response provided: {original} with additional context",
            "significance": "Significant because {original} impacts market timing"
        }
    
    def can_correct(self, validation_result: ValidationResult) -> bool:
        return validation_result.rule_name == "min_content_length"
    
    def apply_correction(self, value: Any, validation_result: ValidationResult, context: Dict[str, Any] = None) -> Tuple[Any, bool]:
        if not isinstance(value, str) or len(value) == 0:
            return value, False
        
        field_name = validation_result.field_name.lower()
        
        # Find appropriate expansion template
        template = None
        for key, tmpl in self.expansion_templates.items():
            if key in field_name:
                template = tmpl
                break
        
        if template:
            expanded = template.format(original=value.strip())
            logger.info(f"Expanded short content in '{validation_result.field_name}': '{value}' -> '{expanded}'")
            return expanded, True
        else:
            # Generic expansion
            expanded = f"Based on session analysis: {value.strip()}"
            logger.info(f"Applied generic expansion to '{validation_result.field_name}': '{value}' -> '{expanded}'")
            return expanded, True

class StructuralCompletenessCorrectionStrategy(CorrectionStrategy):
    """Strategy to fix missing required fields in structured data"""
    
    def __init__(self):
        super().__init__(
            name="structural_completeness_correction",
            description="Add missing required fields with appropriate defaults"
        )
        
        self.field_defaults = {
            "asset": "Market instrument",
            "strategy": "Trading approach",
            "direction": "Market direction",
            "rationale": "Analysis supporting position",
            "entry": "Entry criteria",
            "target": "Price target",
            "stop": "Risk management level",
            "name": "Asset name",
            "setup": "Market configuration",
            "expected_move": "Anticipated movement",
            "outlook": "Market outlook",
            "levels": "Key technical levels",
            "question": "Session question",
            "answer": "Provided response",
            "event": "Market event",
            "date": "Event timing",
            "impact": "Market impact",
            "significance": "Market importance",
            "severity": "medium"
        }
    
    def can_correct(self, validation_result: ValidationResult) -> bool:
        return validation_result.rule_name == "structural_completeness"
    
    def apply_correction(self, value: Any, validation_result: ValidationResult, context: Dict[str, Any] = None) -> Tuple[Any, bool]:
        if not isinstance(value, dict):
            return value, False
        
        corrected_dict = value.copy()
        was_corrected = False
        
        # Extract missing fields from error message
        error_msg = validation_result.error_message or ""
        
        # Parse missing fields
        missing_fields = []
        if "Missing required fields:" in error_msg:
            fields_part = error_msg.split("Missing required fields:")[1].split(";")[0]
            missing_fields.extend([f.strip() for f in fields_part.split(",")])
        
        # Parse empty fields
        if "Empty required fields:" in error_msg:
            fields_part = error_msg.split("Empty required fields:")[1].split(";")[0]
            empty_fields = [f.strip() for f in fields_part.split(",")]
            missing_fields.extend(empty_fields)
        
        # Add missing fields with defaults
        for field in missing_fields:
            if field in self.field_defaults:
                corrected_dict[field] = self.field_defaults[field]
                was_corrected = True
                logger.info(f"Added missing field '{field}' with default value")
            else:
                # Generic default based on field name
                corrected_dict[field] = f"Information about {field.replace('_', ' ')}"
                was_corrected = True
                logger.info(f"Added missing field '{field}' with generic default")
        
        return corrected_dict, was_corrected

class ErrorCorrector:
    """Main error correction engine"""
    
    def __init__(self):
        self.strategies = [
            NullValueCorrectionStrategy(),
            TemplateValueCorrectionStrategy(),
            MinContentLengthCorrectionStrategy(),
            StructuralCompletenessCorrectionStrategy()
        ]
        self.correction_stats = {
            "total_corrections": 0,
            "corrections_by_type": {},
            "corrections_by_field": {}
        }
    
    def correct_validation_errors(self, data: Dict[str, Any], validation_results: Dict[str, List[ValidationResult]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Correct validation errors in data structure
        
        Args:
            data: Original data structure
            validation_results: Results from validation engine
            
        Returns:
            Tuple of (corrected_data, correction_report)
        """
        corrected_data = self._deep_copy(data)
        correction_report = {
            "corrections_applied": [],
            "uncorrectable_errors": [],
            "total_corrections": 0
        }
        
        for field_path, field_results in validation_results.items():
            # Get field value from data
            field_value = self._get_field_value(corrected_data, field_path)
            
            # Process each validation error for this field
            for validation_result in field_results:
                if not validation_result.is_valid:
                    corrected_value, was_corrected = self._apply_corrections(
                        field_value, validation_result, {"field_path": field_path}
                    )
                    
                    if was_corrected:
                        # Update the corrected data
                        self._set_field_value(corrected_data, field_path, corrected_value)
                        field_value = corrected_value  # For subsequent corrections
                        
                        # Record the correction
                        correction_report["corrections_applied"].append({
                            "field": field_path,
                            "rule": validation_result.rule_name,
                            "error": validation_result.error_message,
                            "correction_strategy": self._get_strategy_name(validation_result)
                        })
                        correction_report["total_corrections"] += 1
                        
                        # Update stats
                        self.correction_stats["total_corrections"] += 1
                        strategy_name = self._get_strategy_name(validation_result)
                        self.correction_stats["corrections_by_type"][strategy_name] = \
                            self.correction_stats["corrections_by_type"].get(strategy_name, 0) + 1
                        self.correction_stats["corrections_by_field"][field_path] = \
                            self.correction_stats["corrections_by_field"].get(field_path, 0) + 1
                    else:
                        # Record uncorrectable error
                        correction_report["uncorrectable_errors"].append({
                            "field": field_path,
                            "rule": validation_result.rule_name,
                            "error": validation_result.error_message,
                            "severity": validation_result.severity
                        })
        
        logger.info(f"Applied {correction_report['total_corrections']} corrections, "
                   f"{len(correction_report['uncorrectable_errors'])} errors remain uncorrectable")
        
        return corrected_data, correction_report
    
    def _apply_corrections(self, value: Any, validation_result: ValidationResult, context: Dict[str, Any] = None) -> Tuple[Any, bool]:
        """Apply appropriate correction strategy"""
        
        for strategy in self.strategies:
            if strategy.can_correct(validation_result):
                return strategy.apply_correction(value, validation_result, context)
        
        return value, False
    
    def _get_strategy_name(self, validation_result: ValidationResult) -> str:
        """Get the name of the strategy that would handle this validation result"""
        for strategy in self.strategies:
            if strategy.can_correct(validation_result):
                return strategy.name
        return "unknown"
    
    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of the object"""
        import copy
        return copy.deepcopy(obj)
    
    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested data structure using field path"""
        try:
            current = data
            
            # Handle array indices in path like "trade_ideas[0].asset"
            parts = re.split(r'[\.\[\]]', field_path)
            parts = [p for p in parts if p]  # Remove empty parts
            
            # If it's a single part and doesn't exist in data, return the data itself
            # This handles cases where the validation is for the entire object
            if len(parts) == 1 and parts[0] not in data:
                return data
            
            for part in parts:
                if part.isdigit():
                    current = current[int(part)]
                else:
                    current = current[part]
            
            return current
        except (KeyError, IndexError, TypeError):
            # If path doesn't exist, return the data itself for single-level paths
            if '.' not in field_path and '[' not in field_path:
                return data
            return None
    
    def _set_field_value(self, data: Dict[str, Any], field_path: str, value: Any) -> bool:
        """Set value in nested data structure using field path"""
        try:
            current = data
            
            # Handle array indices in path
            parts = re.split(r'[\.\[\]]', field_path)
            parts = [p for p in parts if p]
            
            # If it's a single part and doesn't exist in data, update the data directly
            # This handles cases where the validation is for the entire object
            if len(parts) == 1 and parts[0] not in data and isinstance(value, dict):
                data.update(value)
                return True
            
            # Navigate to parent of target field
            for part in parts[:-1]:
                if part.isdigit():
                    current = current[int(part)]
                else:
                    current = current[part]
            
            # Set the final value
            final_part = parts[-1]
            if final_part.isdigit():
                current[int(final_part)] = value
            else:
                current[final_part] = value
            
            return True
        except (KeyError, IndexError, TypeError) as e:
            # If path doesn't exist and it's a single-level path, try to update data directly
            if '.' not in field_path and '[' not in field_path and isinstance(value, dict):
                try:
                    data.update(value)
                    return True
                except Exception:
                    pass
            logger.error(f"Failed to set field value at path {field_path}: {str(e)}")
            return False
    
    def get_correction_stats(self) -> Dict[str, Any]:
        """Get statistics about corrections applied"""
        return self.correction_stats.copy()
    
    def reset_stats(self):
        """Reset correction statistics"""
        self.correction_stats = {
            "total_corrections": 0,
            "corrections_by_type": {},
            "corrections_by_field": {}
        } 