# BPT Trading Assistant - Web Interface Guide

## 🌟 Overview

The BPT Web Interface provides a ChatGPT-like experience for analyzing trading session transcripts. Built with Streamlit, it offers an intuitive alternative to the Slack bot with enhanced features and better user experience.

## 🚀 Quick Start

### 1. Launch the Web Interface

```bash
# Simple launch (recommended)
python run_web_interface.py

# Custom port
python run_web_interface.py --port 8080

# Development mode with auto-reload
python run_web_interface.py --dev

# Allow external connections
python run_web_interface.py --host 0.0.0.0

# Test API connection first
python run_web_interface.py --check-api
```

### 2. Access the Interface

- **Local URL**: http://localhost:8501
- **Custom Port**: http://localhost:YOUR_PORT
- **External Access**: http://YOUR_IP:8501

## 💬 Using the Interface

### Chat Experience
- **Natural Language**: Ask questions like "What trades did we discuss today?"
- **Real-time Streaming**: Responses appear as they're generated
- **Context Aware**: Maintains conversation history
- **Smart Examples**: Click example questions to get started

### Quick Actions
- 📈 **Recent Trades**: View latest trading discussions
- 💰 **Best Performers**: Find top performing trade ideas
- ⚠️ **Risk Analysis**: Review risk management strategies
- 📊 **Market Outlook**: Get current market sentiment
- 🎯 **High Conviction**: Find highest conviction trades
- 🔍 **Specific Stock**: Search for ticker mentions

### Example Questions

**Trading Questions:**
- "What trades did we discuss today?"
- "Show me all AAPL mentions"
- "Any options strategies discussed?"

**Strategy Questions:**
- "What swing trades were mentioned?"
- "Any sector rotation ideas?"
- "What's the risk management approach?"

**Analysis Questions:**
- "What's driving the market?"
- "Any earnings plays discussed?"
- "What technical levels were mentioned?"

## 🛠️ Features

### Core Functionality
- **💬 ChatGPT-style Interface**: Familiar conversation experience
- **📱 Mobile Responsive**: Works on phones, tablets, and desktop
- **⚡ Quick Actions**: One-click access to common queries
- **🔍 Smart Search**: Context-aware transcript analysis
- **📊 Session Stats**: Track usage and conversation metrics

### Testing & Development
- **📄 Transcript Upload**: Optional testing with manual uploads
- **🔄 Live Reload**: Development mode with auto-refresh
- **🗑️ Chat Management**: Clear history, export conversations
- **⚠️ Error Tracking**: Comprehensive error logging

### Export Options
- **📄 Markdown Export**: Download conversations as .md files
- **📋 JSON Export**: Structured data export for analysis
- **📊 Session Statistics**: Detailed usage metrics

## ⚙️ Configuration

### Environment Variables

Set these in your `.env` file or environment:

```bash
# API Configuration
BPT_API_URL=http://localhost:8000  # Default: auto-detected

# Optional: Custom endpoints (if different from standard)
API_URL=http://localhost:8000      # Alternative API URL variable
```

### Streamlit Configuration

The launcher automatically configures Streamlit for optimal performance:

```bash
# Auto-configured settings:
--server.headless=true
--browser.gatherUsageStats=false
--server.fileWatcherType=auto
```

## 🔧 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Fix: Ensure you're in the project root
cd /path/to/BPT
python run_web_interface.py

# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/BPT"
```

**2. API Connection Issues**
```bash
# Test API connection
python run_web_interface.py --check-api

# Check if API server is running
curl http://localhost:8000/health
```

**3. Port Already in Use**
```bash
# Use different port
python run_web_interface.py --port 8502

# Or kill existing process
lsof -ti:8501 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8501   # Windows
```

**4. Module Not Found Errors**
```bash
# Install missing dependencies
pip install streamlit requests

# Or reinstall requirements
pip install -r requirements.txt
```

### Performance Tips

**1. Large Transcript Datasets**
- The interface caches API status for better performance
- Message history is limited to 1000 messages
- Error logs are automatically truncated

**2. Slow Response Times**
- Check API server performance
- Verify database connectivity
- Consider using shorter questions for faster responses

**3. Memory Usage**
- Clear chat history regularly for long sessions
- Export conversations before clearing
- Restart the interface if memory usage is high

### Development Mode

```bash
# Enable development features
python run_web_interface.py --dev

# Features enabled in dev mode:
# - Auto-reload on file changes
# - Extended debugging info
# - Non-headless browser mode
```

## 🔗 Integration

### With Existing BPT System

The web interface works alongside existing components:

- **✅ Slack Bot**: Continues to work for quick queries
- **✅ Fireflies Webhook**: Primary transcript source remains unchanged
- **✅ Email Summaries**: All existing features preserved
- **✅ Database**: Uses same transcript database

### API Endpoints Used

- `GET /health` - System health check
- `POST /api/qa` - Question answering
- `POST /api/process-transcript` - Manual transcript processing
- `GET /api/sessions` - Session listing
- `GET /api/sessions/{id}` - Session details

## 📱 Mobile Usage

### Responsive Design
- **Phone**: Single column layout, full-width components
- **Tablet**: Optimized sidebar, touch-friendly buttons
- **Desktop**: Full layout with sidebar and main content

### Quick Mobile Access
- Use quick action buttons for common queries
- Voice input works with most mobile browsers
- Export feature creates mobile-friendly markdown

### Slack Alternative
For quick mobile queries, you can still use:
```
/ask-bpt What trades did we discuss today?
```

## 🎯 Use Cases

### Daily Trading Review
1. Open web interface in the morning
2. Ask: "What trades were discussed yesterday?"
3. Follow up: "Any risk management updates?"
4. Export key insights for team sharing

### Historical Analysis
1. Use search to find specific stock mentions
2. Ask: "Tell me about AAPL over the last month"
3. Export detailed analysis for reporting

### Strategy Development
1. Ask about trading patterns
2. Query risk management approaches
3. Analyze market sentiment trends
4. Export findings for strategy documents

### Team Collaboration
1. Share web interface URL with team
2. Export conversations for meeting prep
3. Use alongside Slack for different contexts

## 🔒 Security Notes

- **Local Access**: Default configuration only allows localhost
- **External Access**: Use `--host 0.0.0.0` only in secure networks
- **API Security**: Inherits security from main BPT API
- **Data Privacy**: No data leaves your infrastructure

## 🆚 Comparison with Slack Bot

| Feature | Web Interface | Slack Bot |
|---------|---------------|-----------|
| **Interface** | ChatGPT-style, rich UI | Text-based commands |
| **Mobile** | Responsive web app | Native Slack mobile |
| **History** | Full conversation history | Limited message history |
| **Export** | Markdown/JSON export | Manual copy-paste |
| **Examples** | Interactive buttons | Text suggestions |
| **Testing** | Upload transcripts | Command-only |
| **Sharing** | URL sharing | Slack workspace only |
| **Offline** | Works when API available | Requires Slack connection |

## 🎨 Customization

### Styling
The interface uses custom CSS for:
- Trading-themed color scheme (green gradients)
- Professional button styling
- Mobile-responsive layouts
- Dark/light theme compatibility

### Adding Features
The modular structure makes it easy to add:
- New quick action buttons
- Additional export formats
- Custom analysis widgets
- Extended session management

## 📊 Analytics & Monitoring

### Built-in Metrics
- Session duration tracking
- Message count statistics
- Error rate monitoring
- API response times

### Export Analytics
- Conversation patterns
- Most asked questions
- User engagement metrics
- Error analysis

## 🔄 Updates & Maintenance

### Updating the Interface
```bash
# Pull latest changes
git pull origin main

# Restart the interface
# (Ctrl+C to stop, then run again)
python run_web_interface.py
```

### Backup Conversations
```bash
# Regular exports recommended
# Use the built-in export feature before updates
```

---

## 🆘 Support

### Getting Help
1. Check this documentation first
2. Review error logs in the sidebar
3. Test API connection with `--check-api`
4. Check the main BPT documentation

### Contributing
The web interface follows the modular BPT architecture:
- `components/` - Reusable UI components
- `utils/` - Utility classes and functions
- `streamlit_app.py` - Main application entry point

---

*This web interface complements the existing BPT system, providing an enhanced user experience while preserving all existing functionality.* 