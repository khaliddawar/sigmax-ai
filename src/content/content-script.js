import { MESSAGE_TYPES, PLATFORMS } from '../shared/constants.js';
import { detectPlatform, generateId } from '../shared/utils.js';
import { createLogger } from '../shared/logger.js';
import DomObserver from './dom-observer.js';
import MessageParser from './message-parser.js';
import SelectorEngine from './selector-engine.js';
import IntelligenceAnalyzer from '../shared/intelligence-analyzer.js';

const logger = createLogger('ContentScript');

// Set flag to indicate content script is loaded
window.signalScopeContentScript = true;

// Enhanced test function for Circle.so debugging
window.testSignalScope = function() {
  const platform = detectPlatform(window.location.href);
  let messages = [];

  console.log('🔍 SignalScope Circle.so Test Starting...');

  if (platform === 'circle') {
    // Circle.so specific comprehensive test
    const circleSelectors = [
      '[data-testid="message-item"]',
      '[class*="message-"]',
      '.message-container',
      '[role="article"][class*="message"]',
      'div[class*="post-"][class*="item"]'
    ];

    console.log('🎯 Testing Circle.so selectors:');
    circleSelectors.forEach(selector => {
      const found = document.querySelectorAll(selector);
      console.log(`  ${selector}: ${found.length} elements`);
      if (found.length > 0) {
        messages.push(...found);
      }
    });

    // Test containers
    const containers = [
      '[class*="messages-"]',
      '[class*="feed-"]',
      '[class*="timeline-"]',
      '[data-testid="messages-container"]',
      '.message-list'
    ];

    console.log('📦 Circle.so containers found:');
    containers.forEach(selector => {
      const container = document.querySelector(selector);
      console.log(`  ${selector}: ${container ? 'FOUND' : 'not found'}`);
    });

    // Test TipTap editor
    const editors = document.querySelectorAll('.tiptap.ProseMirror, .ProseMirror, [contenteditable="true"]');
    console.log(`✍️ Rich text editors found: ${editors.length}`);

  } else {
    // Generic test for other platforms
    messages = document.querySelectorAll('.message-out, .message-in, [data-testid="message-item"]');
  }

  // Remove duplicates
  const uniqueMessages = [...new Set(messages)];

  const testResult = {
    platform: platform,
    messagesFound: uniqueMessages.length,
    url: window.location.href,
    contentScriptLoaded: true,
    isCircle: platform === 'circle',
    sampleMessage: uniqueMessages.length > 0 ? {
      id: uniqueMessages[0].id,
      classes: uniqueMessages[0].className,
      textPreview: uniqueMessages[0].textContent?.substring(0, 100),
      hasDataTestId: uniqueMessages[0].hasAttribute('data-testid'),
      dataTestId: uniqueMessages[0].getAttribute('data-testid')
    } : null
  };

  console.log('✅ SignalScope Test Results:', testResult);

  // Test message parsing on first message
  if (uniqueMessages.length > 0) {
    try {
      const parser = new MessageParser('circle');
      const parsed = parser.parse(uniqueMessages[0]);
      console.log('📝 Sample parsed message:', parsed);
    } catch (error) {
      console.error('❌ Message parsing error:', error);
    }
  }

  return uniqueMessages.length;
};

// Circle.so specific test function
window.testCircleCapture = function() {
  console.log('🔄 Testing Circle.so message capture...');

  const messages = document.querySelectorAll('[data-testid="message-item"], [class*="message-"]');
  console.log(`Found ${messages.length} potential messages`);

  if (messages.length > 0) {
    const testMessage = messages[0];
    console.log('Testing message element:', testMessage);

    // Test author extraction
    const authorSelectors = [
      '[data-testid="number-of-replies"]',
      '[data-testid="author-name"]',
      '[class*="author-"]',
      '[class*="username-"]',
      '.author-name',
      '.post-author',
      '[class*="member-name"]'
    ];

    console.log('Author extraction test:');
    authorSelectors.forEach(selector => {
      const element = testMessage.querySelector(selector);
      if (element) {
        console.log(`  ✅ ${selector}: "${element.textContent?.trim()}"`);
      }
    });

    // Test content extraction
    const contentSelectors = [
      '[data-testid="message-text"]',
      '[class*="message-content"]',
      '[class*="post-content"]',
      '.tiptap.ProseMirror',
      '[class*="editor-content"]',
      '.message-body'
    ];

    console.log('Content extraction test:');
    contentSelectors.forEach(selector => {
      const element = testMessage.querySelector(selector);
      if (element) {
        console.log(`  ✅ ${selector}: "${element.textContent?.trim().substring(0, 50)}..."`);
      }
    });
  }

  return messages.length;
};

class ContentScript {
  constructor() {
    this.platform = null;
    this.domObserver = null;
    this.messageParser = null;
    this.selectorEngine = null;
    this.intelligenceAnalyzer = new IntelligenceAnalyzer();
    this.isInitialized = false;
    this.processedMessages = new Set();
    this.lastScanTimestamp = 0;
    this.periodicScanInterval = null;
    this.messageDatabase = new Map(); // Store message metadata for comparison
    this.lastKnownMessageCount = 0;
  }

  async initialize() {
    try {
      logger.info('Initializing content script...');
      
      // Detect platform
      this.platform = detectPlatform(window.location.href);
      
      if (!this.platform) {
        logger.warn('Platform not detected, using generic selectors');
        this.platform = 'generic';
      }
      
      logger.info(`Platform detected: ${this.platform}`);
      
      // Notify background about platform detection
      await this.sendToBackground(MESSAGE_TYPES.PLATFORM_DETECTED, {
        platform: this.platform,
        url: window.location.href
      });
      
      // Initialize components
      this.selectorEngine = new SelectorEngine(this.platform);
      this.messageParser = new MessageParser(this.platform);
      this.domObserver = new DomObserver(this.handleDomChange.bind(this));
      
      // Load platform selectors
      await this.selectorEngine.loadSelectors();
      
      // Start observing DOM
      this.startObserving();
      
      // Process existing messages
      await this.processExistingMessages();
      
      // Set up message listener
      this.setupMessageListener();
      
      // Set up unload handler
      this.setupUnloadHandler();

      // Start periodic scanning for missed messages
      this.startPeriodicScan();

      // Set up visibility change handler to catch missed messages on focus
      this.setupVisibilityHandler();

      this.isInitialized = true;
      logger.info('Content script initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize content script:', error);
      throw error;
    }
  }

  startObserving() {
    try {
      // For Circle.so, use enhanced container detection
      let container = null;

      if (this.platform === 'circle') {
        // Circle.so specific container selectors
        const circleContainers = [
          '[class*="messages-"]',
          '[class*="feed-"]',
          '[class*="timeline-"]',
          '[data-testid="messages-container"]',
          '.message-list',
          '[class*="posts-"]',
          '[class*="comments-"]'
        ];

        for (const selector of circleContainers) {
          container = document.querySelector(selector);
          if (container) {
            logger.info('Found Circle.so container:', selector);
            break;
          }
        }
      }

      // Fallback to generic container detection
      if (!container) {
        const containerSelector = this.selectorEngine.getContainerSelector();
        container = document.querySelector(containerSelector);
      }

      if (!container) {
        logger.warn('Chat container not found, observing entire body');
        this.domObserver.observe(document.body);
      } else {
        logger.info('Observing chat container for platform:', this.platform);
        this.domObserver.observe(container);

        // For Circle.so, also observe the main content area for dynamic updates
        if (this.platform === 'circle') {
          const mainContent = document.querySelector('main, [role="main"], .main-content');
          if (mainContent && mainContent !== container) {
            this.domObserver.observe(mainContent);
            logger.info('Also observing Circle.so main content area');
          }
        }
      }
    } catch (error) {
      logger.error('Failed to start observing:', error);
      // Fallback to observing entire body
      this.domObserver.observe(document.body);
    }
  }

  async handleDomChange(mutations) {
    try {
      for (const mutation of mutations) {
        if (mutation.type === 'childList') {
          for (const node of mutation.addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              await this.processElement(node);
            }
          }
        }
      }
    } catch (error) {
      logger.error('Error handling DOM change:', error);
    }
  }

  async processElement(element) {
    try {
      // Check if element is a message
      const messageSelector = this.selectorEngine.getMessageSelector();
      
      if (!messageSelector) {
        return;
      }
      
      let messages = [];
      
      // Check if element itself is a message
      if (element.matches && element.matches(messageSelector)) {
        messages.push(element);
      }
      
      // Check if element contains messages
      const containedMessages = element.querySelectorAll(messageSelector);
      messages.push(...containedMessages);
      
      // Process each message
      for (const messageElement of messages) {
        await this.processMessage(messageElement);
      }
    } catch (error) {
      logger.error('Error processing element:', error);
    }
  }

  async processMessage(messageElement) {
    try {
      // Generate unique ID for the element
      const elementId = this.getElementId(messageElement);
      
      // Check if already processed
      if (this.processedMessages.has(elementId)) {
        return;
      }
      
      // Mark as processed AFTER successful processing to allow retries
      // Parse message data
      const messageData = this.messageParser.parse(messageElement);
      
      // Skip only if message has no textual content *and* no attachments
      if (!messageData || (!messageData.content && (!messageData.attachments || messageData.attachments.length === 0))) {
        logger.debug('Skipping message with no content or attachments');
        // Still mark as processed to avoid retrying empty messages
        this.processedMessages.add(elementId);
        return;
      }
      
      // Analyze message intelligence
      const intelligence = this.intelligenceAnalyzer.analyzeMessage(messageData.content || '');
      
      // Add metadata
      const enrichedMessage = {
        ...messageData,
        id: generateId(),
        platform: this.platform,
        url: window.location.href,
        capturedAt: new Date().toISOString(),
        intelligence
      };
      
      logger.info('Processing message:', {
        author: enrichedMessage.author,
        contentPreview: enrichedMessage.content?.substring(0, 50)
      });
      
      // Send to background
      const result = await this.sendToBackground(MESSAGE_TYPES.CAPTURE_MESSAGE, enrichedMessage);
      
      // Only mark as processed if successfully sent
      if (result) {
        this.processedMessages.add(elementId);
        logger.info('Message sent successfully:', elementId);
      } else {
        logger.warn('Failed to send message, will retry:', elementId);
      }
      
      // Clean up old processed messages (keep last 1000)
      if (this.processedMessages.size > 1000) {
        const oldestItems = Array.from(this.processedMessages).slice(0, 100);
        oldestItems.forEach((item) => this.processedMessages.delete(item));
      }
    } catch (error) {
      logger.error('Error processing message:', error, messageElement);
      // Don't mark as processed on error to allow retry
    }
  }

  getElementId(element) {
    // Try to get existing ID
    if (element.id) {
      return element.id;
    }

    // Try to get data attribute
    const dataId = element.getAttribute('data-message-id') ||
                   element.getAttribute('data-id') ||
                   element.getAttribute('id');

    if (dataId) {
      return dataId;
    }

    // Enhanced ID generation with better uniqueness
    const content = element.textContent?.trim() || '';
    const timestamp = element.querySelector('time')?.getAttribute('datetime') ||
                     element.querySelector('[class*="timestamp"]')?.textContent?.trim() ||
                     '';

    // Include author and position for better uniqueness
    const author = element.querySelector('[class*="author"], [class*="username"]')?.textContent?.trim() || '';
    const position = this.getElementPosition(element);

    const combinedData = `${content}${timestamp}${author}${position}`;
    const hash = this.simpleHash(combinedData);

    return `msg-${hash}`;
  }

  getElementPosition(element) {
    // Get element position in DOM to help with uniqueness
    let position = '';
    let current = element;
    let index = 0;

    while (current && index < 5) { // Limit depth to avoid performance issues
      const siblings = current.parentNode?.children || [];
      const siblingIndex = Array.from(siblings).indexOf(current);
      position = `${siblingIndex}-${position}`;
      current = current.parentNode;
      index++;
    }

    return position;
  }

  simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(36);
  }

  async processExistingMessages() {
    try {
      logger.info('Processing existing messages...');
      
      const messageSelector = this.selectorEngine.getMessageSelector();
      if (!messageSelector) {
        logger.warn('No message selector available');
        return;
      }
      
      const messages = document.querySelectorAll(messageSelector);
      logger.info(`Found ${messages.length} existing messages`);
      
      // Process in batches to avoid blocking
      const batchSize = 10;
      for (let i = 0; i < messages.length; i += batchSize) {
        const batch = Array.from(messages).slice(i, i + batchSize);
        
        await Promise.all(batch.map((msg) => this.processMessage(msg)));
        
        // Small delay between batches
        if (i + batchSize < messages.length) {
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
      }
      
      logger.info('Finished processing existing messages');
    } catch (error) {
      logger.error('Error processing existing messages:', error);
    }
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      this.handleBackgroundMessage(request)
        .then((response) => sendResponse({ success: true, data: response }))
        .catch((error) => {
          logger.error('Message handling error:', error);
          sendResponse({ success: false, error: error.message });
        });
      
      return true; // Async response
    });
  }

  async handleBackgroundMessage(request) {
    const { type, data } = request;
    
    switch (type) {
      case MESSAGE_TYPES.UPDATE_SETTINGS:
        return await this.handleSettingsUpdate(data);
        
      case MESSAGE_TYPES.GET_STATS:
        return this.getStats();
        
      case 'RESET_CAPTURE':
        // Reset processed messages to allow re-capturing
        logger.info('Resetting capture state');
        this.processedMessages.clear();
        // Re-process existing messages
        await this.processExistingMessages();
        return { reset: true, reprocessed: this.processedMessages.size };
        
      default:
        logger.debug('Unknown message type:', type);
        return null;
    }
  }

  async handleSettingsUpdate(settings) {
    logger.info('Settings updated, reloading selectors');
    
    if (settings.platform) {
      this.platform = settings.platform;
      await this.selectorEngine.loadSelectors();
      
      // Restart observation with new selectors
      this.domObserver.disconnect();
      this.startObserving();
    }
    
    return { updated: true };
  }

  getStats() {
    return {
      platform: this.platform,
      processedMessages: this.processedMessages.size,
      isObserving: this.domObserver?.isObserving || false
    };
  }

  async sendToBackground(type, data) {
    try {
      return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type, data }, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (response && !response.success) {
            reject(new Error(response.error || 'Unknown error'));
          } else {
            resolve(response?.data);
          }
        });
      });
    } catch (error) {
      logger.error('Failed to send message to background:', error);
      throw error;
    }
  }

  setupUnloadHandler() {
    window.addEventListener('beforeunload', () => {
      logger.info('Page unloading, cleaning up...');
      this.cleanup();
    });
  }

  startPeriodicScan() {
    // Scan for new messages every 3 seconds
    this.periodicScanInterval = setInterval(async () => {
      await this.scanForMissedMessages();
    }, 3000);

    logger.info('Periodic message scanning started');
  }

  async scanForMissedMessages() {
    try {
      if (!this.selectorEngine || !this.isInitialized) {
        return;
      }

      const messageSelector = this.selectorEngine.getMessageSelector();
      if (!messageSelector) {
        return;
      }

      const currentMessages = document.querySelectorAll(messageSelector);
      const currentCount = currentMessages.length;

      // Check if new messages appeared
      if (currentCount > this.lastKnownMessageCount) {
        logger.info(`Detected ${currentCount - this.lastKnownMessageCount} potential new messages`);

        // Process newer messages that might have been missed
        const potentiallyNewMessages = Array.from(currentMessages).slice(this.lastKnownMessageCount);

        for (const messageElement of potentiallyNewMessages) {
          const elementId = this.getElementId(messageElement);

          // Only process if not already processed
          if (!this.processedMessages.has(elementId)) {
            await this.processMessage(messageElement);
          }
        }

        this.lastKnownMessageCount = currentCount;
      }

      // Additional check for messages with newer timestamps
      await this.checkForOutOfOrderMessages(currentMessages);

    } catch (error) {
      logger.error('Error during periodic scan:', error);
    }
  }

  async checkForOutOfOrderMessages(messages) {
    try {
      const currentTimestamp = Date.now();

      for (const messageElement of messages) {
        const elementId = this.getElementId(messageElement);

        if (this.processedMessages.has(elementId)) {
          continue;
        }

        // Parse the message to get its timestamp
        const messageData = this.messageParser.parse(messageElement);
        if (!messageData) {
          continue;
        }

        const messageTime = new Date(messageData.timestamp).getTime();

        // If message timestamp is recent (within last 30 seconds) and we haven't processed it
        if (currentTimestamp - messageTime < 30000) {
          logger.info('Found potentially missed recent message:', elementId);
          await this.processMessage(messageElement);
        }
      }
    } catch (error) {
      logger.error('Error checking for out-of-order messages:', error);
    }
  }

  setupVisibilityHandler() {
    document.addEventListener('visibilitychange', async () => {
      if (!document.hidden && this.isInitialized) {
        logger.info('Page became visible, scanning for missed messages');
        // Wait a bit for the page to fully load
        setTimeout(async () => {
          await this.scanForMissedMessages();
          await this.processExistingMessages();
        }, 1000);
      }
    });

    // Also handle focus events
    window.addEventListener('focus', async () => {
      if (this.isInitialized) {
        setTimeout(async () => {
          await this.scanForMissedMessages();
        }, 500);
      }
    });

    logger.info('Visibility change handlers set up');
  }

  cleanup() {
    if (this.domObserver) {
      this.domObserver.disconnect();
    }

    if (this.periodicScanInterval) {
      clearInterval(this.periodicScanInterval);
      this.periodicScanInterval = null;
    }

    this.processedMessages.clear();
    this.messageDatabase.clear();
    this.isInitialized = false;

    logger.info('Cleanup completed');
  }
}

// Initialize content script
const contentScript = new ContentScript();

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    contentScript.initialize().catch((error) => {
      console.error('Failed to initialize content script:', error);
    });
  });
} else {
  contentScript.initialize().catch((error) => {
    console.error('Failed to initialize content script:', error);
  });
}

// Export for testing
export default ContentScript;