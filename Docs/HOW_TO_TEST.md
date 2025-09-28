# 🧪 How to Test Your SignalScope Extension

## ✅ Servers Running Successfully

Your servers are now running:
- **Backend API**: `http://localhost:8000` ✅ Healthy
- **Test Server**: `http://localhost:8080` ✅ Ready

## 🚀 Step-by-Step Testing Guide

### **Step 1: Open the Test Interface**
1. Open your web browser
2. Go to: **`http://localhost:8080/test_sidebar_fixes.html`**
3. You should see the "SignalScope Sidebar Fix Test" interface

### **Step 2: Reload Your Extension**
1. Go to `chrome://extensions/`
2. Find "SignalScope" extension
3. Click the **refresh/reload button** 🔄

### **Step 3: Open the Sidebar**
1. Click the **SignalScope extension icon** in your browser toolbar
2. The sidebar should open on the right side

### **Step 4: Run Automated Tests**
In the test interface:

1. **Click "Check System Status"** - This will verify:
   - ✅ Chrome API availability
   - ✅ Extension configuration
   - ✅ Service worker status
   - ✅ Preview buffer status

2. **Click "Auto Fix Issues"** - This will:
   - ✅ Fix configuration settings
   - ✅ Sync queue to preview
   - ✅ Test message capture

3. **Click "Test Message Capture"** - This will:
   - ✅ Send 4 test messages
   - ✅ Verify they're captured
   - ✅ Check if they appear in sidebar

### **Step 5: Manual Testing**
1. **Open the sidebar** (click extension icon)
2. **Send a test message** using browser console:
   ```javascript
   chrome.runtime.sendMessage(chrome.runtime.id, {
       type: 'CAPTURE_MESSAGE',
       data: {
           id: `test-${Date.now()}`,
           content: 'Manual test message',
           author: 'Test User',
           platform: 'generic',
           channel: 'test',
           timestamp: new Date().toISOString()
       }
   }, response => {
       console.log('Result:', response);
   });
   ```
3. **Check the sidebar** - The message should appear immediately

## 🔍 What to Look For

### **✅ Success Indicators:**
- Test interface shows all green status indicators
- Messages appear in the sidebar in real-time
- Stats panel shows correct counts
- No console errors

### **❌ Troubleshooting:**
If tests fail:
1. **Click "Fix Configuration"** in test interface
2. **Click "Force Reload Extension"**
3. **Try "Clear & Reset"** if needed
4. Check browser console for errors

## 📊 Expected Results

After successful testing:
- ✅ Extension captures messages from chat platforms
- ✅ Messages appear immediately in sidebar
- ✅ Backend receives webhook calls at `http://localhost:8000/api/webhooks/signalscope`
- ✅ Stats show correct message counts
- ✅ Platform filtering works
- ✅ Search functionality works

## 🎯 Quick Test Commands

**Test Backend Health:**
```bash
curl http://localhost:8000/health
```

**Test Extension in Console:**
```javascript
// Quick extension test
chrome.runtime.sendMessage(chrome.runtime.id, {
    type: 'GET_STATS'
}, response => console.log('Extension Stats:', response));
```

## 🚨 If Something Goes Wrong

1. **Check servers are running:**
   - Backend: `http://localhost:8000/health`
   - Test server: `http://localhost:8080`

2. **Restart servers if needed:**
   ```bash
   # In signalscope-backend directory
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   
   # In project root
   python -m http.server 8080
   ```

3. **Use the diagnostic tools** I provided earlier

---

**🎉 Ready to test! Go to: `http://localhost:8080/test_sidebar_fixes.html`**
