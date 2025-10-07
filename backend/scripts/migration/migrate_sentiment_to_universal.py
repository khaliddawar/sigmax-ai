#!/usr/bin/env python3
"""
Migrate Sentiment Values to Universal Categories

This script converts financial-specific sentiment values (bullish/bearish) 
to universal sentiment categories (positive/negative/neutral) for true 
domain-agnostic RAG system.
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

async def migrate_sentiment_values():
    """Migrate sentiment values from financial-specific to universal categories"""
    print("🔄 Migrating Sentiment Values to Universal Categories")
    print("=" * 60)
    
    # Initialize service
    service = SemanticChunksService()
    
    if not service.is_initialized():
        print("❌ SemanticChunksService not initialized")
        return False
    
    try:
        # Get current sentiment distribution
        print("\n📊 Current Sentiment Distribution:")
        result = service.client.table("semantic_chunks").select("sentiment").execute()
        
        if result.data:
            sentiment_counts = {}
            for row in result.data:
                sentiment = row.get('sentiment', 'unknown')
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            for sentiment, count in sentiment_counts.items():
                print(f"   {sentiment}: {count} chunks")
        
        # Perform migration
        print("\n🔄 Converting sentiment values...")
        
        # Update bullish -> positive
        bullish_result = service.client.table("semantic_chunks").update({
            "sentiment": "positive"
        }).eq("sentiment", "bullish").execute()
        
        bullish_count = len(bullish_result.data) if bullish_result.data else 0
        print(f"   ✅ Converted {bullish_count} 'bullish' chunks to 'positive'")
        
        # Update bearish -> negative  
        bearish_result = service.client.table("semantic_chunks").update({
            "sentiment": "negative"
        }).eq("sentiment", "bearish").execute()
        
        bearish_count = len(bearish_result.data) if bearish_result.data else 0
        print(f"   ✅ Converted {bearish_count} 'bearish' chunks to 'negative'")
        
        # Verify migration
        print("\n📊 Updated Sentiment Distribution:")
        result = service.client.table("semantic_chunks").select("sentiment").execute()
        
        if result.data:
            sentiment_counts = {}
            for row in result.data:
                sentiment = row.get('sentiment', 'unknown')
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            for sentiment, count in sentiment_counts.items():
                print(f"   {sentiment}: {count} chunks")
        
        print(f"\n🎉 Migration Complete!")
        print(f"   Total conversions: {bullish_count + bearish_count}")
        print(f"   System is now using universal sentiment categories")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(migrate_sentiment_values())
    print(f"\nMigration result: {'SUCCESS' if success else 'FAILED'}")
    
    if success:
        print("\n✨ The RAG system now uses universal sentiment categories!")
        print("   • positive (instead of bullish)")
        print("   • negative (instead of bearish)")  
        print("   • neutral (unchanged)")
        print("\nThis makes the system truly domain-agnostic and suitable for:")
        print("   • Medical documents (positive/negative outcomes)")
        print("   • Legal documents (favorable/unfavorable rulings)")
        print("   • Technical documents (working/broken systems)")
        print("   • Any domain without financial assumptions!") 