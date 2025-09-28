# 📡 SignalScope → Telegram Bridge Setup Guide

## 🎯 Overview

The Telegram Bridge streams **every message** captured by your SignalScope extension **directly to Telegram** in real-time, **parallel to the existing LLM processing**. This means:

- ✅ **No disruption** to existing LLM reports
- ✅ **Immediate delivery** of chat messages to Telegram
- ✅ **Beautiful formatting** with platform emojis and timestamps
- ✅ **Image support** for shared charts and attachments
- ✅ **Link previews** for shared URLs

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Create Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Send** `/newbot`
3. **Choose a name** for your bot (e.g., "SignalScope Trading Bot")
4. **Choose a username** (e.g., "signalscope_trading_bot")
5. **Copy the BOT_TOKEN** (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Get Chat ID

**Option A: Personal Chat (Recommended)**
1. **Send any message** to your new bot
2. **Visit**: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. **Find the chat_id** in the response (usually a positive number)

**Option B: Channel/Group**
1. **Add your bot** to the channel/group
2. **Make it an admin** (required to post messages)
3. **Forward any message** from that channel to `@getidsbot`
4. **Copy the chat_id** (usually negative for groups/channels)

### Step 3: Configure Environment Variables

Add these to your **Render.com environment variables** (or `.env` file for local testing):

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_ENABLED=true
```

### Step 4: Deploy & Test

1. **Deploy your backend** to Render.com
2. **Test the connection**: `POST https://your-backend.onrender.com/webhook/telegram/test`
3. **Check your Telegram** - you should see a test message!

---

## 🔧 Implementation Details

### Current Architecture

```
┌─────────────────┐    JSON Payload    ┌─────────────────┐
│ SignalScope Ext │ ──────────────────► │ FastAPI Backend │
└─────────────────┘                     └─────────────────┘
                                                │
                                                ├─► Redis Queue ──► LLM Reports (existing)
                                                │
                                                └─► Telegram Bridge (NEW) ──► 📱 Telegram
```

### Message Flow

1. **Extension captures** message from Circle.so chat
2. **Webhook receives** message with attachments/images
3. **Two parallel processes** start:
   - **Existing**: Message → Redis → LLM → Reports
   - **New**: Message → Telegram (immediate)

### Message Format in Telegram

```
🔵 Julian Komar in #Live Chat
08:22 PM

I bought some DQ. Probably a bit of chasing here. Stock is already up 11%. Stop low of day ~7%.

📸 1 image(s) attached
```

---

## 🖼️ Image Handling

### Supported Formats
- **Base64 images** (from extension) → Sent as Telegram photos
- **Image URLs** → Sent as clickable links with preview
- **Trading charts** → Automatically detected and labeled

### Example Image Message
```
🔵 Julian Komar in #Live Chat
08:22 PM

Check out this DQ setup - looking bullish!

[📈 Chart Image Appears Here]
📈 DQ 5-min chart 08:22 PM
```

---

## 🧪 Testing

### Test Endpoints

1. **Connection Test**:
   ```bash
   curl -X POST https://your-backend.onrender.com/webhook/telegram/test
   ```

2. **Status Check**:
   ```bash
   curl https://your-backend.onrender.com/webhook/status
   ```

3. **Live Test**: Send a message in your Circle.so chat and check Telegram

### Expected Test Results

✅ **Connection Test Response**:
```json
{
  "success": true,
  "message": "Test message sent to Telegram successfully"
}
```

✅ **Status Response**:
```json
{
  "status": "operational",
  "telegram": {
    "enabled": true,
    "configured": true
  }
}
```

---

## 🔒 Security & Privacy

### Environment Variables
- **BOT_TOKEN**: Keep secret, never commit to code
- **CHAT_ID**: Can be shared, identifies destination chat
- **TELEGRAM_ENABLED**: Easy on/off switch

### Rate Limiting
- **Built-in delays** between messages (0.1s)
- **Attachment delays** (0.2s between images)
- **Telegram limits**: 30 messages/second per bot

### Privacy Considerations
- Messages are sent **immediately** to Telegram
- **No message storage** in Telegram service
- **Same data** that goes to LLM processing

---

## 🛠️ Troubleshooting

### Common Issues

**❌ "Telegram not configured"**
- Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` env vars
- Ensure `TELEGRAM_ENABLED=true`

**❌ "Telegram connection failed"**
- Verify BOT_TOKEN is correct
- Check if bot is blocked or deleted
- Test with: `https://api.telegram.org/bot<TOKEN>/getMe`

**❌ "Failed to send message"**
- Check CHAT_ID is correct
- For groups/channels: ensure bot is admin
- Check Telegram API status

**❌ Messages not appearing**
- Check if bot is muted in the chat
- Verify chat permissions
- Check backend logs for errors

### Debug Commands

```bash
# Test bot token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Get chat updates
curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates

# Check backend logs
# (In Render.com dashboard → Logs)
```

---

## 🎛️ Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | - | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | - | Destination chat ID |
| `TELEGRAM_ENABLED` | ❌ | `false` | Enable/disable bridge |

### Message Customization

The message format can be customized in `telegram_service.py`:

```python
def _format_raw_message(self, message: Dict[str, Any]) -> str:
    # Customize this function to change message format
    platform_emoji = platform_emojis.get(platform, '💭')
    message_text = f"{platform_emoji} <b>{author}</b> in #{channel}\n"
    # ... rest of formatting
```

---

## 🚀 Next Steps

### Phase 1: Basic Bridge ✅ (Complete)
- [x] Real-time message streaming
- [x] Platform detection and emojis
- [x] Image attachment support
- [x] Link preview support
- [x] Test endpoints

### Phase 2: Enhanced Features (Optional)
- [ ] Message threading by ticker symbols
- [ ] Reaction support (👍, 📈, 📉)
- [ ] Command interface (`/status`, `/toggle`)
- [ ] Message filtering (importance threshold)
- [ ] Batch summarization (hourly digests)

### Phase 3: Advanced Integration (Future)
- [ ] Bi-directional bridge (Telegram → Circle.so)
- [ ] Voice message transcription
- [ ] Alert customization per user
- [ ] Integration with trading platforms

---

## 📞 Support

If you encounter issues:

1. **Check the logs** in Render.com dashboard
2. **Test the endpoints** using the provided curl commands
3. **Verify environment variables** are set correctly
4. **Check Telegram bot permissions** in your chat

The bridge is designed to **fail gracefully** - if Telegram is unavailable, the existing LLM processing continues unaffected.

---

*🎯 **Goal Achieved**: Every message from your Circle.so trading chat now streams directly to Telegram in beautiful, real-time format with full image support!*
