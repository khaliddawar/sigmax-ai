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

// Add test function for debugging
window.testSignalScope = function() {
  const platform = detectPlatform(window.location.href);
  let messages = [];
  
  // Test different selectors based on detected platform
  if (platform === 'circle' || platform === 'webchat') {
    messages = document.querySelectorAll('[data-testid="message-item"], .message-item, [class*="message-"][class*="item"]');
  } else {
    messages = document.querySelectorAll('.message-out, .message-in');
  }
  
  console.log('SignalScope Test:', {
    platform: platform,
    messagesFound: messages.length,
    url: window.location.href,
    contentScriptLoaded: true,
    sampleMessage: messages.length > 0 ? {
      id: messages[0].id,
      classes: messages[0].className,
      textPreview: messages[0].textContent?.substring(0, 100)
    } : null
  });
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
      
      this.isInitialized = true;
      logger.info('Content script initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize content script:', error);
      throw error;
    }
  }

  startObserving() {
    try {
      // Get the chat container selector
      const containerSelector = this.selectorEngine.getContainerSelector();
      const container = document.querySelector(containerSelector);
      
      if (!container) {
        logger.warn('Chat container not found, observing entire body');
        this.domObserver.observe(document.body);
      } else {
        logger.info('Observing chat container:', containerSelector);
        this.domObserver.observe(container);
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
    
    // Generate ID based on content hash
    const content = element.textContent || '';
    const timestamp = element.querySelector('time')?.getAttribute('datetime') || '';
    const hash = this.simpleHash(content + timestamp);
    
    return `msg-${hash}`;
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

  cleanup() {
    if (this.domObserver) {
      this.domObserver.disconnect();
    }
    
    this.processedMessages.clear();
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