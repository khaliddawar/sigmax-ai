# 🚀 Telegram Testing Guide for Enhanced Capture System

## 🎯 **Why You're Not Getting Messages in Telegram**

The issue is that your extension is still using the **old DOM-only content script**. The enhanced capture system we built isn't integrated yet. Here's how to fix it:

## 🔧 **Step 1: Update Your Extension**

### **Files Updated:**
✅ `manifest.json` - Updated to use enhanced content script  
✅ `content/content-script-enhanced.js` - New enhanced content script  
✅ `content/hybrid-capture.js` - Hybrid capture system  
✅ `content/network-interceptor.js` - Enhanced network interceptor  

### **Reload Your Extension:**
1. **Open Chrome Extensions** (chrome://extensions/)
2. **Find SignalScope extension**
3. **Click the reload button** (🔄) to reload the extension
4. **Verify** the extension is active

## 🧪 **Step 2: Test on Telegram Web**

### **Navigate to Telegram:**
1. **Go to** https://web.telegram.org/
2. **Log in** to your Telegram account
3. **Open any chat** (preferably one with recent messages)

### **Test the Enhanced System:**
1. **Open Developer Console** (F12)
2. **Paste this test script:**

```javascript
// Test if enhanced content script is loaded
console.log('Enhanced content script loaded:', window.signalScopeEnhancedContentScript);
console.log('Enhanced capture system available:', !!window.signalScopeEnhanced);

if (window.signalScopeEnhanced) {
  const stats = window.signalScopeEnhanced.getStats();
  console.log('Capture stats:', stats);
  
  // Test message detection
  const testResult = window.testSignalScopeEnhanced();
  console.log(`Found ${testResult} messages on page`);
}
```

### **Expected Results:**
- ✅ `Enhanced content script loaded: true`
- ✅ `Enhanced capture system available: true`
- ✅ `Found X messages on page` (where X > 0)

## 🎮 **Step 3: Start Capture from Extension**

### **Start the Enhanced Capture:**
1. **Click the SignalScope extension icon**
2. **Open the sidebar or popup**
3. **Click "Start Capture"** or similar button
4. **Verify** the status shows "Active"

### **Test Message Capture:**
1. **Send a message** in the Telegram chat
2. **Check the server terminal** - you should see webhook data
3. **Check the extension sidebar** - should show captured messages

## 🔍 **Step 4: Debug if Still Not Working**

### **Check Extension Console:**
1. **Right-click** on the extension icon
2. **Select "Inspect popup"** or "Inspect sidebar"
3. **Check for errors** in the console

### **Check Content Script Console:**
1. **Open Developer Tools** (F12) on Telegram page
2. **Go to Console tab**
3. **Look for SignalScope logs** - should see initialization messages

### **Run Advanced Test:**
1. **Copy the test script** from `test_telegram_capture.js`
2. **Paste in Telegram console**
3. **Run `runAllTests()`** to get detailed diagnostics

## 🚨 **Common Issues & Solutions**

### **Issue 1: Extension Not Reloaded**
**Solution:** Make sure you clicked the reload button in chrome://extensions/

### **Issue 2: Content Script Not Loading**
**Solution:** Check if the file paths in manifest.json are correct

### **Issue 3: Webhook URL Wrong**
**Solution:** Make sure webhook URL is set to `http://localhost:8000/api/webhooks/signalscope`

### **Issue 4: Capture Not Starting**
**Solution:** Check extension popup/sidebar for start button

## 📊 **What You Should See**

### **In Server Terminal:**
```
📨 Received POST to /api/webhooks/signalscope
📦 Data: {
  "messages": [
    {
      "id": "...",
      "platform": "telegram",
      "author": "User Name",
      "content": "Message content",
      "timestamp": "2025-09-15T...",
      "intelligence": { ... }
    }
  ]
}
```

### **In Extension Sidebar:**
- List of captured messages
- Message details (author, content, timestamp)
- Intelligence analysis results

### **In Browser Console:**
```
[INFO] Enhanced content script initialized successfully
[INFO] Platform detected: telegram
[INFO] Starting enhanced capture system...
[SUCCESS] Network interception started
[SUCCESS] DOM observation started
[SUCCESS] Capture system started in hybrid mode
```

## 🎯 **Advanced Testing**

### **Test Different Capture Methods:**
1. **DOM Capture:** Send messages and check if they're captured
2. **Network Capture:** Check if WebSocket/API calls are intercepted
3. **Hybrid Mode:** Should use both methods automatically

### **Test Background Tab Resilience:**
1. **Start capture** on Telegram
2. **Switch to another tab**
3. **Send messages** in Telegram (in background)
4. **Check server** - should still receive messages

### **Test Platform Detection:**
```javascript
// In Telegram console
console.log('Detected platform:', window.signalScopeEnhanced?.platform);
// Should show: "telegram"
```

## 🚀 **Expected Results After Fix**

Once properly integrated, you should see:

1. ✅ **Extension loads** enhanced content script
2. ✅ **Telegram messages** are captured automatically
3. ✅ **Server receives** webhook data with message details
4. ✅ **Background tab** continues capturing when minimized
5. ✅ **Network interception** captures WebSocket/API calls
6. ✅ **Intelligence analysis** processes messages for trading signals

## 📞 **If Still Not Working**

1. **Check the server terminal** for any error messages
2. **Verify webhook URL** is correct in extension settings
3. **Test with the test page** first (`test_enhanced_capture.html`)
4. **Check browser console** for JavaScript errors
5. **Try reloading** the extension and Telegram page

---

**🎉 Once working, your Telegram capture will be bulletproof and work regardless of browser state!**



