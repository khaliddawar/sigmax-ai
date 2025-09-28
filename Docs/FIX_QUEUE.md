# Fix for Queued Messages

## Quick Fix Steps:

### 1. Reload the Extension
Go to `chrome://extensions/` and click the refresh button on SignalScope

### 2. Open Extension Sidebar
Click the SignalScope icon to open the sidebar

### 3. Process Queued Messages
Open the browser console on any page (F12) and run this command:

```javascript
// Send the 72 queued messages
chrome.runtime.sendMessage(chrome.runtime.id, {
  type: 'PROCESS_QUEUE'
}, response => console.log('Queue processing:', response));
```

### 4. Fix Configuration
If status still shows "Configure", run this in the console:

```javascript
// Set webhook URL directly
chrome.storage.local.set({
  'webhookUrl': 'http://localhost:8000/webhook',
  'webhookSecret': 'webhook-secret-key',
  'enabled': true,
  'batchSize': 5,
  'batchInterval': 10000
}, () => console.log('Configuration updated'));
```

Then refresh the sidebar.

### 5. Verify Messages Are Being Captured
After fixing configuration:
1. Go to test page: http://localhost:8080/test_chat.html
2. Click "Add Message" button
3. Check sidebar - should show messages
4. Check server console for webhook receipts

## What Was Fixed:

1. **Storage Keys Issue**: Fixed mismatch between snake_case and camelCase storage keys
2. **Webhook URL**: Corrected from `/api/webhooks/signalscope` to `/webhook`
3. **Queue Processing**: Added manual queue processing capability
4. **Extension State**: Ensured 'enabled' flag is set to true

## If Still Not Working:

1. Check Service Worker Console:
   - Go to chrome://extensions/
   - Click "Inspect views: service worker"
   - Look for errors

2. Check if servers are running:
   - Webhook server: http://localhost:8000 (should see status page)
   - Test page server: http://localhost:8080 (should serve test page)

3. Clear all data and restart:
```javascript
// Clear everything and reset
chrome.storage.local.clear(() => {
  chrome.storage.local.set({
    'webhookUrl': 'http://localhost:8000/webhook',
    'enabled': true,
    'batchSize': 5,
    'batchInterval': 10000
  }, () => console.log('Reset complete'));
});
```

Then reload the extension.