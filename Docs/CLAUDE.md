# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SignalScope is a Chrome Extension (Manifest V3) that captures chatroom discussions and streams structured JSON to backend webhooks. The project consists of:
- **Chrome Extension**: Frontend that monitors web-based chat platforms
- **Python Backend**: FastAPI server for webhook processing and transcript analysis (optional)

## Development Commands

### Chrome Extension (Frontend)

```bash
# Install dependencies
npm install

# Development build with watch mode (use this for active development)
npm run dev

# Production build
npm run build

# Run tests
npm test
npm run test:coverage  # with coverage report

# Code quality
npm run lint        # Check for linting issues
npm run lint:fix    # Auto-fix linting issues
npm run format      # Format code with Prettier

# Package for distribution
npm run package

# Clean build artifacts
npm run clean
```

### Python Backend (Optional)

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run development server
cd backend
python app/main.py

# Run with specific features
python development/runners/run_with_ingestion.py  # With ingestion pipeline
python development/runners/run_with_auth.py       # With authentication

# Run Streamlit web interface
streamlit run app/web/streamlit_app.py

# Run tests
pytest tests/
```

## Architecture Overview

### Chrome Extension Structure

The extension follows Manifest V3 architecture with a service worker pattern:

- **`src/background/`**: Service worker for managing extension lifecycle and webhook delivery
  - `service-worker.js`: Main background script handling message routing and webhook queuing
  - `webhook-manager.js`: Manages webhook delivery with retry logic
  - `storage-manager.js`: Handles local storage and IndexedDB operations

- **`src/content/`**: Content scripts injected into web pages
  - `content-script.js`: Main content script coordinating message capture
  - `dom-observer.js`: Monitors DOM changes for new messages
  - `message-parser.js`: Extracts message data from DOM elements
  - `selector-engine.js`: Platform-specific CSS selectors

- **`src/popup/`**: Extension popup UI
  - Shows connection status and recent activity

- **`src/options/`**: Options page for configuration
  - Webhook URL configuration
  - Platform selector setup
  - Authentication settings

- **`src/shared/`**: Shared utilities
  - `constants.js`: Configuration constants
  - `logger.js`: Logging utilities
  - `utils.js`: Common helper functions

### Backend Architecture (If Using)

The backend uses FastAPI with modular service architecture:

- **`app/routes/`**: API endpoints
  - `webhook_routes.py`: Handles incoming webhooks
  - `transcript_routes.py`: Transcript processing endpoints

- **`app/services/`**: Business logic
  - `ingestion_service.py`: Processes incoming data
  - `summary_service_v2.py`: Generates summaries
  - `embedding_service.py`: Vector embeddings for search
  - `supabase_client.py`: Database operations

- **`app/middleware/`**: Request processing
  - `auth_middleware.py`: Authentication
  - `security_middleware.py`: Security headers

## Key Development Patterns

### Chrome Extension Development

1. **Loading the Extension**:
   - Run `npm run dev` to build with watch mode
   - Open `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `build` folder
   - Extension will auto-reload on code changes

2. **Testing Content Scripts**:
   - Content scripts are injected based on manifest permissions
   - Use Chrome DevTools console in the target page
   - Check for errors in both page console and extension console

3. **Service Worker Debugging**:
   - Click "Inspect views: service worker" in chrome://extensions/
   - Service worker restarts on idle; use persistent DevTools

4. **Message Passing**:
   - Content scripts communicate with service worker via `chrome.runtime.sendMessage`
   - Use structured message format with `type` field for routing

### Webhook Integration

The extension sends webhooks in this format:
```json
{
  "id": "unique-message-id",
  "platform": "discord",
  "channel": "general",
  "author": "username",
  "content": "Message content",
  "timestamp": "2025-01-15T10:30:00Z",
  "metadata": {
    "url": "https://discord.com/channels/...",
    "selectors": {...}
  }
}
```

### Platform Support

Pre-configured selectors exist for:
- Discord (Web)
- Telegram Web
- Slack
- WhatsApp Web

Custom platforms can be added by defining CSS selectors in options.

## Testing Approach

### Extension Testing
- Use Jest with Chrome Extension Testing Library
- Mock Chrome APIs with `jest-chrome`
- Test files in `tests/` directory

### Backend Testing
- Use pytest for Python tests
- Test webhook endpoints with mock data
- Integration tests for database operations

## Common Tasks

### Adding a New Platform
1. Add platform configuration to `src/shared/constants.js`
2. Create selector mapping in `src/content/selector-engine.js`
3. Test with actual platform website
4. Update options UI if needed

### Modifying Webhook Format
1. Update data structure in `src/background/webhook-manager.js`
2. Adjust content script message extraction
3. Update backend webhook handler if using
4. Test end-to-end with sample data

### Debugging Webhook Delivery
1. Check service worker console for errors
2. Verify webhook URL in options
3. Check network tab for failed requests
4. Review retry queue in IndexedDB

## Important Notes

- Extension uses Manifest V3 - service workers instead of background pages
- All webhook endpoints must use HTTPS
- Extension has minimal permissions for security
- Local storage used for configuration, IndexedDB for message queue
- No external dependencies in production bundle for performance