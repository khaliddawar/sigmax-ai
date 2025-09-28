# SignalScope Source Tree Structure

## Overview
This document defines the project structure and file organization for the SignalScope Chrome Extension.

## Directory Structure

```
SignalScope/
├── src/                          # Source code
│   ├── background/              # Service worker scripts
│   │   ├── service-worker.js   # Main service worker
│   │   ├── webhook-manager.js  # Webhook queue and delivery
│   │   ├── storage-manager.js  # Chrome storage operations
│   │   └── message-handler.js  # Runtime message handling
│   │
│   ├── content/                 # Content scripts
│   │   ├── content-script.js   # Main content script
│   │   ├── dom-observer.js     # MutationObserver logic
│   │   ├── message-parser.js   # Message extraction logic
│   │   ├── selector-engine.js  # CSS selector management
│   │   └── platforms/          # Platform-specific logic
│   │       ├── discord.js      # Discord-specific selectors
│   │       ├── telegram.js     # Telegram-specific selectors
│   │       ├── slack.js        # Slack-specific selectors
│   │       └── generic.js      # Generic chat platform
│   │
│   ├── popup/                   # Extension popup
│   │   ├── popup.html          # Popup UI
│   │   ├── popup.js            # Popup logic
│   │   └── popup.css           # Popup styles
│   │
│   ├── options/                 # Options page
│   │   ├── options.html        # Settings UI
│   │   ├── options.js          # Settings logic
│   │   └── options.css         # Settings styles
│   │
│   ├── shared/                  # Shared utilities
│   │   ├── constants.js        # App constants
│   │   ├── utils.js            # Utility functions
│   │   ├── crypto.js           # HMAC signing utilities
│   │   ├── validator.js        # Input validation
│   │   └── logger.js           # Logging utilities
│   │
│   └── assets/                  # Static assets
│       ├── icons/              # Extension icons
│       │   ├── icon-16.png     # Toolbar icon
│       │   ├── icon-48.png     # Extension management
│       │   └── icon-128.png    # Web store icon
│       ├── styles/             # Shared styles
│       │   └── common.css      # Common styles
│       └── templates/          # HTML templates
│           └── webhook-test.html
│
├── tests/                        # Test files
│   ├── unit/                    # Unit tests
│   │   ├── background/         # Service worker tests
│   │   ├── content/            # Content script tests
│   │   └── shared/             # Utility tests
│   │
│   ├── integration/             # Integration tests
│   │   ├── webhook.test.js     # Webhook delivery tests
│   │   └── storage.test.js     # Storage operation tests
│   │
│   └── fixtures/                # Test data
│       ├── messages.json       # Sample messages
│       └── selectors.json      # Test selectors
│
├── docs/                         # Documentation
│   ├── architecture/            # Architecture docs
│   │   ├── coding-standards.md # Coding standards
│   │   ├── tech-stack.md       # Technology stack
│   │   └── source-tree.md      # This file
│   │
│   ├── prd/                     # Product requirements
│   │   └── *.md                # PRD shards
│   │
│   ├── stories/                 # User stories
│   │   └── *.md                # Story files
│   │
│   └── Docs/                    # Legacy docs
│       ├── SignalScope_PRD.md
│       └── SignalScope_Market_Analysis.md
│
├── build/                        # Build output (git-ignored)
│   └── ...                      # Compiled extension files
│
├── dist/                         # Distribution packages (git-ignored)
│   └── signalscope-v*.zip      # Release packages
│
├── .bmad-core/                   # BMad framework files
│   ├── tasks/                   # Development tasks
│   ├── templates/               # File templates
│   ├── checklists/              # QA checklists
│   └── core-config.yaml        # BMad configuration
│
├── .claude/                      # Claude AI configuration
│   └── commands/                # Custom commands
│       └── BMad/               # BMad integration
│
├── .ai/                          # AI development artifacts
│   └── debug-log.md            # Development debug log
│
├── scripts/                      # Build and utility scripts
│   ├── build.js                # Build script
│   ├── package.js              # Package for distribution
│   ├── test-webhook.js         # Webhook testing utility
│   └── watch.js                # Development watcher
│
├── config/                       # Configuration files
│   ├── webpack.config.js       # Webpack configuration
│   ├── jest.config.js          # Jest configuration
│   └── eslint.config.js        # ESLint configuration
│
├── manifest.json                 # Chrome Extension manifest
├── package.json                  # Node.js dependencies
├── package-lock.json            # Dependency lock file
├── .gitignore                   # Git ignore rules
├── .eslintrc.js                 # ESLint configuration
├── .prettierrc                  # Prettier configuration
├── README.md                    # Project documentation
├── CHANGELOG.md                 # Version history
└── LICENSE                      # License file
```

## File Naming Conventions

### JavaScript Files
- **Service Worker**: `service-worker.js` (required name)
- **Modules**: `{feature}-{type}.js` (e.g., `webhook-manager.js`)
- **Tests**: `{module}.test.js` or `{module}.spec.js`
- **Config**: `{tool}.config.js`

### Asset Files
- **Icons**: `icon-{size}.png` (16, 48, 128)
- **Images**: `{name}-{variant}.{ext}`
- **Styles**: `{component}.css`

### Documentation
- **Markdown**: `{topic}.md` or `{TOPIC}__{subtopic}.md`
- **User Stories**: `story-{number}-{title}.md`
- **Epics**: `epic-{number}-{title}.md`

## Module Organization

### Background Scripts
- **service-worker.js**: Entry point, orchestrates all background tasks
- **webhook-manager.js**: Queue management, retry logic, delivery
- **storage-manager.js**: Abstraction over chrome.storage API
- **message-handler.js**: Inter-context communication

### Content Scripts
- **content-script.js**: Entry point, initialization
- **dom-observer.js**: MutationObserver setup and management
- **message-parser.js**: Extract and structure message data
- **selector-engine.js**: Dynamic selector management
- **platforms/**: Platform-specific implementations

### Shared Modules
- **constants.js**: Centralized constants
- **utils.js**: Reusable utility functions
- **crypto.js**: Security utilities
- **validator.js**: Input validation functions
- **logger.js**: Consistent logging

## Build Artifacts

### Development Build (`/build`)
```
build/
├── background/
├── content/
├── popup/
├── options/
├── assets/
└── manifest.json
```

### Production Distribution (`/dist`)
```
dist/
└── signalscope-v1.0.0.zip
    ├── All minified source files
    ├── Optimized assets
    └── Production manifest.json
```

## Import Paths

### Absolute Imports (Webpack Aliases)
```javascript
// Instead of: ../../../shared/utils.js
import { debounce } from '@shared/utils';
import { WEBHOOK_EVENTS } from '@shared/constants';
import { validateUrl } from '@shared/validator';
```

### Webpack Aliases Configuration
```javascript
{
  '@background': 'src/background',
  '@content': 'src/content',
  '@popup': 'src/popup',
  '@options': 'src/options',
  '@shared': 'src/shared',
  '@assets': 'src/assets'
}
```

## Key Files Description

### manifest.json
Chrome Extension manifest defining permissions, scripts, and metadata.

### service-worker.js
Background script that handles:
- Webhook queue management
- Message routing
- Storage operations
- Alarm scheduling

### content-script.js
Injected into web pages to:
- Monitor DOM changes
- Extract messages
- Send data to service worker

### webhook-manager.js
Handles:
- Queue persistence
- Retry logic with exponential backoff
- Batch processing
- HMAC signing

### Platform Adapters
Each platform file exports:
```javascript
export default {
  name: 'discord',
  selectors: {
    message: '[data-list-item-id^="chat-messages"]',
    author: '.username-h_Y3Us',
    content: '.messageContent-2t3eCI',
    timestamp: 'time[datetime]'
  },
  parser: (element) => { /* ... */ }
};
```

## Development Workflow Files

### package.json Scripts
```json
{
  "scripts": {
    "dev": "webpack --mode development --watch",
    "build": "webpack --mode production",
    "test": "jest",
    "lint": "eslint src/",
    "format": "prettier --write src/",
    "package": "node scripts/package.js"
  }
}
```

### Testing Structure
- Unit tests mirror source structure
- Integration tests in dedicated folder
- Fixtures provide test data
- Coverage reports in `/coverage` (git-ignored)

## Git Ignored Paths
```
node_modules/
build/
dist/
coverage/
*.log
.env
.DS_Store
*.zip
```

## Environment Variables
Development environment variables (create `.env` file):
```
WEBHOOK_TEST_URL=https://webhook.site/your-uuid
DEBUG_MODE=true
LOG_LEVEL=verbose
```

## CI/CD Artifacts
GitHub Actions will create:
- Release builds in `/dist`
- Test reports in `/coverage`
- Documentation in `/docs/generated`