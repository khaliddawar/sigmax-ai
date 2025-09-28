/**
 * Hybrid Capture System
 * 
 * Combines DOM-based and Network-based capture methods for maximum reliability.
 * Automatically switches between methods based on browser state and platform capabilities.
 */

import { createLogger } from '../shared/logger.js';
import NetworkInterceptor from './network-interceptor.js';
import DomObserver from './dom-observer.js';
import MessageParser from './message-parser.js';
import { shouldSkipMessage } from './platform-filters.js';
import SelectorEngine from './selector-engine.js';

const logger = createLogger('HybridCapture');

class HybridCapture {
  constructor() {
    this.networkInterceptor = new NetworkInterceptor();
    this.domObserver = null;
    this.messageParser = null;
    this.selectorEngine = null;
    this.isActive = false;
    this.platform = null;
    this.captureMode = 'auto'; // 'dom', 'network', 'hybrid', 'auto'
    this.processedMessages = new Set();
    this.messageHandlers = [];
    this.visibilityState = 'visible';
    this.lastActivity = Date.now();
    this.healthCheckInterval = null;
  }

  async initialize(platform = 'generic') {
    try {
      logger.info('Initializing hybrid capture system...');
      
      this.platform = platform;
      
      // Initialize components
      this.selectorEngine = new SelectorEngine(platform);
      this.messageParser = new MessageParser(platform);
      this.domObserver = new DomObserver(this.handleDomChange.bind(this));
      
      // Load platform selectors
      await this.selectorEngine.loadSelectors();
      
      // Set up network interceptor
      this.networkInterceptor.addMessageHandler(this.handleNetworkMessage.bind(this));
      
      // Set up visibility change detection
      this.setupVisibilityHandling();
      
      // Set up health monitoring
      this.setupHealthMonitoring();
      
      // Determine optimal capture mode
      await this.determineCaptureMode();
      
      // Start capture
      await this.startCapture();
      
      this.isActive = true;
      logger.info(`Hybrid capture initialized in ${this.captureMode} mode`);
      
    } catch (error) {
      logger.error('Failed to initialize hybrid capture:', error);
      throw error;
    }
  }

  async determineCaptureMode() {
    try {
      // Check if we're in a background tab
      if (this.visibilityState === 'hidden') {
        this.captureMode = 'network';
        logger.info('Background tab detected, using network-only capture');
        return;
      }
      
      // Check platform capabilities
      const platformCapabilities = this.getPlatformCapabilities();
      
      if (platformCapabilities.networkReliable && platformCapabilities.domReliable) {
        this.captureMode = 'hybrid';
        logger.info('Platform supports both methods, using hybrid capture');
      } else if (platformCapabilities.networkReliable) {
        this.captureMode = 'network';
        logger.info('Platform has reliable network API, using network capture');
      } else if (platformCapabilities.domReliable) {
        this.captureMode = 'dom';
        logger.info('Platform has reliable DOM structure, using DOM capture');
      } else {
        this.captureMode = 'hybrid';
        logger.info('Uncertain platform capabilities, using hybrid capture as fallback');
      }
      
    } catch (error) {
      logger.error('Error determining capture mode:', error);
      this.captureMode = 'hybrid'; // Safe fallback
    }
  }

  getPlatformCapabilities() {
    const capabilities = {
      networkReliable: false,
      domReliable: false
    };
    
    switch (this.platform) {
      case 'discord':
        capabilities.networkReliable = true; // Discord has reliable WebSocket API
        capabilities.domReliable = true; // Discord has stable DOM structure
        break;
        
      case 'telegram':
        capabilities.networkReliable = true; // Telegram Web has WebSocket API
        capabilities.domReliable = true; // Telegram has stable DOM
        break;
        
      case 'slack':
        capabilities.networkReliable = true; // Slack has WebSocket API
        capabilities.domReliable = true; // Slack has stable DOM
        break;
        
      case 'whatsapp':
        capabilities.networkReliable = false; // WhatsApp Web doesn't expose reliable network API
        capabilities.domReliable = true; // WhatsApp has stable DOM
        break;
        
      case 'circle':
        capabilities.networkReliable = true; // Circle.so has API
        capabilities.domReliable = true; // Circle has stable DOM
        break;
        
      default:
        capabilities.networkReliable = true; // Assume network is available
        capabilities.domReliable = true; // Assume DOM is available
    }
    
    return capabilities;
  }

  async startCapture() {
    try {
      switch (this.captureMode) {
        case 'network':
          await this.startNetworkCapture();
          break;
          
        case 'dom':
          await this.startDomCapture();
          break;
          
        case 'hybrid':
          await this.startHybridCapture();
          break;
          
        default:
          throw new Error(`Unknown capture mode: ${this.captureMode}`);
      }
      
      logger.info(`Capture started in ${this.captureMode} mode`);
      
    } catch (error) {
      logger.error('Failed to start capture:', error);
      throw error;
    }
  }

  async startNetworkCapture() {
    logger.info('Starting network-only capture');
    this.networkInterceptor.start();
  }

  async startDomCapture() {
    logger.info('Starting DOM-only capture');
    
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
    
    // Process existing messages
    await this.processExistingMessages();
  }

  async startHybridCapture() {
    logger.info('Starting hybrid capture (DOM + Network)');
    
    // Start both methods
    this.networkInterceptor.start();
    
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
    
    // Process existing messages
    await this.processExistingMessages();
  }

  setupVisibilityHandling() {
    // Listen for visibility changes
    document.addEventListener('visibilitychange', () => {
      const newState = document.visibilityState;
      
      if (newState !== this.visibilityState) {
        logger.info(`Visibility changed from ${this.visibilityState} to ${newState}`);
        this.visibilityState = newState;
        
        // Adjust capture strategy based on visibility
        this.handleVisibilityChange(newState);
      }
    });
    
    // Listen for page focus/blur
    window.addEventListener('focus', () => {
      this.visibilityState = 'visible';
      this.lastActivity = Date.now();
    });
    
    window.addEventListener('blur', () => {
      this.visibilityState = 'hidden';
    });
  }

  handleVisibilityChange(newState) {
    if (newState === 'hidden') {
      // Page is hidden, prioritize network capture
      if (this.captureMode === 'dom') {
        logger.info('Switching to network capture due to hidden page');
        this.switchToNetworkCapture();
      }
    } else if (newState === 'visible') {
      // Page is visible, can use DOM capture
      if (this.captureMode === 'network' && this.getPlatformCapabilities().domReliable) {
        logger.info('Switching to hybrid capture due to visible page');
        this.switchToHybridCapture();
      }
    }
  }

  async switchToNetworkCapture() {
    try {
      // Stop DOM observation
      if (this.domObserver) {
        this.domObserver.disconnect();
      }
      
      // Ensure network capture is active
      if (!this.networkInterceptor.isActive) {
        this.networkInterceptor.start();
      }
      
      this.captureMode = 'network';
      logger.info('Switched to network capture');
      
    } catch (error) {
      logger.error('Error switching to network capture:', error);
    }
  }

  async switchToHybridCapture() {
    try {
      // Start network capture if not active
      if (!this.networkInterceptor.isActive) {
        this.networkInterceptor.start();
      }
      
      // Start DOM observation
      const containerSelector = this.selectorEngine.getContainerSelector();
      const container = document.querySelector(containerSelector);
      
      if (container) {
        this.domObserver.observe(container);
      } else {
        this.domObserver.observe(document.body);
      }
      
      this.captureMode = 'hybrid';
      logger.info('Switched to hybrid capture');
      
    } catch (error) {
      logger.error('Error switching to hybrid capture:', error);
    }
  }

  setupHealthMonitoring() {
    // Health check every 30 seconds
    this.healthCheckInterval = setInterval(() => {
      this.performHealthCheck();
    }, 30000);
  }

  performHealthCheck() {
    try {
      const now = Date.now();
      const timeSinceActivity = now - this.lastActivity;
      
      // If no activity for 2 minutes, consider it unhealthy
      if (timeSinceActivity > 120000) {
        logger.warn('No activity detected for 2+ minutes, performing health check');
        
        // Try to recover by switching capture modes
        if (this.captureMode === 'dom') {
          this.switchToNetworkCapture();
        } else if (this.captureMode === 'network') {
          this.switchToHybridCapture();
        }
        
        // Reset activity timer
        this.lastActivity = now;
      }
      
    } catch (error) {
      logger.error('Error in health check:', error);
    }
  }

  handleNetworkMessage(messages, context) {
    try {
      this.lastActivity = Date.now();
      
      // Process each message
      messages.forEach(message => {
        this.processMessage(message, 'network');
      });
      
    } catch (error) {
      logger.error('Error handling network message:', error);
    }
  }

  async handleDomChange(mutations) {
    try {
      this.lastActivity = Date.now();
      
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
        await this.processMessageElement(messageElement);
      }
      
    } catch (error) {
      logger.error('Error processing element:', error);
    }
  }

  async processMessageElement(messageElement) {
    try {
      // Generate unique ID for the element
      const elementId = this.getElementId(messageElement);
      
      // Check if already processed
      if (this.processedMessages.has(elementId)) {
        return;
      }
      
      // Mark as processed
      this.processedMessages.add(elementId);
      
      // Parse message data
      const messageData = this.messageParser.parse(messageElement);

      // Centralized skip check
      if (shouldSkipMessage({ ...messageData, platform: this.platform })) {
        logger.debug('Skipping message by platform filter');
        return;
      }
      
      if (!messageData || !messageData.content) {
        logger.debug('Skipping empty message');
        return;
      }
      
      // Add metadata
      const enrichedMessage = {
        ...messageData,
        platform: this.platform,
        url: window.location.href,
        capturedAt: new Date().toISOString(),
        source: 'dom'
      };
      
      this.processMessage(enrichedMessage, 'dom');
      
    } catch (error) {
      logger.error('Error processing message element:', error);
    }
  }

  processMessage(message, source) {
    try {
      // Generate unique message ID
      const messageId = this.generateMessageId(message);
      
      // Check for duplicates across sources
      if (this.processedMessages.has(messageId)) {
        logger.debug(`Duplicate message detected: ${messageId}`);
        return;
      }
      
      // Mark as processed
      this.processedMessages.add(messageId);
      
      // Add source information
      const enrichedMessage = {
        ...message,
        id: messageId,
        captureSource: source,
        captureMode: this.captureMode
      };
      
      logger.debug(`Message captured via ${source}:`, enrichedMessage);
      
      // Notify handlers
      this.messageHandlers.forEach(handler => {
        try {
          handler(enrichedMessage, { source, mode: this.captureMode });
        } catch (error) {
          logger.error('Error in message handler:', error);
        }
      });
      
      // Clean up old processed messages (keep last 1000)
      if (this.processedMessages.size > 1000) {
        const oldestItems = Array.from(this.processedMessages).slice(0, 100);
        oldestItems.forEach((item) => this.processedMessages.delete(item));
      }
      
    } catch (error) {
      logger.error('Error processing message:', error);
    }
  }

  generateMessageId(message) {
    // Try to use existing ID
    if (message.id) {
      return message.id;
    }
    
    // Generate ID based on content and timestamp
    const content = message.content || '';
    const timestamp = message.timestamp || message.capturedAt || '';
    const author = message.author || '';
    
    return this.simpleHash(content + timestamp + author);
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
        
        await Promise.all(batch.map((msg) => this.processMessageElement(msg)));
        
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

  // Handler management
  addMessageHandler(handler) {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler) {
    const index = this.messageHandlers.indexOf(handler);
    if (index > -1) {
      this.messageHandlers.splice(index, 1);
    }
  }

  clearMessageHandlers() {
    this.messageHandlers = [];
  }

  // Control methods
  async stop() {
    try {
      logger.info('Stopping hybrid capture system');
      
      this.isActive = false;
      
      // Stop network interceptor
      if (this.networkInterceptor) {
        this.networkInterceptor.stop();
      }
      
      // Stop DOM observer
      if (this.domObserver) {
        this.domObserver.disconnect();
      }
      
      // Clear health check interval
      if (this.healthCheckInterval) {
        clearInterval(this.healthCheckInterval);
        this.healthCheckInterval = null;
      }
      
      // Clear processed messages
      this.processedMessages.clear();
      
      logger.info('Hybrid capture system stopped');
      
    } catch (error) {
      logger.error('Error stopping hybrid capture system:', error);
    }
  }

  getStats() {
    return {
      isActive: this.isActive,
      captureMode: this.captureMode,
      platform: this.platform,
      visibilityState: this.visibilityState,
      processedMessages: this.processedMessages.size,
      lastActivity: new Date(this.lastActivity).toISOString(),
      networkActive: this.networkInterceptor?.isActive || false,
      domObserving: this.domObserver?.isObserving || false
    };
  }
}

export default HybridCapture;
