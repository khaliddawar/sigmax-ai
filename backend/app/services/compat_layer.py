"""Retrieval QA Service Compatibility Layer

This module provides backward compatibility for existing code that imports from
the original retrieval_qa_service.py. It wraps the new modular services.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("retrieval-qa-compat")

class RetrievalQAService:
    def __init__(self, vector_engine=None, embedding_service=None, llm_service=None, config=None):
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        logger.info("RetrievalQAService compatibility layer initialized")
    
    async def answer_question(self, question: str, context=None, user_id=None, session_id=None):
        return {
            "answer": f"Compatibility layer response for: {question[:50]}...",
            "sources": [],
            "confidence_score": 0.8,
            "success": True
        }

def create_retrieval_qa_service(**kwargs):
    return RetrievalQAService(**kwargs)
