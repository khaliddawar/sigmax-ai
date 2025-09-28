import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from app.services.redis_service import RedisService
from app.services.llm_service import LLMService
from app.services.telegram_service import TelegramService
from app.services.supabase_service import SupabaseService
import structlog

load_dotenv()

logger = structlog.get_logger()

async def main():
    # Initialize services
    redis_service = RedisService()
    llm_service = LLMService()
    telegram_service = TelegramService()
    db_service = SupabaseService()
    
    await redis_service.initialize()
    
    # Get archive messages
    stream = "signalscope:messages:archive"
    batch_data = await redis_service.get_messages_batch(
        stream=stream,
        count=50
    )
    
    messages = []
    message_ids = []
    for msg_data in batch_data:
        messages.append(msg_data.get("message"))
        message_ids.append(msg_data.get("id"))
    
    if not messages:
        print("No messages in archive queue")
        return
    
    print(f"Processing {len(messages)} archive messages")
    
    # Generate report with author attribution
    report = await llm_service.generate_report(messages, report_type="hourly")
    
    # Display actionables with authors
    print("\n=== ACTIONABLES ===")
    for item in report.get("actionables", []):
        print(f"${item.get('ticker')} - {item.get('direction')} by @{item.get('author', 'Unknown')}")
        if item.get('entry'):
            print(f"  Entry: {item['entry']}")
        if item.get('stop'):
            print(f"  Stop: {item['stop']}")
        print(f"  Time: {item.get('time_local', '')}")
        print()
    
    # Send to Telegram with author info
    await telegram_service.send_hourly_report(report)
    print(f"\nReport sent to Telegram with {len(report.get('actionables', []))} actionables")
    
    # Save to database
    try:
        await db_service.save_batch({"batch_type": "hourly", "report_data": report})
        print(f"Report saved to database")
    except Exception as e:
        print(f"Could not save to database: {e}")
    
    # Acknowledge processed messages
    if message_ids:
        await redis_service.ack_messages(stream, message_ids)
    
    print(f"Acknowledged {len(messages)} messages")

if __name__ == "__main__":
    asyncio.run(main())