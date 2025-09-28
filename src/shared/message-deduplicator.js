/**
 * Message Deduplication System for SignalScope
 * Handles page refresh scenarios and prevents duplicate message processing
 */

class MessageDeduplicator {
  constructor() {
    this.dbName = 'SignalScope';
    this.dbVersion = 1;
    this.storeName = 'processedMessages';
    this.maxStoredHashes = 1000; // Limit storage size
    this.hashExpiryHours = 24; // Hash expires after 24 hours
  }

  /**
   * Initialize IndexedDB for message deduplication
   */
  async init() {
    try {
      this.db = await this.openDB();
      console.log('🔒 Message deduplicator initialized');
      return true;
    } catch (error) {
      console.error('❌ Failed to initialize deduplicator:', error);
      return false;
    }
  }

  /**
   * Open IndexedDB connection
   */
  async openDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        
        // Create object store for processed message hashes
        if (!db.objectStoreNames.contains(this.storeName)) {
          const store = db.createObjectStore(this.storeName, { keyPath: 'hash' });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('expiry', 'expiry', { unique: false });
        }
      };
    });
  }

  /**
   * Generate unique hash for message deduplication
   */
  generateMessageHash(message) {
    // Create deterministic hash from message content
    const content = `${message.author}:${message.content}:${message.timestamp}`;
    
    // Simple hash function (can be replaced with crypto.subtle for better security)
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    
    return Math.abs(hash).toString(36);
  }

  /**
   * Check if message has already been processed
   */
  async isMessageProcessed(message) {
    try {
      const hash = this.generateMessageHash(message);
      const db = await this.openDB();
      const transaction = db.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      
      const request = store.get(hash);
      
      return new Promise((resolve) => {
        request.onsuccess = () => {
          const result = request.result;
          if (result) {
            // Check if hash has expired
            const now = Date.now();
            if (now > result.expiry) {
              // Hash expired, remove it
              this.removeExpiredHash(hash);
              resolve(false);
            } else {
              resolve(true);
            }
          } else {
            resolve(false);
          }
        };
        
        request.onerror = () => resolve(false);
      });
    } catch (error) {
      console.error('❌ Error checking message hash:', error);
      return false;
    }
  }

  /**
   * Mark message as processed
   */
  async markMessageProcessed(message) {
    try {
      const hash = this.generateMessageHash(message);
      const now = Date.now();
      const expiry = now + (this.hashExpiryHours * 60 * 60 * 1000);
      
      const db = await this.openDB();
      const transaction = db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      
      await store.put({
        hash,
        timestamp: now,
        expiry,
        author: message.author,
        contentPreview: message.content.substring(0, 50)
      });
      
      // Clean up old hashes periodically
      this.cleanupOldHashes();
      
      return true;
    } catch (error) {
      console.error('❌ Error marking message as processed:', error);
      return false;
    }
  }

  /**
   * Remove expired hash
   */
  async removeExpiredHash(hash) {
    try {
      const db = await this.openDB();
      const transaction = db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      await store.delete(hash);
    } catch (error) {
      console.error('❌ Error removing expired hash:', error);
    }
  }

  /**
   * Clean up old hashes to prevent storage bloat
   */
  async cleanupOldHashes() {
    try {
      const db = await this.openDB();
      const transaction = db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const index = store.index('expiry');
      
      const now = Date.now();
      const range = IDBKeyRange.upperBound(now);
      const request = index.openCursor(range);
      
      request.onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        }
      };
      
      // Also limit total number of stored hashes
      const countRequest = store.count();
      countRequest.onsuccess = () => {
        if (countRequest.result > this.maxStoredHashes) {
          // Remove oldest hashes
          const oldestRequest = store.index('timestamp').openCursor();
          let removed = 0;
          const toRemove = countRequest.result - this.maxStoredHashes;
          
          oldestRequest.onsuccess = (event) => {
            const cursor = event.target.result;
            if (cursor && removed < toRemove) {
              cursor.delete();
              removed++;
              cursor.continue();
            }
          };
        }
      };
    } catch (error) {
      console.error('❌ Error cleaning up old hashes:', error);
    }
  }

  /**
   * Get statistics about processed messages
   */
  async getStats() {
    try {
      const db = await this.openDB();
      const transaction = db.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      
      const countRequest = store.count();
      return new Promise((resolve) => {
        countRequest.onsuccess = () => {
          resolve({
            totalProcessed: countRequest.result,
            maxStored: this.maxStoredHashes,
            expiryHours: this.hashExpiryHours
          });
        };
        countRequest.onerror = () => resolve({ totalProcessed: 0 });
      });
    } catch (error) {
      console.error('❌ Error getting deduplication stats:', error);
      return { totalProcessed: 0 };
    }
  }

  /**
   * Clear all stored hashes (for testing/debugging)
   */
  async clearAllHashes() {
    try {
      const db = await this.openDB();
      const transaction = db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      await store.clear();
      console.log('🧹 Cleared all message hashes');
      return true;
    } catch (error) {
      console.error('❌ Error clearing hashes:', error);
      return false;
    }
  }
}

// Export for use in content scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = MessageDeduplicator;
} else {
  window.MessageDeduplicator = MessageDeduplicator;
}
