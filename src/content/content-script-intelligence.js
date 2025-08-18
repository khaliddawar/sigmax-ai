// Intelligent content script for SignalScope with Trading Intelligence
// Captures and analyzes trading signals from chat messages

console.log('SignalScope Intelligence loaded on:', window.location.href);

// Set flag to indicate content script is loaded
window.signalScopeContentScript = true;

// Add test function for debugging
window.testSignalScope = function() {
  const messages = document.querySelectorAll('.message-out, .message-in');
  console.log('SignalScope Test:', {
    platform: detectPlatform(window.location.href),
    messagesFound: messages.length,
    url: window.location.href,
    contentScriptLoaded: true
  });
  return messages.length;
};

// Trading Intelligence Module (inline since no ES6 imports)
const TradingIntelligence = {
  // Enhanced ticker patterns
  TICKER_PATTERNS: {
    // More specific US stock pattern with common prefixes
    US_STOCK: /\b(?:\$)?([A-Z]{1,5})\b(?=[\s,.:;!?]|$)/g,
    // Extended crypto list
    CRYPTO: /\b(BTC|ETH|SOL|DOGE|ADA|DOT|MATIC|LINK|UNI|AVAX|XRP|BNB|SHIB|LUNA|ATOM|FTM|NEAR|ALGO|VET|MANA|SAND|AXS|GALA|LRC|CRO|FIL|AAVE|GRT|SNX|CAKE)\b/gi,
    FOREX: /\b(EUR\/USD|GBP\/USD|USD\/JPY|AUD\/USD|USD\/CAD|EUR\/GBP|NZD\/USD)\b/gi,
    // Options format (e.g., "AAPL 150C", "SPY 400P")
    OPTIONS: /\b([A-Z]{1,5})\s+\d+[CP]\b/g
  },

  // Common words to exclude from ticker detection
  EXCLUDE_WORDS: ['I', 'A', 'THE', 'AND', 'OR', 'UP', 'IT', 'AT', 'BE', 'BY', 'DO', 'GO', 'HE', 'IF', 'IN', 'IS', 'ME', 'MY', 'NO', 'OF', 'ON', 'SO', 'TO', 'WE', 'AM', 'AN', 'AS', 'CAN', 'FOR', 'HAS', 'HIM', 'HIS', 'ITS', 'MAY', 'NOT', 'NOW', 'ONE', 'OUR', 'OUT', 'SHE', 'TOO', 'TWO', 'USE', 'WAS', 'WHO', 'WIN', 'YES', 'YOU', 'ALL', 'ARE', 'BUT', 'DID', 'GET', 'GOT', 'HAD', 'HER', 'HOW', 'LET', 'NEW', 'OLD', 'OWN', 'PUT', 'RUN', 'SAY', 'SEE', 'SET', 'TRY', 'WAY', 'WHY', 'WILL', 'BUY', 'SELL', 'HOLD', 'LONG', 'SHORT', 'CALL', 'PUT', 'IPO', 'CEO', 'CFO', 'ETF', 'EPS', 'P', 'DD', 'YOLO', 'FOMO', 'ATH', 'DIP', 'RSI', 'MACD', 'EMA', 'SMA', 'IV', 'FD', 'WSB', 'SEC', 'FDA', 'USA', 'UK', 'EU', 'AI', 'ML', 'API', 'UI', 'UX', 'PM', 'AM', 'EST', 'PST', 'GMT', 'PDT', 'Q1', 'Q2', 'Q3', 'Q4', 'YTD', 'EOD', 'EOW', 'IMO', 'BTW', 'FYI', 'ASAP', 'FAQ', 'HR', 'IT', 'PR', 'JR', 'SR', 'DR', 'MR', 'MS', 'US', 'OK', 'PC', 'TV', 'DVD', 'USB', 'HTML', 'CSS', 'JS', 'SQL', 'PDF', 'FAQ'],

  // Trading keywords
  TRADING_KEYWORDS: {
    BUY: ['buy', 'buying', 'bought', 'long', 'bullish', 'calls', 'accumulate', 'adding', 'loading', 'grab', 'entered', 'position'],
    SELL: ['sell', 'selling', 'sold', 'short', 'bearish', 'puts', 'dump', 'exit', 'close', 'out of'],
    POSITIVE: ['up', 'gain', 'profit', 'green', 'moon', 'rocket', 'breakout', 'surge', 'rally', 'pump'],
    NEGATIVE: ['down', 'loss', 'red', 'crash', 'dump', 'plunge', 'fall', 'drop', 'tank', 'decline']
  },

  extractEntities(text) {
    const entities = {
      tickers: [],
      prices: [],
      percentages: [],
      quantities: []
    };
    
    // Extract tickers with enhanced detection
    const tickers = new Set();
    
    // Extract US stocks with $ prefix support
    const stockMatches = text.match(this.TICKER_PATTERNS.US_STOCK) || [];
    stockMatches.forEach(match => {
      // Remove $ if present
      const ticker = match.replace('$', '').toUpperCase();
      // Validate: 1-5 chars, not in exclude list, contains at least one uncommon letter
      if (ticker.length >= 2 && ticker.length <= 5 && !this.EXCLUDE_WORDS.includes(ticker)) {
        // Additional validation: should look like a ticker (not all vowels, etc)
        if (!/^[AEIOU]+$/.test(ticker) && !/^[^AEIOU]+$/.test(ticker)) {
          tickers.add(ticker);
        }
      }
    });
    
    // Extract options
    const optionMatches = text.match(this.TICKER_PATTERNS.OPTIONS) || [];
    optionMatches.forEach(match => {
      const ticker = match.split(' ')[0].toUpperCase();
      if (!this.EXCLUDE_WORDS.includes(ticker)) {
        tickers.add(ticker);
      }
    });
    
    // Extract crypto
    const cryptoMatches = text.match(this.TICKER_PATTERNS.CRYPTO) || [];
    cryptoMatches.forEach(ticker => tickers.add(ticker.toUpperCase()));
    
    entities.tickers = Array.from(tickers);
    
    // Extract prices ($123.45)
    const priceMatches = text.match(/\$[\d,]+\.?\d*/g) || [];
    entities.prices = priceMatches;
    
    // Extract percentages (+15%, -3.2%)
    const percentMatches = text.match(/[\+\-]?\d+\.?\d*%/g) || [];
    entities.percentages = percentMatches;
    
    // Extract quantities (1000 shares, 5M)
    const quantityMatches = text.match(/\b\d+[kKmMbB]?\s*(shares?|units?|coins?)\b/gi) || [];
    const millionMatches = text.match(/\b\d+\.?\d*\s*(million|billion|mil|bil)\b/gi) || [];
    entities.quantities = [...quantityMatches, ...millionMatches];
    
    return entities;
  },

  analyzeSentiment(text) {
    const lowerText = text.toLowerCase();
    let score = 0;
    let signals = [];
    
    // Count buy signals
    this.TRADING_KEYWORDS.BUY.forEach(word => {
      if (lowerText.includes(word)) {
        score += 1;
        signals.push(word);
      }
    });
    
    // Count positive words
    this.TRADING_KEYWORDS.POSITIVE.forEach(word => {
      if (lowerText.includes(word)) {
        score += 0.5;
      }
    });
    
    // Count sell signals
    this.TRADING_KEYWORDS.SELL.forEach(word => {
      if (lowerText.includes(word)) {
        score -= 1;
        signals.push(word);
      }
    });
    
    // Count negative words
    this.TRADING_KEYWORDS.NEGATIVE.forEach(word => {
      if (lowerText.includes(word)) {
        score -= 0.5;
      }
    });
    
    // Normalize to -1 to 1
    const normalizedScore = Math.max(-1, Math.min(1, score / 5));
    
    return {
      score: normalizedScore,
      sentiment: normalizedScore > 0.3 ? 'bullish' : normalizedScore < -0.3 ? 'bearish' : 'neutral',
      confidence: Math.min(1, signals.length / 5)
    };
  },

  processMessage(text) {
    const entities = this.extractEntities(text);
    
    // Additional context-based ticker detection
    this.enhanceTickerDetection(text, entities);
    
    const sentiment = this.analyzeSentiment(text);
    
    // Determine trading signal
    let tradingSignal = null;
    const lowerText = text.toLowerCase();
    
    if (entities.tickers.length > 0) {
      if (this.TRADING_KEYWORDS.BUY.some(word => lowerText.includes(word))) {
        tradingSignal = {
          action: 'BUY',
          tickers: entities.tickers,
          strength: sentiment.score > 0.5 ? 'strong' : 'moderate'
        };
      } else if (this.TRADING_KEYWORDS.SELL.some(word => lowerText.includes(word))) {
        tradingSignal = {
          action: 'SELL',
          tickers: entities.tickers,
          strength: sentiment.score < -0.5 ? 'strong' : 'moderate'
        };
      }
    }
    
    return {
      entities,
      sentiment,
      tradingSignal,
      importance: this.calculateImportance(entities, sentiment, tradingSignal)
    };
  },

  calculateImportance(entities, sentiment, tradingSignal) {
    let score = 0;
    if (tradingSignal) score += 3;
    score += Math.min(entities.tickers.length, 2);
    score += entities.prices.length * 0.5;
    if (Math.abs(sentiment.score) > 0.7) score += 2;
    return Math.min(10, score);
  },

  // Enhanced ticker detection using context clues
  enhanceTickerDetection(text, entities) {
    const contextPatterns = [
      // "bought/sold/buying TICKER" pattern
      /(?:bought|sold|buying|selling|long|short|holding|watching)\s+(?:\$)?([A-Z]{2,5})\b/gi,
      // "TICKER to/at $XX" pattern
      /\b([A-Z]{2,5})\s+(?:to|at|near|around|above|below)\s+\$/gi,
      // "TICKER calls/puts" pattern
      /\b([A-Z]{2,5})\s+(?:calls?|puts?|options?)\b/gi,
      // "TICKER earnings/report" pattern
      /\b([A-Z]{2,5})\s+(?:earnings?|reports?|guidance|revenue)\b/gi,
      // "Position in TICKER" pattern
      /(?:position|stake|shares?)\s+(?:in|of)\s+([A-Z]{2,5})\b/gi
    ];
    
    contextPatterns.forEach(pattern => {
      const matches = text.matchAll(pattern);
      for (const match of matches) {
        const ticker = match[1].toUpperCase();
        if (ticker.length >= 2 && ticker.length <= 5 && !this.EXCLUDE_WORDS.includes(ticker)) {
          if (!entities.tickers.includes(ticker)) {
            entities.tickers.push(ticker);
          }
        }
      }
    });
  }
};

// Whitelist of trading/chat sites
const TRADING_CHAT_SITES = [
  'members.julian-komar.com',
  'discord.com',
  'telegram.org',
  'web.whatsapp.com',  // WhatsApp Web support
  'web.telegram.org',   // Telegram Web
  'reddit.com/r/wallstreetbets',
  'reddit.com/r/stocks',
  'reddit.com/r/cryptocurrency',
  'stocktwits.com',
  'tradingview.com',
  'seekingalpha.com'
];

// Check if site is relevant for trading intelligence
function isTradingSite(url) {
  const hostname = new URL(url).hostname;
  const pathname = url.toLowerCase();
  return TRADING_CHAT_SITES.some(site => hostname.includes(site.split('/')[0]) || pathname.includes(site));
}

// Platform-specific selectors with enhanced author detection
const SELECTORS = {
  'julian-komar': {
    message: '[class*="message"]:not(nav):not(header), .comment, div[class*="chat"] > div',
    // Enhanced author selectors for various chat formats
    author: '[class*="author"], [class*="username"], [class*="user"], [class*="sender"], [class*="from"], .name, h3, h4, strong:first-child, b:first-child, [class*="member"], [class*="nick"], [data-author], [data-user], [aria-label*="user"], [aria-label*="author"]',
    content: '[class*="content"], [class*="text"]:not([class*="username"]):not([class*="author"]), .message-body, p',
    container: '[class*="chat"], [class*="messages"], [class*="conversation"], main, #chat, .chat-container'
  },
  'whatsapp': {
    message: '.message-out, .message-in',
    author: '[data-pre-plain-text]',
    content: '[class*="selectable-text"]',
    container: 'div[role="application"]'
  },
  'discord': {
    message: '[id^="chat-messages-"]',
    author: '[class*="username-"]',
    content: '[class*="messageContent-"]',
    container: '[class*="chatContent-"]'
  },
  'reddit': {
    message: '[data-testid="comment"], .Comment, .thing.comment',
    author: '.author, [data-testid="comment_author"]',
    content: '.usertext-body, [data-testid="comment"] p',
    container: '.commentarea, [data-testid="comment-tree"]'
  }
};

// State
let platform = null;
let selectors = null;
let observer = null;
const processedMessages = new Set();
let messageCounter = 0;
let importantMessages = [];

// Initialize
async function initialize() {
  const url = window.location.href;
  
  if (!isTradingSite(url)) {
    console.log('SignalScope: Not a trading/investment site');
    return;
  }
  
  // Detect platform
  const hostname = new URL(url).hostname;
  if (hostname.includes('julian-komar')) platform = 'julian-komar';
  else if (hostname.includes('discord')) platform = 'discord';
  else if (hostname.includes('reddit')) platform = 'reddit';
  else if (hostname.includes('web.whatsapp.com')) platform = 'whatsapp';
  else if (hostname.includes('web.telegram.org')) platform = 'telegram';
  else platform = hostname.split('.')[0];
  
  console.log('Trading platform detected:', platform);
  
  selectors = SELECTORS[platform] || SELECTORS['julian-komar'];
  
  // Notify background
  chrome.runtime.sendMessage({
    type: 'PLATFORM_DETECTED',
    data: { platform, url, hostname }
  });
  
  // Start observing
  startObserving();
  
  // Process existing messages
  setTimeout(processExistingMessages, 1500);
  
  // Periodically send important messages
  setInterval(sendImportantMessages, 10000);
}

// Start DOM observation
function startObserving() {
  const container = document.querySelector(selectors.container) || document.body;
  
  observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === 'childList') {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            processElement(node);
          }
        }
      }
    }
  });
  
  observer.observe(container, {
    childList: true,
    subtree: true
  });
  
  console.log('Observing for trading signals...');
}

// Process element
function processElement(element) {
  if (!element.querySelector) return;
  
  // Check if element is a message
  try {
    if (element.matches && element.matches(selectors.message)) {
      processMessage(element);
    }
    
    // Check for messages within
    const messages = element.querySelectorAll(selectors.message);
    messages.forEach(processMessage);
  } catch (e) {}
}

// Process message with intelligence
function processMessage(messageElement) {
  const elementId = getElementId(messageElement);
  
  if (processedMessages.has(elementId)) return;
  
  processedMessages.add(elementId);
  
  // Enhanced author extraction
  let author = 'Unknown';
  
  // Try multiple strategies to find author
  // Strategy 1: Direct selector
  const authorEl = messageElement.querySelector(selectors.author);
  if (authorEl) {
    author = authorEl.textContent?.trim();
  }
  
  // Strategy 2: Look for author in parent/sibling elements
  if (author === 'Unknown' || !author) {
    const parent = messageElement.parentElement;
    if (parent) {
      const parentAuthor = parent.querySelector(selectors.author);
      if (parentAuthor && parentAuthor !== messageElement) {
        author = parentAuthor.textContent?.trim();
      }
    }
  }
  
  // Strategy 3: Look for author pattern in text (e.g., "John: message")
  if (author === 'Unknown' || !author) {
    const text = messageElement.textContent || '';
    const colonMatch = text.match(/^([A-Za-z0-9_\-\s]+):\s/);
    if (colonMatch && colonMatch[1].length < 30) {
      author = colonMatch[1].trim();
    }
  }
  
  // Strategy 4: Check data attributes
  if (author === 'Unknown' || !author) {
    author = messageElement.getAttribute('data-author') || 
             messageElement.getAttribute('data-user') || 
             messageElement.getAttribute('data-sender') || 
             messageElement.getAttribute('aria-label')?.replace(/.*from |.*by /i, '') || 
             'Unknown';
  }
  
  // Clean up author name
  author = author.replace(/^@/, '').trim();
  if (!author || author.length > 50) author = 'Unknown';
  
  // Extract content (excluding author if it's in the content)
  let content = '';
  const contentEl = messageElement.querySelector(selectors.content);
  if (contentEl) {
    content = contentEl.textContent?.trim() || '';
  } else {
    content = messageElement.textContent?.trim() || '';
  }
  
  // Remove author from content if it's prefixed
  if (author !== 'Unknown' && content.startsWith(author + ':')) {
    content = content.substring(author.length + 1).trim();
  }
  
  // Skip only if textual content is very short and no image attachments present
  const hasImage = messageElement.querySelector('img[src]');
  if ((!content || content.length < 3) && !hasImage) return; // Only skip if really empty
  
  // Apply trading intelligence (but don't filter based on it)
  const intelligence = TradingIntelligence.processMessage(content);
  
  // Log intelligence for debugging but capture ALL messages
  if (intelligence.tradingSignal) {
    console.log('🎯 Trading Signal Detected:', intelligence.tradingSignal);
  }
  console.log(`📊 Message importance: ${intelligence.importance}/10`);
  
  const messageData = {
    id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    platform: platform || 'whatsapp',
    author: author || 'Unknown',
    content: content || '',
    timestamp: new Date().toISOString(),
    url: window.location.href,
    intelligence: intelligence || {
      entities: {
        tickers: [],
        prices: [],
        percentages: [],
        quantities: []
      },
      sentiment: {
        score: 0,
        sentiment: 'neutral',
        confidence: 0.5
      },
      importance: 0
    },
    capturedAt: new Date().toISOString()  // Add this required field
  };
  
  messageCounter++;
  
  // Log important signals
  if (intelligence.tradingSignal) {
    console.log('🎯 Trading Signal Detected:', intelligence.tradingSignal);
    console.log('📊 Tickers:', intelligence.entities.tickers.join(', '));
    console.log('💭 Sentiment:', intelligence.sentiment.sentiment, `(${intelligence.sentiment.score.toFixed(2)})`);
  }
  
  // Queue ALL messages for batch sending (no filtering)
  importantMessages.push(messageData);
  console.log(`📨 Message queued for batch (importance: ${intelligence.importance})`);
  
  // Optionally send immediately if very important (but still keep in batch)
  if (intelligence.importance >= 9) {
    console.log('⚡ Very important message - sending immediately');
    sendToBackground(messageData);
  }
}

// Send message to background
function sendToBackground(messageData) {
  chrome.runtime.sendMessage({
    type: 'CAPTURE_MESSAGE',
    data: messageData
  }, (response) => {
    if (response?.success) {
      console.log('Message sent:', messageData.id);
    }
  });
}

// Send batch of important messages
function sendImportantMessages() {
  if (importantMessages.length === 0) return;
  
  console.log(`Sending batch of ${importantMessages.length} messages`);
  
  // Send as a batch, not individually
  chrome.runtime.sendMessage({
    type: 'CAPTURE_MESSAGE_BATCH',
    data: importantMessages
  }, (response) => {
    if (response?.success) {
      console.log(`Batch of ${importantMessages.length} messages sent successfully`);
    } else {
      console.log('Batch send failed:', response?.error);
    }
  });
  
  importantMessages = [];
}

// Process existing messages
function processExistingMessages() {
  console.log('Scanning for existing trading signals...');
  
  const messages = document.querySelectorAll(selectors.message);
  let tradingSignalsFound = 0;
  
  messages.forEach((message, index) => {
    setTimeout(() => {
      const content = message.textContent || '';
      const intelligence = TradingIntelligence.processMessage(content);
      
      if (intelligence.tradingSignal) {
        tradingSignalsFound++;
        processMessage(message);
      }
    }, index * 50);
  });
  
  setTimeout(() => {
    console.log(`Found ${tradingSignalsFound} messages with trading signals`);
  }, messages.length * 50 + 100);
}

// Get element ID
function getElementId(element) {
  if (element.id) return element.id;
  
  const content = element.textContent || '';
  let hash = 0;
  for (let i = 0; i < Math.min(content.length, 100); i++) {
    hash = ((hash << 5) - hash) + content.charCodeAt(i);
    hash = hash & hash;
  }
  return 'msg-' + Math.abs(hash).toString(36);
}

// Listen for commands
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_STATS') {
    sendResponse({
      success: true,
      data: {
        platform,
        messagesProcessed: processedMessages.size,
        messagesCaptured: messageCounter,
        importantQueued: importantMessages.length
      }
    });
  }
  return true;
});

// Initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}

console.log('SignalScope Trading Intelligence ready! 📈');