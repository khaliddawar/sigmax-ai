# Console Debug Commands

## IMPORTANT: Run These From The Right Place

These commands MUST be run from a page where Chrome extension APIs are available:

### Option 1: From the Test Chat Page
1. Open: http://localhost:8080/test_chat.html
2. Open Console (F12)
3. Run the commands below

### Option 2: From Any Regular Website
1. Open any website (e.g., google.com)
2. Open Console (F12)
3. Run the commands below

### Option 3: From Extension Pages
1. Open the sidebar (click extension icon)
2. Right-click inside sidebar → Inspect
3. Run commands in that console

## Debug Commands

### 1. Check If Extension Is Working

```javascript
// Check if we can talk to the extension
if (typeof chrome !== 'undefined' && chrome.runtime) {
    console.log('✅ Chrome API available');
    console.log('Extension ID:', chrome.runtime.id);
} else {
    console.log('❌ Chrome API not available');
}
```

### 2. Check Storage Configuration

```javascript
// Check storage
chrome.storage.local.get(null, (data) => {
    console.log('=== STORAGE CONTENTS ===');
    console.log('Webhook URL:', data.webhookUrl || 'NOT SET');
    console.log('Enabled:', data.enabled);
    console.log('Queue size:', data.messageQueue?.length || 0);
    console.log('Stats:', data.stats);
    
    if (data.messageQueue?.length > 0) {
        console.log('First message in queue:', data.messageQueue[0]);
    }
});
```

### 3. Get Preview Buffer

```javascript
// Check preview buffer
chrome.runtime.sendMessage(chrome.runtime.id, {
    type: 'GET_PREVIEW_MESSAGES'
}, response => {
    if (chrome.runtime.lastError) {
        console.error('Error:', chrome.runtime.lastError.message);
    } else {
        console.log('=== PREVIEW BUFFER ===');
        console.log('Response:', response);
        
        // Handle wrapped response
        let messages = response?.data || response;
        if (Array.isArray(messages)) {
            console.log(`Preview has ${messages.length} messages`);
            if (messages.length > 0) {
                console.log('First message:', messages[0]);
            }
        } else {
            console.log('No messages in preview');
        }
    }
});
```

### 4. Test Message Capture

```javascript
// Send a test message
chrome.runtime.sendMessage(chrome.runtime.id, {
    type: 'CAPTURE_MESSAGE',
    data: {
        id: `test-${Date.now()}`,
        content: 'Test message from console',
        author: 'Console User',
        platform: 'generic',
        channel: 'test',
        timestamp: new Date().toISOString()
    }
}, response => {
    console.log('Capture response:', response);
});
```

### 5. Fix Configuration

```javascript
// Set correct configuration
chrome.storage.local.set({
    webhookUrl: 'http://localhost:8000/webhook',
    enabled: true,
    batchSize: 5,
    batchInterval: 10000
}, () => {
    console.log('✅ Configuration fixed');
});
```

### 6. Force Queue to Preview Sync

```javascript
// Get queue and add to preview
chrome.storage.local.get('messageQueue', (data) => {
    const queue = data.messageQueue || [];
    console.log(`Found ${queue.length} messages in queue`);
    
    if (queue.length > 0) {
        // Re-capture first 5 messages
        queue.slice(0, 5).forEach((msg, i) => {
            setTimeout(() => {
                chrome.runtime.sendMessage(chrome.runtime.id, {
                    type: 'CAPTURE_MESSAGE',
                    data: {
                        ...msg,
                        id: `resync-${Date.now()}-${i}`
                    }
                }, response => {
                    console.log(`Message ${i+1}:`, response?.success ? '✅' : '❌');
                });
            }, i * 200);
        });
    }
});
```

### 7. Check Sidebar Console

**IMPORTANT**: Also check the sidebar's own console:
1. Open sidebar (click extension icon)
2. Right-click inside sidebar → Inspect
3. Look for these logs:
   - `[Sidebar] Loading messages...`
   - `[Sidebar] Response received: ...`
   - `[Sidebar] Got X messages`

### 8. Process Queue

```javascript
// Send queued messages to webhook
chrome.runtime.sendMessage(chrome.runtime.id, {
    type: 'PROCESS_QUEUE'
}, response => {
    console.log('Queue processing:', response);
});
```

### 9. Complete Reset

```javascript
// Nuclear option - clear everything
chrome.storage.local.clear(() => {
    chrome.storage.local.set({
        webhookUrl: 'http://localhost:8000/webhook',
        enabled: true,
        messageQueue: [],
        stats: { totalCaptured: 0, totalSent: 0, totalFailed: 0 }
    }, () => {
        console.log('✅ Storage reset');
        chrome.runtime.reload();
    });
});
```

## What to Report

Please run commands 1-3 and tell me:

1. **From Command 2**: 
   - What's the queue size?
   - Is webhookUrl set correctly?

2. **From Command 3**:
   - What does the response look like?
   - Is it `{success: true, data: []}` or something else?
   - How many messages in preview?

3. **From Sidebar Console**:
   - What does `[Sidebar] Response received:` show?
   - Any errors?

## Quick Test

After running the fix commands (5 & 6), try adding a message on the test page and see if it appears in the sidebar.