# Telegram Bot Setup Guide

This guide shows you how to set up a Telegram bot to receive Circle trading signals.

## 🤖 Step 1: Create a Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start chat** with BotFather
3. **Send command**: `/newbot`
4. **Choose bot name**: e.g., "Circle Trading Signals"
5. **Choose bot username**: e.g., "circle_trading_bot" (must end with 'bot')
6. **Save the token**: BotFather will give you a token like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

## 💬 Step 2: Create a Chat/Channel

### Option A: Private Chat (Just You)
1. **Search for your bot** in Telegram
2. **Start the bot** by sending `/start`
3. **Get your chat ID** (see step 3 below)

### Option B: Group Chat
1. **Create a group** in Telegram
2. **Add your bot** to the group
3. **Make bot admin** (optional but recommended)

### Option C: Channel
1. **Create a channel** in Telegram
2. **Add your bot** as an admin to the channel

## 🔍 Step 3: Get Chat ID

### Method 1: Using Bot
1. **Send a message** to your bot or group
2. **Visit**: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. **Look for "chat":{"id":...}** in the response
4. **Copy the ID** (e.g., `123456789` or `-123456789` for groups)

### Method 2: Using @userinfobot
1. **Add @userinfobot** to your group/channel
2. **Send any message**
3. **Bot will reply** with chat ID

## ⚙️ Step 4: Configure the Server

### Option A: Environment Variables (Recommended)
```bash
set TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
set TELEGRAM_CHAT_ID=123456789
```

### Option B: Edit the Python File
Open `telegram_forwarder_server.py` and replace:
```python
# TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
# TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"
```

With your actual values:
```python
TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID = "123456789"
```

## 🚀 Step 5: Start the Server

1. **Stop the current server** (Ctrl+C in the terminal)
2. **Install requests** if needed: `pip install requests`
3. **Start new server**: `python telegram_forwarder_server.py`

## 🧪 Step 6: Test the Setup

1. **Test Telegram bot**: `curl -X POST http://localhost:8000/telegram/test`
2. **Check Telegram** - you should receive a test message
3. **Send a message** in Circle with a stock ticker (e.g., "$AAPL looks good")
4. **Check Telegram** - should receive the trading signal

## 📋 Message Format

The bot will send messages like this:

```
🚨 Trading Signal Detected

👤 Author: Boris
📍 Platform: Circle
⏰ Time: 2025-09-19T19:46:00.000Z

💬 Message:
I am tempted to take some profit but I don't want to regret it 😟 $NRGV, there is either short squeeze or big news coming

📊 Analysis:
🎯 Tickers: $NRGV
📈 Sentiment: Bullish (0.20)
⭐ Importance: 6/10

🔗 Source: https://members.julian-komar.com/c/community-chat/
```

## 🎯 Filtering Rules

The bot will only forward messages that have:
- **Stock tickers** (like $AAPL, $NRGV), OR
- **High importance** (5+ out of 10)

This prevents spam and only sends relevant trading signals.

## 🔧 Troubleshooting

- **"Telegram forwarding: DISABLED"**: Check your bot token and chat ID
- **"Failed to send to Telegram"**: Verify bot token and that bot is added to chat
- **No messages received**: Make sure Circle messages contain stock tickers
- **403 Forbidden**: Bot needs to be added to the group/channel

## 📱 Next Steps

Once set up, every trading signal from Circle will automatically appear in your Telegram chat!