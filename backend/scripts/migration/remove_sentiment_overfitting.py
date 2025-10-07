#!/usr/bin/env python3
"""
Remove Sentiment Column to Prevent LLM Overfitting

This script removes the sentiment column from the database because:
1. Pre-computed sentiment can bias LLM responses
2. Sentiment is context-dependent and should be analyzed in real-time
3. The LLM should reason about sentiment based on the specific query
4. Removes potential domain overfitting from sentiment analysis

The LLM will now analyze sentiment dynamically based on:
- The specific question being asked
- The context of the retrieved chunks
- The user's intent and perspective
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))

from app.services.semantic_chunks_service import SemanticChunksService

async def remove_sentiment_column():
    """Remove sentiment column to prevent LLM overfitting"""
    print("🧹 Removing Sentiment Column to Prevent LLM Overfitting")
    print("=" * 70)
    
    print("📋 Rationale for Removal:")
    print("   • Pre-computed sentiment can bias LLM responses")
    print("   • Sentiment is context-dependent (positive for one query, negative for another)")
    print("   • LLM should analyze sentiment based on specific question context")
    print("   • Removes potential domain overfitting from sentiment analysis")
    print("   • Enables more nuanced, query-specific sentiment analysis")
    
    # Initialize service
    service = SemanticChunksService()
    
    if not service.is_initialized():
        print("❌ SemanticChunksService not initialized")
        return False
    
    try:
        print("\n🔄 Executing Database Migration...")
        
        # Step 1: Drop sentiment-related indexes
        print("   1. Dropping sentiment indexes...")
        try:
            service.client.rpc('exec_sql', {
                'sql': 'DROP INDEX IF EXISTS idx_semantic_chunks_sentiment;'
            }).execute()
            print("      ✅ Dropped sentiment index")
        except Exception as e:
            print(f"      ⚠️ Index drop warning: {e}")
        
        # Step 2: Drop sentiment-based search functions
        print("   2. Dropping sentiment-based search functions...")
        try:
            service.client.rpc('exec_sql', {
                'sql': 'DROP FUNCTION IF EXISTS match_chunks_by_sentiment(vector, varchar, float, int);'
            }).execute()
            print("      ✅ Dropped sentiment search function")
        except Exception as e:
            print(f"      ⚠️ Function drop warning: {e}")
        
        # Step 3: Remove sentiment column
        print("   3. Removing sentiment column...")
        try:
            service.client.rpc('exec_sql', {
                'sql': 'ALTER TABLE semantic_chunks DROP COLUMN IF EXISTS sentiment;'
            }).execute()
            print("      ✅ Removed sentiment column")
        except Exception as e:
            print(f"      ❌ Column removal failed: {e}")
            return False
        
        # Step 4: Add documentation comment
        print("   4. Adding documentation...")
        try:
            service.client.rpc('exec_sql', {
                'sql': """COMMENT ON TABLE semantic_chunks IS 
                'Domain-agnostic semantic chunks without pre-computed sentiment to prevent LLM overfitting. 
                Sentiment analysis should be performed by LLM in real-time based on query context.';"""
            }).execute()
            print("      ✅ Added documentation comment")
        except Exception as e:
            print(f"      ⚠️ Comment warning: {e}")
        
        print("\n✅ Database Migration Completed Successfully!")
        print("\n📊 Benefits of Sentiment Removal:")
        print("   • LLM will analyze sentiment dynamically based on query context")
        print("   • Eliminates pre-computed bias in sentiment analysis")
        print("   • Enables context-aware sentiment interpretation")
        print("   • Reduces risk of domain overfitting")
        print("   • Allows for more nuanced sentiment analysis")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

async def verify_removal():
    """Verify that sentiment column has been removed"""
    print("\n🔍 Verifying Sentiment Column Removal...")
    
    service = SemanticChunksService()
    
    try:
        # Try to query sentiment column - should fail
        result = service.client.table("semantic_chunks").select("sentiment").limit(1).execute()
        
        if hasattr(result, 'error') and result.error:
            print("✅ Sentiment column successfully removed (query failed as expected)")
            return True
        else:
            print("❌ Sentiment column still exists")
            return False
            
    except Exception as e:
        if "column" in str(e).lower() and "sentiment" in str(e).lower():
            print("✅ Sentiment column successfully removed (column not found)")
            return True
        else:
            print(f"❌ Verification failed: {e}")
            return False

if __name__ == "__main__":
    try:
        success = asyncio.run(remove_sentiment_column())
        if success:
            asyncio.run(verify_removal())
        else:
            print("\n❌ Migration failed - please check database permissions")
    except Exception as e:
        print(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc() 