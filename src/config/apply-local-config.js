/**
 * Apply local backend configuration to SignalScope Extension
 * Run this in the extension's background page or service worker
 */

// Configuration for local backend
const LOCAL_CONFIG = {
    webhook_url: 'http://localhost:8000/api/webhooks/signalscope',
    webhookUrl: 'http://localhost:8000/api/webhooks/signalscope',  // Support both formats
    webhook_secret: 'webhook-secret-key',
    webhookSecret: 'webhook-secret-key',
    batch_size: 5,
    batchSize: 5,
    batch_interval: 10000,  // 10 seconds
    batchInterval: 10000,
    enabled: true,
    platforms: ['discord', 'telegram', 'slack', 'whatsapp'],
    debug: true,
    features: {
        REAL_TIME_PROCESSING: true,
        AUTO_SEND: true,
        IMPORTANCE_SCORING: true,
        SENTIMENT_ANALYSIS: true,
        TRADING_SIGNALS: true
    }
};

// Apply configuration
chrome.storage.local.set(LOCAL_CONFIG, function() {
    console.log('✅ SignalScope configured for local backend!');
    console.log('Webhook URL:', LOCAL_CONFIG.webhook_url);
    console.log('Batch interval:', LOCAL_CONFIG.batch_interval / 1000, 'seconds');
    
    // Verify it was saved
    chrome.storage.local.get(['webhook_url', 'webhookUrl'], function(result) {
        console.log('Verification - Saved URL:', result.webhook_url || result.webhookUrl);
        
        // Send a message to content scripts to reload configuration
        chrome.tabs.query({}, function(tabs) {
            tabs.forEach(tab => {
                chrome.tabs.sendMessage(tab.id, {
                    type: 'CONFIG_UPDATED',
                    config: LOCAL_CONFIG
                }, function(response) {
                    // Ignore errors for tabs without content script
                });
            });
        });
    });
});

// Also set in sync storage for backup
chrome.storage.sync.set({
    webhook_url: LOCAL_CONFIG.webhook_url,
    webhook_secret: LOCAL_CONFIG.webhook_secret
}, function() {
    console.log('✅ Config also saved to sync storage');
});

console.log('Configuration script executed. Extension should now use local backend.');