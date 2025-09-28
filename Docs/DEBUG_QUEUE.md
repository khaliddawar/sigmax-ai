# Debug & Fix Queue Issues

## Issue
- 102 messages in queue
- 0 showing in preview
- Messages being captured but not displayed

## Quick Fix Commands

Run these in browser console (F12) on any page:

### 1. Check Current State
```javascript
// See what's in storage
chrome.storage.local.get(null, (data) => {
  console.log('Queue size:', data.messageQueue?.length || 0);
  console.log('Webhook URL:', data.webhookUrl);
  console.log('Enabled:', data.enabled);
  console.log('Stats:', data.stats);
  // Check first few messages
  if (data.messageQueue?.length > 0) {
    console.log('First message:', data.messageQueue[0]);
  }
});
```

### 2. Get Preview Buffer Status
```javascript
// Check preview buffer
chrome.runtime.sendMessage(chrome.runtime.id, {
  type: 'GET_PREVIEW_MESSAGES'
}, response => {
  console.log('Preview buffer:', response);
  console.log('Count:', response?.length || 0);
});
```

### 3. Force Process Queue
```javascript
// Send queued messages to webhook
chrome.runtime.sendMessage(chrome.runtime.id, {
  type: 'PROCESS_QUEUE'
}, response => console.log('Queue processing:', response));
```

### 4. Clear Everything and Reset
```javascript
// Nuclear option - clear all and reset
chrome.storage.local.clear(() => {
  chrome.storage.local.set({
    'webhookUrl': 'http://localhost:8000/webhook',
    'enabled': true,
    'batchSize': 5,
    'batchInterval': 10000,
    'messageQueue': [],
    'stats': {
      totalCaptured: 0,
      totalSent: 0,
      totalFailed: 0
    }
  }, () => {
    console.log('Reset complete');
    // Reload extension
    chrome.runtime.reload();
  });
});
```

### 5. Manually Add to Preview
```javascript
// Test if preview works at all
chrome.runtime.sendMessage(chrome.runtime.id, {
  type: 'CAPTURE_MESSAGE',
  data: {
    content: 'Test message for preview',
    author: 'Debug User',
    platform: 'generic',
    channel: 'test',
    timestamp: new Date().toISOString()
  }
}, response => console.log('Test capture:', response));
```

## Likely Causes

1. **Messages captured before fixes** - Old format without proper structure
2. **Preview buffer not initialized** - Service worker might have restarted
3. **Sidebar not receiving messages** - Connection issue

## Step-by-Step Fix

1. Run command #1 to check state
2. Run command #2 to check preview buffer
3. If preview is empty but queue has messages:
   - Run command #4 to reset everything
   - Reload extension
   - Test with fresh messages

## Test After Fix

1. Go to test page: http://localhost:8080/test_chat.html
2. Add a new message
3. Check sidebar - should show immediately
4. Check stats - should update

## If Still Broken

Check service worker console:
1. Go to `chrome://extensions/`
2. Click "Inspect views: service worker"
3. Look for errors
4. Run: `console.log(this)` to inspect state