// Smart content script for SignalScope - only captures from actual chat/community sites

console.log('SignalScope content script loaded on:', window.location.href);

// Whitelist of domains that are known chat/community sites
const CHAT_DOMAINS = [
  'discord.com',
  'telegram.org',
  'slack.com',
  'whatsapp.com',
  'members.julian-komar.com',
  'chat.openai.com',
  'claude.ai',
  'teams.microsoft.com',
  'messenger.com',
  'gitter.im',
  'reddit.com', // comments
  'twitch.tv', // chat
  'youtube.com' // live chat
];

// Check if current site is a chat site
function isChatSite(url) {
  const hostname = new URL(url).hostname;
  return CHAT_DOMAINS.some(domain => hostname.includes(domain));
}

// Check if current page looks like a chat interface
function looksLikeChatPage() {
  // Look for chat-specific indicators
  const chatIndicators = [
    'chat', 'message', 'conversation', 'discussion',
    'comment', 'reply', 'post', 'thread'
  ];
  
  // Check URL path
  const path = window.location.pathname.toLowerCase();
  const hasPathIndicator = chatIndicators.some(indicator => path.includes(indicator));
  
  // Check page title
  const title = document.title.toLowerCase();
  const hasTitleIndicator = chatIndicators.some(indicator => title.includes(indicator));
  
  // Check for chat-like elements
  const hasChatElements = document.querySelector('[class*="chat"], [class*="message"], [class*="comment"], [id*="chat"], [id*="message"]');
  
  return hasPathIndicator || hasTitleIndicator || hasChatElements;
}

// Platform detection
function detectPlatform(url) {
  const hostname = new URL(url).hostname;
  
  if (hostname.includes('discord.com')) return 'discord';
  if (hostname.includes('telegram.org')) return 'telegram';
  if (hostname.includes('slack.com')) return 'slack';
  if (hostname.includes('whatsapp.com')) return 'whatsapp';
  if (hostname.includes('julian-komar.com')) return 'julian-komar';
  if (hostname.includes('reddit.com')) return 'reddit';
  if (hostname.includes('youtube.com')) return 'youtube';
  
  return hostname.replace('www.', '').split('.')[0];
}

// Platform-specific selectors
const PLATFORM_SELECTORS = {
  'julian-komar': {
    message: '.chat-message, [class*="message"]:not(nav):not(header):not(footer)',
    author: '.author-name, [class*="author"], .username',
    content: '.message-content, [class*="content"] p, .text',
    timestamp: 'time, [class*="time"]',
    container: '.chat-container, [class*="chat"], main'
  },
  discord: {
    message: '[id^="chat-messages-"]',
    author: '[class*="username-"]',
    content: '[class*="messageContent-"]',
    timestamp: 'time[datetime]',
    container: '[class*="chatContent-"]'
  },
  telegram: {
    message: '.message',
    author: '.message-title',
    content: '.message-text',
    timestamp: '.message-time',
    container: '.messages-container'
  },
  reddit: {
    message: '[data-testid="comment"], .Comment',
    author: '[data-testid="comment_author"], .author',
    content: '[data-testid="comment"] p, .Comment p',
    timestamp: 'time, [data-testid="comment_timestamp"]',
    container: '[data-testid="comment-tree"], .commentarea'
  }
};

// State
let platform = null;
let selectors = null;
let observer = null;
let isEnabled = false;
const processedMessages = new Set();
let messageCounter = 0;

// Initialize
async function initialize() {
  const url = window.location.href;
  
  // Check if we should activate on this site
  const shouldActivate = await checkIfShouldActivate(url);
  
  if (!shouldActivate) {
    console.log('SignalScope: Not a chat site or disabled for this domain');
    return;
  }
  
  platform = detectPlatform(url);
  console.log('Platform detected:', platform);
  
  // Use platform-specific selectors or generic ones
  selectors = PLATFORM_SELECTORS[platform] || {
    message: '[class*="message"]:not(nav):not(header):not(footer), .comment:not(nav):not(header)',
    author: '[class*="author"], [class*="user"], .username',
    content: '[class*="content"] p, [class*="text"], .body',
    timestamp: 'time, [class*="time"]',
    container: 'main, #root, .container'
  };
  
  isEnabled = true;
  
  // Notify background
  chrome.runtime.sendMessage({
    type: 'PLATFORM_DETECTED',
    data: { 
      platform, 
      url,
      hostname: window.location.hostname,
      enabled: isEnabled
    }
  });
  
  // Start observing
  startObserving();
  
  // Process existing messages after a delay
  setTimeout(() => {
    processExistingMessages();
  }, 1500);
}

// Check if we should activate on this site
async function checkIfShouldActivate(url) {
  // First check if it's a known chat site
  if (!isChatSite(url)) {
    return false;
  }
  
  // Check if it looks like a chat page
  if (!looksLikeChatPage()) {
    console.log('Not a chat page on this site');
    return false;
  }
  
  // Check if user has disabled this domain
  try {
    const hostname = new URL(url).hostname;
    const result = await chrome.storage.local.get(`disabled_${hostname}`);
    if (result[`disabled_${hostname}`]) {
      console.log('SignalScope disabled for this domain');
      return false;
    }
  } catch (error) {
    console.error('Error checking domain settings:', error);
  }
  
  return true;
}

// Start DOM observation
function startObserving() {
  if (!selectors || !isEnabled) return;
  
  let container = document.querySelector(selectors.container) || document.body;
  
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
  
  console.log('Started observing container');
}

// Process element for messages
function processElement(element) {
  if (!selectors || !isEnabled || !element.querySelector) return;
  
  // Check if element matches message selector
  try {
    if (element.matches && element.matches(selectors.message)) {
      if (isValidMessage(element)) {
        processMessage(element);
      }
    }
    
    // Check for messages within element
    const messages = element.querySelectorAll(selectors.message);
    messages.forEach(msg => {
      if (isValidMessage(msg)) {
        processMessage(msg);
      }
    });
  } catch (e) {
    // Selector error
  }
}

// Check if element is a valid message
function isValidMessage(element) {
  // Get text content
  const text = element.textContent?.trim() || '';
  
  // Filter out too short content
  if (text.length < 5) return false;
  
  // Filter out navigation/UI elements
  if (text.length < 20 && (
    text === 'Reply' || 
    text === 'Share' || 
    text === 'Edit' || 
    text === 'Delete' ||
    text === 'Like' ||
    text.startsWith('/') ||
    text === 'yt-dlp' ||
    /^[A-Z][a-z]+$/.test(text) // Single words like "Home", "About"
  )) {
    return false;
  }
  
  // Filter out error messages
  if (text.includes("You can't perform that action") ||
      text.includes("Error") ||
      text.includes("Loading")) {
    return false;
  }
  
  // Check if it's in a navigation or header
  const parent = element.closest('nav, header, footer, aside');
  if (parent) return false;
  
  return true;
}

// Process a message element
function processMessage(messageElement) {
  const elementId = getElementId(messageElement);
  
  if (processedMessages.has(elementId)) {
    return;
  }
  
  processedMessages.add(elementId);
  
  const messageData = parseMessage(messageElement);
  
  if (!messageData || !messageData.content || messageData.content.length < 5) {
    return;
  }
  
  messageCounter++;
  console.log('Captured message:', messageData.content.substring(0, 50) + '...');
  
  // Send to background
  chrome.runtime.sendMessage({
    type: 'CAPTURE_MESSAGE',
    data: messageData
  });
  
  // Clean up old processed messages
  if (processedMessages.size > 1000) {
    const oldestItems = Array.from(processedMessages).slice(0, 100);
    oldestItems.forEach(item => processedMessages.delete(item));
  }
}

// Parse message from element
function parseMessage(element) {
  try {
    let author = 'Unknown';
    if (selectors.author) {
      const authorEl = element.querySelector(selectors.author);
      if (authorEl) {
        author = authorEl.textContent?.trim() || 'Unknown';
      }
    }
    
    let content = '';
    if (selectors.content) {
      const contentEl = element.querySelector(selectors.content);
      content = contentEl?.textContent?.trim() || element.textContent?.trim() || '';
    } else {
      content = element.textContent?.trim() || '';
    }
    
    let timestamp = new Date().toISOString();
    if (selectors.timestamp) {
      const timeEl = element.querySelector(selectors.timestamp);
      if (timeEl) {
        timestamp = timeEl.getAttribute('datetime') ||
                   timeEl.getAttribute('title') ||
                   timeEl.textContent ||
                   timestamp;
      }
    }
    
    return {
      platform,
      author,
      content,
      timestamp,
      url: window.location.href,
      hostname: window.location.hostname
    };
  } catch (error) {
    console.error('Error parsing message:', error);
    return null;
  }
}

// Get unique ID for element
function getElementId(element) {
  if (element.id) return element.id;
  
  const dataId = element.getAttribute('data-message-id') || 
                 element.getAttribute('data-id');
  if (dataId) return dataId;
  
  const content = element.textContent || '';
  let hash = 0;
  for (let i = 0; i < Math.min(content.length, 100); i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return 'msg-' + Math.abs(hash).toString(36);
}

// Process existing messages on page
function processExistingMessages() {
  if (!selectors || !isEnabled) return;
  
  console.log('Looking for existing messages...');
  
  const messages = document.querySelectorAll(selectors.message);
  let validCount = 0;
  
  messages.forEach((message, index) => {
    if (isValidMessage(message)) {
      validCount++;
      setTimeout(() => {
        processMessage(message);
      }, index * 100);
    }
  });
  
  console.log(`Found ${validCount} valid messages out of ${messages.length} elements`);
}

// Listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_STATS') {
    sendResponse({
      success: true,
      data: {
        platform,
        processedMessages: processedMessages.size,
        messagesCaptured: messageCounter,
        isObserving: observer !== null,
        isEnabled
      }
    });
  } else if (request.type === 'TOGGLE_CAPTURE') {
    isEnabled = !isEnabled;
    console.log(`SignalScope ${isEnabled ? 'enabled' : 'disabled'} for this site`);
    
    if (isEnabled && !observer) {
      startObserving();
      processExistingMessages();
    } else if (!isEnabled && observer) {
      observer.disconnect();
      observer = null;
    }
    
    sendResponse({ success: true, enabled: isEnabled });
  }
  return true;
});

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}