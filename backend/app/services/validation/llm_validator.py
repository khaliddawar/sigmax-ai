"""
LLM Validator

Main validation coordinator that validates LLM outputs using configurable rules
and applies automatic corrections. Designed to be used as a non-breaking layer
in the existing summary generation pipeline.
"""

import logging
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import time

from .validation_rules import ValidationRuleEngine, ValidationResult
from .error_corrector import ErrorCorrector

logger = logging.getLogger("bpt-llm-validator")

class ValidationConfig:
    """Configuration for LLM validation"""
    
    def __init__(self):
        # Much more lenient validation settings
        self.enable_validation = os.getenv("ENABLE_LLM_VALIDATION", "true").lower() == "true"
        self.enable_error_correction = os.getenv("ENABLE_ERROR_CORRECTION", "false").lower() == "true"  # Disabled by default
        self.min_severity_to_correct = os.getenv("MIN_CORRECTION_SEVERITY", "high")
        
        # Relaxed validation thresholds
        self.min_content_length = 3  # Very relaxed
        self.min_word_count = 1      # Very relaxed
        
        logger.info(f"Validation config: validation={self.enable_validation}, correction={self.enable_error_correction}")

class LLMValidator:
    """
    LLM Validator with enhanced validation and error correction capabilities
    """
    
    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()
        self.rule_engine = ValidationRuleEngine()
        self.error_corrector = ErrorCorrector()
        
        # Statistics tracking
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "corrections_applied": 0,
            "last_validation": None
        }
        
        logger.info("Enhanced LLM Validator initialized")
    
    def validate_summary(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main validation method with JSON serialization safety
        """
        if not self.config.enable_validation:
            logger.info("Validation disabled, returning data as-is")
            return {
                "validation_enabled": False,
                "is_valid": True,
                "original_data": data,
                "validated_data": data
            }
        
        try:
            start_time = time.time()
            
            # Perform validation
            validation_results = self.rule_engine.validate_all(data, context)
            
            # Convert ValidationResult objects to JSON-serializable format
            serializable_results = {}
            all_results = []
            
            for field_path, results in validation_results.items():
                serializable_field_results = []
                for result in results:
                    # Convert ValidationResult to dict
                    if hasattr(result, 'to_dict'):
                        serializable_field_results.append(result.to_dict())
                    else:
                        # Fallback for old ValidationResult format
                        serializable_field_results.append({
                            "is_valid": getattr(result, 'is_valid', True),
                            "field_name": getattr(result, 'field_name', field_path),
                            "rule_name": getattr(result, 'rule_name', 'unknown'),
                            "error_message": getattr(result, 'error_message', None),
                            "suggested_fix": getattr(result, 'suggested_fix', None),
                            "severity": getattr(result, 'severity', 'medium')
                        })
                
                serializable_results[field_path] = serializable_field_results
                all_results.extend(serializable_field_results)
            
            # Count validation results
            failed_results = [r for r in all_results if not r.get('is_valid', True)]
            total_checks = len(all_results)
            failed_checks = len(failed_results)
            success_rate = (total_checks - failed_checks) / total_checks if total_checks > 0 else 1.0
            
            # Be very lenient - allow up to 50% failures and still consider valid
            validation_passed = success_rate >= 0.5  # Much more lenient
            
            # Summary statistics
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            failed_fields = []
            
            for result in failed_results:
                severity = result.get('severity', 'medium')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                field_name = result.get('field_name', 'unknown')
                error_msg = result.get('error_message', 'Unknown error')
                
                existing_field = next((f for f in failed_fields if f["field"] == field_name), None)
                if existing_field:
                    existing_field["failures"] += 1
                    existing_field["errors"].append(error_msg)
                else:
                    failed_fields.append({
                        "field": field_name,
                        "failures": 1,
                        "errors": [error_msg]
                    })
            
            # Log results
            if validation_passed:
                logger.info("Summary passed validation")
            else:
                logger.info(f"Validation failed - Field: {failed_fields[0]['field'] if failed_fields else 'unknown'}, Success rate: {success_rate:.1%}")
            
            # Apply corrections if enabled
            corrected_data = data
            correction_report = {"corrections_applied": [], "uncorrectable_errors": [], "total_corrections": 0}
            
            if not validation_passed and self.config.enable_error_correction:
                logger.info("Applying automatic corrections to validation errors")
                corrected_data, correction_report = self.error_corrector.correct_validation_errors(
                    data, {"validation_summary": {"failed_fields": failed_fields}}
                )
            
            validation_time = (time.time() - start_time) * 1000
            
            # Update stats
            self.validation_stats["total_validations"] += 1
            if validation_passed:
                self.validation_stats["successful_validations"] += 1
            else:
                self.validation_stats["failed_validations"] += 1
            self.validation_stats["corrections_applied"] += correction_report.get("total_corrections", 0)
            self.validation_stats["last_validation"] = datetime.now().isoformat()
            
            return {
                "validation_enabled": True,
                "original_data": data,
                "validated_data": corrected_data,
                "is_valid": validation_passed,
                "validation_summary": {
                    "total_checks": total_checks,
                    "failed_checks": failed_checks,
                    "success_rate": success_rate,
                    "severity_counts": severity_counts,
                    "failed_fields": failed_fields,
                    "is_valid": validation_passed
                },
                "correction_report": correction_report,
                "validation_time_ms": validation_time,
                "validation_results": serializable_results  # Now properly serializable
            }
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {
                "validation_enabled": True,
                "is_valid": False,
                "error": str(e),
                "original_data": data,
                "validated_data": data
            }

    def validate_summary_output(self, summary_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhanced summary validation with comprehensive checks
        """
        return self.validate_summary(summary_data, context)

    def validate_trade_idea(self, trade_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate individual trade ideas for completeness and quality
        """
        validation_results = []
        
        # Check for required fields (very minimal requirements)
        required_fields = ["idea"]  # Only require the basic idea field
        for field in required_fields:
            if field not in trade_data or not trade_data[field]:
                validation_results.append({
                    "is_valid": False,
                    "field_name": field,
                    "rule_name": "required_field",
                    "error_message": f"Missing required field: {field}",
                    "severity": "medium"
                })
            else:
                validation_results.append({
                    "is_valid": True,
                    "field_name": field,
                    "rule_name": "required_field",
                    "severity": "low"
                })
        
        failed_validations = [r for r in validation_results if not r["is_valid"]]
        is_valid = len(failed_validations) == 0
        
        return {
            "is_valid": is_valid,
            "validation_results": validation_results,
            "failed_count": len(failed_validations),
            "total_count": len(validation_results)
        }

    def validate_qa_content(self, qa_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate Q&A content for completeness
        """
        validation_results = []
        
        # Check for required fields (minimal requirements)
        required_fields = ["question"]  # Only require question
        for field in required_fields:
            if field not in qa_data or not qa_data[field]:
                validation_results.append({
                    "is_valid": False,
                    "field_name": field,
                    "rule_name": "required_field",
                    "error_message": f"Missing required field: {field}",
                    "severity": "medium"
                })
            else:
                validation_results.append({
                    "is_valid": True,
                    "field_name": field,
                    "rule_name": "required_field",
                    "severity": "low"
                })
        
        failed_validations = [r for r in validation_results if not r["is_valid"]]
        is_valid = len(failed_validations) == 0
        
        return {
            "is_valid": is_valid,
            "validation_results": validation_results,
            "failed_count": len(failed_validations),
            "total_count": len(validation_results)
        }

    def _log_validation_details(self, validation_results: Dict[str, List[ValidationResult]], context: Dict[str, Any] = None):
        """Log detailed validation results for debugging"""
        total_checks = sum(len(results) for results in validation_results.values())
        failed_checks = sum(1 for results in validation_results.values() for result in results if not result.is_valid)
        
        logger.info(f"Validation completed: {total_checks} checks, {failed_checks} failures")
        
        if failed_checks > 0:
            for field_path, results in validation_results.items():
                failed_results = [r for r in results if not r.is_valid]
                if failed_results:
                    for result in failed_results:
                        logger.info(
                            f"Validation failed - Field: {field_path}, "
                            f"Rule: {result.rule_name}, "
                            f"Error: {result.error_message}, "
                            f"Suggested fix: {result.suggested_fix}"
                        )

    def _save_validation_report(self, validation_result: Dict[str, Any], context: Dict[str, Any] = None):
        """Save validation report for analysis"""
        try:
            # Create reports directory if it doesn't exist
            os.makedirs("reports", exist_ok=True)
            
            # Create report filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"reports/validation_report_{timestamp}.json"
            
            # Prepare report data
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "context": context or {},
                "validation_result": validation_result,
                "stats": self.validation_stats
            }
            
            # Save report
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.debug(f"Validation report saved to {report_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save validation report: {e}")

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            **self.validation_stats,
            "success_rate": (
                self.validation_stats["successful_validations"] / 
                max(self.validation_stats["total_validations"], 1)
            ),
            "config": {
                "validation_enabled": self.config.enable_validation,
                "error_correction_enabled": self.config.enable_error_correction
            }
        }

    def reset_stats(self):
        """Reset validation statistics"""
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "corrections_applied": 0,
            "last_validation": None
        }
        logger.info("Validation statistics reset")

# Convenience function for backward compatibility
def validate_summary(summary_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Standalone function for summary validation
    """
    validator = LLMValidator()
    return validator.validate_summary(summary_data, context) 