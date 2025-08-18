import { createLogger } from '../shared/logger.js';
import { MESSAGE_TYPES, STORAGE_KEYS } from '../shared/constants.js';
import { debounce, throttle } from '../shared/utils.js';

const logger = createLogger('Sidebar');

class MessageThrottler {
  constructor(callback, limit = 10, interval = 100) {
    this.callback = callback;
    this.limit = limit;
    this.interval = interval;
    this.queue = [];
    this.processing = false;
  }

  add(message) {
    this.queue.push(message);
    if (!this.processing) {
      this.process();
    }
  }

  process() {
    if (this.queue.length === 0) {
      this.processing = false;
      return;
    }

    this.processing = true;
    const batch = this.queue.splice(0, this.limit);
    
    batch.forEach(msg => this.callback(msg));
    
    setTimeout(() => this.process(), this.interval);
  }
}

class SidebarManager {
  constructor() {
    this.messages = [];
    this.filteredMessages = [];
    this.isPreviewActive = true;
    this.isCaptureActive = true;
    this.currentFilter = 'all';
    this.searchTerm = '';
    this.maxMessages = 500;
    this.displayLimit = 100;
    
    // Throttle message additions for performance
    this.messageThrottler = new MessageThrottler(
      (msg) => this.addMessageToUI(msg),
      5,
      50
    );
    
    this.init();
  }

  async init() {
    try {
      console.log('[Sidebar] Initializing...');
      
      // Load initial state
      await this.loadInitialState();
      
      // Set up event listeners
      this.setupEventListeners();
      
      // Listen for new messages
      this.listenForMessages();
      
      // Update stats periodically
      this.startStatsUpdate();
      
      // Load existing messages
      await this.loadMessages();
      
      // Debug: Check what we have
      console.log('[Sidebar] Init complete. Messages:', this.messages.length);
      
      // Debug: Try to get queue directly
      chrome.storage.local.get('messageQueue', (data) => {
        console.log('[Sidebar] Queue in storage:', data.messageQueue?.length || 0);
        if (data.messageQueue?.length > 0 && this.messages.length === 0) {
          console.warn('[Sidebar] Queue has messages but preview is empty!');
          console.log('[Sidebar] First queued message:', data.messageQueue[0]);
        }
      });
      
      logger.info('Sidebar initialized successfully');
    } catch (error) {
      console.error('[Sidebar] Failed to initialize:', error);
      logger.error('Failed to initialize sidebar:', error);
      this.showError('Failed to initialize sidebar');
    }
  }

  async loadInitialState() {
    try {
      const result = await chrome.storage.local.get([
        STORAGE_KEYS.ENABLED,
        STORAGE_KEYS.WEBHOOK_URL
      ]);
      
      this.isCaptureActive = result[STORAGE_KEYS.ENABLED] !== false;
      this.updateCaptureButton(this.isCaptureActive);
      
      // Update connection status
      const statusIndicator = document.getElementById('statusIndicator');
      const statusText = document.getElementById('statusText');
      
      if (result[STORAGE_KEYS.WEBHOOK_URL]) {
        statusIndicator.classList.add('connected');
        statusIndicator.classList.remove('disconnected');
        statusText.textContent = 'Connected';
      } else {
        statusIndicator.classList.add('disconnected');
        statusIndicator.classList.remove('connected');
        statusText.textContent = 'Configure';
      }
    } catch (error) {
      logger.error('Failed to load initial state:', error);
    }
  }

  async loadMessages() {
    try {
      console.log('[Sidebar] Loading messages...');
      
      // Add timeout to prevent hanging
      const response = await Promise.race([
        chrome.runtime.sendMessage({
          type: 'GET_PREVIEW_MESSAGES'
        }),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout')), 5000)
        )
      ]);
      
      console.log('[Sidebar] Response received:', response);
      
      // Handle wrapped response format
      let messages = null;
      if (response?.success && response.data) {
        messages = response.data;
      } else if (Array.isArray(response)) {
        messages = response;
      }
      
      if (messages && Array.isArray(messages)) {
        console.log(`[Sidebar] Got ${messages.length} messages`);
        this.messages = messages;
        this.applyFilters();
        this.renderMessages();
        this.updateMessageStats();
      } else if (response?.success === false) {
        console.error('[Sidebar] Error response:', response.error);
        this.showError(`Failed to load messages: ${response.error}`);
      } else {
        console.warn('[Sidebar] No messages or invalid response:', response);
        this.messages = [];
        this.renderMessages();
        this.updateMessageStats();
        
        // Try to sync queue to preview if empty
        if (this.messages.length === 0) {
          console.log('[Sidebar] Attempting to sync queue to preview...');
          this.syncQueueToPreview();
        }
      }
    } catch (error) {
      console.error('[Sidebar] Failed to load messages:', error);
      logger.error('Failed to load messages:', error);
      
      if (error.message === 'Timeout') {
        this.showError('Service worker not responding. Try reloading the extension.');
      } else {
        this.showError('Failed to load messages. Check console for details.');
      }
    }
  }

  listenForMessages() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      console.log('[Sidebar] Message received:', request.type, request.data);
      
      if (request.type === 'NEW_PREVIEW_MESSAGE' && this.isPreviewActive) {
        console.log('[Sidebar] Adding message to preview:', request.data);
        this.messageThrottler.add(request.data);
      } else if (request.type === 'CAPTURE_STATE_CHANGED') {
        this.isCaptureActive = request.data.enabled;
        this.updateCaptureButton(this.isCaptureActive);
      }
    });
  }

  addMessageToUI(message) {
    // Add to messages array
    this.messages.unshift(message);
    
    // Limit array size
    if (this.messages.length > this.maxMessages) {
      this.messages = this.messages.slice(0, this.maxMessages);
    }
    
    // Check if message passes filters
    if (this.shouldShowMessage(message)) {
      this.renderNewMessage(message);
    }
    
    this.updateMessageStats();
  }

  shouldShowMessage(message) {
    // Platform filter
    if (this.currentFilter !== 'all' && message.platform !== this.currentFilter) {
      return false;
    }
    
    // Search filter
    if (this.searchTerm && !this.matchesSearch(message)) {
      return false;
    }
    
    return true;
  }

  matchesSearch(message) {
    const term = this.searchTerm.toLowerCase();
    return (
      message.content?.toLowerCase().includes(term) ||
      message.author?.toLowerCase().includes(term) ||
      message.channel?.toLowerCase().includes(term)
    );
  }

  applyFilters() {
    this.filteredMessages = this.messages.filter(msg => this.shouldShowMessage(msg));
  }

  renderMessages() {
    const container = document.getElementById('messageList');
    const emptyState = document.getElementById('emptyState');
    
    if (this.filteredMessages.length === 0) {
      emptyState.style.display = 'flex';
      container.innerHTML = '';
      return;
    }
    
    emptyState.style.display = 'none';
    container.innerHTML = '';
    
    // Render limited number of messages for performance
    const messagesToRender = this.filteredMessages.slice(0, this.displayLimit);
    
    const fragment = document.createDocumentFragment();
    messagesToRender.forEach(message => {
      fragment.appendChild(this.createMessageElement(message));
    });
    
    container.appendChild(fragment);
  }

  renderNewMessage(message) {
    const container = document.getElementById('messageList');
    const emptyState = document.getElementById('emptyState');
    
    // Hide empty state
    emptyState.style.display = 'none';
    
    const element = this.createMessageElement(message);
    element.classList.add('message-new');
    
    // Insert at the beginning
    container.insertBefore(element, container.firstChild);
    
    // Remove animation class after animation
    setTimeout(() => element.classList.remove('message-new'), 500);
    
    // Remove old messages if too many in DOM
    while (container.children.length > this.displayLimit) {
      container.removeChild(container.lastChild);
    }
  }

  createMessageElement(message) {
    const div = document.createElement('div');
    div.className = `message-item platform-${message.platform || 'unknown'}`;
    
    const messageTime = this.formatTime(message.timestamp);
    const authorName = this.escapeHtml(message.author || 'Unknown');
    const channelName = this.escapeHtml(message.channel || 'Live Chat');
    const messageContent = this.escapeHtml(message.content || '');
    const platform = message.platform || 'unknown';
    
    // Build reactions HTML
    let reactionsHtml = '';
    if (message.reactions && message.reactions.length > 0) {
      const reactionItems = message.reactions.map(reaction => 
        `<span class="message-reaction">${reaction.emoji} ${reaction.count}</span>`
      ).join('');
      reactionsHtml = `<div class="message-reactions">${reactionItems}</div>`;
    }
    
    // Build attachments HTML
    let attachmentsHtml = '';
    if (message.attachments && message.attachments.length > 0) {
      const attachmentItems = message.attachments.map(attachment => {
        if (attachment.type === 'image') {
          // Display images inline
          return `<img src="${attachment.url}" alt="${attachment.alt || 'Shared Image'}" class="message-attachment-image" onclick="window.open('${attachment.url}', '_blank')" />`;
        } else if (attachment.type === 'link') {
          // Display link previews
          const imageHtml = attachment.image ? 
            `<img src="${attachment.image}" alt="" class="message-link-preview-image" />` : '';
          const descriptionHtml = attachment.description ? 
            `<div class="message-link-preview-description">${this.escapeHtml(attachment.description)}</div>` : '';
          const domain = this.extractDomain(attachment.url);
          
          return `
            <a href="${attachment.url}" target="_blank" class="message-link-preview">
              ${imageHtml}
              <div class="message-link-preview-content">
                <div class="message-link-preview-title">${this.escapeHtml(attachment.title || 'Link')}</div>
                ${descriptionHtml}
                <div class="message-link-preview-domain">🔗 ${domain}</div>
              </div>
            </a>
          `;
        } else {
          // Display other attachments as simple links
          return `<a href="${attachment.url || '#'}" target="_blank" class="message-attachment">📎 ${attachment.name || attachment.type || 'Attachment'}</a>`;
        }
      }).join('');
      attachmentsHtml = `<div class="message-attachments">${attachmentItems}</div>`;
    }
    
    div.innerHTML = `
      <div class="message-meta">
        <span class="message-author-name">${authorName}</span>
        <span class="message-platform-badge">${channelName}</span>
        <span class="message-timestamp">${messageTime}</span>
      </div>
      <div class="message-text">${messageContent}</div>
      ${reactionsHtml}
      ${attachmentsHtml}
    `;
    
    return div;
  }

  formatTime(timestamp) {
    if (!timestamp) return '--:--';
    
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return '--:--';
    
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true
    });
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  extractDomain(url) {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname.replace('www.', '');
    } catch {
      return 'Unknown';
    }
  }

  updateMessageStats() {
    document.getElementById('filteredCount').textContent = this.filteredMessages.length;
    document.getElementById('totalMessages').textContent = this.messages.length;
  }

  setupEventListeners() {
    // Toggle preview
    document.getElementById('togglePreview').addEventListener('click', () => {
      this.togglePreview();
    });
    
    // Clear preview
    document.getElementById('clearPreview').addEventListener('click', () => {
      this.clearMessages();
    });
    
    // Platform filter
    document.getElementById('platformFilter').addEventListener('change', (e) => {
      this.currentFilter = e.target.value;
      this.applyFilters();
      this.renderMessages();
      this.updateMessageStats();
    });
    
    // Search filter with debounce
    const searchInput = document.getElementById('searchFilter');
    const debouncedSearch = debounce(() => {
      this.searchTerm = searchInput.value;
      this.applyFilters();
      this.renderMessages();
      this.updateMessageStats();
    }, 300);
    
    searchInput.addEventListener('input', debouncedSearch);
    
    // Control buttons
    document.getElementById('pauseCapture').addEventListener('click', () => {
      this.toggleCapture();
    });
    
    document.getElementById('openSettings').addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });
    
    document.getElementById('exportMessages').addEventListener('click', () => {
      this.exportMessages();
    });
  }

  togglePreview() {
    this.isPreviewActive = !this.isPreviewActive;
    const btn = document.getElementById('togglePreview');
    
    if (this.isPreviewActive) {
      btn.innerHTML = `<span class="btn-icon">⏸️</span>`;
      btn.title = 'Pause Preview';
    } else {
      btn.innerHTML = `<span class="btn-icon">▶️</span>`;
      btn.title = 'Resume Preview';
    }
  }

  async clearMessages() {
    this.messages = [];
    this.filteredMessages = [];
    this.renderMessages();
    this.updateMessageStats();
    
    try {
      await chrome.runtime.sendMessage({ type: 'CLEAR_PREVIEW' });
    } catch (error) {
      logger.error('Failed to clear preview buffer:', error);
    }
  }

  async toggleCapture() {
    try {
      const response = await chrome.runtime.sendMessage({ type: MESSAGE_TYPES.TOGGLE_CAPTURE });
      if (response && response.success) {
        this.isCaptureActive = response.data.enabled;
        this.updateCaptureButton(this.isCaptureActive);
      }
    } catch (error) {
      logger.error('Failed to toggle capture:', error);
      this.showError('Failed to toggle capture');
    }
  }

  updateCaptureButton(isActive) {
    const btn = document.getElementById('pauseCapture');
    if (isActive) {
      btn.innerHTML = `
        <span class="btn-icon">⏸️</span>
        <span>Pause Capture</span>
      `;
      btn.classList.remove('capture-paused');
    } else {
      btn.innerHTML = `
        <span class="btn-icon">▶️</span>
        <span>Resume Capture</span>
      `;
      btn.classList.add('capture-paused');
    }
  }

  async startStatsUpdate() {
    // Update immediately
    await this.updateStats();
    
    // Update every 2 seconds
    setInterval(() => this.updateStats(), 2000);
  }

  async updateStats() {
    try {
      const response = await chrome.runtime.sendMessage({ type: MESSAGE_TYPES.GET_STATS });
      
      if (response && response.success && response.data) {
        const stats = response.data;
        document.getElementById('messageCount').textContent = 
          this.formatNumber(stats.totalCaptured || 0);
        document.getElementById('queueSize').textContent = 
          this.formatNumber(stats.queueSize?.total || 0);
        document.getElementById('sentCount').textContent = 
          this.formatNumber(stats.totalSent || 0);
      }
    } catch (error) {
      logger.error('Failed to update stats:', error);
    }
  }

  formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  }

  exportMessages() {
    if (this.messages.length === 0) {
      this.showError('No messages to export');
      return;
    }
    
    const exportData = {
      version: '1.0',
      exportDate: new Date().toISOString(),
      totalMessages: this.messages.length,
      messages: this.messages
    };
    
    const data = JSON.stringify(exportData, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `signalscope-messages-${timestamp}.json`;
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    
    URL.revokeObjectURL(url);
    
    logger.info(`Exported ${this.messages.length} messages`);
  }

  async syncQueueToPreview() {
    try {
      console.log('[Sidebar] Requesting queue sync...');
      const response = await chrome.runtime.sendMessage({
        type: 'SYNC_QUEUE_TO_PREVIEW'
      });
      
      if (response?.success) {
        console.log('[Sidebar] Queue sync completed');
        // Reload messages after sync
        setTimeout(() => this.loadMessages(), 1000);
      } else {
        console.warn('[Sidebar] Queue sync failed:', response);
      }
    } catch (error) {
      console.error('[Sidebar] Queue sync error:', error);
    }
  }

  showError(message) {
    // Create a temporary error notification
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// Initialize sidebar when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new SidebarManager();
  });
} else {
  new SidebarManager();
}