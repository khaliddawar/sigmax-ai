"""Anti-hallucination validation utilities."""

import re
from typing import List, NamedTuple
import logging

logger = logging.getLogger(__name__)

class ValidationResult(NamedTuple):
    """Validation result container."""
    ok: bool
    errors: List[str]
    warnings: List[str] 
    error_count: int
    confidence_score: float

class SimpleBoundaryValidator:
    """Lightweight timestamp and content validation."""
    
    def validate(self, summary: str, max_duration_seconds: int, 
                 source_transcript: str = "") -> ValidationResult:
        """Validate summary against boundary constraints."""
        return self(summary, max_duration_seconds, source_transcript)
    
    def __call__(self, summary: str, max_duration_seconds: int, 
                 source_transcript: str = "") -> ValidationResult:
        """Validate summary against boundary constraints."""
        
        errors = []
        warnings = []
        
        # 1. CRITICAL: Timestamp boundary validation
        timestamp_pattern = r'(\d{1,2}):(\d{2})'
        for match in re.finditer(timestamp_pattern, summary):
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            total_seconds = minutes * 60 + seconds
            
            if total_seconds > max_duration_seconds:
                errors.append(
                    f"CRITICAL: Timestamp {match.group(0)} exceeds duration {max_duration_seconds}s"
                )
        
        # 2. Fabrication indicator detection  
        fabrication_indicators = [
            'according to sources', 'it is reported', 'allegedly',
            'sources suggest', 'it appears that', 'presumably'
        ]
        
        for indicator in fabrication_indicators:
            if indicator.lower() in summary.lower():
                warnings.append(f"Fabrication indicator: '{indicator}'")
        
        # 3. Quote validation against source
        if source_transcript:
            quote_errors = self._validate_quotes(summary, source_transcript)
            errors.extend(quote_errors)
        
        # 4. Confidence scoring
        error_count = len(errors)
        warning_count = len(warnings)
        confidence_score = max(0, 1.0 - (error_count * 0.4) - (warning_count * 0.1))
        
        return ValidationResult(
            ok=(error_count == 0 and confidence_score > 0.7),
            errors=errors,
            warnings=warnings,
            error_count=error_count,
            confidence_score=confidence_score
        )
    
    def _validate_quotes(self, summary: str, source: str) -> List[str]:
        """Validate substantial quotes exist in source."""
        errors = []
        quotes = re.findall(r'"([^"]*)"', summary)
        source_lower = source.lower()
        
        for quote in quotes:
            quote_words = set(quote.lower().split())

            # 💡 FIX: Add leniency for short quotes to avoid false positives
            if len(quote_words) < 8:
                continue # Treat as paraphrase, not a formal quote

            if len(quote) > 15:  # Only substantial quotes
                words_in_source = sum(1 for word in quote_words if word in source_lower)
                overlap_ratio = words_in_source / len(quote_words) if quote_words else 0
                
                if overlap_ratio < 0.6:
                    errors.append(f"Quote not in source: '{quote[:40]}...'")
        
        return errors 