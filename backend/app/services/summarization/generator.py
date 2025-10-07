"""Summary Generator Module

Handles summary generation logic extracted from the monolithic summary_service_v2.py
for better maintainability and single responsibility.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("summary-generator")

class SummaryType(Enum):
    EXECUTIVE = "executive"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"

class SummaryGenerator:
    def __init__(self):
        pass
    
    async def generate_summary(self, content: str) -> str:
        return f"Summary: {content[:200]}..."

def create_default_generator() -> SummaryGenerator:
    return SummaryGenerator()
