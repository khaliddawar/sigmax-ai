import { MESSAGE_TYPES, STORAGE_KEYS, ALARM_NAMES, DEFAULT_SETTINGS } from '../shared/constants.js';
import { createLogger } from '../shared/logger.js';
import { isValidUrl } from '../shared/utils.js';
import WebhookManager from './webhook-manager.js';
import StorageManager from './storage-manager.js';
import MessageHandler from './message-handler.js';
import { configureForLocalBackend } from '../config/local-backend-config.js';

const logger = createLogger('ServiceWorker');

class ServiceWorker {
  constructor() {
    this.webhookManager = new WebhookManager();
    this.storageManager = new StorageManager();
    this.messageHandler = new MessageHandler(this);
    this.isInitialized = false;
    this.batchIntervalId = null;  // Track interval for cleanup
  }

  async initialize() {
    try {
      logger.info('Initializing service worker...');
      
      // Configure for local backend (development mode)
      await configureForLocalBackend();
      logger.info('Configured for local backend at http://localhost:8000');
      
      // Load settings from storage
      await this.loadSettings();
      
      // Set up message listeners
      this.setupMessageListeners();
      
      // Set up alarm listeners
      this.setupAlarmListeners();
      
      // Set up installation and activation handlers
      this.setupLifecycleHandlers();
      
      // Initialize webhook manager
      await this.webhookManager.initialize();
      
      // Sync queued messages to preview buffer
      await this.syncQueueToPreview();
      
      // Set up context menu
      await this.setupContextMenu();
      
      // Set up sidebar panel behavior
      this.setupSidePanel();
      
      this.isInitialized = true;
      logger.info('Service worker initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize service worker:', error);
      throw error;
    }
  }

  async loadSettings() {
    try {
      const settings = await this.storageManager.get([
        STORAGE_KEYS.ENABLED,
        STORAGE_KEYS.WEBHOOK_URL,
        STORAGE_KEYS.WEBHOOK_SECRET,
        STORAGE_KEYS.BATCH_SIZE,
        STORAGE_KEYS.BATCH_INTERVAL
      ]);
      
      // Apply default settings if not set
      const finalSettings = { ...DEFAULT_SETTINGS, ...settings };
      
      // Save back to ensure defaults are stored
      await this.storageManager.set(finalSettings);
      
      logger.info('Settings loaded:', finalSettings);
      return finalSettings;
    } catch (error) {
      logger.error('Failed to load settings:', error);
      throw error;
    }
  }

  setupMessageListeners() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      // Validate sender
      if (sender.id !== chrome.runtime.id) {
        logger.warn('Message from unknown sender:', sender);
        return false;
      }
      
      // Handle message asynchronously
      this.handleMessage(request, sender)
        .then((response) => sendResponse({ success: true, data: response }))
        .catch((error) => {
          logger.error('Message handling error:', error);
          sendResponse({ success: false, error: error.message });
        });
      
      // Return true to indicate async response
      return true;
    });
  }

  async handleMessage(request, sender) {
    const { type, data } = request;
    logger.debug('Handling message:', type, data);
    
    switch (type) {
      case MESSAGE_TYPES.CAPTURE_MESSAGE:
        return await this.handleCaptureMessage(data, sender);
        
      case 'CAPTURE_MESSAGE_BATCH':
        return await this.handleCaptureMessageBatch(data, sender);
        
      case MESSAGE_TYPES.UPDATE_SETTINGS:
        return await this.handleUpdateSettings(data);
        
      case MESSAGE_TYPES.GET_STATS:
        return await this.handleGetStats();
        
      case MESSAGE_TYPES.CLEAR_QUEUE:
        return await this.handleClearQueue();
        
      case MESSAGE_TYPES.TEST_WEBHOOK:
        return await this.handleTestWebhook(data);
        
      case MESSAGE_TYPES.PLATFORM_DETECTED:
        return await this.handlePlatformDetected(data, sender);
        
      case MESSAGE_TYPES.TOGGLE_CAPTURE:
        return await this.handleToggleCapture();
        
      case 'GET_PREVIEW_MESSAGES':
        return this.messageHandler.getPreviewMessages();
        
      case 'CLEAR_PREVIEW':
        this.messageHandler.clearPreviewBuffer();
        return { success: true };
        
      case 'PROCESS_QUEUE':
        // Manually trigger queue processing
        await this.webhookManager.processBatch();
        return { success: true, message: 'Queue processing triggered' };
        
      case 'SYNC_QUEUE_TO_PREVIEW':
        // Manually sync queue to preview buffer
        await this.syncQueueToPreview();
        return { success: true, message: 'Queue synced to preview' };
        
      case 'INJECT_CONTENT_SCRIPT':
        // Programmatically inject content script
        return await this.handleInjectContentScript(data, sender);

      case MESSAGE_TYPES.CAPTURE_STARTED:
        return await this.handleCaptureStarted(data, sender);

      case MESSAGE_TYPES.CAPTURE_STOPPED:
        return await this.handleCaptureStopped(data, sender);

      case MESSAGE_TYPES.GET_SETTINGS:
        return await this.handleGetSettings();

      default:
        throw new Error(`Unknown message type: ${type}`);
    }
  }

  async handleCaptureMessage(data, sender) {
    try {
      console.log('🔄 Service Worker received message - Author:', data.author, 'Content:', data.content?.substring(0, 50));

      const settings = await this.storageManager.get(STORAGE_KEYS.ENABLED);

      if (!settings[STORAGE_KEYS.ENABLED]) {
        logger.debug('Extension disabled, ignoring message');
        return { captured: false, reason: 'Extension disabled' };
      }

      // Parse timestamp for ordering
      const messageTimestamp = this.parseMessageTimestamp(data.timestamp);

      // Add metadata with enhanced timestamp handling
      const message = {
        ...data,
        tabId: sender.tab?.id,
        url: sender.tab?.url,
        capturedAt: new Date().toISOString(),
        parsedTimestamp: messageTimestamp,
        sequenceId: this.generateSequenceId(messageTimestamp, data.id)
      };

      // Add to preview buffer for sidebar
      this.messageHandler.addToPreviewBuffer(message);

      // Queue message for webhook delivery with timestamp-based ordering
      await this.webhookManager.queueMessage(message, { preserveOrder: true });

      logger.info('Message captured and queued:', message.id, 'at', messageTimestamp);
      return { captured: true, messageId: message.id, sequenceId: message.sequenceId };
    } catch (error) {
      logger.error('Failed to capture message:', error);
      throw error;
    }
  }

  async handleCaptureMessageBatch(messages, sender) {
    try {
      if (!Array.isArray(messages)) {
        logger.error('Invalid batch: not an array');
        return { success: false, error: 'Messages must be an array' };
      }
      
      logger.info(`Batch received: ${messages.length} messages from tab ${sender.tab?.id}`);
      
      // Queue all messages
      const queuedIds = [];
      for (const message of messages) {
        const messageId = await this.webhookManager.queueMessage(message);
        queuedIds.push(messageId);
      }
      
      logger.info(`Batch queued: ${queuedIds.length} messages`);
      
      // Update stats
      const stats = await this.storageManager.get(STORAGE_KEYS.STATS);
      const currentStats = stats[STORAGE_KEYS.STATS] || {};
      currentStats.totalCaptured = (currentStats.totalCaptured || 0) + messages.length;
      await this.storageManager.set({
        [STORAGE_KEYS.STATS]: currentStats
      });
      
      return { success: true, queued: queuedIds.length };
    } catch (error) {
      logger.error('Failed to handle message batch:', error);
      return { success: false, error: error.message };
    }
  }

  async handleUpdateSettings(settings) {
    try {
      // Validate webhook URL if provided
      if (settings[STORAGE_KEYS.WEBHOOK_URL]) {
        if (!isValidUrl(settings[STORAGE_KEYS.WEBHOOK_URL])) {
          throw new Error('Invalid webhook URL');
        }
      }
      
      // Save settings
      await this.storageManager.set(settings);
      
      // Update webhook manager configuration
      if (settings[STORAGE_KEYS.WEBHOOK_URL] || settings[STORAGE_KEYS.WEBHOOK_SECRET]) {
        await this.webhookManager.updateConfig({
          url: settings[STORAGE_KEYS.WEBHOOK_URL],
          secret: settings[STORAGE_KEYS.WEBHOOK_SECRET]
        });
      }
      
      // Update batch processing
      if (settings[STORAGE_KEYS.BATCH_INTERVAL]) {
        await this.setupBatchAlarm(settings[STORAGE_KEYS.BATCH_INTERVAL]);
      }
      
      logger.info('Settings updated:', settings);
      return { updated: true };
    } catch (error) {
      logger.error('Failed to update settings:', error);
      throw error;
    }
  }

  async handleGetStats() {
    try {
      const stats = await this.storageManager.get(STORAGE_KEYS.STATS);
      const queueSize = await this.webhookManager.getQueueSize();
      
      return {
        ...stats[STORAGE_KEYS.STATS],
        queueSize,
        isEnabled: await this.isEnabled(),
        totalCaptured: stats[STORAGE_KEYS.STATS]?.totalSent || 0,
        totalSent: stats[STORAGE_KEYS.STATS]?.totalSent || 0
      };
    } catch (error) {
      logger.error('Failed to get stats:', error);
      throw error;
    }
  }
  
  async handleToggleCapture() {
    try {
      const currentState = await this.storageManager.get(STORAGE_KEYS.ENABLED);
      const newState = !currentState[STORAGE_KEYS.ENABLED];
      
      await this.storageManager.set({
        [STORAGE_KEYS.ENABLED]: newState
      });
      
      // Broadcast state change
      await this.messageHandler.broadcastUpdate('CAPTURE_STATE_CHANGED', { enabled: newState });
      
      logger.info(`Capture ${newState ? 'enabled' : 'disabled'}`);
      return { enabled: newState };
    } catch (error) {
      logger.error('Failed to toggle capture:', error);
      throw error;
    }
  }

  async handleClearQueue() {
    try {
      await this.webhookManager.clearQueue();
      logger.info('Queue cleared');
      return { cleared: true };
    } catch (error) {
      logger.error('Failed to clear queue:', error);
      throw error;
    }
  }

  async handleInjectContentScript(data, sender) {
    try {
      const tabId = data?.tabId || sender?.tab?.id;
      
      if (!tabId) {
        throw new Error('No tab ID provided for content script injection');
      }
      
      logger.info('Attempting programmatic content script injection', { tabId });
      
      // Inject the content script programmatically
      await chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: ['content/content-script.js']
      });
      
      logger.info('Content script injected successfully', { tabId });
      
      return {
        success: true,
        message: 'Content script injected successfully',
        tabId: tabId
      };
      
    } catch (error) {
      logger.error('Failed to inject content script:', error);
      return { 
        success: false, 
        error: error.message,
        details: 'Programmatic injection failed'
      };
    }
  }

  async handleTestWebhook(data) {
    try {
      const result = await this.webhookManager.testWebhook(data);
      logger.info('Webhook test result:', result);
      return result;
    } catch (error) {
      logger.error('Webhook test failed:', error);
      throw error;
    }
  }

  async handlePlatformDetected(data, sender) {
    try {
      logger.info('Platform detected:', data.platform, 'on tab:', sender.tab?.id);
      
      // Store platform info for the tab
      await this.storageManager.set({
        [`tab_${sender.tab?.id}_platform`]: data.platform
      });
      
      // Update badge to show active
      await this.updateBadge(sender.tab?.id, true);
      
      return { acknowledged: true };
    } catch (error) {
      logger.error('Failed to handle platform detection:', error);
      throw error;
    }
  }

  setupSidePanel() {
    // Configure side panel to open on action click
    if (chrome.sidePanel) {
      chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
        .catch((error) => {
          logger.warn('Failed to set panel behavior:', error);
        });
      
      // Allow manual opening of side panel
      chrome.action.onClicked.addListener((tab) => {
        chrome.sidePanel.open({ windowId: tab.windowId })
          .catch((error) => {
            logger.error('Failed to open side panel:', error);
          });
      });
      
      logger.info('Side panel configured');
    } else {
      logger.warn('Side panel API not available');
    }
  }

  setupAlarmListeners() {
    chrome.alarms.onAlarm.addListener(async (alarm) => {
      logger.debug('Alarm triggered:', alarm.name);
      
      switch (alarm.name) {
        case ALARM_NAMES.BATCH_PROCESS:
          await this.processBatch();
          break;
          
        case ALARM_NAMES.RETRY_FAILED:
          await this.retryFailedMessages();
          break;
          
        case ALARM_NAMES.CLEANUP:
          await this.performCleanup();
          break;
          
        default:
          logger.warn('Unknown alarm:', alarm.name);
      }
    });
    
    // Set up initial alarms
    this.setupInitialAlarms();
  }

  async setupInitialAlarms() {
    try {
      const settings = await this.loadSettings();
      
      // Batch processing alarm
      await this.setupBatchAlarm(settings.batchInterval);
      
      // Retry failed messages every 5 minutes
      chrome.alarms.create(ALARM_NAMES.RETRY_FAILED, {
        periodInMinutes: 5
      });
      
      // Cleanup old data every hour
      chrome.alarms.create(ALARM_NAMES.CLEANUP, {
        periodInMinutes: 60
      });
      
      logger.info('Alarms set up successfully');
    } catch (error) {
      logger.error('Failed to set up alarms:', error);
    }
  }

  async setupBatchAlarm(intervalMs) {
    // For intervals less than 1 minute, use setInterval instead of chrome.alarms
    if (intervalMs < 60000) {
      // Clear any existing interval
      if (this.batchIntervalId) {
        clearInterval(this.batchIntervalId);
      }
      
      // Set up regular interval for short periods
      this.batchIntervalId = setInterval(async () => {
        await this.processBatch();
      }, intervalMs);
      
      logger.info(`Batch processing interval set for every ${intervalMs / 1000} seconds`);
    } else {
      // Use chrome alarms for longer periods (1 minute or more)
      const periodInMinutes = Math.max(1, intervalMs / 60000);
      
      chrome.alarms.create(ALARM_NAMES.BATCH_PROCESS, {
        periodInMinutes
      });
      
      logger.info(`Batch processing alarm set for every ${periodInMinutes} minutes`);
    }
  }

  async processBatch() {
    try {
      const isEnabled = await this.isEnabled();
      if (!isEnabled) {
        logger.debug('Extension disabled, skipping batch processing');
        return;
      }
      
      await this.webhookManager.processBatch();
    } catch (error) {
      logger.error('Batch processing failed:', error);
    }
  }

  async retryFailedMessages() {
    try {
      const isEnabled = await this.isEnabled();
      if (!isEnabled) {
        return;
      }
      
      await this.webhookManager.retryFailed();
    } catch (error) {
      logger.error('Failed message retry failed:', error);
    }
  }

  async performCleanup() {
    try {
      // Clean up old messages from queue
      await this.webhookManager.cleanupOldMessages();
      
      // Clean up old stats
      const stats = await this.storageManager.get(STORAGE_KEYS.STATS);
      if (stats[STORAGE_KEYS.STATS]) {
        // Keep only last 7 days of stats
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - 7);
        // Implementation would filter stats by date
      }
      
      logger.info('Cleanup completed');
    } catch (error) {
      logger.error('Cleanup failed:', error);
    }
  }

  setupLifecycleHandlers() {
    // Handle extension installation
    chrome.runtime.onInstalled.addListener(async (details) => {
      logger.info('Extension installed/updated:', details.reason);
      
      if (details.reason === 'install') {
        await this.handleFirstInstall();
      } else if (details.reason === 'update') {
        await this.handleUpdate(details.previousVersion);
      }
    });
    
    // Handle browser startup
    chrome.runtime.onStartup.addListener(async () => {
      logger.info('Browser started, reinitializing extension');
      await this.initialize();
    });
  }

  async handleFirstInstall() {
    try {
      // Set default settings
      await this.storageManager.set(DEFAULT_SETTINGS);
      
      // Open options page for initial setup
      chrome.runtime.openOptionsPage();
      
      logger.info('First installation completed');
    } catch (error) {
      logger.error('First installation setup failed:', error);
    }
  }

  async handleUpdate(previousVersion) {
    logger.info(`Extension updated from ${previousVersion} to ${chrome.runtime.getManifest().version}`);
    // Handle any migration if needed
  }

  async syncQueueToPreview() {
    try {
      // Get queued messages from storage
      const storage = await this.storageManager.get(STORAGE_KEYS.MESSAGE_QUEUE);
      const queue = storage[STORAGE_KEYS.MESSAGE_QUEUE] || [];
      
      if (queue.length > 0) {
        logger.info(`Syncing ${queue.length} queued messages to preview buffer`);
        
        // Add recent messages to preview buffer (limit to last 50)
        const recentMessages = queue.slice(-50).reverse();
        for (const message of recentMessages) {
          this.messageHandler.addToPreviewBuffer(message);
        }
        
        logger.info('Queue synced to preview buffer');
      }
    } catch (error) {
      logger.error('Failed to sync queue to preview:', error);
    }
  }

  async setupContextMenu() {
    try {
      chrome.contextMenus.create({
        id: 'signalscope-capture',
        title: 'Capture with SignalScope',
        contexts: ['selection', 'page']
      });
      
      chrome.contextMenus.onClicked.addListener(async (info, tab) => {
        if (info.menuItemId === 'signalscope-capture') {
          await this.handleContextMenuCapture(info, tab);
        }
      });
      
      logger.info('Context menu set up');
    } catch (error) {
      logger.error('Failed to set up context menu:', error);
    }
  }

  async handleContextMenuCapture(info, tab) {
    try {
      const message = {
        id: `manual-${Date.now()}`,
        content: info.selectionText || 'Manual capture',
        url: tab.url,
        timestamp: new Date().toISOString(),
        source: 'context-menu'
      };
      
      await this.webhookManager.queueMessage(message);
      
      // Show notification
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/assets/icons/icon-48.png',
        title: 'SignalScope',
        message: 'Content captured successfully'
      });
    } catch (error) {
      logger.error('Context menu capture failed:', error);
    }
  }

  async updateBadge(tabId, active) {
    try {
      if (active) {
        chrome.action.setBadgeText({ text: 'ON', tabId });
        chrome.action.setBadgeBackgroundColor({ color: '#4CAF50', tabId });
      } else {
        chrome.action.setBadgeText({ text: '', tabId });
      }
    } catch (error) {
      logger.error('Failed to update badge:', error);
    }
  }

  async handleCaptureStarted(data, sender) {
    try {
      logger.info('Capture started on tab:', sender.tab?.id, 'Platform:', data.platform, 'Mode:', data.mode);

      // Update badge to show active
      await this.updateBadge(sender.tab?.id, true);

      return { acknowledged: true, status: 'capture_started' };
    } catch (error) {
      logger.error('Failed to handle capture started:', error);
      throw error;
    }
  }

  async handleCaptureStopped(data, sender) {
    try {
      logger.info('Capture stopped on tab:', sender.tab?.id);

      // Update badge to show inactive
      await this.updateBadge(sender.tab?.id, false);

      return { acknowledged: true, status: 'capture_stopped' };
    } catch (error) {
      logger.error('Failed to handle capture stopped:', error);
      throw error;
    }
  }

  async handleGetSettings() {
    try {
      const settings = await this.loadSettings();
      return settings;
    } catch (error) {
      logger.error('Failed to get settings:', error);
      throw error;
    }
  }

  async isEnabled() {
    const settings = await this.storageManager.get(STORAGE_KEYS.ENABLED);
    return settings[STORAGE_KEYS.ENABLED] !== false;
  }

  parseMessageTimestamp(timestamp) {
    try {
      if (!timestamp) {
        return new Date().getTime();
      }

      // Handle ISO string timestamps
      if (typeof timestamp === 'string') {
        const date = new Date(timestamp);
        if (!isNaN(date.getTime())) {
          return date.getTime();
        }
      }

      // Handle timestamp numbers
      if (typeof timestamp === 'number') {
        // Convert seconds to milliseconds if needed
        return timestamp > 1000000000000 ? timestamp : timestamp * 1000;
      }

      // Fallback to current time
      return new Date().getTime();
    } catch (error) {
      logger.warn('Failed to parse timestamp:', timestamp, error);
      return new Date().getTime();
    }
  }

  generateSequenceId(timestamp, messageId) {
    // Create a sequence ID that combines timestamp and message ID for ordering
    const paddedTimestamp = timestamp.toString().padStart(13, '0');
    const shortId = messageId ? messageId.slice(-8) : Math.random().toString(36).slice(-8);
    return `${paddedTimestamp}-${shortId}`;
  }
}

// Initialize service worker
const serviceWorker = new ServiceWorker();
serviceWorker.initialize().catch((error) => {
  console.error('Failed to initialize service worker:', error);
});

// Make service worker globally accessible for debugging
self.signalScopeWorker = serviceWorker;

// Export for testing
export default ServiceWorker;