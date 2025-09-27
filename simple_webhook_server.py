#!/usr/bin/env python3
"""
Simple webhook server for SignalScope extension
Receives and logs messages from the Chrome extension
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SignalScope-Webhook")

app = FastAPI(title="SignalScope Webhook Server", version="1.0.0")

# Add CORS middleware to allow Chrome extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store received messages (in memory for this simple server)
messages_store = []

@app.get("/")
async def root():
    return {
        "message": "SignalScope Webhook Server is running!",
        "status": "active",
        "messages_received": len(messages_store),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook")
async def webhook_endpoint(request: Request):
    """
    Main webhook endpoint that receives messages from SignalScope extension
    """
    global messages_store

    try:
        # Get the raw body
        body = await request.body()

        # Parse JSON
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # Log the received message
        timestamp = datetime.now().isoformat()

        # Check if it's a single message or batch
        if isinstance(data, list):
            # Batch of messages
            logger.info(f"📦 Received batch of {len(data)} messages")
            for i, message in enumerate(data):
                message['received_at'] = timestamp
                message['batch_index'] = i
                messages_store.append(message)
                logger.info(f"  📝 Message {i+1}: {message.get('author', 'Unknown')} - {message.get('content', '')[:50]}...")
        else:
            # Single message
            data['received_at'] = timestamp
            messages_store.append(data)
            logger.info(f"📝 Message from {data.get('author', 'Unknown')}: {data.get('content', '')[:100]}...")

        # Keep only last 1000 messages to prevent memory issues
        if len(messages_store) > 1000:
            messages_store = messages_store[-1000:]

        return {
            "status": "success",
            "message": "Webhook received successfully",
            "messages_count": len(data) if isinstance(data, list) else 1,
            "total_messages": len(messages_store),
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/messages")
async def get_messages(limit: int = 50):
    """
    Get recent messages received by the webhook
    """
    recent_messages = messages_store[-limit:] if messages_store else []
    return {
        "messages": recent_messages,
        "total_count": len(messages_store),
        "showing": len(recent_messages)
    }

@app.get("/stats")
async def get_stats():
    """
    Get webhook statistics
    """
    platforms = {}
    authors = {}

    for msg in messages_store:
        platform = msg.get('platform', 'unknown')
        author = msg.get('author', 'unknown')

        platforms[platform] = platforms.get(platform, 0) + 1
        authors[author] = authors.get(author, 0) + 1

    return {
        "total_messages": len(messages_store),
        "platforms": platforms,
        "top_authors": dict(sorted(authors.items(), key=lambda x: x[1], reverse=True)[:10]),
        "first_message": messages_store[0]['received_at'] if messages_store else None,
        "last_message": messages_store[-1]['received_at'] if messages_store else None
    }

@app.delete("/messages")
async def clear_messages():
    """
    Clear all stored messages
    """
    global messages_store
    count = len(messages_store)
    messages_store.clear()
    logger.info(f"🗑️ Cleared {count} messages")
    return {"status": "success", "cleared_count": count}

if __name__ == "__main__":
    logger.info("🚀 Starting SignalScope Webhook Server...")
    logger.info("📡 Extension webhook URL: http://localhost:8000/webhook")
    logger.info("🌐 API docs available at: http://localhost:8000/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )