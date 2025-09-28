import { MESSAGE_TYPES, PLATFORMS } from '../shared/constants.js';
import { detectPlatform, generateId } from '../shared/utils.js';
import { createLogger } from '../shared/logger.js';
import RobustMessageCapture from './robust-message-capture.js';
import IntelligenceAnalyzer from '../shared/intelligence-analyzer.js';

const logger = createLogger('RobustContentScript');

// Set flag to indicate content script is loaded
window.signalScopeContentScript = true;

class RobustContentScript {
  constructor() {
    this.platform = null;
    this.robustCapture = null;
    this.intelligenceAnalyzer = new IntelligenceAnalyzer();
    this.isInitialized = false;
    this.retryAttempts = 0;
    this.maxRetries = 3;
  }

  async initialize() {
    try {
      logger.info('Initializing robust content script...');
      
      // Detect platform
      this.platform = detectPlatform(window.location.href);
      
      if (!this.platform) {
        logger.warn('Platform not detected, using generic approach');
        this.platform = 'generic';
      }
      
      logger.info(`Platform detected: ${this.platform}`);
      
      // Notify background about platform detection
      await this.sendToBackground(MESSAGE_TYPES.PLATFORM_DETECTED, {
        platform: this.platform,
        url: window.location.href
      });
      
      // Initialize robust message capture
      this.robustCapture = new RobustMessageCapture();
      
      // Start robust capture system
      await this.robustCapture.start();
      
      // Set up message listener
      this.setupMessageListener();
      
      // Set up unload handler
      this.setupUnloadHandler();
      
      // Set up page change detection
      this.setupPageChangeDetection();
      
      // Set up periodic health checks
      this.setupPeriodicHealthChecks();
      
      this.isInitialized = true;
      logger.info('Robust content script initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize robust content script:', error);
      await this.handleInitializationError(error);
    }
  }

  async handleInitializationError(error) {
    this.retryAttempts++;
    
    if (this.retryAttempts < this.maxRetries) {
      logger.warn(`Initialization failed, retrying in 5 seconds (attempt ${this.retryAttempts}/${this.maxRetries})`);
      setTimeout(() => {
        this.initialize();
      }, 5000);
    } else {
      logger.error('Max retry attempts reached, falling back to basic mode');
      await this.fallbackToBasicMode();
    }
  }

  async fallbackToBasicMode() {
    try {
      logger.info('Falling back to basic message capture mode');
      
      // Simple polling-based capture as last resort
      setInterval(() => {
        this.scanForMessages();
      }, 3000);
      
      this.isInitialized = true;
    } catch (error) {
      logger.error('Fallback mode also failed:', error);
    }
  }

  setupPageChangeDetection() {
    // Detect page changes (SPA navigation)
    let currentUrl = window.location.href;
    
    const checkForPageChange = () => {
      if (window.location.href !== currentUrl) {
        logger.info('Page change detected, reinitializing...');
        currentUrl = window.location.href;
        this.handlePageChange();
      }
    };

    // Check for URL changes every 2 seconds
    setInterval(checkForPageChange, 2000);

    // Also listen for popstate events
    window.addEventListener('popstate', () => {
      setTimeout(() => this.handlePageChange(), 1000);
    });

    // Listen for pushstate/replacestate (for SPAs)
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function(...args) {
      originalPushState.apply(history, args);
      setTimeout(() => this.handlePageChange(), 1000);
    };

    history.replaceState = function(...args) {
      originalReplaceState.apply(history, args);
      setTimeout(() => this.handlePageChange(), 1000);
    };
  }

  async handlePageChange() {
    try {
      logger.info('Handling page change...');
      
      // Stop current capture
      if (this.robustCapture) {
        await this.robustCapture.stop();
      }
      
      // Wait for page to stabilize
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Reinitialize
      await this.initialize();
    } catch (error) {
      logger.error('Error handling page change:', error);
    }
  }

  setupPeriodicHealthChecks() {
    // Comprehensive health check every 30 seconds
    setInterval(async () => {
      await this.performHealthCheck();
    }, 30000);

    // Light health check every 10 seconds
    setInterval(async () => {
      await this.performLightHealthCheck();
    }, 10000);
  }

  async performHealthCheck() {
    try {
      if (!this.isInitialized) {
        logger.warn('Content script not initialized, attempting recovery...');
        await this.initialize();
        return;
      }

      // Check if robust capture is still active
      if (this.robustCapture && !this.robustCapture.isActive) {
        logger.warn('Robust capture inactive, restarting...');
        await this.robustCapture.start();
      }

      // Check for recent message activity
      const recentActivity = await this.checkRecentActivity();
      if (!recentActivity) {
        logger.warn('No recent message activity detected');
        await this.triggerRecovery();
      }

    } catch (error) {
      logger.error('Health check failed:', error);
      await this.triggerRecovery();
    }
  }

  async performLightHealthCheck() {
    try {
      // Quick check if we can still access the DOM
      const testElement = document.querySelector('body');
      if (!testElement) {
        logger.error('Cannot access DOM, triggering recovery');
        await this.triggerRecovery();
      }
    } catch (error) {
      logger.error('Light health check failed:', error);
    }
  }

  async checkRecentActivity() {
    // Check if we've processed any messages in the last 2 minutes
    const twoMinutesAgo = Date.now() - (2 * 60 * 1000);
    
    // This would need to be implemented based on your activity tracking
    // For now, we'll do a simple DOM check
    const messageElements = document.querySelectorAll('[class*="message"], [data-testid*="message"]');
    return messageElements.length > 0;
  }

  async triggerRecovery() {
    try {
      logger.warn('Triggering recovery sequence...');
      
      // Stop current systems
      if (this.robustCapture) {
        await this.robustCapture.stop();
      }
      
      // Clear processed messages to allow reprocessing
      if (this.robustCapture) {
        this.robustCapture.processedMessages.clear();
      }
      
      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Restart
      await this.initialize();
      
      logger.info('Recovery sequence completed');
    } catch (error) {
      logger.error('Recovery sequence failed:', error);
    }
  }

  async scanForMessages() {
    try {
      // Simple fallback scanning
      const selectors = [
        '[class*="message"]',
        '[data-testid*="message"]',
        '[class*="chat"] > div',
        '[class*="conversation"] > div'
      ];

      for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        for (const element of elements) {
          await this.processElement(element);
        }
      }
    } catch (error) {
      logger.error('Error in fallback scanning:', error);
    }
  }

  async processElement(element) {
    try {
      const elementId = this.getElementId(element);
      
      if (this.processedMessages && this.processedMessages.has(elementId)) {
        return;
      }

      // Simple message parsing
      const content = element.textContent?.trim();
      if (!content || content.length < 3) {
        return;
      }

      const messageData = {
        id: generateId(),
        platform: this.platform,
        author: this.extractAuthor(element) || 'Unknown',
        content: content,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        capturedAt: new Date().toISOString()
      };

      // Analyze intelligence
      messageData.intelligence = this.intelligenceAnalyzer.analyzeMessage(content);

      // Send to background
      await this.sendToBackground(MESSAGE_TYPES.CAPTURE_MESSAGE, messageData);

      // Mark as processed
      if (this.processedMessages) {
        this.processedMessages.add(elementId);
      }

    } catch (error) {
      logger.error('Error processing element:', error);
    }
  }

  extractAuthor(element) {
    // Try to find author in various ways
    const authorSelectors = [
      '[class*="author"]',
      '[class*="username"]',
      '[class*="sender"]',
      '[data-testid*="author"]',
      '[data-testid*="username"]'
    ];

    for (const selector of authorSelectors) {
      const authorEl = element.querySelector(selector);
      if (authorEl?.textContent?.trim()) {
        return authorEl.textContent.trim();
      }
    }

    // Try parent elements
    let parent = element.parentElement;
    for (let i = 0; i < 3 && parent; i++) {
      for (const selector of authorSelectors) {
        const authorEl = parent.querySelector(selector);
        if (authorEl?.textContent?.trim()) {
          return authorEl.textContent.trim();
        }
      }
      parent = parent.parentElement;
    }

    return null;
  }

  getElementId(element) {
    if (element.id) return element.id;
    
    const dataId = element.getAttribute('data-message-id') || 
                   element.getAttribute('data-id') ||
                   element.getAttribute('id');
    
    if (dataId) return dataId;
    
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
      hash = hash & hash;
    }
    return Math.abs(hash).toString(36);
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
        logger.info('Resetting capture state');
        if (this.robustCapture) {
          this.robustCapture.processedMessages.clear();
          await this.robustCapture.stop();
          await this.robustCapture.start();
        }
        return { reset: true };
        
      case 'FORCE_RECOVERY':
        await this.triggerRecovery();
        return { recovery: true };
        
      default:
        logger.debug('Unknown message type:', type);
        return null;
    }
  }

  async handleSettingsUpdate(settings) {
    logger.info('Settings updated');
    
    if (settings.platform && settings.platform !== this.platform) {
      this.platform = settings.platform;
      await this.handlePageChange();
    }
    
    return { updated: true };
  }

  getStats() {
    return {
      platform: this.platform,
      isInitialized: this.isInitialized,
      robustCaptureActive: this.robustCapture?.isActive || false,
      processedMessages: this.robustCapture?.processedMessages?.size || 0,
      retryAttempts: this.retryAttempts
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

  async cleanup() {
    if (this.robustCapture) {
      await this.robustCapture.stop();
    }
    
    this.isInitialized = false;
    logger.info('Cleanup completed');
  }
}

// Initialize robust content script
const robustContentScript = new RobustContentScript();

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    robustContentScript.initialize().catch((error) => {
      console.error('Failed to initialize robust content script:', error);
    });
  });
} else {
  robustContentScript.initialize().catch((error) => {
    console.error('Failed to initialize robust content script:', error);
  });
}

// Export for debugging
window.signalScopeRobust = robustContentScript;
