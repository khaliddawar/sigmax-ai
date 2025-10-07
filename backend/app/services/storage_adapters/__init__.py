"""Storage Adapters Package

This package contains implementations of the storage interfaces for
different backends (Supabase, Pinecone, local files, etc.).
"""

# Import adapters to register them with the factory
from . import supabase_adapter

__all__ = ["supabase_adapter"] 