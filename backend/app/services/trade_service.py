"""Deprecated Trade Extraction Service

This module has been **deprecated** after the migration to the
generic, domain-agnostic `DecisionExtractionService`.

The stubs below are kept **only** to avoid import errors in legacy
code.  They intentionally return empty results so the rest of the
pipeline continues to run without any trade-specific logic.
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger("deprecated-trade-service")

__all__ = [
    "TradeExtractionService",
    "extract_trades",
]


async def extract_trades(*_args, **_kwargs) -> List[Dict[str, Any]]:  # type: ignore[name-defined]
    """Legacy coroutine that now returns an empty list."""
    logger.info("extract_trades() called – trade functionality is disabled. Returning [].")
    return []


class TradeExtractionService:  # noqa: D101 – legacy stub
    """Stub replacement for the old TradeExtractionService.

    All methods now return empty structures or do nothing. The sole
    purpose is to keep backwards compatibility for code paths that
    still import this class while the real extraction logic has been
    migrated away.
    """

    async def extract_trades(self, *_args, **_kwargs) -> List[Dict[str, Any]]:
        logger.info("TradeExtractionService.extract_trades() called – feature disabled. Returning [].")
        return []

# For backward compatibility
async def extract_trades(transcript_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Legacy function to extract trades from transcript chunks
    
    Args:
        transcript_chunks: List of transcript chunks
        
    Returns:
        List of extracted trades
    """
    # Create service and call with concatenated chunks
    service = TradeExtractionService()
    transcript_text = "\n".join([chunk.get("text", "") for chunk in transcript_chunks])
    return await service.extract_trades(transcript_text) 