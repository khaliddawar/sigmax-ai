"""
Automatic Batch Processor for SignalScope
Processes messages from Redis queues at regular intervals
"""
import asyncio
import signal
import sys
from datetime import datetime
from app.services.batch_processor import BatchProcessor
import structlog

logger = structlog.get_logger()

class AutoProcessor:
    def __init__(self):
        self.processor = BatchProcessor()
        self.running = True
        
        # Processing intervals (in seconds)
        self.realtime_interval = 300  # 5 minutes for high-priority
        self.standard_interval = 900  # 15 minutes for normal
        self.archive_interval = 3600  # 1 hour for low-priority
        
    async def process_realtime(self):
        """Process realtime queue every 5 minutes"""
        while self.running:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking realtime queue...")
                result = await self.processor.process_single_batch("realtime")
                
                # Check if there were messages
                if result.get('messages_processed', 0) > 0:
                    print(f"  ✓ Processed {result['messages_processed']} realtime messages")
                    print(f"  → Report sent to Telegram!")
                else:
                    print(f"  - No realtime messages to process")
                    
            except Exception as e:
                print(f"  ✗ Error processing realtime: {e}")
                
            await asyncio.sleep(self.realtime_interval)
    
    async def process_standard(self):
        """Process standard queue every 15 minutes"""
        while self.running:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking standard queue...")
                result = await self.processor.process_single_batch("standard")
                
                if result.get('messages_processed', 0) > 0:
                    print(f"  ✓ Processed {result['messages_processed']} standard messages")
                    print(f"  → Report sent to Telegram!")
                else:
                    print(f"  - No standard messages to process")
                    
            except Exception as e:
                print(f"  ✗ Error processing standard: {e}")
                
            await asyncio.sleep(self.standard_interval)
    
    async def process_archive(self):
        """Process archive queue every hour"""
        while self.running:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking archive queue...")
                result = await self.processor.process_single_batch("archive")
                
                if result.get('messages_processed', 0) > 0:
                    print(f"  ✓ Processed {result['messages_processed']} archive messages")
                    print(f"  → Report sent to Telegram!")
                else:
                    print(f"  - No archive messages to process")
                    
            except Exception as e:
                print(f"  ✗ Error processing archive: {e}")
                
            await asyncio.sleep(self.archive_interval)
    
    async def run(self):
        """Run all processors concurrently"""
        print("\n" + "="*60)
        print("🚀 SignalScope Auto-Processor Started")
        print("="*60)
        print("Processing intervals:")
        print(f"  • Realtime: Every {self.realtime_interval//60} minutes (importance ≥8)")
        print(f"  • Standard: Every {self.standard_interval//60} minutes (importance 5-7)")
        print(f"  • Archive: Every {self.archive_interval//60} minutes (importance <5)")
        print("\nPress Ctrl+C to stop")
        print("="*60)
        
        # Initial check on startup
        print("\nRunning initial check...")
        await self.processor.process_single_batch("realtime")
        await self.processor.process_single_batch("standard")
        
        # Start concurrent processing
        tasks = [
            asyncio.create_task(self.process_realtime()),
            asyncio.create_task(self.process_standard()),
            asyncio.create_task(self.process_archive())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("\n\nShutting down auto-processor...")
            self.running = False

def signal_handler(sig, frame):
    print("\n\nReceived interrupt signal. Shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    auto_processor = AutoProcessor()
    
    try:
        asyncio.run(auto_processor.run())
    except KeyboardInterrupt:
        print("\nAuto-processor stopped.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)