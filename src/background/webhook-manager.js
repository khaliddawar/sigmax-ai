import { STORAGE_KEYS, WEBHOOK_CONFIG, HTTP_STATUS } from '../shared/constants.js';
import { retryWithBackoff, generateId, chunkArray, createIdempotencyKey } from '../shared/utils.js';
import { createLogger } from '../shared/logger.js';
import StorageManager from './storage-manager.js';

const logger = createLogger('WebhookManager');

class WebhookManager {
  constructor() {
    this.storageManager = new StorageManager();
    this.webhookUrl = null;
    this.webhookSecret = null;
    this.messageQueue = [];
    this.failedQueue = [];
    this.isProcessing = false;
  }

  async initialize() {
    try {
      // Load webhook configuration
      const config = await this.storageManager.get([
        STORAGE_KEYS.WEBHOOK_URL,
        STORAGE_KEYS.WEBHOOK_SECRET,
        STORAGE_KEYS.MESSAGE_QUEUE,
        STORAGE_KEYS.FAILED_QUEUE
      ]);
      
      this.webhookUrl = config[STORAGE_KEYS.WEBHOOK_URL];
      this.webhookSecret = config[STORAGE_KEYS.WEBHOOK_SECRET];
      this.messageQueue = config[STORAGE_KEYS.MESSAGE_QUEUE] || [];
      this.failedQueue = config[STORAGE_KEYS.FAILED_QUEUE] || [];
      
      logger.info('Webhook manager initialized', {
        queueSize: this.messageQueue.length,
        failedSize: this.failedQueue.length
      });
    } catch (error) {
      logger.error('Failed to initialize webhook manager:', error);
      throw error;
    }
  }

  async updateConfig({ url, secret }) {
    if (url !== undefined) {
      this.webhookUrl = url;
    }
    if (secret !== undefined) {
      this.webhookSecret = secret;
    }
    
    await this.storageManager.set({
      [STORAGE_KEYS.WEBHOOK_URL]: this.webhookUrl,
      [STORAGE_KEYS.WEBHOOK_SECRET]: this.webhookSecret
    });
    
    logger.info('Webhook configuration updated');
  }

  async queueMessage(message) {
    try {
      // Check queue size limit
      if (this.messageQueue.length >= WEBHOOK_CONFIG.MAX_QUEUE_SIZE) {
        logger.warn('Message queue full, removing oldest message');
        this.messageQueue.shift();
      }
      
      // Add message to queue
      const queuedMessage = {
        ...message,
        id: message.id || generateId(),
        queuedAt: new Date().toISOString(),
        attempts: 0
      };
      
      this.messageQueue.push(queuedMessage);
      
      // Save to storage
      await this.saveQueue();
      
      logger.debug('Message queued:', queuedMessage.id);
      
      // Process immediately if not batching
      if (this.messageQueue.length >= WEBHOOK_CONFIG.DEFAULT_BATCH_SIZE) {
        await this.processBatch();
      }
      
      return queuedMessage.id;
    } catch (error) {
      logger.error('Failed to queue message:', error);
      throw error;
    }
  }

  async processBatch() {
    if (this.isProcessing) {
      logger.debug('Already processing batch, skipping');
      return;
    }
    
    if (!this.webhookUrl) {
      logger.warn('No webhook URL configured');
      return;
    }
    
    if (this.messageQueue.length === 0) {
      logger.debug('No messages to process');
      return;
    }
    
    this.isProcessing = true;
    
    try {
      const settings = await this.storageManager.get([
        STORAGE_KEYS.BATCH_SIZE,
        STORAGE_KEYS.RETRY_ATTEMPTS
      ]);
      
      const batchSize = settings[STORAGE_KEYS.BATCH_SIZE] || WEBHOOK_CONFIG.DEFAULT_BATCH_SIZE;
      const maxRetries = settings[STORAGE_KEYS.RETRY_ATTEMPTS] || WEBHOOK_CONFIG.MAX_RETRY_ATTEMPTS;
      
      // Get batch of messages
      const batch = this.messageQueue.splice(0, batchSize);
      
      logger.info(`Processing batch of ${batch.length} messages`);
      
      // Send webhook
      const result = await this.sendWebhook(batch, maxRetries);
      
      if (result.success) {
        // Update stats
        await this.updateStats({
          sent: batch.length,
          success: true
        });
        
        logger.info(`Batch processed successfully: ${batch.length} messages`);
      } else {
        // Move to failed queue
        batch.forEach((msg) => {
          msg.attempts++;
          msg.lastError = result.error;
          msg.failedAt = new Date().toISOString();
          this.failedQueue.push(msg);
        });
        
        logger.error(`Batch processing failed: ${result.error}`);
      }
      
      // Save updated queues
      await this.saveQueue();
    } catch (error) {
      logger.error('Batch processing error:', error);
    } finally {
      this.isProcessing = false;
    }
  }

  async sendWebhook(messages, maxRetries = WEBHOOK_CONFIG.MAX_RETRY_ATTEMPTS) {
    try {
      // Fix message format issues
      const fixedMessages = (Array.isArray(messages) ? messages : [messages]).map(msg => {
        // Ensure importance is an integer
        if (msg.intelligence && typeof msg.intelligence.importance === 'number') {
          msg.intelligence.importance = Math.round(msg.intelligence.importance);
        }
        
        // Clean message - remove queue-specific fields
        return {
          id: msg.id,
          platform: msg.platform || 'unknown',
          author: msg.author || 'Unknown',
          content: msg.content || '',
          timestamp: msg.timestamp,
          url: msg.url,
          intelligence: msg.intelligence,
          attachments: msg.attachments,
          capturedAt: msg.capturedAt || msg.timestamp
        };
      });
      
      const payload = {
        messages: fixedMessages,
        timestamp: new Date().toISOString(),
        source: {type: 'signalscope'},  // Changed to object
        version: chrome.runtime.getManifest().version
      };
      
      // Add idempotency key
      const idempotencyKey = createIdempotencyKey(payload);
      
      // Prepare headers
      const headers = {
        'Content-Type': 'application/json',
        'X-SignalScope-Version': chrome.runtime.getManifest().version,
        'X-Idempotency-Key': idempotencyKey
      };
      
      // Add HMAC signature if secret is configured
      if (this.webhookSecret) {
        const signature = await this.generateHmacSignature(payload);
        headers['X-SignalScope-Signature'] = signature;
      }
      
      // Send with retry logic
      const response = await retryWithBackoff(
        async () => {
          const res = await fetch(this.webhookUrl, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
            signal: AbortSignal.timeout(WEBHOOK_CONFIG.TIMEOUT)
          });
          
          if (!res.ok) {
            const error = new Error(`HTTP ${res.status}: ${res.statusText}`);
            error.status = res.status;
            
            // Don't retry on client errors
            if (res.status >= 400 && res.status < 500) {
              error.shouldRetry = false;
            }
            
            throw error;
          }
          
          return res;
        },
        maxRetries,
        WEBHOOK_CONFIG.RETRY_DELAY_BASE
      );
      
      logger.info('Webhook sent successfully:', response.status);
      
      return {
        success: true,
        status: response.status,
        idempotencyKey
      };
    } catch (error) {
      logger.error('Webhook send failed:', error);
      
      return {
        success: false,
        error: error.message,
        status: error.status
      };
    }
  }

  async generateHmacSignature(payload) {
    try {
      const encoder = new TextEncoder();
      const data = encoder.encode(JSON.stringify(payload));
      const key = encoder.encode(this.webhookSecret);
      
      // Import key
      const cryptoKey = await crypto.subtle.importKey(
        'raw',
        key,
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
      );
      
      // Generate signature
      const signature = await crypto.subtle.sign('HMAC', cryptoKey, data);
      
      // Convert to hex string
      const hexString = Array.from(new Uint8Array(signature))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
      
      return `sha256=${hexString}`;
    } catch (error) {
      logger.error('Failed to generate HMAC signature:', error);
      throw error;
    }
  }

  async retryFailed() {
    if (this.failedQueue.length === 0) {
      return;
    }
    
    logger.info(`Retrying ${this.failedQueue.length} failed messages`);
    
    const settings = await this.storageManager.get(STORAGE_KEYS.RETRY_ATTEMPTS);
    const maxRetries = settings[STORAGE_KEYS.RETRY_ATTEMPTS] || WEBHOOK_CONFIG.MAX_RETRY_ATTEMPTS;
    
    const retryable = [];
    const permanent = [];
    
    // Separate retryable from permanently failed
    this.failedQueue.forEach((msg) => {
      if (msg.attempts < maxRetries) {
        retryable.push(msg);
      } else {
        permanent.push(msg);
      }
    });
    
    // Clear failed queue
    this.failedQueue = [];
    
    // Move retryable back to main queue
    retryable.forEach((msg) => {
      msg.retryAt = new Date().toISOString();
      this.messageQueue.push(msg);
    });
    
    // Log permanently failed
    if (permanent.length > 0) {
      logger.warn(`${permanent.length} messages permanently failed after ${maxRetries} attempts`);
      await this.updateStats({
        failed: permanent.length
      });
    }
    
    // Save updated queues
    await this.saveQueue();
    
    // Process if we have messages
    if (this.messageQueue.length > 0) {
      await this.processBatch();
    }
  }

  async testWebhook(testData = {}) {
    try {
      const testMessage = {
        id: 'test-' + generateId(),
        content: testData.content || 'This is a test message from SignalScope',
        platform: testData.platform || 'test',
        author: testData.author || 'Test User',
        timestamp: new Date().toISOString(),
        url: testData.url || 'https://signalscope.ai/test',
        intelligence: {
          entities: {
            tickers: [],
            prices: [],
            percentages: [],
            quantities: []
          },
          sentiment: {
            score: 0.5,
            sentiment: 'neutral',
            confidence: 0.8
          },
          importance: 5
        },
        capturedAt: new Date().toISOString(),
        test: true
      };
      
      const result = await this.sendWebhook(testMessage, 1);
      
      return {
        success: result.success,
        status: result.status,
        error: result.error,
        message: result.success ? 'Webhook test successful' : 'Webhook test failed'
      };
    } catch (error) {
      logger.error('Webhook test error:', error);
      return {
        success: false,
        error: error.message,
        message: 'Webhook test failed'
      };
    }
  }

  async clearQueue() {
    this.messageQueue = [];
    this.failedQueue = [];
    
    await this.storageManager.set({
      [STORAGE_KEYS.MESSAGE_QUEUE]: [],
      [STORAGE_KEYS.FAILED_QUEUE]: []
    });
    
    logger.info('Queues cleared');
  }

  async getQueueSize() {
    return {
      pending: this.messageQueue.length,
      failed: this.failedQueue.length,
      total: this.messageQueue.length + this.failedQueue.length
    };
  }

  async cleanupOldMessages() {
    try {
      const cutoffDate = new Date();
      cutoffDate.setHours(cutoffDate.getHours() - 24); // 24 hours old
      
      const cutoffTime = cutoffDate.getTime();
      
      // Filter out old messages
      const originalQueueSize = this.messageQueue.length;
      this.messageQueue = this.messageQueue.filter((msg) => {
        const msgTime = new Date(msg.queuedAt).getTime();
        return msgTime > cutoffTime;
      });
      
      const removed = originalQueueSize - this.messageQueue.length;
      
      if (removed > 0) {
        logger.info(`Cleaned up ${removed} old messages`);
        await this.saveQueue();
      }
    } catch (error) {
      logger.error('Cleanup error:', error);
    }
  }

  async saveQueue() {
    await this.storageManager.set({
      [STORAGE_KEYS.MESSAGE_QUEUE]: this.messageQueue,
      [STORAGE_KEYS.FAILED_QUEUE]: this.failedQueue
    });
  }

  async updateStats(update) {
    try {
      const stats = await this.storageManager.get(STORAGE_KEYS.STATS);
      const currentStats = stats[STORAGE_KEYS.STATS] || {
        totalSent: 0,
        totalFailed: 0,
        lastSuccess: null,
        lastFailure: null
      };
      
      if (update.sent) {
        currentStats.totalSent += update.sent;
      }
      
      if (update.failed) {
        currentStats.totalFailed += update.failed;
      }
      
      if (update.success) {
        currentStats.lastSuccess = new Date().toISOString();
      } else if (update.success === false) {
        currentStats.lastFailure = new Date().toISOString();
      }
      
      await this.storageManager.set({
        [STORAGE_KEYS.STATS]: currentStats
      });
    } catch (error) {
      logger.error('Failed to update stats:', error);
    }
  }
}

export default WebhookManager;