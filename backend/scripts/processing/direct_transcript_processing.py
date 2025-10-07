#!/usr/bin/env python3
"""
Direct transcript processing using individual services
"""
import sys
import os
import json
import time
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

try:
    from app.services.transcript_processor import TranscriptProcessor
    from app.services.embedding_service import EmbeddingService
    from app.services.supabase_client import SupabaseService
    from app.services.trade_service import TradeExtractionService
    
    async def main():
        print("🎯 BPT Direct Transcript Processing")
        print("=" * 50)
        
        # Read the test transcript
        transcript_path = 'config/test_transcript.txt'
        if not os.path.exists(transcript_path):
            print(f"❌ Transcript file not found: {transcript_path}")
            return
            
        with open(transcript_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 Processing transcript with {len(content)} characters...")
        
        # Create unique ID
        transcript_id = f'trading_analysis_{int(time.time())}'
        
        # Initialize services
        transcript_processor = TranscriptProcessor()
        embedding_service = EmbeddingService()
        supabase_service = SupabaseService()
        trade_service = TradeExtractionService()
        
        # Prepare metadata
        metadata = {
            'title': 'Trading Market Analysis - Patrick Ceresna - May 23rd, 2025',
            'meeting_id': 'macro_outlook_may23_2025',
            'date': '2025-05-23T00:00:00Z',
            'word_count': len(content.split()),
            'duration_seconds': 600,
            'source': 'manual',
            'speakers': ['Patrick Ceresna'],
            'topics': ['S&P 500', 'Dollar Index', 'Bitcoin', 'Gold', 'Crude Oil', 'Natural Gas', 'Bonds'],
            'analysis_type': 'macro_market_outlook'
        }
        
        print(f"📊 Transcript metadata:")
        print(f"   • ID: {transcript_id}")
        print(f"   • Title: {metadata['title']}")
        print(f"   • Word count: {metadata['word_count']}")
        
        try:
            # Step 1: Process transcript into chunks
            print(f"\n🔄 Step 1: Processing transcript into chunks...")
            processed_data = transcript_processor.process_transcript(content)
            
            if not processed_data.get("success", False):
                print(f"❌ Failed to process transcript: {processed_data.get('error', 'Unknown error')}")
                return
                
            chunks = processed_data["chunks"]
            
            # Add metadata to chunks
            for i, chunk in enumerate(chunks):
                chunk.update({
                    "transcript_id": transcript_id,
                    "chunk_index": i + 1,
                    "position": i,
                    "is_first": i == 0,
                    "is_last": i == len(chunks) - 1,
                    "metadata": {}
                })
            
            print(f"✅ Created {len(chunks)} chunks")
            
            # Step 2: Generate embeddings
            print(f"\n🔄 Step 2: Generating embeddings...")
            chunk_texts = [chunk["text"] for chunk in chunks]
            embeddings = await embedding_service.get_embeddings(chunk_texts)
            
            if embeddings:
                print(f"✅ Generated {len(embeddings)} embeddings")
            else:
                print(f"⚠️  No embeddings generated")
                embeddings = []
            
            # Step 3: Store in Supabase
            print(f"\n🔄 Step 3: Storing in database...")
            
            # Create transcript record first
            store_result = await supabase_service.create_transcript_with_embeddings(
                transcript_id=transcript_id,
                metadata=metadata,
                chunks=chunks,
                embeddings=embeddings
            )
            
            if store_result.get("success"):
                print(f"✅ Stored transcript and chunks in database")
                print(f"   • Chunks stored: {store_result.get('chunks_stored', 0)}")
                print(f"   • Processing time: {store_result.get('processing_time', 0):.2f}s")
            else:
                print(f"❌ Failed to store transcript: {store_result.get('error')}")
                return
            
            # Step 4: Extract trades
            print(f"\n🔄 Step 4: Extracting trade ideas...")
            trades = await trade_service.extract_trades(content)
            
            if trades:
                print(f"✅ Extracted {len(trades)} trade ideas:")
                for i, trade in enumerate(trades[:5], 1):
                    ticker = trade.get('ticker_symbol', 'N/A')
                    direction = trade.get('direction', 'N/A') 
                    confidence = trade.get('confidence', 0)
                    rationale = trade.get('rationale', 'N/A')[:100] + "..." if len(trade.get('rationale', '')) > 100 else trade.get('rationale', 'N/A')
                    print(f"   {i}. {ticker} - {direction} (confidence: {confidence:.2f})")
                    print(f"      Rationale: {rationale}")
            else:
                print(f"⚠️  No trade ideas extracted")
            
            print(f"\n🎯 Processing Complete!")
            print(f"🌐 Test the web interface at: http://localhost:8501")
            print(f"📊 Try asking questions about:")
            print(f"   • S&P 500 market outlook")
            print(f"   • Bitcoin price targets") 
            print(f"   • Dollar index movements")
            print(f"   • Gold breakout levels")
            print(f"   • Crude oil analysis")
            
        except Exception as e:
            print(f"❌ Error processing transcript: {e}")
            import traceback
            traceback.print_exc()
    
    def run_main():
        """Run the async main function"""
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        asyncio.run(main())
            
    if __name__ == "__main__":
        run_main()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root and dependencies are installed")
    import traceback
    traceback.print_exc() 