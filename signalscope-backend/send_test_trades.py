"""
Send fresh trading messages for testing
"""
import requests
import json
from datetime import datetime
import random

# Trading scenarios
trading_messages = [
    {
        "author": "TechBull",
        "content": "$GOOGL breaking above $150 resistance! Loading up for move to $160. Cloud AI dominance play.",
        "tickers": ["GOOGL"],
        "sentiment": "bullish",
        "importance": 8
    },
    {
        "author": "MetaTrader",
        "content": "$META showing strength at $500 level. VR/AR future is here. Target $550 by month end.",
        "tickers": ["META"],
        "sentiment": "bullish",
        "importance": 7
    },
    {
        "author": "CryptoKing",
        "content": "$ETH forming bullish flag above $3000. Next leg up targets $3500. DeFi explosion incoming!",
        "tickers": ["ETH"],
        "sentiment": "bullish",
        "importance": 9
    },
    {
        "author": "BearHunter",
        "content": "Warning: $TSLA overextended at current levels. RSI screaming overbought. Pullback to $800 likely.",
        "tickers": ["TSLA"],
        "sentiment": "bearish",
        "importance": 6
    },
    {
        "author": "OptionsFlow",
        "content": "Unusual options activity in $AAPL. Massive call buying at $200 strike. Institutions positioning for breakout.",
        "tickers": ["AAPL"],
        "sentiment": "bullish",
        "importance": 9
    }
]

def send_messages():
    webhook_url = "http://localhost:8000/api/webhooks/signalscope"
    
    messages_to_send = []
    
    for i, msg_data in enumerate(trading_messages):
        message = {
            "id": f"trade_{datetime.now().timestamp()}_{i}",
            "platform": "test-trades",
            "author": msg_data["author"],
            "content": msg_data["content"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "url": "http://localhost:8080/test",
            "intelligence": {
                "entities": {
                    "tickers": msg_data["tickers"],
                    "prices": [],
                    "percentages": [],
                    "quantities": []
                },
                "sentiment": {
                    "score": 0.8 if msg_data["sentiment"] == "bullish" else -0.8,
                    "sentiment": msg_data["sentiment"],
                    "confidence": 0.9
                },
                "tradingSignal": {
                    "action": "BUY" if msg_data["sentiment"] == "bullish" else "SELL",
                    "tickers": msg_data["tickers"],
                    "strength": "strong" if msg_data["importance"] >= 8 else "moderate"
                } if msg_data["importance"] >= 6 else None,
                "importance": msg_data["importance"]
            },
            "capturedAt": datetime.utcnow().isoformat() + "Z"
        }
        messages_to_send.append(message)
    
    payload = {
        "messages": messages_to_send,
        "client": {
            "extension_version": "1.0.0",
            "browser": "Chrome",
            "tz": "America/New_York"
        },
        "source": {
            "origin": "http://localhost:8080",
            "page_title": "Trading Test"
        }
    }
    
    print("Sending trading messages...")
    print("="*50)
    
    for msg in messages_to_send:
        print(f"- {msg['author']}: {msg['content'][:50]}...")
    
    response = requests.post(webhook_url, json=payload)
    
    print("\n" + "="*50)
    print(f"Response: {response.status_code}")
    print(f"Result: {response.json()}")
    
    # Check status
    status_response = requests.get("http://localhost:8000/api/webhooks/status")
    status = status_response.json()
    
    print("\n" + "="*50)
    print("Queue Status:")
    print(f"  Realtime: {status['queues']['realtime']} messages")
    print(f"  Standard: {status['queues']['standard']} messages")
    print(f"  Archive: {status['queues']['archive']} messages")

if __name__ == "__main__":
    send_messages()