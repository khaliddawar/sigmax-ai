"""
Field Validator Utility

This module provides utilities to validate and safely access fields in API responses
and data structures, helping prevent field name mismatches like the recent issue
where 'transcript_text' was used instead of 'text' in transcript handler responses.

This utility is designed to be used alongside existing code without breaking changes.
It provides logging and validation helpers that can be gradually adopted.
"""

import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger("field-validator")


class FieldAccessError(Exception):
    """Custom exception for field access errors"""
    pass


class FieldValidator:
    """
    Utility class for validating and safely accessing fields in data structures.
    
    This class helps prevent field name mismatches and provides clear error messages
    when expected fields are missing or have unexpected values.
    """
    
    @staticmethod
    def safe_get(data: Dict[str, Any], field_name: str, 
                 expected_type: type = None, 
                 default: Any = None,
                 required: bool = False,
                 context: str = "") -> Any:
        """
        Safely get a field from a dictionary with validation and logging.
        
        Args:
            data: Dictionary to access
            field_name: Name of field to retrieve
            expected_type: Expected type of the field value
            default: Default value if field missing
            required: Whether field is required (raises exception if missing)
            context: Context string for better error messages
            
        Returns:
            Field value or default
            
        Raises:
            FieldAccessError: If required field is missing or has wrong type
        """
        context_msg = f" in {context}" if context else ""
        
        if not isinstance(data, dict):
            error_msg = f"Expected dictionary but got {type(data)}{context_msg}"
            logger.error(error_msg)
            if required:
                raise FieldAccessError(error_msg)
            return default
        
        # Check if field exists
        if field_name not in data:
            error_msg = f"Required field '{field_name}' missing{context_msg}"
            if required:
                logger.error(error_msg)
                raise FieldAccessError(error_msg)
            else:
                logger.debug(f"Optional field '{field_name}' missing{context_msg}, using default: {default}")
                return default
        
        value = data[field_name]
        
        # Type validation if specified
        if expected_type is not None and value is not None:
            if not isinstance(value, expected_type):
                error_msg = f"Field '{field_name}' expected {expected_type.__name__} but got {type(value).__name__}{context_msg}"
                logger.warning(error_msg)
                if required:
                    raise FieldAccessError(error_msg)
        
        logger.debug(f"Successfully accessed field '{field_name}'{context_msg}: {type(value).__name__}")
        return value
    
    @staticmethod
    def validate_supabase_response(response: Dict[str, Any], 
                                 expected_fields: List[str] = None,
                                 context: str = "supabase response") -> bool:
        """
        Validate a typical Supabase service response structure.
        
        Args:
            response: Response dictionary from Supabase service
            expected_fields: List of field names that should be present
            context: Context for error messages
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(response, dict):
            logger.error(f"Invalid {context}: expected dict, got {type(response)}")
            return False
        
        # Check for success field
        success = FieldValidator.safe_get(response, "success", bool, False, False, context)
        if not success:
            error = FieldValidator.safe_get(response, "error", str, "Unknown error", False, context)
            logger.error(f"Service response indicates failure in {context}: {error}")
            return False
        
        # Check expected fields if provided
        if expected_fields:
            missing_fields = []
            for field in expected_fields:
                if field not in response:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"Missing expected fields in {context}: {missing_fields}")
                return False
        
        logger.debug(f"Valid {context} with fields: {list(response.keys())}")
        return True
    
    @staticmethod
    def validate_transcript_text_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Specifically validate a transcript text response from SupabaseService.get_transcript_text()
        
        This method knows the exact expected structure and provides helpful error messages
        for the specific field name issues we've encountered.
        
        Args:
            response: Response from get_transcript_text()
            
        Returns:
            Validated response with additional metadata
        """
        context = "transcript text response"
        
        # Validate basic structure
        if not FieldValidator.validate_supabase_response(response, context=context):
            return {
                "valid": False,
                "error": "Invalid response structure",
                "original_response": response
            }
        
        # Check for required fields in successful response
        required_fields = ["text", "transcript_id", "chunk_count"]
        validation_result = {
            "valid": True,
            "field_checks": {},
            "warnings": [],
            "original_response": response
        }
        
        for field in required_fields:
            if field in response:
                validation_result["field_checks"][field] = "present"
                
                # Specific validation for text field
                if field == "text":
                    text_value = response[field]
                    if isinstance(text_value, str):
                        validation_result["field_checks"]["text_length"] = len(text_value)
                        if len(text_value) == 0:
                            validation_result["warnings"].append("Text field is empty - this may indicate a processing issue")
                    else:
                        validation_result["warnings"].append(f"Text field should be string, got {type(text_value)}")
                        
            else:
                validation_result["field_checks"][field] = "missing"
                validation_result["warnings"].append(f"Missing required field: {field}")
        
        # Check for deprecated field names that might cause confusion
        deprecated_fields = ["transcript_text", "character_count"]
        for field in deprecated_fields:
            if field in response:
                validation_result["warnings"].append(
                    f"Deprecated field '{field}' found - this may indicate an outdated API response"
                )
        
        if validation_result["warnings"]:
            validation_result["valid"] = False
            logger.warning(f"Transcript text response validation warnings: {validation_result['warnings']}")
        
        return validation_result


class TranscriptFieldHelper:
    """
    Helper class specifically for transcript-related field access patterns.
    
    This provides safe accessors for the common patterns we use in transcript processing.
    """
    
    @staticmethod
    def get_transcript_text(response: Dict[str, Any]) -> str:
        """
        Safely extract transcript text from a service response.
        
        Args:
            response: Response from SupabaseService.get_transcript_text()
            
        Returns:
            Transcript text string (empty string if not found)
        """
        validation = FieldValidator.validate_transcript_text_response(response)
        
        if not validation["valid"]:
            logger.error(f"Invalid transcript text response: {validation.get('error', 'Unknown error')}")
            return ""
        
        text = FieldValidator.safe_get(
            response, 
            "text", 
            str, 
            "", 
            required=False, 
            context="transcript text response"
        )
        
        return text if text is not None else ""
    
    @staticmethod
    def get_transcript_length(response: Dict[str, Any]) -> int:
        """
        Calculate transcript character count from response.
        
        Args:
            response: Response from SupabaseService.get_transcript_text()
            
        Returns:
            Character count (0 if no text)
        """
        text = TranscriptFieldHelper.get_transcript_text(response)
        return len(text)
    
    @staticmethod
    def log_transcript_retrieval(transcript_id: str, response: Dict[str, Any]) -> None:
        """
        Log transcript retrieval with proper field validation.
        
        Args:
            transcript_id: ID of transcript being retrieved
            response: Response from SupabaseService.get_transcript_text()
        """
        if response.get("success"):
            char_count = TranscriptFieldHelper.get_transcript_length(response)
            chunk_count = FieldValidator.safe_get(response, "chunk_count", int, 0, False, "transcript response")
            
            logger.info(f"Retrieved transcript text for {transcript_id}: {char_count} characters from {chunk_count} chunks")
            
            if char_count == 0 and chunk_count > 0:
                logger.warning(f"Transcript {transcript_id} has {chunk_count} chunks but 0 characters - possible data issue")
        else:
            error = FieldValidator.safe_get(response, "error", str, "Unknown error", False, "transcript response")
            logger.error(f"Failed to retrieve transcript text for {transcript_id}: {error}")


# Example usage patterns that can be adopted gradually:
"""
# Old pattern (prone to field name errors):
text_result = await supabase.get_transcript_text(transcript_id)
transcript_text = text_result.get("text")  # CORRECT FIELD NAME
character_count = len(text_result.get("text", ""))  # CORRECT CALCULATION

# New pattern (with validation):
text_result = await supabase.get_transcript_text(transcript_id)
transcript_text = TranscriptFieldHelper.get_transcript_text(text_result)  # SAFE
character_count = TranscriptFieldHelper.get_transcript_length(text_result)  # SAFE
TranscriptFieldHelper.log_transcript_retrieval(transcript_id, text_result)  # SAFE LOGGING
"""

def example_correct_usage():
    \"\"\"Example of correct field access patterns\"\"\"
    # ✅ CORRECT: Access supabase service response
    text_result = await supabase_service.get_transcript_text(transcript_id)
    transcript_text = text_result.get("text")  # CORRECT FIELD NAME
    character_count = len(transcript_text) if transcript_text else 0  # CORRECT CALCULATION
    
    # ✅ CORRECT: Access fireflies API response  
    fireflies_result = await fireflies_client.get_transcript_by_meeting_id(meeting_id)
    fireflies_text = fireflies_result.get("transcript_text")  # CORRECT for Fireflies API
    
    return {
        "transcript_text": transcript_text,  # Using descriptive name
        "character_count": character_count,
        "success": True
    } 