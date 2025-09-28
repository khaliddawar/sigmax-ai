#!/usr/bin/env python3
"""
Circle.so to Telegram Bridge Server
Routes Circle.so messages from SignalScope extension directly to Telegram
"""

import sys
import os
from pathlib import Path

# Add signalscope-backend to Python path
signalscope_backend_path = Path(__file__).parent / "signalscope-backend"
sys.path.insert(0, str(signalscope_backend_path))

# Load environment variables from signalscope-backend directory
from dotenv import load_dotenv
load_dotenv(signalscope_backend_path / ".env")

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from datetime import datetime
import logging
import asyncio

# Import your existing TelegramService
from app.services.telegram_service import TelegramService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Circle-to-Telegram")

app = FastAPI(title="Circle.so to Telegram Bridge", version="1.0.0")

# Add CORS middleware to allow Chrome extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Telegram service
telegram_service = TelegramService()

# Store recent messages for debugging
recent_messages = []

def is_timestamp_author(author):
    """Check if author looks like a timestamp (e.g., '11:23 PM', '08:45 AM')"""
    if not author or len(author) < 4:
        return False
    
    import re
    # Match patterns like "11:23 PM", "8:45 AM", "14:30", etc.
    timestamp_patterns = [
        r'^\d{1,2}:\d{2}\s*(AM|PM)$',  # 12-hour format with AM/PM
        r'^\d{1,2}:\d{2}$',            # 24-hour format
        r'^\d{1,2}:\d{2}:\d{2}$'       # With seconds
    ]
    
    for pattern in timestamp_patterns:
        if re.match(pattern, author.strip(), re.IGNORECASE):
            return True
    
    return False

@app.get("/")
async def root():
    return {
        "message": "Circle.so to Telegram Bridge is running!",
        "status": "active",
        "telegram_enabled": telegram_service.enabled,
        "telegram_chat_id": telegram_service.chat_id if telegram_service.enabled else None,
        "messages_processed": len(recent_messages),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook")
async def webhook_endpoint(request: Request):
    """
    Main webhook endpoint that receives messages from SignalScope extension
    and forwards them to Telegram
    """
    try:
        # Get the raw body
        body = await request.body()

        # Parse JSON
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Add timestamp
        timestamp = datetime.now().isoformat()

        # Handle both single messages and batches
        if isinstance(data, list):
            # Batch of messages
            logger.info(f"📦 Received batch of {len(data)} messages from Circle.so")

            # Filter out messages with "Unknown" authors or empty content
            good_messages = []
            for message in data:
                author = message.get('author', 'Unknown')
                content = message.get('content', '').strip()

                # Filter timestamp authors and system messages
                should_skip = (
                    (author == 'Unknown' and 'in #general' in content) or  # System messages
                    (content.strip().startswith('💭 Unknown in #')) or      # Emoji system messages  
                    is_timestamp_author(author)                            # Timestamp authors like "11:23 PM"
                )

                if not should_skip:
                    good_messages.append(message)
                    logger.info(f"✅ Good message: {author} - {content[:50]}...")
                else:
                    logger.info(f"⏭️ FILTERED OUT: {author} - {content[:50]}...")

            for i, message in enumerate(good_messages):
                message['received_at'] = timestamp
                message['batch_index'] = i
                recent_messages.append(message)

                # Send each good message to Telegram
                if telegram_service.enabled:
                    try:
                        success = await telegram_service.send_raw_message(message)
                        if success:
                            logger.info(f"📱 Sent to Telegram: {message.get('author', 'Unknown')} - {message.get('content', '')[:50]}...")
                        else:
                            logger.warning(f"❌ Failed to send message {i+1} to Telegram")
                    except Exception as e:
                        logger.error(f"Error sending message {i+1} to Telegram: {e}")
                else:
                    logger.warning("⚠️ Telegram is not enabled - message not sent")

                # Small delay between messages to avoid rate limits
                if i < len(good_messages) - 1:  # Don't delay after the last message
                    await asyncio.sleep(0.2)

        else:
            # Single message - apply same filtering
            author = data.get('author', 'Unknown')
            content = data.get('content', '').strip()
            
            should_skip = (
                (author == 'Unknown' and 'in #general' in content) or  # System messages
                (content.strip().startswith('💭 Unknown in #')) or      # Emoji system messages  
                is_timestamp_author(author)                            # Timestamp authors like "11:23 PM"
            )
            
            if should_skip:
                logger.info(f"⏭️ FILTERED SINGLE: {author} - {content[:50]}...")
                return {"status": "skipped", "reason": "filtered_message"}
            
            data['received_at'] = timestamp
            recent_messages.append(data)

            logger.info(f"📝 Message from {author}: {content[:100]}...")

            # Send to Telegram
            if telegram_service.enabled:
                try:
                    logger.info(f"🔄 Attempting to send to Telegram: {author} - {content[:50]}...")
                    success = await telegram_service.send_raw_message(data)
                    if success:
                        logger.info(f"✅ Message sent to Telegram successfully")
                    else:
                        logger.warning(f"❌ Failed to send message to Telegram")
                except Exception as e:
                    logger.error(f"💥 Error sending message to Telegram: {e}")
            else:
                logger.warning("⚠️ Telegram is not enabled - message not sent")

        # Keep only last 100 messages to prevent memory issues
        if len(recent_messages) > 100:
            recent_messages[:] = recent_messages[-100:]

        return {
            "status": "success",
            "message": "Webhook received and processed",
            "messages_count": len(data) if isinstance(data, list) else 1,
            "telegram_sent": telegram_service.enabled,
            "total_messages": len(recent_messages),
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/messages")
async def get_messages(limit: int = 50):
    """
    Get recent messages received from Circle.so
    """
    recent = recent_messages[-limit:] if recent_messages else []
    return {
        "messages": recent,
        "total_count": len(recent_messages),
        "showing": len(recent),
        "telegram_enabled": telegram_service.enabled
    }

@app.get("/telegram/status")
async def telegram_status():
    """
    Get Telegram service status
    """
    return {
        "enabled": telegram_service.enabled,
        "chat_id": telegram_service.chat_id if telegram_service.enabled else None,
        "bot_configured": bool(telegram_service.bot_token),
        "status": "active" if telegram_service.enabled else "disabled"
    }

@app.post("/telegram/test")
async def test_telegram():
    """
    Test Telegram connection
    """
    if not telegram_service.enabled:
        return {
            "success": False,
            "message": "Telegram service is not enabled",
            "error": "Check TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID in .env file"
        }

    try:
        success = await telegram_service.test_connection()
        return {
            "success": success,
            "message": "Test message sent to Telegram" if success else "Failed to send test message",
            "chat_id": telegram_service.chat_id
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing Telegram: {str(e)}"
        }

@app.delete("/messages")
async def clear_messages():
    """
    Clear all stored messages
    """
    global recent_messages
    count = len(recent_messages)
    recent_messages.clear()
    logger.info(f"🗑️ Cleared {count} messages")
    return {"status": "success", "cleared_count": count}

if __name__ == "__main__":
    logger.info("🚀 Starting Circle.so to Telegram Bridge Server...")
    logger.info("📡 Extension webhook URL: http://localhost:8000/webhook")
    logger.info("🌐 API docs available at: http://localhost:8000/docs")

    if telegram_service.enabled:
        logger.info(f"✅ Telegram forwarding: ENABLED")
        logger.info(f"📱 Telegram Chat ID: {telegram_service.chat_id}")
    else:
        logger.warning("❌ Telegram forwarding: DISABLED")
        logger.warning("   Check TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and TELEGRAM_ENABLED in signalscope-backend/.env")

    logger.info("="*60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )