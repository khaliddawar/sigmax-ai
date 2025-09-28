# 🧪 SignalScope Extension Testing Guide

## ✅ Current Status
- **Backend Server**: ✅ Running at `http://localhost:8000` (Simple Test Backend)
- **Test Interface**: ✅ Available at `http://localhost:8080/test_sidebar_fixes.html`
- **Extension**: ⚠️ Communication issues detected

## 🔧 How to Fix and Test Your Extension

### **Step 1: Reload Your Extension**
1. Go to `chrome://extensions/`
2. Find "SignalScope" extension
3. Click the **🔄 reload button**
4. Make sure it's **enabled**

### **Step 2: Test Extension Communication**

#### **Method A: Direct Extension Test (Recommended)**
1. **Click the SignalScope extension icon** in your browser toolbar
2. **Right-click inside the sidebar** and select **"Inspect"**
3. **In the console that opens**, paste and run this code:

```javascript
// Copy the entire content of extension_direct_test.js and paste it here
```

#### **Method B: Test from Any Webpage**
1. Open any webpage (like Google.com)
2. Press **F12** to open Developer Console
3. **Copy and paste** the content from `extension_direct_test.js`
4. Press Enter to run the tests

### **Step 3: Understanding the Errors**

#### **"The message port closed before a response was received"**
This error means:
- ❌ Extension service worker is not responding
- ❌ Message handlers are not properly set up
- ❌ Extension may need to be reloaded

#### **"Chrome API not available"**
This error means:
- ❌ You're running the test from a webpage instead of extension context
- ❌ Extension is not loaded or enabled

### **Step 4: Manual Testing Steps**

1. **Open the sidebar**:
   - Click the SignalScope extension icon
   - Sidebar should appear on the right

2. **Check for messages**:
   - Look for any captured messages in the sidebar
   - Messages should appear automatically

3. **Test message capture**:
   - Go to Discord, Telegram, or any chat platform
   - Send a message
   - Check if it appears in the sidebar

### **Step 5: Common Fixes**

#### **Fix 1: Extension Configuration**
Run this in the extension console:
```javascript
chrome.storage.local.set({
    webhookUrl: 'http://localhost:8000/api/webhooks/signalscope',
    enabled: true,
    platforms: {
        discord: true,
        telegram: true,
        slack: true,
        whatsapp: true
    }
});
```

#### **Fix 2: Clear Storage and Reset**
```javascript
chrome.storage.local.clear(() => {
    console.log('Storage cleared');
    // Then set configuration again
});
```

#### **Fix 3: Sync Queue to Preview**
```javascript
chrome.runtime.sendMessage({
    type: 'SYNC_QUEUE_TO_PREVIEW'
}).then(response => {
    console.log('Sync response:', response);
});
```

## 🎯 Expected Results

### **Working Extension Should Show:**
- ✅ Chrome API available
- ✅ Storage accessible with proper configuration
- ✅ Service worker responding to messages
- ✅ Message capture working
- ✅ Messages appearing in sidebar

### **If Still Not Working:**
1. **Check extension permissions** at `chrome://extensions/`
2. **Try restarting Chrome** completely
3. **Check if content scripts are injected** on chat platforms
4. **Look for errors** in the extension's background page console

## 🔍 Debugging Tips

### **Check Extension Background Page:**
1. Go to `chrome://extensions/`
2. Find SignalScope extension
3. Click **"Inspect views: background page"**
4. Look for errors in the console

### **Check Content Script Injection:**
1. Go to a chat platform (Discord, Telegram, etc.)
2. Press F12
3. In console, type: `console.log('Content script loaded:', !!window.signalScopeContentScript)`
4. Should return `true` if content script is loaded

### **Monitor Network Requests:**
1. Open Network tab in DevTools
2. Look for requests to `localhost:8000`
3. Check if webhook calls are being made

## 📞 Backend Server Status

The simple test backend is running and will log all received messages:
- **Health**: http://localhost:8000/health
- **Webhook**: http://localhost:8000/api/webhooks/signalscope

You should see logs in the terminal when messages are sent to the backend.

## 🚀 Next Steps

1. Run the direct extension test
2. Check the results and fix any issues
3. Test message capture on real chat platforms
4. Monitor the backend logs for incoming messages
5. If everything works, switch back to the full backend server

---

**Remember**: The key is to test in the **extension context** (sidebar console or extension background page), not from regular webpages!
