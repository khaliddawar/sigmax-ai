import { createLogger } from '../shared/logger.js';
import { MESSAGE_TYPES } from '../shared/constants.js';
import { generateId } from '../shared/utils.js';

const logger = createLogger('MessageHandler');

class MessageHandler {
  constructor(serviceWorker) {
    this.serviceWorker = serviceWorker;
    this.previewBuffer = [];
    this.maxPreviewSize = 500;
  }

  async sendToTab(tabId, message) {
    try {
      return new Promise((resolve, reject) => {
        chrome.tabs.sendMessage(tabId, message, (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(response);
          }
        });
      });
    } catch (error) {
      logger.error('Failed to send message to tab:', error);
      throw error;
    }
  }

  async sendToAllTabs(message) {
    try {
      const tabs = await this.getAllTabs();
      const promises = tabs.map((tab) => this.sendToTab(tab.id, message));
      return await Promise.allSettled(promises);
    } catch (error) {
      logger.error('Failed to send message to all tabs:', error);
      throw error;
    }
  }

  async getAllTabs() {
    return new Promise((resolve) => {
      chrome.tabs.query({}, (tabs) => {
        resolve(tabs);
      });
    });
  }

  async getActiveTab() {
    return new Promise((resolve) => {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        resolve(tabs[0] || null);
      });
    });
  }

  async broadcastUpdate(type, data) {
    const message = { type, data, timestamp: new Date().toISOString() };
    await this.sendToAllTabs(message);
    logger.debug('Broadcast sent:', type);
  }

  addToPreviewBuffer(message) {
    try {
      // Add message with proper structure
      const previewMessage = {
        ...message,
        id: message.id || generateId(),
        timestamp: message.timestamp || Date.now(),
        previewTime: Date.now()
      };
      
      // Add to beginning of buffer
      this.previewBuffer.unshift(previewMessage);
      
      // Maintain buffer size
      if (this.previewBuffer.length > this.maxPreviewSize) {
        this.previewBuffer = this.previewBuffer.slice(0, this.maxPreviewSize);
      }
      
      // Send to sidebar if open
      this.notifySidebar(previewMessage);
      
      logger.debug('Message added to preview buffer');
    } catch (error) {
      logger.error('Failed to add message to preview buffer:', error);
    }
  }

  async notifySidebar(message) {
    try {
      // Send to sidebar and popup
      await chrome.runtime.sendMessage({
        type: 'NEW_PREVIEW_MESSAGE',
        data: message
      }).catch(() => {
        // Sidebar/popup might not be open, ignore error
      });
    } catch (error) {
      // Silent fail - sidebar might not be open
    }
  }

  getPreviewMessages() {
    return this.previewBuffer;
  }

  clearPreviewBuffer() {
    this.previewBuffer = [];
    logger.info('Preview buffer cleared');
  }
}

export default MessageHandler;