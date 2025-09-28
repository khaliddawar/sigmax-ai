// Simple service worker without ES6 modules for Chrome Extension

// Message types
const MESSAGE_TYPES = {
  CAPTURE_MESSAGE: 'CAPTURE_MESSAGE',
  SEND_WEBHOOK: 'SEND_WEBHOOK',
  UPDATE_SETTINGS: 'UPDATE_SETTINGS',
  GET_STATS: 'GET_STATS',
  CLEAR_QUEUE: 'CLEAR_QUEUE',
  TEST_WEBHOOK: 'TEST_WEBHOOK',
  PLATFORM_DETECTED: 'PLATFORM_DETECTED'
};

// Storage keys
const STORAGE_KEYS = {
  WEBHOOK_URL: 'webhookUrl',
  WEBHOOK_SECRET: 'webhookSecret',
  ENABLED: 'enabled',
  MESSAGE_QUEUE: 'messageQueue',
  STATS: 'stats'
};

// Initialize
console.log('SignalScope service worker starting...');

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Received message:', request.type);
  
  handleMessage(request, sender)
    .then(response => sendResponse({ success: true, data: response }))
    .catch(error => {
      console.error('Error:', error);
      sendResponse({ success: false, error: error.message });
    });
  
  return true; // Async response
});

async function handleMessage(request, sender) {
  const { type, data } = request;
  
  switch (type) {
    case MESSAGE_TYPES.CAPTURE_MESSAGE:
      return await captureMessage(data, sender);
      
    case MESSAGE_TYPES.UPDATE_SETTINGS:
      return await updateSettings(data);
      
    case MESSAGE_TYPES.GET_STATS:
      return await getStats();
      
    case MESSAGE_TYPES.CLEAR_QUEUE:
      return await clearQueue();
      
    case MESSAGE_TYPES.TEST_WEBHOOK:
      return await testWebhook(data);
      
    case MESSAGE_TYPES.PLATFORM_DETECTED:
      console.log('Platform detected:', data.platform);
      return { acknowledged: true };
      
    default:
      throw new Error(`Unknown message type: ${type}`);
  }
}

async function captureMessage(data, sender) {
  try {
    // Check if enabled
    const settings = await chrome.storage.local.get(STORAGE_KEYS.ENABLED);
    if (settings[STORAGE_KEYS.ENABLED] === false) {
      return { captured: false, reason: 'Extension disabled' };
    }
    
    // Get current queue
    const storage = await chrome.storage.local.get(STORAGE_KEYS.MESSAGE_QUEUE);
    const queue = storage[STORAGE_KEYS.MESSAGE_QUEUE] || [];
    
    // Add message to queue
    const message = {
      ...data,
      id: Date.now() + '-' + Math.random().toString(36).substr(2, 9),
      tabId: sender.tab?.id,
      url: sender.tab?.url,
      capturedAt: new Date().toISOString()
    };
    
    queue.push(message);
    
    // Save queue (limit to 100 messages)
    if (queue.length > 100) {
      queue.shift();
    }
    
    await chrome.storage.local.set({ [STORAGE_KEYS.MESSAGE_QUEUE]: queue });
    
    console.log('Message captured:', message.id);
    
    // Try to send immediately if webhook is configured
    const webhookSettings = await chrome.storage.local.get(STORAGE_KEYS.WEBHOOK_URL);
    if (webhookSettings[STORAGE_KEYS.WEBHOOK_URL]) {
      processQueue();
    }
    
    return { captured: true, messageId: message.id };
  } catch (error) {
    console.error('Failed to capture message:', error);
    throw error;
  }
}

async function updateSettings(settings) {
  try {
    await chrome.storage.local.set(settings);
    console.log('Settings updated:', settings);
    return { updated: true };
  } catch (error) {
    console.error('Failed to update settings:', error);
    throw error;
  }
}

async function getStats() {
  try {
    const storage = await chrome.storage.local.get([
      STORAGE_KEYS.STATS,
      STORAGE_KEYS.MESSAGE_QUEUE
    ]);
    
    const stats = storage[STORAGE_KEYS.STATS] || {
      totalSent: 0,
      totalFailed: 0,
      lastSuccess: null,
      lastFailure: null
    };
    
    const queue = storage[STORAGE_KEYS.MESSAGE_QUEUE] || [];
    
    return {
      ...stats,
      queueSize: { total: queue.length }
    };
  } catch (error) {
    console.error('Failed to get stats:', error);
    throw error;
  }
}

async function clearQueue() {
  try {
    await chrome.storage.local.set({ [STORAGE_KEYS.MESSAGE_QUEUE]: [] });
    console.log('Queue cleared');
    return { cleared: true };
  } catch (error) {
    console.error('Failed to clear queue:', error);
    throw error;
  }
}

async function testWebhook(data) {
  try {
    const storage = await chrome.storage.local.get(STORAGE_KEYS.WEBHOOK_URL);
    const webhookUrl = storage[STORAGE_KEYS.WEBHOOK_URL];
    
    if (!webhookUrl) {
      throw new Error('Webhook URL not configured');
    }
    
    const testMessage = {
      id: 'test-' + Date.now(),
      content: data.content || 'Test message from SignalScope',
      platform: 'test',
      timestamp: new Date().toISOString(),
      test: true
    };
    
    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: [testMessage],
        source: 'signalscope',
        version: chrome.runtime.getManifest().version
      })
    });
    
    if (response.ok) {
      return { success: true, message: 'Webhook test successful' };
    } else {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  } catch (error) {
    console.error('Webhook test failed:', error);
    return { success: false, error: error.message };
  }
}

async function processQueue() {
  try {
    const storage = await chrome.storage.local.get([
      STORAGE_KEYS.WEBHOOK_URL,
      STORAGE_KEYS.MESSAGE_QUEUE,
      STORAGE_KEYS.STATS
    ]);
    
    const webhookUrl = storage[STORAGE_KEYS.WEBHOOK_URL];
    const queue = storage[STORAGE_KEYS.MESSAGE_QUEUE] || [];
    const stats = storage[STORAGE_KEYS.STATS] || {
      totalSent: 0,
      totalFailed: 0,
      lastSuccess: null,
      lastFailure: null
    };
    
    if (!webhookUrl || queue.length === 0) {
      return;
    }
    
    // Take up to 10 messages
    const batch = queue.splice(0, 10);
    
    try {
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messages: batch,
          source: 'signalscope',
          version: chrome.runtime.getManifest().version,
          timestamp: new Date().toISOString()
        })
      });
      
      if (response.ok) {
        stats.totalSent += batch.length;
        stats.lastSuccess = new Date().toISOString();
        console.log(`Sent ${batch.length} messages successfully`);
      } else {
        // Put messages back in queue
        queue.unshift(...batch);
        stats.totalFailed += batch.length;
        stats.lastFailure = new Date().toISOString();
        console.error(`Failed to send messages: ${response.status}`);
      }
    } catch (error) {
      // Put messages back in queue
      queue.unshift(...batch);
      stats.totalFailed += batch.length;
      stats.lastFailure = new Date().toISOString();
      console.error('Failed to send messages:', error);
    }
    
    // Save updated queue and stats
    await chrome.storage.local.set({
      [STORAGE_KEYS.MESSAGE_QUEUE]: queue,
      [STORAGE_KEYS.STATS]: stats
    });
  } catch (error) {
    console.error('Queue processing error:', error);
  }
}

// Process queue every 5 seconds
setInterval(processQueue, 5000);

// Installation handler
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Extension installed:', details.reason);
  
  if (details.reason === 'install') {
    // Set default settings
    chrome.storage.local.set({
      [STORAGE_KEYS.ENABLED]: true,
      [STORAGE_KEYS.MESSAGE_QUEUE]: [],
      [STORAGE_KEYS.STATS]: {
        totalSent: 0,
        totalFailed: 0,
        lastSuccess: null,
        lastFailure: null
      }
    });
    
    // Open options page
    chrome.runtime.openOptionsPage();
  }
});

console.log('SignalScope service worker ready');