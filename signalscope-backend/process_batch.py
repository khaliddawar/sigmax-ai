"""
Manually process a batch of messages
"""
import asyncio
from app.services.batch_processor import BatchProcessor

async def process_batch():
    """Process messages from Redis queue and generate report"""
    
    print("\n" + "="*60)
    print("Processing Message Batch")
    print("="*60)
    
    processor = BatchProcessor()
    
    # Check all queues
    print("\nChecking queues...")
    
    # Process realtime queue first
    print("Processing realtime queue...")
    result = await processor.process_single_batch("realtime")
    print(f"Realtime result: {result}")
    
    # Process standard queue
    print("\nProcessing standard queue...")
    result = await processor.process_single_batch("standard")
    print(f"Standard result: {result}")
    
    print("\nBatch processing complete!")
    print("Check your Telegram for the trading report!")

if __name__ == "__main__":
    asyncio.run(process_batch())