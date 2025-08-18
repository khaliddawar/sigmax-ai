# SignalScope (SigMax AI)

A powerful Chrome extension that captures trading signals and chat discussions from various platforms and streams structured data to backend webhooks for AI analysis.

## 🚀 Features

- **Multi-Platform Support**: Works with Discord, Telegram, WhatsApp, Slack, Reddit, Circle.so, and custom trading platforms
- **Intelligent Message Parsing**: Extracts trading signals, tickers, prices, and sentiment from chat messages
- **Attachment Support**: Captures charts, images, and files shared in conversations
- **Real-time Processing**: Streams messages to your backend via webhooks with intelligent batching
- **Trading Intelligence**: Built-in analysis for trading signals, sentiment, and importance scoring
- **Secure**: HMAC signature verification for webhook security
- **Configurable**: Flexible selectors and settings for different platforms

## 📦 Installation

### From Source
1. Clone this repository
2. Run `npm install` to install dependencies
3. Run `npm run build` to build the extension
4. Load the `build` folder as an unpacked extension in Chrome

### Chrome Web Store
*Coming soon*

## 🔧 Configuration

1. **Open Extension Options**: Click the SignalScope icon and go to Options
2. **Configure Webhook**: Set your backend webhook URL and secret key
3. **Platform Settings**: Adjust selectors for specific platforms if needed
4. **Telegram Bridge** (Optional): Set up Telegram integration using the provided setup guide

## 🏗️ Architecture

### Core Components

- **Content Scripts**: Platform-specific message capture and parsing
- **Background Service Worker**: Message processing, queueing, and webhook delivery
- **Intelligence Analyzer**: Trading signal detection and sentiment analysis
- **Message Parser**: Extracts structured data from various chat platforms
- **Webhook Manager**: Secure delivery with retry logic and batching

### Supported Platforms

| Platform | Status | Features |
|----------|--------|----------|
| Discord | ✅ Full | Messages, attachments, reactions |
| Telegram Web | ✅ Full | Messages, media, forwards |
| WhatsApp Web | ✅ Full | Messages, attachments, status |
| Slack | ✅ Full | Messages, threads, files |
| Reddit | ✅ Partial | Comments, posts |
| Circle.so | ✅ Full | Messages, attachments, reactions |
| Custom Platforms | ⚙️ Configurable | Via custom selectors |

## 🔗 Webhook Integration

### Payload Format
```json
{
  "messages": [{
    "id": "unique-message-id",
    "platform": "discord",
    "author": "username",
    "content": "message text",
    "timestamp": "2024-01-01T12:00:00Z",
    "url": "platform-url",
    "attachments": [{
      "type": "image",
      "url": "image-url",
      "context": "Trading Chart"
    }],
    "intelligence": {
      "entities": {
        "tickers": ["AAPL", "MSFT"],
        "prices": [150.25],
        "percentages": [5.2]
      },
      "sentiment": {
        "score": 0.8,
        "sentiment": "bullish",
        "confidence": 0.9
      },
      "importance": 8,
      "tradingSignal": {
        "action": "buy",
        "confidence": "high"
      }
    }
  }],
  "timestamp": "2024-01-01T12:00:00Z",
  "source": {"type": "signalscope"},
  "version": "1.0.0"
}
```

### Security
- HMAC-SHA256 signature in `X-SignalScope-Signature` header
- Idempotency keys to prevent duplicate processing
- Configurable retry logic with exponential backoff

## 🧠 Intelligence Features

### Trading Signal Detection
- **Buy/Sell Signals**: Detects trading recommendations
- **Ticker Extraction**: Identifies stock/crypto symbols
- **Price Tracking**: Captures price mentions and targets
- **Sentiment Analysis**: Bullish/bearish sentiment scoring

### Message Importance Scoring
- **0-3**: General chat, low relevance
- **4-6**: Market discussion, moderate relevance  
- **7-8**: Trading signals, high relevance
- **9-10**: Critical alerts, immediate attention

## 🔧 Development

### Setup
```bash
# Install dependencies
npm install

# Development build with watch
npm run dev

# Production build
npm run build

# Run tests
npm test

# Lint code
npm run lint
```

### Project Structure
```
src/
├── background/          # Service worker and background processing
├── content/            # Content scripts for different platforms
├── popup/              # Extension popup UI
├── options/            # Configuration page
├── sidebar/            # Debug sidebar
├── shared/             # Shared utilities and constants
└── assets/             # Icons and static files
```

## 📋 Telegram Bridge Setup

The extension includes a comprehensive Telegram bridge for forwarding captured messages. See `TELEGRAM_BRIDGE_SETUP.md` for detailed setup instructions.

## 🐛 Debugging

### Debug Tools
- **Console Logging**: Detailed logs in browser console
- **Preview Buffer**: Real-time message preview in sidebar
- **Test Functions**: Built-in testing utilities
- **Statistics**: Message capture and delivery stats

### Common Issues
1. **Messages Not Captured**: Check platform selectors in options
2. **Webhook Failures**: Verify URL and signature configuration
3. **Missing Attachments**: Ensure content security policy allows image access

## 🔒 Privacy & Security

- **Local Processing**: All analysis happens locally in the browser
- **Secure Transmission**: HMAC signatures protect webhook data
- **No Data Storage**: Messages are processed and forwarded, not stored
- **Permission Minimal**: Only requests necessary browser permissions

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Open a GitHub issue
- Check the documentation in `/docs`
- Review the Telegram setup guide

## 🚀 Roadmap

- [ ] Chrome Web Store publication
- [ ] Firefox extension support  
- [ ] Advanced AI analysis features
- [ ] Real-time dashboard
- [ ] Mobile app companion
- [ ] Advanced trading strategy detection

---

**Note**: This extension is designed for educational and research purposes. Always verify trading signals independently before making investment decisions.