// Options page JavaScript

document.addEventListener('DOMContentLoaded', async () => {
  // Load saved settings
  await loadSettings();
  await loadStatistics();
  
  // Event listeners
  document.getElementById('saveSettings').addEventListener('click', saveSettings);
  document.getElementById('resetSettings').addEventListener('click', resetSettings);
  document.getElementById('testWebhook').addEventListener('click', testWebhook);
  document.getElementById('clearStats').addEventListener('click', clearStatistics);
  document.getElementById('exportSettings').addEventListener('click', exportSettings);
  document.getElementById('importSettings').addEventListener('click', () => {
    document.getElementById('importFile').click();
  });
  document.getElementById('importFile').addEventListener('change', importSettings);
});

async function loadSettings() {
  try {
    const settings = await chrome.storage.local.get([
      'webhookUrl',
      'webhookSecret',
      'batchSize',
      'batchInterval',
      'retryAttempts',
      'platforms',
      'customSelectors'
    ]);
    
    // Webhook settings
    document.getElementById('webhookUrl').value = settings.webhookUrl || '';
    document.getElementById('webhookSecret').value = settings.webhookSecret || '';
    
    // Capture settings
    document.getElementById('batchSize').value = settings.batchSize || 10;
    document.getElementById('batchInterval').value = settings.batchInterval || 5;
    document.getElementById('retryAttempts').value = settings.retryAttempts || 3;
    
    // Platform settings
    const platforms = settings.platforms || ['discord', 'telegram', 'slack', 'whatsapp'];
    document.getElementById('platform-discord').checked = platforms.includes('discord');
    document.getElementById('platform-telegram').checked = platforms.includes('telegram');
    document.getElementById('platform-slack').checked = platforms.includes('slack');
    document.getElementById('platform-whatsapp').checked = platforms.includes('whatsapp');
    
    // Custom selectors
    if (settings.customSelectors) {
      document.getElementById('customSelectors').value = JSON.stringify(settings.customSelectors, null, 2);
    }
  } catch (error) {
    console.error('Error loading settings:', error);
    showNotification('Failed to load settings', 'error');
  }
}

async function saveSettings() {
  try {
    const saveBtn = document.getElementById('saveSettings');
    saveBtn.disabled = true;
    saveBtn.classList.add('loading');
    
    // Validate webhook URL
    const webhookUrl = document.getElementById('webhookUrl').value.trim();
    if (webhookUrl && !isValidUrl(webhookUrl)) {
      showNotification('Invalid webhook URL', 'error');
      return;
    }
    
    // Get enabled platforms
    const platforms = [];
    if (document.getElementById('platform-discord').checked) platforms.push('discord');
    if (document.getElementById('platform-telegram').checked) platforms.push('telegram');
    if (document.getElementById('platform-slack').checked) platforms.push('slack');
    if (document.getElementById('platform-whatsapp').checked) platforms.push('whatsapp');
    
    // Parse custom selectors
    let customSelectors = null;
    const customSelectorsText = document.getElementById('customSelectors').value.trim();
    if (customSelectorsText) {
      try {
        customSelectors = JSON.parse(customSelectorsText);
      } catch (error) {
        showNotification('Invalid JSON in custom selectors', 'error');
        return;
      }
    }
    
    // Save settings
    const settings = {
      webhookUrl,
      webhookSecret: document.getElementById('webhookSecret').value,
      batchSize: parseInt(document.getElementById('batchSize').value),
      batchInterval: parseInt(document.getElementById('batchInterval').value) * 1000, // Convert to ms
      retryAttempts: parseInt(document.getElementById('retryAttempts').value),
      platforms,
      customSelectors
    };
    
    await chrome.storage.local.set(settings);
    
    // Notify background script
    await sendMessage('UPDATE_SETTINGS', settings);
    
    showNotification('Settings saved successfully', 'success');
  } catch (error) {
    console.error('Error saving settings:', error);
    showNotification('Failed to save settings', 'error');
  } finally {
    const saveBtn = document.getElementById('saveSettings');
    saveBtn.disabled = false;
    saveBtn.classList.remove('loading');
  }
}

async function resetSettings() {
  if (!confirm('Are you sure you want to reset all settings to defaults?')) {
    return;
  }
  
  try {
    const defaults = {
      webhookUrl: '',
      webhookSecret: '',
      batchSize: 10,
      batchInterval: 5000,
      retryAttempts: 3,
      platforms: ['discord', 'telegram', 'slack', 'whatsapp'],
      customSelectors: null,
      enabled: true
    };
    
    await chrome.storage.local.set(defaults);
    await loadSettings();
    
    showNotification('Settings reset to defaults', 'success');
  } catch (error) {
    console.error('Error resetting settings:', error);
    showNotification('Failed to reset settings', 'error');
  }
}

async function testWebhook() {
  try {
    const testBtn = document.getElementById('testWebhook');
    testBtn.disabled = true;
    testBtn.classList.add('loading');
    
    const webhookUrl = document.getElementById('webhookUrl').value.trim();
    if (!webhookUrl) {
      showNotification('Please enter a webhook URL first', 'error');
      return;
    }
    
    const result = await sendMessage('TEST_WEBHOOK', {
      content: 'Test message from SignalScope settings'
    });
    
    if (result && result.success) {
      showNotification('Webhook test successful!', 'success');
    } else {
      showNotification(`Webhook test failed: ${result?.error || 'Unknown error'}`, 'error');
    }
  } catch (error) {
    console.error('Error testing webhook:', error);
    showNotification('Failed to test webhook', 'error');
  } finally {
    const testBtn = document.getElementById('testWebhook');
    testBtn.disabled = false;
    testBtn.classList.remove('loading');
  }
}

async function loadStatistics() {
  try {
    const stats = await sendMessage('GET_STATS');
    
    if (stats) {
      document.getElementById('statTotalSent').textContent = stats.totalSent || 0;
      document.getElementById('statTotalFailed').textContent = stats.totalFailed || 0;
      document.getElementById('statLastSuccess').textContent = 
        stats.lastSuccess ? new Date(stats.lastSuccess).toLocaleString() : 'Never';
      document.getElementById('statQueueSize').textContent = stats.queueSize?.total || 0;
    }
  } catch (error) {
    console.error('Error loading statistics:', error);
  }
}

async function clearStatistics() {
  if (!confirm('Are you sure you want to clear all statistics?')) {
    return;
  }
  
  try {
    await chrome.storage.local.set({
      stats: {
        totalSent: 0,
        totalFailed: 0,
        lastSuccess: null,
        lastFailure: null
      }
    });
    
    await loadStatistics();
    showNotification('Statistics cleared', 'success');
  } catch (error) {
    console.error('Error clearing statistics:', error);
    showNotification('Failed to clear statistics', 'error');
  }
}

async function exportSettings() {
  try {
    const settings = await chrome.storage.local.get(null);
    const dataStr = JSON.stringify(settings, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `signalscope-settings-${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    showNotification('Settings exported successfully', 'success');
  } catch (error) {
    console.error('Error exporting settings:', error);
    showNotification('Failed to export settings', 'error');
  }
}

async function importSettings(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  try {
    const text = await file.text();
    const settings = JSON.parse(text);
    
    // Validate settings structure
    if (typeof settings !== 'object') {
      throw new Error('Invalid settings file');
    }
    
    await chrome.storage.local.set(settings);
    await loadSettings();
    await loadStatistics();
    
    showNotification('Settings imported successfully', 'success');
  } catch (error) {
    console.error('Error importing settings:', error);
    showNotification('Failed to import settings: Invalid file', 'error');
  }
  
  // Reset file input
  event.target.value = '';
}

function isValidUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
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

function showNotification(message, type = 'success') {
  const notification = document.getElementById('notification');
  notification.textContent = message;
  notification.className = `notification ${type} show`;
  
  setTimeout(() => {
    notification.classList.remove('show');
  }, 3000);
}

// Auto-refresh statistics every 10 seconds
setInterval(loadStatistics, 10000);