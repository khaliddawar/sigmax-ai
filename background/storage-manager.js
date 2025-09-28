import { createLogger } from '../shared/logger.js';

const logger = createLogger('StorageManager');

class StorageManager {
  constructor(storageArea = 'local') {
    this.storage = chrome.storage[storageArea];
  }

  async get(keys) {
    try {
      return new Promise((resolve, reject) => {
        this.storage.get(keys, (result) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(result);
          }
        });
      });
    } catch (error) {
      logger.error('Storage get error:', error);
      throw error;
    }
  }

  async set(items) {
    try {
      return new Promise((resolve, reject) => {
        this.storage.set(items, () => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve();
          }
        });
      });
    } catch (error) {
      logger.error('Storage set error:', error);
      throw error;
    }
  }

  async remove(keys) {
    try {
      return new Promise((resolve, reject) => {
        this.storage.remove(keys, () => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve();
          }
        });
      });
    } catch (error) {
      logger.error('Storage remove error:', error);
      throw error;
    }
  }

  async clear() {
    try {
      return new Promise((resolve, reject) => {
        this.storage.clear(() => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve();
          }
        });
      });
    } catch (error) {
      logger.error('Storage clear error:', error);
      throw error;
    }
  }

  async getBytesInUse(keys = null) {
    try {
      return new Promise((resolve, reject) => {
        this.storage.getBytesInUse(keys, (bytes) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(bytes);
          }
        });
      });
    } catch (error) {
      logger.error('Storage getBytesInUse error:', error);
      throw error;
    }
  }

  onChanged(callback) {
    chrome.storage.onChanged.addListener((changes, areaName) => {
      if (areaName === this.storage.name) {
        callback(changes);
      }
    });
  }
}

export default StorageManager;