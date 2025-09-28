// Simple content script without ES6 modules for Chrome Extension

console.log('SignalScope content script loaded on:', window.location.href);

// Platform detection
function detectPlatform(url) {
  if (url.includes('discord.com')) return 'discord';
  if (url.includes('telegram.org')) return 'telegram';
  if (url.includes('slack.com')) return 'slack';
  if (url.includes('whatsapp.com')) return 'whatsapp';
  return null;
}

// Platform selectors
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
  }
};

// State
let platform = null;
let selectors = null;
let observer = null;
const processedMessages = new Set();

// Initialize
function initialize() {
  platform = detectPlatform(window.location.href);
  
  if (!platform) {
    console.log('Platform not detected');
    return;
  }
  
  console.log('Platform detected:', platform);
  selectors = PLATFORM_SELECTORS[platform];
  
  // Notify background
  chrome.runtime.sendMessage({
    type: 'PLATFORM_DETECTED',
    data: { platform, url: window.location.href }
  });
  
  // Start observing
  startObserving();
  
  // Process existing messages
  processExistingMessages();
}

// Start DOM observation
function startObserving() {
  if (!selectors) return;
  
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
  
  console.log('Started observing container');
}

// Process element for messages
function processElement(element) {
  if (!selectors || !selectors.message) return;
  
  // Check if element is a message
  if (element.matches && element.matches(selectors.message)) {
    processMessage(element);
  }
  
  // Check for messages within element
  const messages = element.querySelectorAll(selectors.message);
  messages.forEach(processMessage);
}

// Process a message element
function processMessage(messageElement) {
  // Generate ID for deduplication
  const elementId = getElementId(messageElement);
  
  if (processedMessages.has(elementId)) {
    return;
  }
  
  processedMessages.add(elementId);
  
  // Parse message data
  const messageData = parseMessage(messageElement);
  
  if (!messageData || !messageData.content) {
    return;
  }
  
  // Send to background
  chrome.runtime.sendMessage({
    type: 'CAPTURE_MESSAGE',
    data: messageData
  }, (response) => {
    if (response && response.success) {
      console.log('Message captured:', response.data.messageId);
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
  if (!selectors) return null;
  
  try {
    const author = element.querySelector(selectors.author)?.textContent?.trim() || 'Unknown';
    const content = element.querySelector(selectors.content)?.textContent?.trim() || '';
    const timestamp = element.querySelector(selectors.timestamp)?.getAttribute('datetime') ||
                     element.querySelector(selectors.timestamp)?.textContent ||
                     new Date().toISOString();
    
    return {
      platform,
      author,
      content,
      timestamp,
      url: window.location.href
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
  
  // Generate hash from content
  const content = element.textContent || '';
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return 'msg-' + Math.abs(hash).toString(36);
}

// Process existing messages on page
function processExistingMessages() {
  if (!selectors || !selectors.message) return;
  
  const messages = document.querySelectorAll(selectors.message);
  console.log(`Found ${messages.length} existing messages`);
  
  messages.forEach((message, index) => {
    // Process in batches with delay
    setTimeout(() => {
      processMessage(message);
    }, index * 10);
  });
}

// Listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_STATS') {
    sendResponse({
      success: true,
      data: {
        platform,
        processedMessages: processedMessages.size,
        isObserving: observer !== null
      }
    });
  }
  return true;
});

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}