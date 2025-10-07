"""
Webhook routes for receiving messages from SignalScope Chrome Extension
"""
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("bpt-api")

router = APIRouter()


@router.post("/test")
async def test_webhook(request: Request):
    """Simple test endpoint for webhook connectivity"""
    try:
        body = await request.json()
        logger.info("Test webhook received", extra={"body": body})
        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Test webhook received successfully"}
        )
    except Exception as e:
        logger.error("Test webhook failed", extra={"error": str(e)})
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )


@router.post("/")
async def receive_signalscope_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signalscope_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None)
):
    """
    Receive messages from SignalScope Chrome Extension
    
    This endpoint:
    1. Receives messages from Chrome extension
    2. Processes them for Telegram forwarding
    3. Returns immediate acknowledgment
    """
    try:
        # Get request body
        body = await request.body()
        
        # Parse JSON manually to handle validation errors better
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in webhook request", extra={"error": str(e)})
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Log the received data for debugging
        logger.info("SignalScope webhook received", extra={
            "data_keys": list(data.keys()) if isinstance(data, dict) else "not_dict",
            "message_count": len(data.get("messages", [])) if isinstance(data, dict) else 0
        })
        
        # Extract messages
        messages = data.get("messages", [])
        message_count = len(messages)
        
        if message_count == 0:
            logger.warning("No messages in webhook payload")
            return JSONResponse(
                status_code=200,
                content={"success": True, "received": 0, "message": "No messages to process"}
            )
        
        # Log first message for debugging
        if messages:
            first_msg = messages[0]
            logger.info("First message details", extra={
                "platform": first_msg.get("platform"),
                "author": first_msg.get("author"),
                "content_length": len(first_msg.get("content", "")),
                "timestamp": first_msg.get("timestamp")
            })
        
        # Add background task to process messages
        background_tasks.add_task(
            process_messages_background,
            messages
        )
        
        # Return immediate response
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "received": message_count,
                "message": f"Received {message_count} messages for processing"
            }
        )
        
    except ValueError as e:
        logger.error("Invalid webhook payload", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Webhook processing failed", extra={"error": str(e), "error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_messages_background(messages: List[Dict[str, Any]]):
    """
    Process messages asynchronously in the background
    
    Args:
        messages: List of messages to process
    """
    try:
        processed_count = 0
        
        for message in messages:
            try:
                # Log each message
                logger.info("Processing message", extra={
                    "id": message.get("id"),
                    "platform": message.get("platform"),
                    "author": message.get("author"),
                    "content_preview": message.get("content", "")[:100] + "..." if len(message.get("content", "")) > 100 else message.get("content", "")
                })
                
                # Process message for Slack forwarding
                await process_for_slack(message)
                processed_count += 1
                
            except Exception as e:
                logger.error("Failed to process message", extra={
                    "message_id": message.get("id"),
                    "error": str(e)
                })
        
        logger.info("Message batch processed", extra={
            "total": len(messages),
            "processed": processed_count
        })
        
    except Exception as e:
        logger.error("Background message processing failed", extra={"error": str(e)})


@router.get("/status")
async def webhook_status(request: Request):
    """Get webhook service status"""
    try:
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "SignalScope webhook endpoint is running"
        }
    except Exception as e:
        logger.error("Failed to get webhook status", extra={"error": str(e)})
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": str(e)}
        )


async def process_for_slack(message: Dict[str, Any]):
    """
    Process message for Slack forwarding if it contains trading signals

    Args:
        message: The message to process
    """
    try:
        # Check if Slack is configured
        slack_app_token = os.getenv("SLACK_APP_TOKEN")
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        slack_channel = os.getenv("SLACK_CHANNEL", "#trading-signals")

        if not slack_app_token or not slack_bot_token:
            logger.debug("Slack not configured - skipping message forwarding")
            return

        # Extract message data
        author = message.get("author", "Unknown")
        content = message.get("content", "")
        platform = message.get("platform", "unknown")
        url = message.get("url", "")
        timestamp = message.get("timestamp", "")

        # Get intelligence data
        intelligence = message.get("intelligence", {})
        entities = intelligence.get("entities", {})
        tickers = entities.get("tickers", [])
        prices = entities.get("prices", [])
        sentiment = intelligence.get("sentiment", {})
        importance = intelligence.get("importance", 0)

        # Only forward messages with trading content
        should_forward = (
            len(tickers) > 0 or  # Has stock tickers
            len(prices) > 0 or   # Has price mentions
            importance >= 5 or   # High importance
            any(keyword in content.lower() for keyword in [
                "buy", "sell", "bought", "sold", "position", "trade",
                "long", "short", "entry", "exit", "stop", "target"
            ])
        )

        if not should_forward:
            logger.debug(f"Message not forwarded - no trading signals detected: {content[:50]}...")
            return

        # Use requests to send directly to Slack webhook or Web API
        import requests

        # Format message for Slack
        slack_message = f"🚨 *Trading Signal Detected*\n\n"
        slack_message += f"👤 *Author:* {author}\n"
        slack_message += f"📍 *Platform:* {platform.title()}\n"
        slack_message += f"⏰ *Time:* {timestamp}\n\n"
        slack_message += f"💬 *Message:*\n{content}\n\n"

        # Add analysis if available
        if tickers:
            slack_message += f"🎯 *Tickers:* {', '.join([f'${ticker}' for ticker in tickers])}\n"

        if prices:
            slack_message += f"💰 *Prices:* {', '.join(prices)}\n"

        if sentiment.get("sentiment"):
            sentiment_emoji = {
                "bullish": "📈",
                "bearish": "📉",
                "neutral": "➡️"
            }.get(sentiment.get("sentiment", "neutral"), "➡️")
            slack_message += f"{sentiment_emoji} *Sentiment:* {sentiment['sentiment'].title()} ({sentiment.get('confidence', 0):.2f})\n"

        slack_message += f"⭐ *Importance:* {importance}/10\n"

        if url:
            slack_message += f"\n🔗 <{url}|View Source>"

        # Send to Slack using Web API
        headers = {
            "Authorization": f"Bearer {slack_bot_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "channel": slack_channel,
            "text": slack_message,
            "unfurl_links": False
        }

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200 and response.json().get("ok"):
            logger.info(f"Message forwarded to Slack successfully - Author: {author}")
        else:
            logger.error(f"Failed to forward message to Slack - Author: {author}, Response: {response.text}")

    except Exception as e:
        logger.error(f"Error processing message for Slack: {str(e)}", extra={
            "message_id": message.get("id"),
            "error_type": type(e).__name__
        })
