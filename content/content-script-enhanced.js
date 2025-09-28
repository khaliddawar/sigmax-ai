/**
 * Enhanced Content Script with Hybrid Capture System
 * 
 * This integrates the enhanced capture system (DOM + Network + WebSocket + SSE)
 * into the main SignalScope extension for maximum reliability.
 */

import { MESSAGE_TYPES, PLATFORMS } from '../shared/constants.js';
import { detectPlatform, generateId } from '../shared/utils.js';
import { createLogger } from '../shared/logger.js';
import HybridCapture from './hybrid-capture.js';
import IntelligenceAnalyzer from '../shared/intelligence-analyzer.js';

const logger = createLogger('EnhancedContentScript');

// Set flag to indicate enhanced content script is loaded
window.signalScopeEnhancedContentScript = true;

// Add test function for debugging
window.testSignalScopeEnhanced = function() {
  const platform = detectPlatform(window.location.href);
  let messages = [];
  
  // Test different selectors based on detected platform
  if (platform === 'circle' || platform === 'webchat') {
    messages = document.querySelectorAll('[data-testid="message-item"], .message-item, [class*="message-"][class*="item"]');
  } else if (platform === 'telegram') {
    messages = document.querySelectorAll('.message-out, .message-in, .message');
  } else if (platform === 'discord') {
    messages = document.querySelectorAll('[class*="message"], [data-list-item-id*="chat-messages"]');
  } else if (platform === 'slack') {
    messages = document.querySelectorAll('[data-qa="message_container"], .c-virtual_list__item');
  } else if (platform === 'whatsapp') {
    messages = document.querySelectorAll('[data-testid="msg-container"], .message-in, .message-out');
  } else {
    messages = document.querySelectorAll('.message-out, .message-in, [class*="message"]');
  }
  
  console.log('SignalScope Enhanced Test:', {
    platform: platform,
    messagesFound: messages.length,
    url: window.location.href,
    enhancedContentScriptLoaded: true,
    captureSystemActive: window.signalScopeEnhanced?.isActive || false,
    sampleMessage: messages.length > 0 ? {
      id: messages[0].id,
      classes: messages[0].className,
      textPreview: messages[0].textContent?.substring(0, 100)
    } : null
  });
  return messages.length;
};

class EnhancedContentScript {
  constructor() {
    this.platform = null;
    this.hybridCapture = null;
    this.intelligenceAnalyzer = new IntelligenceAnalyzer();
    this.isInitialized = false;
    this.isEnabled = false;
    this.messageHandlers = [];
  }

  async initialize() {
    try {
      logger.info('Initializing enhanced content script...');
      
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
        url: window.location.href,
        enhanced: true
      });
      
      // Initialize hybrid capture system
      this.hybridCapture = new HybridCapture();
      await this.hybridCapture.initialize(this.platform);
      
      // Set up message handler
      this.hybridCapture.addMessageHandler(this.handleCapturedMessage.bind(this));
      
      // Set up message listener for background communication
      this.setupMessageListener();
      
      // Set up unload handler
      this.setupUnloadHandler();
      
      // Make available globally for debugging
      window.signalScopeEnhanced = this;
      
      this.isInitialized = true;
      logger.info('Enhanced content script initialized successfully');
      
      // Auto-start capture if enabled
      await this.checkAndStartCapture();
      
    } catch (error) {
      logger.error('Failed to initialize enhanced content script:', error);
      throw error;
    }
  }

  async checkAndStartCapture() {
    try {
      // Check if extension is enabled
      const settings = await this.getSettings();
      if (settings.enabled) {
        await this.startCapture();
      }
    } catch (error) {
      logger.error('Error checking capture settings:', error);
    }
  }

  async startCapture() {
    try {
      if (!this.isInitialized) {
        logger.warn('Content script not initialized, cannot start capture');
        return;
      }

      if (this.isEnabled) {
        logger.warn('Capture already active');
        return;
      }

      logger.info('Starting enhanced capture system...');
      
      // Start hybrid capture
      await this.hybridCapture.startCapture();
      
      this.isEnabled = true;
      
      // Notify background
      await this.sendToBackground(MESSAGE_TYPES.CAPTURE_STARTED, {
        platform: this.platform,
        mode: this.hybridCapture.captureMode,
        enhanced: true
      });
      
      logger.info('Enhanced capture system started successfully');
      
    } catch (error) {
      logger.error('Failed to start capture:', error);
      throw error;
    }
  }

  async stopCapture() {
    try {
      if (!this.isEnabled) {
        logger.warn('Capture not active');
        return;
      }

      logger.info('Stopping enhanced capture system...');
      
      // Stop hybrid capture
      await this.hybridCapture.stop();
      
      this.isEnabled = false;
      
      // Notify background
      await this.sendToBackground(MESSAGE_TYPES.CAPTURE_STOPPED, {
        platform: this.platform,
        enhanced: true
      });
      
      logger.info('Enhanced capture system stopped');
      
    } catch (error) {
      logger.error('Failed to stop capture:', error);
      throw error;
    }
  }

  async handleCapturedMessage(message, context) {
    try {
      logger.debug('Message captured via enhanced system:', message);
      
      // Add intelligence analysis
      const intelligence = await this.intelligenceAnalyzer.analyze(message);
      
      // Enrich message with intelligence
      const enrichedMessage = {
        ...message,
        intelligence,
        captureMethod: context.source,
        captureMode: context.mode || 'hybrid'
      };
      
      // Send to background for webhook delivery
      await this.sendToBackground(MESSAGE_TYPES.CAPTURE_MESSAGE, enrichedMessage);
      
      // Notify handlers
      this.messageHandlers.forEach(handler => {
        try {
          handler(enrichedMessage, context);
        } catch (error) {
          logger.error('Error in message handler:', error);
        }
      });
      
    } catch (error) {
      logger.error('Error handling captured message:', error);
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
      case MESSAGE_TYPES.START_CAPTURE:
        await this.startCapture();
        return { started: true };
        
      case MESSAGE_TYPES.STOP_CAPTURE:
        await this.stopCapture();
        return { stopped: true };
        
      case MESSAGE_TYPES.UPDATE_SETTINGS:
        return await this.handleSettingsUpdate(data);
        
      case MESSAGE_TYPES.GET_STATS:
        return this.getStats();
        
      case MESSAGE_TYPES.TEST_CAPTURE:
        return await this.testCapture();
        
      default:
        logger.debug('Unknown message type:', type);
        return null;
    }
  }

  async handleSettingsUpdate(settings) {
    logger.info('Settings updated, reloading capture system');
    
    if (settings.enabled !== undefined) {
      if (settings.enabled && !this.isEnabled) {
        await this.startCapture();
      } else if (!settings.enabled && this.isEnabled) {
        await this.stopCapture();
      }
    }
    
    return { updated: true };
  }

  async testCapture() {
    try {
      logger.info('Testing enhanced capture system...');
      
      // Test DOM capture
      const testMessage = {
        id: 'test-' + generateId(),
        content: 'Test message from enhanced capture system',
        author: 'Test User',
        timestamp: new Date().toISOString(),
        platform: this.platform,
        source: 'test'
      };
      
      await this.handleCapturedMessage(testMessage, { source: 'test' });
      
      return { 
        success: true, 
        message: 'Enhanced capture test completed',
        stats: this.getStats()
      };
      
    } catch (error) {
      logger.error('Capture test failed:', error);
      return { 
        success: false, 
        error: error.message 
      };
    }
  }

  getStats() {
    const captureStats = this.hybridCapture ? this.hybridCapture.getStats() : {};
    
    return {
      platform: this.platform,
      isInitialized: this.isInitialized,
      isEnabled: this.isEnabled,
      enhanced: true,
      ...captureStats
    };
  }

  async getSettings() {
    try {
      return new Promise((resolve) => {
        chrome.storage.local.get(['enabled', 'webhook_url'], (result) => {
          resolve({
            enabled: result.enabled !== false, // Default to true
            webhookUrl: result.webhook_url
          });
        });
      });
    } catch (error) {
      logger.error('Error getting settings:', error);
      return { enabled: true, webhookUrl: null };
    }
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
      logger.info('Page unloading, cleaning up enhanced content script...');
      this.cleanup();
    });
  }

  cleanup() {
    if (this.hybridCapture) {
      this.hybridCapture.stop();
    }
    
    this.isEnabled = false;
    this.isInitialized = false;
    
    logger.info('Enhanced content script cleanup completed');
  }

  // Public methods for debugging
  getCaptureSystem() {
    return this.hybridCapture;
  }

  addMessageHandler(handler) {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler) {
    const index = this.messageHandlers.indexOf(handler);
    if (index > -1) {
      this.messageHandlers.splice(index, 1);
    }
  }
}

// Initialize enhanced content script
const enhancedContentScript = new EnhancedContentScript();

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    enhancedContentScript.initialize().catch((error) => {
      console.error('Failed to initialize enhanced content script:', error);
    });
  });
} else {
  enhancedContentScript.initialize().catch((error) => {
    console.error('Failed to initialize enhanced content script:', error);
  });
}

// Export for testing
export default EnhancedContentScript;
