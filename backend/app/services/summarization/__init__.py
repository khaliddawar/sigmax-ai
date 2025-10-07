"""Summarization Services Module

This package contains modular summarization services extracted from the monolithic
summary_service_v2.py for better maintainability and single responsibility.

Modules:
- generator: Summary generation logic
- validator: Summary validation and quality checks
- formatter: Output formatting and templates
"""

from .generator import SummaryGenerator, SummaryType, create_default_generator

__all__ = [
    "SummaryGenerator",
    "SummaryType", 
    "create_default_generator"
] 