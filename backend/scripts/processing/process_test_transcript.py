#!/usr/bin/env python3
"""
Process test transcript and add to vector database
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
    from app.services.ingestion_service import IngestionService
    from app.services.supabase_client import SupabaseService
    
    async def main():
        print("🎯 BPT Transcript Processing")
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
        ingestion_service = IngestionService()
        
        # Prepare transcript data
        webhook_data = {
            'transcript_id': transcript_id,
            'meeting_id': 'macro_outlook_may23_2025',
            'title': 'Trading Market Analysis - Patrick Ceresna - May 23rd, 2025',
            'date': '2025-05-23T00:00:00Z',
            'transcript_content': content,
            'word_count': len(content.split()),
            'duration_seconds': 600,  # ~10 minutes estimated
            'source': 'manual',
            'metadata': {
                'speakers': ['Patrick Ceresna'],
                'topics': ['S&P 500', 'Dollar Index', 'Bitcoin', 'Gold', 'Crude Oil', 'Natural Gas', 'Bonds'],
                'analysis_type': 'macro_market_outlook'
            }
        }
        
        print(f"📊 Transcript metadata:")
        print(f"   • ID: {transcript_id}")
        print(f"   • Title: {webhook_data['title']}")
        print(f"   • Word count: {webhook_data['word_count']}")
        
        try:
            # Process through ingestion service
            result = await ingestion_service.process_transcript(webhook_data)
            
            print(f"✅ Successfully processed transcript!")
            print(f"📊 Results:")
            print(f"   • Processing time: {result.get('processing_time', 0):.2f}s")
            print(f"   • Steps completed: {len(result.get('steps_completed', []))}")
            
            if result.get('trades'):
                print(f"   • Trade ideas: {len(result['trades'])}")
                print(f"\n💡 Generated Trade Ideas:")
                for i, trade in enumerate(result['trades'][:5], 1):
                    ticker = trade.get('ticker_symbol', 'N/A')
                    direction = trade.get('direction', 'N/A')
                    confidence = trade.get('confidence', 0)
                    print(f"   {i}. {ticker} - {direction} (confidence: {confidence:.2f})")
            
            print(f"\n🎯 Vector database now ready for queries!")
            print(f"🌐 Test the web interface at: http://localhost:8501")
            
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