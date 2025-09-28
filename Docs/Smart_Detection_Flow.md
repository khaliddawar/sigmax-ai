# SignalScope Smart Chat Detection System

## Overview
SignalScope uses intelligent detection to identify if a webpage contains a chat interface, then allows users to start monitoring with a single click.

---

## Detection Flow

### Step 1: Automatic Page Analysis
When user clicks extension icon, SignalScope analyzes the current page:

```javascript
// popup.js - Runs when extension popup opens
async function analyzeCurrentPage() {
  const tab = await chrome.tabs.query({active: true, currentWindow: true});
  
  // Inject analysis script into page
  const results = await chrome.scripting.executeScript({
    target: {tabId: tab[0].id},
    func: detectChatSignals
  });
  
  return results[0].result;
}

function detectChatSignals() {
  const signals = {
    url: window.location.href,
    title: document.title,
    indicators: []
  };
  
  // Check 1: URL patterns
  const chatUrlPatterns = [
    /chat/i, /message/i, /conversation/i, /discussion/i,
    /forum/i, /community/i, /discord/i, /telegram/i,
    /slack/i, /teams/i, /room/i, /channel/i
  ];
  
  if (chatUrlPatterns.some(pattern => pattern.test(signals.url))) {
    signals.indicators.push('URL contains chat-related keywords');
  }
  
  // Check 2: Page title
  if (chatUrlPatterns.some(pattern => pattern.test(signals.title))) {
    signals.indicators.push('Title suggests chat interface');
  }
  
  // Check 3: DOM structure analysis
  const chatSelectors = [
    '[class*="message"]',
    '[class*="chat"]',
    '[class*="comment"]',
    '[id*="message"]',
    '[id*="chat"]',
    '[data-message]',
    '[role="log"]',  // ARIA role for chat logs
    '[role="listbox"]',
    '.msg', '.post', '.reply'
  ];
  
  let messageElements = 0;
  chatSelectors.forEach(selector => {
    messageElements += document.querySelectorAll(selector).length;
  });
  
  if (messageElements > 5) {
    signals.indicators.push(`Found ${messageElements} message-like elements`);
  }
  
  // Check 4: Username patterns
  const userPatterns = [
    '[class*="user"]',
    '[class*="author"]',
    '[class*="sender"]',
    '[class*="name"]',
    '[class*="nick"]'
  ];
  
  let userElements = 0;
  userPatterns.forEach(selector => {
    userElements += document.querySelectorAll(selector).length;
  });
  
  if (userElements > 3) {
    signals.indicators.push('Username patterns detected');
  }
  
  // Check 5: Timestamp patterns
  const timePatterns = [
    '[class*="time"]',
    '[class*="date"]',
    '[class*="timestamp"]',
    'time',
    '[datetime]'
  ];
  
  let timeElements = 0;
  timePatterns.forEach(selector => {
    timeElements += document.querySelectorAll(selector).length;
  });
  
  if (timeElements > 3) {
    signals.indicators.push('Timestamp patterns found');
  }
  
  // Check 6: Real-time updates (WebSocket/polling)
  if (window.WebSocket && document.querySelector('[class*="live"]')) {
    signals.indicators.push('Real-time updates detected');
  }
  
  // Check 7: Input field for sending messages
  const inputSelectors = [
    'textarea[placeholder*="message"]',
    'input[placeholder*="type"]',
    'input[placeholder*="say"]',
    'input[placeholder*="write"]',
    'div[contenteditable="true"]'
  ];
  
  if (inputSelectors.some(sel => document.querySelector(sel))) {
    signals.indicators.push('Message input field found');
  }
  
  // Calculate confidence score
  signals.confidence = (signals.indicators.length / 7) * 100;
  signals.isLikelyChat = signals.confidence > 30;
  
  // Try to detect platform
  signals.platform = detectPlatform();
  
  return signals;
}

function detectPlatform() {
  const url = window.location.hostname;
  const title = document.title.toLowerCase();
  
  const platforms = {
    'discord.com': 'Discord',
    'web.telegram.org': 'Telegram',
    'slack.com': 'Slack',
    'teams.microsoft.com': 'Microsoft Teams',
    'web.whatsapp.com': 'WhatsApp',
    'facebook.com/messages': 'Facebook Messenger',
    'reddit.com': 'Reddit',
    'twitch.tv': 'Twitch',
    'youtube.com': 'YouTube Live Chat',
    'tradingview.com': 'TradingView',
    'stocktwits.com': 'StockTwits'
  };
  
  for (const [domain, name] of Object.entries(platforms)) {
    if (url.includes(domain)) {
      return { name, preset: true };
    }
  }
  
  // Check for generic indicators
  if (document.querySelector('iframe[src*="disqus"]')) {
    return { name: 'Disqus Comments', preset: true };
  }
  
  if (document.querySelector('[id*="discourse"]')) {
    return { name: 'Discourse Forum', preset: true };
  }
  
  return { name: 'Unknown Platform', preset: false };
}
```

---

## Popup UI States

### State 1: Likely Chat Detected
```
┌─────────────────────────────────────┐
│       🔍 SignalScope                │
├─────────────────────────────────────┤
│                                     │
│  ✅ Chat Interface Detected!        │
│                                     │
│  Platform: TradingView Chat         │
│  Confidence: 85%                    │
│                                     │
│  Found:                             │
│  • 47 message elements             │
│  • Username patterns               │
│  • Timestamps                      │
│  • Real-time updates               │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   🚀 Start Monitoring        │   │
│  └─────────────────────────────┘   │
│                                     │
│  [ ] Use preset configuration      │
│  [ ] Configure manually            │
│                                     │
└─────────────────────────────────────┘
```

### State 2: Possible Chat (Low Confidence)
```
┌─────────────────────────────────────┐
│       🔍 SignalScope                │
├─────────────────────────────────────┤
│                                     │
│  🤔 Possible Chat Interface         │
│                                     │
│  Confidence: 40%                    │
│                                     │
│  Found some indicators:             │
│  • Message-like elements           │
│  • Username patterns               │
│                                     │
│  This might be a chat. Want to      │
│  try monitoring it?                 │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   🔬 Analyze & Configure     │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   ❌ Not a Chat              │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

### State 3: No Chat Detected
```
┌─────────────────────────────────────┐
│       🔍 SignalScope                │
├─────────────────────────────────────┤
│                                     │
│  ❌ No Chat Interface Detected      │
│                                     │
│  This doesn't appear to be a       │
│  chat page.                        │
│                                     │
│  You can still try to configure    │
│  manually if this is incorrect.    │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   ⚙️ Manual Configuration     │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   📚 View Tutorial           │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

### State 4: Currently Monitoring
```
┌─────────────────────────────────────┐
│       🔍 SignalScope                │
├─────────────────────────────────────┤
│                                     │
│  🟢 MONITORING ACTIVE               │
│                                     │
│  Platform: Custom Trading Chat      │
│  Started: 10 minutes ago           │
│                                     │
│  📊 Statistics:                     │
│  • Messages captured: 47           │
│  • Last batch sent: 30s ago        │
│  • Webhook status: ✅ Healthy      │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   ⏸️ Pause Monitoring         │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │   📈 View Dashboard          │   │
│  └─────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

---

## User Flow

### Flow 1: Known Platform (e.g., Discord)
1. User navigates to Discord web
2. Clicks SignalScope extension icon
3. Sees: "✅ Discord Chat Detected!"
4. Clicks "Start Monitoring"
5. Extension loads Discord preset selectors
6. Monitoring begins immediately

### Flow 2: Unknown Platform (Proprietary Chat)
1. User navigates to company's internal chat
2. Clicks SignalScope extension icon
3. Sees: "🤔 Possible Chat Interface (60% confidence)"
4. Clicks "Analyze & Configure"
5. Visual selector builder opens
6. User clicks on message elements to configure
7. Tests configuration
8. Starts monitoring

### Flow 3: Manual Override
1. User on a page not detected as chat
2. Clicks SignalScope extension icon
3. Sees: "❌ No Chat Detected"
4. Clicks "Manual Configuration"
5. Enters custom selectors or uses visual builder
6. Saves and starts monitoring

---

## Smart Features

### 1. Learning System
```javascript
// Extension learns from user configurations
async function saveSuccessfulConfig(url, selectors, platform) {
  const pattern = new URL(url).hostname;
  
  // Save to community library (with user permission)
  await chrome.storage.sync.set({
    [`learned_${pattern}`]: {
      selectors,
      platform,
      successRate: 0,
      usageCount: 0,
      contributed: false
    }
  });
  
  // Prompt to share with community
  if (await promptUserToShare()) {
    await submitToCommunityLibrary(pattern, selectors);
  }
}
```

### 2. Quick Actions
When chat is detected, show quick action buttons:

```javascript
const quickActions = {
  'Trading Platform': {
    icon: '📈',
    filters: ['price', 'buy', 'sell', 'signal'],
    webhookTemplate: 'trading-signals'
  },
  'Customer Support': {
    icon: '🎧',
    filters: ['ticket', 'issue', 'help'],
    webhookTemplate: 'support-tickets'
  },
  'Community Forum': {
    icon: '👥',
    filters: [],
    webhookTemplate: 'community-engagement'
  }
};
```

### 3. Platform Presets
Maintain a library of known configurations:

```javascript
const platformPresets = {
  'discord.com': {
    containerSelector: '[data-list-id="chat-messages"]',
    messageSelector: '[class*="message-"]',
    authorSelector: '[class*="username-"]',
    textSelector: '[class*="messageContent-"]',
    timestampSelector: 'time',
    confidence: 100
  },
  'tradingview.com': {
    containerSelector: '.tv-messagelist',
    messageSelector: '.message-2W_rDYYP',
    authorSelector: '.username-3Cu8Mq1D',
    textSelector: '.text-2W_rDYYP',
    timestampSelector: '.time-3Cu8Mq1D',
    confidence: 100
  },
  // ... more presets
};
```

### 4. Auto-Configuration Attempt
For unknown platforms, try intelligent selector discovery:

```javascript
async function autoConfigureSelectors() {
  const config = {};
  
  // Find repeating structures (likely messages)
  const repeatingElements = findRepeatingPatterns();
  
  if (repeatingElements.length > 0) {
    config.messageSelector = generateSelector(repeatingElements[0]);
    
    // Within each message, look for:
    // - Shortest text that looks like username
    // - Longest text block (likely message content)
    // - Timestamp patterns (ISO dates, relative times)
    
    const sampleMessage = repeatingElements[0];
    config.authorSelector = findUsernameSelector(sampleMessage);
    config.textSelector = findContentSelector(sampleMessage);
    config.timestampSelector = findTimestampSelector(sampleMessage);
  }
  
  return config;
}
```

---

## Benefits of This Approach

### For Users:
1. **One-click setup** for known platforms
2. **Smart detection** reduces configuration time
3. **Visual confirmation** before starting
4. **Manual override** when detection fails
5. **Learning system** improves over time

### For Product:
1. **Lower barrier to entry** - no technical knowledge needed
2. **Faster onboarding** - seconds instead of minutes
3. **Reduced support burden** - smart detection handles most cases
4. **Community growth** - users contribute configurations
5. **Platform agnostic** - works with any chat

### For Development:
1. **Progressive enhancement** - basic detection → AI-powered
2. **Modular system** - easy to add new platform presets
3. **User feedback loop** - learn from successful configs
4. **A/B testing ready** - test different detection algorithms
5. **Analytics friendly** - track platform usage and success rates

---

## Implementation Priority

### Phase 1: MVP (Week 1-2)
- Basic detection (URL + DOM patterns)
- Manual start button
- 5 platform presets (Discord, Telegram, Slack, TradingView, Reddit)
- Simple popup UI

### Phase 2: Enhanced (Week 3-4)
- Smart detection algorithm
- Visual selector builder
- Auto-configuration attempt
- 20+ platform presets

### Phase 3: Advanced (Month 2)
- Machine learning-based detection
- Community library integration
- Quick action templates
- Cross-tab monitoring management

---

## Success Metrics

1. **Detection Accuracy**
   - Target: 90% correct identification for known platforms
   - Target: 60% correct identification for unknown chats

2. **User Activation**
   - Target: 80% of users start monitoring within 1 minute
   - Target: 95% successful setup on first try

3. **Platform Coverage**
   - Target: 50+ platform presets in library
   - Target: 500+ community-contributed configs

4. **User Satisfaction**
   - Target: <5% abandon due to configuration difficulty
   - Target: 4.5+ star rating on ease of use