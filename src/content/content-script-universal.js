// Universal content script for SignalScope - works on ANY website

console.log('SignalScope content script loaded on:', window.location.href);

// Platform detection with support for ANY site
function detectPlatform(url) {
  if (url.includes('discord.com')) return 'discord';
  if (url.includes('telegram.org')) return 'telegram';
  if (url.includes('slack.com')) return 'slack';
  if (url.includes('whatsapp.com')) return 'whatsapp';
  if (url.includes('julian-komar.com')) return 'julian-komar';
  
  // For any other site, use the domain as platform name
  try {
    const hostname = new URL(url).hostname;
    return hostname.replace('www.', '').split('.')[0];
  } catch {
    return 'unknown';
  }
}

// Generic selectors that work on most chat/forum sites
const GENERIC_SELECTORS = {
  // Try multiple common patterns for messages
  message: [
    '[class*="message"]',
    '[class*="chat-message"]',
    '[class*="comment"]',
    '[class*="post"]',
    '[data-message]',
    '[data-comment]',
    '.message',
    '.comment',
    '.post',
    'article',
    '[role="article"]',
    '[role="listitem"]'
  ].join(', '),
  
  // Common patterns for authors
  author: [
    '[class*="author"]',
    '[class*="username"]',
    '[class*="user-name"]',
    '[class*="sender"]',
    '[class*="from"]',
    '[class*="name"]',
    '.author',
    '.username',
    '.user',
    '.name',
    '[data-author]',
    '[data-user]',
    'h3',
    'h4',
    'strong'
  ].join(', '),
  
  // Common patterns for content
  content: [
    '[class*="content"]',
    '[class*="text"]',
    '[class*="body"]',
    '.content',
    '.text',
    '.body',
    'p',
    'span'
  ].join(', '),
  
  // Common patterns for time
  timestamp: [
    'time',
    '[datetime]',
    '[class*="time"]',
    '[class*="date"]',
    '[class*="timestamp"]',
    '.time',
    '.date',
    '.timestamp',
    '[data-time]',
    '[data-timestamp]'
  ].join(', '),
  
  // Common containers
  container: 'body'
};

// Platform-specific selectors (keeping existing ones)
const PLATFORM_SELECTORS = {
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
  slack: {
    message: '[data-qa="message_container"]',
    author: '[data-qa="message_sender"]',
    content: '[data-qa="message_content"]',
    timestamp: '[data-qa="message_time"]',
    container: '[data-qa="message_list"]'
  },
  whatsapp: {
    message: '[class*="message-"]',
    author: '[class*="copyable-text"][data-pre-plain-text]',
    content: '[class*="copyable-text"] span',
    timestamp: '[class*="copyable-text"][data-pre-plain-text]',
    container: '[class*="conversation-panel-messages"]'
  },
  'julian-komar': {
    // Specific selectors for julian-komar.com community chat
    message: '.chat-message-container, .chat-message, [class*="message"], .comment, div[data-message-id], div[class*="chat"] > div',
    author: '.chat-message-author, .author-name, [class*="author"], [class*="user"], .username, strong',
    content: '.chat-message-content, .message-content, [class*="content"], [class*="text"], .text, p',
    timestamp: '.chat-message-time, time, [class*="time"], [class*="timestamp"], [class*="date"]',
    container: '.chat-container, .messages-container, [class*="chat"], [class*="messages"], #chat, main'
  }
};

// State
let platform = null;
let selectors = null;
let observer = null;
const processedMessages = new Set();
let messageCounter = 0;

// Initialize
function initialize() {
  platform = detectPlatform(window.location.href);
  console.log('Platform detected:', platform);
  
  // Use platform-specific selectors if available, otherwise use generic
  selectors = PLATFORM_SELECTORS[platform] || GENERIC_SELECTORS;
  
  // Notify background
  chrome.runtime.sendMessage({
    type: 'PLATFORM_DETECTED',
    data: { 
      platform, 
      url: window.location.href,
      hostname: window.location.hostname
    }
  });
  
  // Start observing
  startObserving();
  
  // Process existing messages
  setTimeout(() => {
    processExistingMessages();
  }, 1000);
  
  // Auto-detect messages if none found initially
  setTimeout(() => {
    if (messageCounter === 0) {
      console.log('No messages found with current selectors, trying auto-detection...');
      autoDetectMessages();
    }
  }, 3000);
}

// Start DOM observation
function startObserving() {
  // Try to find the best container
  let container = document.body;
  
  if (selectors.container && selectors.container !== 'body') {
    const possibleContainers = selectors.container.split(', ');
    for (const selector of possibleContainers) {
      const found = document.querySelector(selector);
      if (found) {
        container = found;
        console.log('Using container:', selector);
        break;
      }
    }
  }
  
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
  if (!element || !element.querySelector) return;
  
  // Try to find messages
  const messageSelectors = selectors.message.split(', ');
  
  for (const selector of messageSelectors) {
    try {
      // Check if element itself matches
      if (element.matches && element.matches(selector)) {
        processMessage(element);
        break;
      }
      
      // Check for messages within element
      const messages = element.querySelectorAll(selector);
      if (messages.length > 0) {
        messages.forEach(processMessage);
        break;
      }
    } catch (e) {
      // Invalid selector, skip
    }
  }
}

// Process a message element
function processMessage(messageElement) {
  // Generate ID for deduplication
  const elementId = getElementId(messageElement);
  
  if (processedMessages.has(elementId)) {
    return;
  }
  
  processedMessages.add(elementId);
  messageCounter++;
  
  // Parse message data
  const messageData = parseMessage(messageElement);
  
  if (!messageData || !messageData.content) {
    return;
  }
  
  console.log('Captured message:', messageData);
  
  // Send to background
  chrome.runtime.sendMessage({
    type: 'CAPTURE_MESSAGE',
    data: messageData
  }, (response) => {
    if (response && response.success) {
      console.log('Message sent to webhook:', response.data.messageId);
    }
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
    // Try to find author
    let author = 'Unknown';
    const authorSelectors = selectors.author.split(', ');
    for (const selector of authorSelectors) {
      try {
        const authorEl = element.querySelector(selector);
        if (authorEl && authorEl.textContent) {
          author = authorEl.textContent.trim();
          if (author) break;
        }
      } catch (e) {}
    }
    
    // Try to find content
    let content = '';
    const contentSelectors = selectors.content.split(', ');
    for (const selector of contentSelectors) {
      try {
        const contentEl = element.querySelector(selector);
        if (contentEl && contentEl.textContent) {
          content = contentEl.textContent.trim();
          if (content) break;
        }
      } catch (e) {}
    }
    
    // If no content found, try the element itself
    if (!content) {
      content = element.textContent?.trim() || '';
    }
    
    // Try to find timestamp
    let timestamp = new Date().toISOString();
    const timeSelectors = selectors.timestamp.split(', ');
    for (const selector of timeSelectors) {
      try {
        const timeEl = element.querySelector(selector);
        if (timeEl) {
          timestamp = timeEl.getAttribute('datetime') ||
                     timeEl.getAttribute('title') ||
                     timeEl.textContent ||
                     timestamp;
          break;
        }
      } catch (e) {}
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

// Auto-detect messages when selectors don't work
function autoDetectMessages() {
  console.log('Running auto-detection...');
  
  // Look for any element with text content that looks like a message
  const allElements = document.querySelectorAll('*');
  const potentialMessages = [];
  
  allElements.forEach(el => {
    // Skip if too high in DOM tree
    if (el === document.body || el === document.documentElement) return;
    
    // Skip scripts, styles, etc.
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'META', 'LINK'].includes(el.tagName)) return;
    
    // Check if element has reasonable text content
    const text = el.textContent?.trim();
    if (text && text.length > 10 && text.length < 5000) {
      // Check if it's not a parent of another potential message
      const hasChildMessages = Array.from(el.children).some(child => 
        child.textContent && child.textContent.trim().length > 10
      );
      
      if (!hasChildMessages) {
        potentialMessages.push(el);
      }
    }
  });
  
  console.log(`Found ${potentialMessages.length} potential messages`);
  
  // Process potential messages
  potentialMessages.slice(0, 50).forEach(el => {
    processMessage(el);
  });
}

// Get unique ID for element
function getElementId(element) {
  if (element.id) return element.id;
  
  const dataId = element.getAttribute('data-message-id') || 
                 element.getAttribute('data-id') ||
                 element.getAttribute('data-key');
  if (dataId) return dataId;
  
  // Generate hash from content and position
  const content = element.textContent || '';
  const position = Array.from(element.parentNode?.children || []).indexOf(element);
  let hash = 0;
  const str = content + position;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return 'msg-' + Math.abs(hash).toString(36);
}

// Process existing messages on page
function processExistingMessages() {
  console.log('Looking for existing messages...');
  
  const messageSelectors = selectors.message.split(', ');
  let allMessages = new Set();
  
  // Try each selector and collect ALL unique messages
  for (const selector of messageSelectors) {
    try {
      const messages = document.querySelectorAll(selector);
      if (messages.length > 0) {
        console.log(`Found ${messages.length} elements with selector: ${selector}`);
        messages.forEach(msg => allMessages.add(msg));
      }
    } catch (e) {
      // Invalid selector, continue
    }
  }
  
  console.log(`Total unique messages found: ${allMessages.size}`);
  
  // Process all unique messages
  let index = 0;
  allMessages.forEach((message) => {
    setTimeout(() => {
      processMessage(message);
    }, index * 100); // Space them out more
    index++;
  });
  
  if (allMessages.size === 0) {
    console.log('No messages found with predefined selectors');
  }
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
        isObserving: observer !== null
      }
    });
  } else if (request.type === 'CAPTURE_ALL') {
    console.log('Manual capture all messages triggered');
    processedMessages.clear(); // Clear to re-process all
    processExistingMessages();
    sendResponse({ success: true, message: 'Capturing all messages' });
  }
  return true;
});

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}

console.log('SignalScope ready to capture messages from any website!');