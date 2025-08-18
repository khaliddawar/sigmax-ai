import { PLATFORMS, STORAGE_KEYS } from '../shared/constants.js';
import { createLogger } from '../shared/logger.js';

const logger = createLogger('SelectorEngine');

class SelectorEngine {
  constructor(platform) {
    this.platform = platform;
    this.selectors = {};
    this.customSelectors = {};
  }

  async loadSelectors() {
    try {
      // Load platform default selectors
      const platformConfig = PLATFORMS[this.platform.toUpperCase()];
      if (platformConfig) {
        this.selectors = { ...platformConfig.selectors };
      }
      
      // Load custom selectors from storage
      const stored = await this.getStoredSelectors();
      if (stored && stored[this.platform]) {
        this.customSelectors = stored[this.platform];
        // Merge custom selectors (override defaults)
        this.selectors = { ...this.selectors, ...this.customSelectors };
      }
      
      logger.info('Selectors loaded for platform:', this.platform, this.selectors);
    } catch (error) {
      logger.error('Failed to load selectors:', error);
      // Use defaults if loading fails
      const platformConfig = PLATFORMS[this.platform.toUpperCase()];
      if (platformConfig) {
        this.selectors = { ...platformConfig.selectors };
      }
    }
  }

  async getStoredSelectors() {
    try {
      return new Promise((resolve) => {
        chrome.storage.local.get(STORAGE_KEYS.SELECTORS, (result) => {
          resolve(result[STORAGE_KEYS.SELECTORS] || {});
        });
      });
    } catch (error) {
      logger.error('Failed to get stored selectors:', error);
      return {};
    }
  }

  async saveCustomSelectors(selectors) {
    try {
      const stored = await this.getStoredSelectors();
      stored[this.platform] = selectors;
      
      await chrome.storage.local.set({
        [STORAGE_KEYS.SELECTORS]: stored
      });
      
      this.customSelectors = selectors;
      this.selectors = { ...this.selectors, ...selectors };
      
      logger.info('Custom selectors saved');
    } catch (error) {
      logger.error('Failed to save custom selectors:', error);
      throw error;
    }
  }

  getMessageSelector() {
    return this.selectors.message || null;
  }

  getAuthorSelector() {
    return this.selectors.author || null;
  }

  getContentSelector() {
    return this.selectors.content || null;
  }

  getTimestampSelector() {
    return this.selectors.timestamp || null;
  }

  getChannelSelector() {
    return this.selectors.channel || null;
  }

  getContainerSelector() {
    // Try to find the main chat container
    switch (this.platform) {
      case 'discord':
        // Try multiple selectors for Discord's changing structure
        const discordSelectors = [
          '[class*="chatContent-"]',
          '[class*="messagesWrapper-"]',
          '[class*="scroller-"][class*="auto-"]',
          '[data-list-id="chat-messages"]',
          'main [class*="chat-"]'
        ];
        for (const selector of discordSelectors) {
          if (document.querySelector(selector)) {
            logger.info('Using Discord container selector:', selector);
            return selector;
          }
        }
        logger.warn('No Discord container found, using body');
        return 'body';
      case 'telegram':
        return '.messages-container';
      case 'slack':
        return '[data-qa="message_list"]';
      case 'whatsapp':
        return '[class*="conversation-panel-messages"]';
      case 'circle':
        return '#message-scroll-view, [class*="message-scroll"], .messages-container';
      case 'webchat':
        // Try multiple common web chat containers
        const webChatSelectors = [
          '#message-scroll-view',
          '[class*="message-scroll"]',
          '.messages-container',
          '[class*="chat-messages"]',
          '[class*="message-list"]',
          'main [class*="messages"]'
        ];
        for (const selector of webChatSelectors) {
          if (document.querySelector(selector)) {
            logger.info('Using web chat container selector:', selector);
            return selector;
          }
        }
        logger.warn('No web chat container found, using body');
        return 'body';
      default:
        return 'body';
    }
  }

  validateSelector(selector) {
    try {
      const elements = document.querySelectorAll(selector);
      return elements.length > 0;
    } catch (error) {
      logger.error('Invalid selector:', selector, error);
      return false;
    }
  }

  testSelectors() {
    const results = {};
    
    for (const [key, selector] of Object.entries(this.selectors)) {
      if (selector) {
        results[key] = {
          selector,
          found: this.validateSelector(selector),
          count: 0
        };
        
        try {
          results[key].count = document.querySelectorAll(selector).length;
        } catch (error) {
          results[key].error = error.message;
        }
      }
    }
    
    return results;
  }

  findBestSelector(element, type) {
    // Try to generate a reliable selector for an element
    const strategies = [
      // ID
      () => {
        if (element.id) {
          return `#${element.id}`;
        }
        return null;
      },
      
      // Data attributes
      () => {
        const dataAttrs = Array.from(element.attributes)
          .filter(attr => attr.name.startsWith('data-'));
        
        if (dataAttrs.length > 0) {
          const selector = dataAttrs
            .map(attr => `[${attr.name}="${attr.value}"]`)
            .join('');
          return selector;
        }
        return null;
      },
      
      // Class combinations
      () => {
        if (element.className) {
          const classes = element.className.split(' ')
            .filter(c => c && !c.includes('hover') && !c.includes('active'))
            .slice(0, 2);
          
          if (classes.length > 0) {
            return '.' + classes.join('.');
          }
        }
        return null;
      },
      
      // Tag + attributes
      () => {
        const tag = element.tagName.toLowerCase();
        const role = element.getAttribute('role');
        const ariaLabel = element.getAttribute('aria-label');
        
        let selector = tag;
        if (role) selector += `[role="${role}"]`;
        if (ariaLabel) selector += `[aria-label="${ariaLabel}"]`;
        
        return selector !== tag ? selector : null;
      }
    ];
    
    for (const strategy of strategies) {
      const selector = strategy();
      if (selector && this.validateSelector(selector)) {
        // Check if selector is specific enough
        const matches = document.querySelectorAll(selector);
        if (matches.length < 10) {
          return selector;
        }
      }
    }
    
    // Fallback to a more complex selector
    return this.generateComplexSelector(element);
  }

  generateComplexSelector(element) {
    const path = [];
    let current = element;
    
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      
      if (current.id) {
        selector = `#${current.id}`;
        path.unshift(selector);
        break;
      }
      
      if (current.className) {
        const classes = current.className.split(' ')
          .filter(c => c && !c.includes('hover'))
          .slice(0, 1);
        
        if (classes.length > 0) {
          selector += '.' + classes[0];
        }
      }
      
      // Add nth-child if needed
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children);
        const index = siblings.indexOf(current);
        if (siblings.length > 1) {
          selector += `:nth-child(${index + 1})`;
        }
      }
      
      path.unshift(selector);
      current = current.parentElement;
    }
    
    return path.join(' > ');
  }
}

export default SelectorEngine;