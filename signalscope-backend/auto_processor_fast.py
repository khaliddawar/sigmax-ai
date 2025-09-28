"""
Fast Auto-Processor for Testing
Processes messages every 30 seconds for testing
"""
import asyncio
from datetime import datetime
from app.services.batch_processor import BatchProcessor
import redis

async def run_fast_processor():
    processor = BatchProcessor()
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print("\n" + "="*60)
    print("SignalScope Fast Auto-Processor (Testing Mode)")
    print("="*60)
    print("Processing every 30 seconds for all queues")
    print("Press Ctrl+C to stop")
    print("="*60)
    
    while True:
        try:
            # Check queue sizes
            realtime_count = r.xlen("signalscope:messages:realtime")
            standard_count = r.xlen("signalscope:messages:standard")
            archive_count = r.xlen("signalscope:messages:archive")
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{timestamp}] Queue Status:")
            print(f"  Realtime: {realtime_count} | Standard: {standard_count} | Archive: {archive_count}")
            
            # Process if there are messages
            if realtime_count > 0:
                print(f"  -> Processing {realtime_count} realtime messages...")
                await processor.process_single_batch("realtime")
                print(f"  [OK] Alert sent to Telegram!")
                
            if standard_count > 0:
                print(f"  -> Processing {standard_count} standard messages...")
                await processor.process_single_batch("standard")
                print(f"  [OK] Hourly report sent to Telegram!")
                
            if archive_count > 0:
                print(f"  -> Processing {archive_count} archive messages...")
                await processor.process_single_batch("archive")
                print(f"  [OK] Daily report sent to Telegram!")
            
            if realtime_count == 0 and standard_count == 0 and archive_count == 0:
                print(f"  - All queues empty, waiting...")
                
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        # Wait 30 seconds before next check
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(run_fast_processor())
    except KeyboardInterrupt:
        print("\n\nFast processor stopped.")