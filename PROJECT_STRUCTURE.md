# SignalScope Project Structure

## 📁 Directory Organization

```
SignalScope/
├── 📄 README.md                    # Main project documentation
├── 📄 LICENSE                      # MIT License
├── 📄 .gitignore                   # Git ignore rules
├── 📄 PROJECT_STRUCTURE.md         # This file
├── 📄 package.json                 # Node.js dependencies
├── 📄 package-lock.json            # Locked dependency versions
├── 📄 manifest.json                # Chrome extension manifest
│
├── 📁 src/                         # Source code
│   ├── 📁 background/              # Service worker scripts
│   ├── 📁 content/                 # Content scripts
│   ├── 📁 popup/                   # Extension popup UI
│   ├── 📁 options/                 # Extension options page
│   ├── 📁 sidebar/                 # Extension sidebar
│   └── 📁 shared/                  # Shared utilities
│
├── 📁 build/                       # Built extension (generated)
│   ├── 📁 background/
│   ├── 📁 content/
│   ├── 📁 popup/
│   ├── 📁 options/
│   ├── 📁 sidebar/
│   └── 📄 manifest.json
│
├── 📁 servers/                     # Server implementations
│   ├── 📄 simple_telegram_server.py    # Simple bridge (recommended)
│   └── 📄 circle_to_telegram_server.py # Full backend bridge
│
├── 📁 signalscope-backend/         # Complete backend system
│   ├── 📁 app/                     # FastAPI application
│   ├── 📁 tests/                   # Backend tests
│   ├── 📄 requirements.txt         # Python dependencies
│   └── 📄 .env                     # Environment variables
│
├── 📁 docs/                        # Documentation
│   ├── 📄 CLAUDE.md               # Development guidelines
│   ├── 📄 DEBUG_INSTRUCTIONS.md   # Debugging guide
│   ├── 📄 TELEGRAM_SETUP.md       # Telegram configuration
│   └── 📄 [other documentation files]
│
├── 📁 assets/                      # Static assets
│   └── 📁 icons/                   # Extension icons
│
├── 📁 config/                      # Build configuration
│   ├── 📄 webpack.config.js       # Webpack build config
│   └── 📄 jest.config.js          # Test configuration
│
└── 📁 tests/                       # Extension tests
```

## 🚀 Quick Start Commands

### Development
```bash
# Install dependencies
npm install

# Build extension
npm run build

# Start simple server
python servers/simple_telegram_server.py
```

### Production
```bash
# Build for production
npm run build

# Package extension
npm run package

# Deploy server
python servers/simple_telegram_server.py
```

## 📋 Key Files

### Extension Core
- `src/content/content-script-enhanced.js` - Main content script
- `src/background/service-worker.js` - Background service worker
- `src/shared/constants.js` - Platform selectors and configuration

### Servers
- `servers/simple_telegram_server.py` - **Recommended** simple bridge
- `servers/circle_to_telegram_server.py` - Full backend integration

### Configuration
- `manifest.json` - Chrome extension manifest
- `package.json` - Node.js project configuration
- `config/webpack.config.js` - Build configuration

### Documentation
- `README.md` - Main project documentation
- `docs/` - Detailed guides and troubleshooting

## 🔧 Development Workflow

1. **Extension Development**: Edit files in `src/`
2. **Build**: Run `npm run build` to generate `build/`
3. **Test**: Load `build/` folder in Chrome extensions
4. **Server**: Run `python servers/simple_telegram_server.py`
5. **Debug**: Check browser console and server logs

## 📦 Distribution

- **Extension**: Package `build/` folder contents
- **Server**: Deploy `servers/simple_telegram_server.py` with dependencies
- **Documentation**: Include `README.md` and `docs/` folder
