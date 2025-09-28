# Fixes Applied - SignalScope Extension

## Issues Fixed

### 1. ✅ Duplicate Messages
- **Problem**: Messages were being captured multiple times
- **Solution**: Refined generic selectors to be more specific (`.message[data-message-id]`)

### 2. ✅ Unknown Author/Channel
- **Problem**: Author and channel showed as "Unknown"  
- **Solution**: Improved genericParse to properly extract from `.message-author` and data attributes

### 3. ✅ Capture Stops After Clear
- **Problem**: Clearing messages stopped new captures
- **Solution**: Added RESET_CAPTURE handler to allow re-processing

### 4. ✅ Webhook Configuration
- **Problem**: Storage keys were snake_case instead of camelCase
- **Solution**: Fixed all storage keys to use camelCase (webhookUrl, not webhook_url)

## Testing Steps

### 1. Reload Extension
```
chrome://extensions/ → Refresh SignalScope
```

### 2. Fix Configuration (One Time)
Open browser console (F12) on any page and run:
```javascript
chrome.storage.local.set({
  'webhookUrl': 'http://localhost:8000/webhook',
  'enabled': true,
  'batchSize': 5,
  'batchInterval': 10000
}, () => console.log('Config fixed'));
```

### 3. Open Test Page
Navigate to: http://localhost:8080/test_chat.html

### 4. Check Sidebar
- Should show "Connected" (not "Configure")
- Messages should show proper author names (Alice, Bob, etc.)
- Channels should show (#general, #random, etc.)

### 5. Test Clear Function
1. Click clear messages button in sidebar
2. Add new messages on test page
3. New messages should still be captured

## If Clear Still Breaks Capture

Run this in the test page console to reset:
```javascript
chrome.runtime.sendMessage(chrome.runtime.id, {
  type: 'RESET_CAPTURE'
}, response => console.log('Capture reset:', response));
```

## What Changed

### File Changes:
1. **src/content/message-parser.js**
   - Improved genericParse to check `.message-author` and data attributes
   - Added null check for empty content

2. **src/content/content-script.js**
   - Added RESET_CAPTURE handler to clear processedMessages

3. **src/shared/constants.js**
   - Refined GENERIC platform selectors to be more specific

4. **src/config/local-backend-config.js**
   - Fixed storage keys from snake_case to camelCase

## Expected Behavior

✅ Messages show correct author (not "Unknown")
✅ Messages show correct channel (not "Unknown")  
✅ No duplicate messages
✅ Clear button doesn't break capture
✅ Sidebar shows "Connected" status
✅ Webhook server receives messages

## Quick Debug

Check if everything is working:
```javascript
// In any page console
chrome.storage.local.get(null, (data) => {
  console.log('Webhook URL:', data.webhookUrl);
  console.log('Enabled:', data.enabled);
  console.log('Queue:', data.messageQueue?.length || 0);
});
```