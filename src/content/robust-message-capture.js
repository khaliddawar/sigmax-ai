/**
 * Robust Message Capture System
 * 
 * This module provides multiple fallback mechanisms to ensure continuous
 * message capture even when DOM observation fails or pages are updated.
 */

import { createLogger } from '../shared/logger.js';
import { detectPlatform } from '../shared/utils.js';
import MessageParser from './message-parser.js';

const logger = createLogger('RobustMessageCapture');

class RobustMessageCapture {
  constructor() {
    this.platform = detectPlatform(window.location.href);
    this.messageParser = new MessageParser(this.platform);
    this.processedMessages = new Set();
    this.captureStrategies = [];
    this.isActive = false;
    this.retryCount = 0;
    this.maxRetries = 5;
    
    // Multiple capture strategies
    this.strategies = {
      DOM_OBSERVER: 'dom_observer',
      POLLING: 'polling',
      EVENT_LISTENER: 'event_listener',
      INTERSECTION_OBSERVER: 'intersection_observer',
      NETWORK_INTERCEPT: 'network_intercept'
    };
    
    this.initializeStrategies();
  }

  initializeStrategies() {
    // Strategy 1: Enhanced DOM Observer
    this.captureStrategies.push({
      name: this.strategies.DOM_OBSERVER,
      active: false,
      observer: null,
      start: () => this.startDOMObserver(),
      stop: () => this.stopDOMObserver(),
      priority: 1
    });

    // Strategy 2: Intelligent Polling
    this.captureStrategies.push({
      name: this.strategies.POLLING,
      active: false,
      interval: null,
      start: () => this.startPolling(),
      stop: () => this.stopPolling(),
      priority: 2
    });

    // Strategy 3: Event-based Capture
    this.captureStrategies.push({
      name: this.strategies.EVENT_LISTENER,
      active: false,
      listeners: [],
      start: () => this.startEventListeners(),
      stop: () => this.stopEventListeners(),
      priority: 3
    });

    // Strategy 4: Intersection Observer for new messages
    this.captureStrategies.push({
      name: this.strategies.INTERSECTION_OBSERVER,
      active: false,
      observer: null,
      start: () => this.startIntersectionObserver(),
      stop: () => this.stopIntersectionObserver(),
      priority: 4
    });
  }

  async start() {
    if (this.isActive) {
      logger.warn('Robust capture already active');
      return;
    }

    logger.info('Starting robust message capture system');
    this.isActive = true;
    this.retryCount = 0;

    // Start strategies in priority order
    for (const strategy of this.captureStrategies.sort((a, b) => a.priority - b.priority)) {
      try {
        await strategy.start();
        strategy.active = true;
        logger.info(`Started capture strategy: ${strategy.name}`);
      } catch (error) {
        logger.error(`Failed to start strategy ${strategy.name}:`, error);
      }
    }

    // Set up health monitoring
    this.startHealthMonitoring();
  }

  async stop() {
    if (!this.isActive) {
      return;
    }

    logger.info('Stopping robust message capture system');
    this.isActive = false;

    // Stop all strategies
    for (const strategy of this.captureStrategies) {
      if (strategy.active) {
        try {
          strategy.stop();
          strategy.active = false;
        } catch (error) {
          logger.error(`Error stopping strategy ${strategy.name}:`, error);
        }
      }
    }

    this.stopHealthMonitoring();
  }

  // Strategy 1: Enhanced DOM Observer with auto-recovery
  startDOMObserver() {
    const container = this.findChatContainer();
    if (!container) {
      throw new Error('Chat container not found');
    }

    this.captureStrategies.find(s => s.name === this.strategies.DOM_OBSERVER).observer = 
      new MutationObserver((mutations) => {
        this.handleDOMChanges(mutations);
      });

    const observer = this.captureStrategies.find(s => s.name === this.strategies.DOM_OBSERVER).observer;
    observer.observe(container, {
      childList: true,
      subtree: true,
      attributes: false,
      characterData: false
    });

    // Auto-recovery mechanism
    this.setupObserverRecovery(observer, container);
  }

  setupObserverRecovery(observer, container) {
    // Check if observer is still working every 30 seconds
    setInterval(() => {
      if (!this.isActive) return;
      
      try {
        const records = observer.takeRecords();
        if (records.length === 0) {
          // Observer might be disconnected, try to reconnect
          logger.warn('DOM Observer appears inactive, attempting recovery');
          this.recoverDOMObserver(container);
        }
      } catch (error) {
        logger.error('DOM Observer health check failed:', error);
        this.recoverDOMObserver(container);
      }
    }, 30000);
  }

  recoverDOMObserver(container) {
    try {
      const strategy = this.captureStrategies.find(s => s.name === this.strategies.DOM_OBSERVER);
      if (strategy.observer) {
        strategy.observer.disconnect();
      }
      this.startDOMObserver();
      logger.info('DOM Observer recovered successfully');
    } catch (error) {
      logger.error('Failed to recover DOM Observer:', error);
    }
  }

  stopDOMObserver() {
    const strategy = this.captureStrategies.find(s => s.name === this.strategies.DOM_OBSERVER);
    if (strategy.observer) {
      strategy.observer.disconnect();
      strategy.observer = null;
    }
  }

  // Strategy 2: Intelligent Polling with adaptive intervals
  startPolling() {
    let pollInterval = 2000; // Start with 2 seconds
    let consecutiveEmptyPolls = 0;
    let maxEmptyPolls = 5;

    const poll = async () => {
      if (!this.isActive) return;

      try {
        const newMessages = await this.scanForNewMessages();
        
        if (newMessages.length > 0) {
          consecutiveEmptyPolls = 0;
          pollInterval = Math.max(1000, pollInterval * 0.8); // Speed up when messages found
        } else {
          consecutiveEmptyPolls++;
          if (consecutiveEmptyPolls >= maxEmptyPolls) {
            pollInterval = Math.min(10000, pollInterval * 1.2); // Slow down when no messages
          }
        }

        // Schedule next poll
        this.captureStrategies.find(s => s.name === this.strategies.POLLING).interval = 
          setTimeout(poll, pollInterval);
      } catch (error) {
        logger.error('Polling error:', error);
        // Increase interval on error
        pollInterval = Math.min(15000, pollInterval * 1.5);
        this.captureStrategies.find(s => s.name === this.strategies.POLLING).interval = 
          setTimeout(poll, pollInterval);
      }
    };

    // Start polling
    poll();
  }

  stopPolling() {
    const strategy = this.captureStrategies.find(s => s.name === this.strategies.POLLING);
    if (strategy.interval) {
      clearTimeout(strategy.interval);
      strategy.interval = null;
    }
  }

  // Strategy 3: Event-based capture
  startEventListeners() {
    const strategy = this.captureStrategies.find(s => s.name === this.strategies.EVENT_LISTENER);
    
    // Listen for various events that might indicate new messages
    const events = [
      'DOMNodeInserted',
      'DOMSubtreeModified',
      'input',
      'change',
      'keyup',
      'paste'
    ];

    events.forEach(eventType => {
      const handler = (event) => {
        if (!this.isActive) return;
        this.handleEvent(event);
      };
      
      document.addEventListener(eventType, handler, true);
      strategy.listeners.push({ type: eventType, handler });
    });

    // Platform-specific events
    this.addPlatformSpecificListeners(strategy);
  }

  addPlatformSpecificListeners(strategy) {
    // Discord-specific events
    if (this.platform === 'discord') {
      const handler = () => this.scanForNewMessages();
      document.addEventListener('message', handler);
      strategy.listeners.push({ type: 'message', handler });
    }

    // Telegram-specific events
    if (this.platform === 'telegram') {
      const handler = () => this.scanForNewMessages();
      document.addEventListener('newMessage', handler);
      strategy.listeners.push({ type: 'newMessage', handler });
    }
  }

  stopEventListeners() {
    const strategy = this.captureStrategies.find(s => s.name === this.strategies.EVENT_LISTENER);
    strategy.listeners.forEach(({ type, handler }) => {
      document.removeEventListener(type, handler, true);
    });
    strategy.listeners = [];
  }

  // Strategy 4: Intersection Observer for new messages
  startIntersectionObserver() {
    const strategy = this.captureStrategies.find(s => s.name === this.strategies.INTERSECTION_OBSERVER);
    
    strategy.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          this.processElement(entry.target);
        }
      });
    }, {
      root: null,
      rootMargin: '0px',
      threshold: 0.1
    });

    // Observe all potential message containers
    this.observeMessageContainers(strategy.observer);
  }

  observeMessageContainers(observer) {
    const selectors = this.getMessageSelectors();
    selectors.forEach(selector => {
      const elements = document.querySelectorAll(selector);
      elements.forEach(element => {
        observer.observe(element);
      });
    });
  }

  stopIntersectionObserver() {
    const strategy = this.captureStrategies.find(s => s.name === this.strategies.INTERSECTION_OBSERVER);
    if (strategy.observer) {
      strategy.observer.disconnect();
      strategy.observer = null;
    }
  }

  // Health monitoring and auto-recovery
  startHealthMonitoring() {
    this.healthInterval = setInterval(() => {
      this.checkHealth();
    }, 10000); // Check every 10 seconds
  }

  stopHealthMonitoring() {
    if (this.healthInterval) {
      clearInterval(this.healthInterval);
      this.healthInterval = null;
    }
  }

  async checkHealth() {
    if (!this.isActive) return;

    const activeStrategies = this.captureStrategies.filter(s => s.active);
    
    if (activeStrategies.length === 0) {
      logger.error('No active capture strategies! Attempting recovery...');
      await this.emergencyRecovery();
      return;
    }

    // Check if we're still capturing messages
    const recentMessages = await this.scanForNewMessages();
    if (recentMessages.length === 0 && this.retryCount < this.maxRetries) {
      this.retryCount++;
      logger.warn(`No recent messages captured, retry ${this.retryCount}/${this.maxRetries}`);
      
      if (this.retryCount >= this.maxRetries) {
        await this.emergencyRecovery();
      }
    } else if (recentMessages.length > 0) {
      this.retryCount = 0; // Reset on successful capture
    }
  }

  async emergencyRecovery() {
    logger.warn('Initiating emergency recovery...');
    
    // Stop all strategies
    await this.stop();
    
    // Wait a moment
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Restart with fresh state
    this.processedMessages.clear();
    await this.start();
    
    logger.info('Emergency recovery completed');
  }

  // Core message processing methods
  async handleDOMChanges(mutations) {
    for (const mutation of mutations) {
      if (mutation.type === 'childList') {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            await this.processElement(node);
          }
        }
      }
    }
  }

  async handleEvent(event) {
    // Process the element that triggered the event
    if (event.target) {
      await this.processElement(event.target);
    }
  }

  async scanForNewMessages() {
    const selectors = this.getMessageSelectors();
    const newMessages = [];

    for (const selector of selectors) {
      const elements = document.querySelectorAll(selector);
      for (const element of elements) {
        const messageData = await this.processElement(element);
        if (messageData) {
          newMessages.push(messageData);
        }
      }
    }

    return newMessages;
  }

  async processElement(element) {
    try {
      const elementId = this.getElementId(element);
      
      if (this.processedMessages.has(elementId)) {
        return null;
      }

      const messageData = this.messageParser.parse(element);
      
      if (!messageData || !messageData.content) {
        return null;
      }

      // Mark as processed
      this.processedMessages.add(elementId);

      // Send to background
      await this.sendToBackground(messageData);
      
      return messageData;
    } catch (error) {
      logger.error('Error processing element:', error);
      return null;
    }
  }

  // Utility methods
  findChatContainer() {
    const selectors = [
      '[data-testid="chat-container"]',
      '[class*="chat-container"]',
      '[class*="messages-container"]',
      '[class*="message-list"]',
      '.chat-content',
      '#chat-content',
      'main',
      'body'
    ];

    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element) {
        return element;
      }
    }

    return document.body;
  }

  getMessageSelectors() {
    const platformSelectors = {
      discord: [
        '[data-list-item-id*="chat-messages"]',
        '[class*="messageListItem"]',
        '[class*="message-"]'
      ],
      telegram: [
        '.message',
        '[class*="message-"]',
        '[data-message-id]'
      ],
      whatsapp: [
        '[data-testid="conversation-panel-messages"] > div',
        '[class*="message-"]'
      ],
      circle: [
        '[data-testid="message-item"]',
        '.message-item',
        '[class*="message-"][class*="item"]'
      ]
    };

    return platformSelectors[this.platform] || [
      '[class*="message"]',
      '[data-testid*="message"]',
      '[class*="chat"] > div',
      '[class*="conversation"] > div'
    ];
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

  async sendToBackground(messageData) {
    try {
      return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({
          type: 'CAPTURE_MESSAGE',
          data: messageData
        }, (response) => {
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
}

export default RobustMessageCapture;
