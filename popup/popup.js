// Popup JavaScript

document.addEventListener('DOMContentLoaded', async () => {
  // Elements
  const toggleCaptureBtn = document.getElementById('toggleCapture');
  const testWebhookBtn = document.getElementById('testWebhook');
  const clearQueueBtn = document.getElementById('clearQueue');
  const openOptionsBtn = document.getElementById('openOptions');
  const openHelpBtn = document.getElementById('openHelp');
  
  const statusDot = document.querySelector('.status-dot');
  const statusText = document.querySelector('.status-text');
  const messagesCaptured = document.getElementById('messagesCapture');
  const queueSize = document.getElementById('queueSize');
  const currentPlatform = document.getElementById('currentPlatform');
  const webhookStatus = document.getElementById('webhookStatus');
  
  // Load initial state
  await loadPopupState();
  
  // Event listeners
  toggleCaptureBtn.addEventListener('click', toggleCapture);
  testWebhookBtn.addEventListener('click', testWebhook);
  clearQueueBtn.addEventListener('click', clearQueue);
  openOptionsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
  openHelpBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://github.com/SignalScope/docs' });
  });
  
  // Functions
  async function loadPopupState() {
    try {
      // Get current state from storage
      const result = await chrome.storage.local.get([
        'enabled',
        'webhookUrl',
        'stats'
      ]);
      
      // Update UI based on state
      const isEnabled = result.enabled !== false;
      updateStatusIndicator(isEnabled);
      updateToggleButton(isEnabled);
      
      // Update webhook status
      if (result.webhookUrl) {
        try {
          const url = new URL(result.webhookUrl);
          webhookStatus.textContent = url.hostname;
          webhookStatus.style.color = '#059669';
        } catch {
          webhookStatus.textContent = 'Invalid URL';
          webhookStatus.style.color = '#dc2626';
        }
      } else {
        webhookStatus.textContent = 'Not configured';
        webhookStatus.style.color = '#f59e0b';
      }
      
      // Get stats from background
      const stats = await sendMessage('GET_STATS');
      if (stats) {
        messagesCaptured.textContent = stats.totalSent || 0;
        queueSize.textContent = stats.queueSize?.total || 0;
      }
      
      // Get current tab info
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab) {
        const platform = detectPlatformFromUrl(tab.url);
        currentPlatform.textContent = platform || 'Not detected';
        currentPlatform.style.color = platform ? '#059669' : '#6b7280';
      }
    } catch (error) {
      console.error('Error loading popup state:', error);
    }
  }
  
  function updateStatusIndicator(isEnabled) {
    if (isEnabled) {
      statusDot.classList.remove('inactive');
      statusText.textContent = 'Active';
    } else {
      statusDot.classList.add('inactive');
      statusText.textContent = 'Paused';
    }
  }
  
  function updateToggleButton(isEnabled) {
    if (isEnabled) {
      toggleCaptureBtn.innerHTML = '<span class="btn-icon">⏸</span> Pause Capture';
    } else {
      toggleCaptureBtn.innerHTML = '<span class="btn-icon">▶</span> Resume Capture';
    }
  }
  
  async function toggleCapture() {
    try {
      toggleCaptureBtn.disabled = true;
      toggleCaptureBtn.classList.add('loading');
      
      // Get current state
      const result = await chrome.storage.local.get('enabled');
      const newState = !(result.enabled !== false);
      
      // Update storage
      await chrome.storage.local.set({ enabled: newState });
      
      // Update UI
      updateStatusIndicator(newState);
      updateToggleButton(newState);
      
      // Notify background
      await sendMessage('UPDATE_SETTINGS', { enabled: newState });
      
    } catch (error) {
      console.error('Error toggling capture:', error);
      alert('Failed to toggle capture');
    } finally {
      toggleCaptureBtn.disabled = false;
      toggleCaptureBtn.classList.remove('loading');
    }
  }
  
  async function testWebhook() {
    try {
      testWebhookBtn.disabled = true;
      testWebhookBtn.classList.add('loading');
      
      const result = await sendMessage('TEST_WEBHOOK', {
        content: 'Test message from SignalScope popup'
      });
      
      if (result && result.success) {
        alert('Webhook test successful!');
      } else {
        alert(`Webhook test failed: ${result?.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error testing webhook:', error);
      alert('Failed to test webhook');
    } finally {
      testWebhookBtn.disabled = false;
      testWebhookBtn.classList.remove('loading');
    }
  }
  
  async function clearQueue() {
    try {
      if (!confirm('Are you sure you want to clear the message queue?')) {
        return;
      }
      
      clearQueueBtn.disabled = true;
      clearQueueBtn.classList.add('loading');
      
      await sendMessage('CLEAR_QUEUE');
      
      // Update queue size display
      queueSize.textContent = '0';
      
      alert('Queue cleared successfully');
    } catch (error) {
      console.error('Error clearing queue:', error);
      alert('Failed to clear queue');
    } finally {
      clearQueueBtn.disabled = false;
      clearQueueBtn.classList.remove('loading');
    }
  }
  
  async function sendMessage(type, data = {}) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type, data }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else if (response && !response.success) {
          reject(new Error(response.error || 'Unknown error'));
        } else {
          resolve(response?.data);
        }
      });
    });
  }
  
  function detectPlatformFromUrl(url) {
    if (!url) return null;
    
    if (url.includes('discord.com')) return 'Discord';
    if (url.includes('telegram.org')) return 'Telegram';
    if (url.includes('slack.com')) return 'Slack';
    if (url.includes('whatsapp.com')) return 'WhatsApp';
    if (url.includes('julian-komar.com')) return 'Julian Komar';
    
    // For any other site, return the domain
    try {
      const hostname = new URL(url).hostname;
      return hostname.replace('www.', '').split('.')[0];
    } catch {
      return 'Unknown';
    }
  }
  
  // Auto-refresh stats every 5 seconds
  setInterval(async () => {
    try {
      const stats = await sendMessage('GET_STATS');
      if (stats) {
        messagesCaptured.textContent = stats.totalSent || 0;
        queueSize.textContent = stats.queueSize?.total || 0;
      }
    } catch (error) {
      console.error('Error refreshing stats:', error);
    }
  }, 5000);
});