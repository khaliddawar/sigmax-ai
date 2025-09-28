# 🚀 Enhanced Capture System Testing Guide

## ✅ Server Status

**Simple Backend Server (Port 8000):** ✅ **RUNNING**
- Health: http://localhost:8000/health
- Webhook: http://localhost:8000/api/webhooks/signalscope

**Main Backend Server (Port 8001):** 🔄 **STARTING**
- Health: http://localhost:8001/health  
- Webhook: http://localhost:8001/api/webhooks/signalscope

## 🎮 How to Test the Enhanced Capture System

### Step 1: Open the Test Page
1. **Open your browser** and navigate to:
   ```
   file:///C:/Users/KhalidNoor/Documents/GitHub/SignalScope/test_enhanced_capture.html
   ```
   
   Or simply **double-click** the `test_enhanced_capture.html` file in your file explorer.

### Step 2: Initialize the System
1. **Wait for initialization** - You should see log messages appear automatically
2. **Look for these messages:**
   ```
   [INFO] Enhanced Capture System Test initialized
   [INFO] Click "Start Capture" to begin testing
   ```

### Step 3: Start Capture
1. **Click "Start Capture"** button
2. **Verify the status** changes to "Active (hybrid mode)"
3. **Check the log** for success messages:
   ```
   [INFO] Starting enhanced capture system...
   [SUCCESS] Network interception started
   [SUCCESS] DOM observation started
   [SUCCESS] Capture system started in hybrid mode
   ```

### Step 4: Test Different Capture Methods

#### 🖱️ **Test DOM Capture:**
1. Click **"Add Message"** button multiple times
2. Watch the **DOM Messages counter** increase
3. Check the log for: `[SUCCESS] DOM message captured: ...`

#### 🌐 **Test Network Capture:**
1. Click **"Simulate WebSocket"** button
2. Click **"Simulate SSE"** button  
3. Watch the **Network Messages** and **WebSocket Messages** counters increase
4. Check the log for network capture messages

#### 🔄 **Test Mode Switching:**
1. Click **"Switch to Network"** - should show "Active (network mode)"
2. Click **"Switch to DOM"** - should show "Active (dom mode)"  
3. Click **"Switch to Hybrid"** - should show "Active (hybrid mode)"

#### 👁️ **Test Background Tab Simulation:**
1. Click **"Simulate Background Tab"** - simulates hidden page
2. Click **"Simulate Foreground Tab"** - simulates visible page
3. Watch the log for visibility change messages

### Step 5: Test with Real Extension

#### Configure Extension for Local Testing:
1. **Open Chrome Extensions** (chrome://extensions/)
2. **Load your SignalScope extension** (if not already loaded)
3. **Open extension options** and set webhook URL to:
   ```
   http://localhost:8000/api/webhooks/signalscope
   ```

#### Test Extension Integration:
1. **Navigate to a chat platform** (Discord, Telegram, etc.)
2. **Open the extension popup** and start capture
3. **Send messages** in the chat
4. **Check the server logs** for received webhook data

## 📊 What to Look For

### ✅ **Success Indicators:**
- Status shows "Active" with mode
- Message counters increase when testing
- Log shows capture success messages
- Server receives webhook data (check terminal)

### ❌ **Error Indicators:**
- Status shows "Inactive" 
- Buttons don't respond (check console for errors)
- No log messages appear
- Server connection errors

## 🔧 Troubleshooting

### **Buttons Not Working:**
- **Refresh the page** - initialization might have failed
- **Check browser console** (F12) for JavaScript errors
- **Wait for initialization** - look for "Enhanced Capture System Test initialized" message

### **Server Connection Issues:**
- **Check if server is running:** Run `python test_servers.py`
- **Try different port:** The simple server runs on port 8000
- **Check firewall:** Windows might be blocking the connection

### **Extension Not Capturing:**
- **Check webhook URL** in extension options
- **Verify extension permissions** for the chat platform
- **Check extension console** for errors
- **Test with the test page first** before real platforms

## 📈 Expected Results

### **Test Page Results:**
- **DOM Messages:** Should increase when clicking "Add Message"
- **Network Messages:** Should increase when simulating WebSocket/SSE
- **Total Captured:** Should be sum of all capture methods
- **Log Messages:** Should show detailed capture information

### **Real Extension Results:**
- **Server Logs:** Should show received webhook data
- **Extension Sidebar:** Should display captured messages
- **Background Tab:** Should continue capturing when tab is hidden

## 🎯 Advanced Testing

### **Test Health Monitoring:**
1. Click **"Test Health Check"** 
2. Should see health check simulation in logs

### **Test Log Export:**
1. Click **"Export Log"** 
2. Should download a text file with all log entries

### **Test Different Platforms:**
1. Try the extension on **Discord, Telegram, Slack, WhatsApp**
2. Each platform should trigger different capture methods
3. Check which method works best for each platform

## 🚀 Next Steps

Once testing is complete:

1. **Integrate the hybrid capture system** into your main extension
2. **Update your content scripts** to use the new capture methods
3. **Test on real chat platforms** with the enhanced system
4. **Monitor performance** and adjust capture modes as needed

## 📞 Support

If you encounter issues:
1. **Check the browser console** for JavaScript errors
2. **Check the server terminal** for backend errors  
3. **Run the test script** to verify server status
4. **Review the log messages** for detailed error information

---

**🎉 Happy Testing!** The enhanced capture system should now work regardless of browser state, tab visibility, or UI changes!