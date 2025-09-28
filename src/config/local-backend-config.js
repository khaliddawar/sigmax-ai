/**
 * Local Backend Configuration for SignalScope Chrome Extension
 * This configuration connects the extension to your local backend server
 */

export const LOCAL_BACKEND_CONFIG = {
  // Local backend URL
  WEBHOOK_URL: 'http://localhost:8000/webhook',
  
  // Webhook secret (must match backend .env)
  WEBHOOK_SECRET: 'webhook-secret-key',
  
  // Batch settings for local testing
  BATCH_SIZE: 5,
  BATCH_INTERVAL: 10000, // 10 seconds
  
  // Enable debug logging
  DEBUG: true,
  
  // Local development features
  FEATURES: {
    REAL_TIME_PROCESSING: true,
    AUTO_SEND: true,
    IMPORTANCE_SCORING: true,
    SENTIMENT_ANALYSIS: true,
    TRADING_SIGNALS: true
  }
};

// Function to configure extension for local backend
export async function configureForLocalBackend() {
  try {
    // Set webhook configuration in storage
    await chrome.storage.local.set({
      'webhookUrl': LOCAL_BACKEND_CONFIG.WEBHOOK_URL,
      'webhookSecret': LOCAL_BACKEND_CONFIG.WEBHOOK_SECRET,
      'batchSize': LOCAL_BACKEND_CONFIG.BATCH_SIZE,
      'batchInterval': LOCAL_BACKEND_CONFIG.BATCH_INTERVAL,
      'enabled': true,
      'debug': LOCAL_BACKEND_CONFIG.DEBUG,
      'features': LOCAL_BACKEND_CONFIG.FEATURES
    });
    
    console.log('✅ Extension configured for local backend:', LOCAL_BACKEND_CONFIG.WEBHOOK_URL);
    return true;
  } catch (error) {
    console.error('❌ Failed to configure extension:', error);
    return false;
  }
}

// Auto-configure on load (for development)
if (typeof chrome !== 'undefined' && chrome.storage) {
  configureForLocalBackend();
}