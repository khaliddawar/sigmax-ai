# Debug Instructions - Finding the Real Issue

## The Problem
Messages are being queued but not showing in the sidebar. We need to find where the breakdown is happening.

## Step-by-Step Debug Process

### 1. Reload Extension First
```
chrome://extensions/ → Refresh SignalScope
```

### 2. Open Debug Page
Navigate to: `http://localhost:8080/debug_test.html`

### 3. Open Sidebar
Click the SignalScope extension icon to open the sidebar

### 4. Open Both Consoles
- **Debug Page Console**: Right-click debug page → Inspect → Console tab
- **Sidebar Console**: Right-click inside sidebar → Inspect → Console tab

### 5. Run Debug Tests (In Order)

#### Test 1: Check Extension
Click "Check Extension" button
- Should show Extension ID
- Should show stats

#### Test 2: Check Storage
Click "Check Storage" button
- Look for `webhookUrl: http://localhost:8000/webhook`
- Look for `enabled: true`
- Note the `messageQueue` count

#### Test 3: Get Preview Buffer
Click "Get Preview Buffer" button
- This directly asks for preview messages
- Check both debug page console AND sidebar console
- Sidebar console should show: `[Sidebar] Response received:`

#### Test 4: Test Direct Capture
Click "Test Direct Capture" button
- Should show success response
- Check sidebar console for any new messages

#### Test 5: Fix Configuration
If webhookUrl is not set, click "Fix Configuration" button

### 6. Check Sidebar Console

In the sidebar console, you should see logs like:
```
[Sidebar] Loading messages...
[Sidebar] Response received: {success: true, data: Array(0)}
[Sidebar] Got 0 messages
```

If you see `data: Array(0)`, the preview buffer is empty even though queue has messages.

### 7. Manual Sync Test

In the debug page, click "Manual Sync Queue→Preview"
This will try to re-send queued messages to populate the preview.

## What to Look For

### In Debug Page Console:
- ✅ Extension ID detected
- ✅ Stats response received  
- ✅ Storage has webhookUrl
- ❓ Preview buffer response

### In Sidebar Console:
- ❓ `[Sidebar] Response received:` - what does it show?
- ❓ `[Sidebar] Got X messages` - is X > 0?
- ❓ Any error messages?

## Report Back

Please run through these steps and tell me:
1. What shows in the sidebar console when you click "Get Preview Buffer"?
2. Does the preview buffer have messages or is it empty?
3. What's the exact response format you see?
4. Any errors in either console?

## Quick Fix Attempt

If preview is empty but queue has messages, run this in debug page console:

```javascript
// Force sync queue to preview
chrome.storage.local.get('messageQueue', (data) => {
  const queue = data.messageQueue || [];
  console.log(`Syncing ${queue.length} messages...`);
  
  queue.slice(0, 5).forEach((msg, i) => {
    setTimeout(() => {
      chrome.runtime.sendMessage(chrome.runtime.id, {
        type: 'CAPTURE_MESSAGE',
        data: {
          ...msg,
          id: `resync-${Date.now()}-${i}`
        }
      }, r => console.log(`Message ${i+1}:`, r));
    }, i * 200);
  });
});
```

This will re-capture the first 5 queued messages.

## Nuclear Option

If nothing works, run this to completely reset:

```javascript
// Complete reset
chrome.storage.local.clear(() => {
  chrome.storage.local.set({
    webhookUrl: 'http://localhost:8000/webhook',
    enabled: true,
    messageQueue: [],
    stats: { totalCaptured: 0, totalSent: 0 }
  }, () => {
    chrome.runtime.reload();
    console.log('Extension reset and reloaded');
  });
});
```

Then test with fresh messages.