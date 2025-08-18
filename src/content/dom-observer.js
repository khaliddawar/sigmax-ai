import { createLogger } from '../shared/logger.js';
import { debounce } from '../shared/utils.js';

const logger = createLogger('DomObserver');

class DomObserver {
  constructor(callback, options = {}) {
    this.callback = callback;
    this.observer = null;
    this.isObserving = false;
    
    // Default options
    this.options = {
      childList: true,
      subtree: true,
      attributes: false,
      attributeOldValue: false,
      characterData: false,
      characterDataOldValue: false,
      debounceDelay: 100,
      ...options
    };
    
    // Debounce callback if specified
    if (this.options.debounceDelay > 0) {
      this.debouncedCallback = debounce(this.callback, this.options.debounceDelay);
    } else {
      this.debouncedCallback = this.callback;
    }
    
    this.initializeObserver();
  }

  initializeObserver() {
    this.observer = new MutationObserver((mutations) => {
      this.handleMutations(mutations);
    });
  }

  handleMutations(mutations) {
    try {
      // Filter out irrelevant mutations
      const relevantMutations = this.filterMutations(mutations);
      
      if (relevantMutations.length > 0) {
        this.debouncedCallback(relevantMutations);
      }
    } catch (error) {
      logger.error('Error handling mutations:', error);
    }
  }

  filterMutations(mutations) {
    return mutations.filter((mutation) => {
      // Skip script and style elements
      if (mutation.target.nodeName === 'SCRIPT' || 
          mutation.target.nodeName === 'STYLE') {
        return false;
      }
      
      // Skip mutations with no added nodes for childList
      if (mutation.type === 'childList' && 
          mutation.addedNodes.length === 0) {
        return false;
      }
      
      // Check for relevant added nodes
      if (mutation.type === 'childList') {
        for (const node of mutation.addedNodes) {
          // Skip text nodes with only whitespace
          if (node.nodeType === Node.TEXT_NODE && 
              !node.textContent.trim()) {
            continue;
          }
          
          // Skip script and style elements
          if (node.nodeName === 'SCRIPT' || 
              node.nodeName === 'STYLE') {
            continue;
          }
          
          // This mutation has relevant content
          return true;
        }
        return false;
      }
      
      return true;
    });
  }

  observe(target) {
    if (!target) {
      logger.error('Invalid target for observation');
      return;
    }
    
    if (this.isObserving) {
      logger.warn('Already observing, disconnecting first');
      this.disconnect();
    }
    
    try {
      this.observer.observe(target, {
        childList: this.options.childList,
        subtree: this.options.subtree,
        attributes: this.options.attributes,
        attributeOldValue: this.options.attributeOldValue,
        characterData: this.options.characterData,
        characterDataOldValue: this.options.characterDataOldValue
      });
      
      this.isObserving = true;
      logger.info('Started observing target');
    } catch (error) {
      logger.error('Failed to start observing:', error);
      throw error;
    }
  }

  disconnect() {
    if (this.observer && this.isObserving) {
      this.observer.disconnect();
      this.isObserving = false;
      logger.info('Stopped observing');
    }
  }

  takeRecords() {
    if (this.observer) {
      return this.observer.takeRecords();
    }
    return [];
  }

  reconnect(target) {
    this.disconnect();
    this.observe(target);
  }

  updateOptions(newOptions) {
    this.options = { ...this.options, ...newOptions };
    
    // Update debounced callback if delay changed
    if (newOptions.debounceDelay !== undefined) {
      if (this.options.debounceDelay > 0) {
        this.debouncedCallback = debounce(this.callback, this.options.debounceDelay);
      } else {
        this.debouncedCallback = this.callback;
      }
    }
    
    // Reconnect if currently observing
    if (this.isObserving) {
      const records = this.takeRecords();
      if (records.length > 0) {
        this.handleMutations(records);
      }
    }
  }
}

export default DomObserver;