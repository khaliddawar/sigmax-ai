"""Storage Services Module

This package contains modular storage services extracted from the monolithic
supabase_client.py for better maintainability and single responsibility.

Modules:
- vector_ops: Vector storage operations
- text_ops: Text storage operations  
- connection: Connection management
"""

from .vector_ops import VectorStorageOps, create_vector_ops
from .text_ops import TextStorageOps, create_text_ops

__all__ = [
    "VectorStorageOps",
    "create_vector_ops",
    "TextStorageOps", 
    "create_text_ops"
] 