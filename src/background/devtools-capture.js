/**
 * DevTools Protocol Capture
 * 
 * Uses Chrome DevTools Protocol to capture network traffic at the protocol level.
 * This provides the most robust capture method that works even when tabs are hidden.
 */

import { createLogger } from '../shared/logger.js';

const logger = createLogger('DevToolsCapture');

class DevToolsCapture {
  constructor() {
    this.attachedTabs = new Map();
    this.messageHandlers = [];
    this.isActive = false;
  }

  async initialize() {
    try {
      logger.info('Initializing DevTools capture');
      
      // Set up message listener
      chrome.debugger.onEvent.addListener(this.handleDebuggerEvent.bind(this));
      chrome.debugger.onDetach.addListener(this.handleDebuggerDetach.bind(this));
      
      this.isActive = true;
      logger.info('DevTools capture initialized');
      
    } catch (error) {
      logger.error('Failed to initialize DevTools capture:', error);
      throw error;
    }
  }

  async attachToTab(tabId) {
    try {
      if (this.attachedTabs.has(tabId)) {
        logger.warn(`Tab ${tabId} already attached`);
        return;
      }

      logger.info(`Attaching DevTools to tab ${tabId}`);
      
      // Attach to tab
      await chrome.debugger.attach({ tabId }, "1.3");
      
      // Enable network domain
      await chrome.debugger.sendCommand({ tabId }, "Network.enable");
      
      // Enable runtime domain for better error handling
      await chrome.debugger.sendCommand({ tabId }, "Runtime.enable");
      
      // Track attached tab
      this.attachedTabs.set(tabId, {
        attachedAt: Date.now(),
        messageCount: 0,
        lastActivity: Date.now()
      });
      
      logger.info(`Successfully attached to tab ${tabId}`);
      
    } catch (error) {
      logger.error(`Failed to attach to tab ${tabId}:`, error);
      throw error;
    }
  }

  async detachFromTab(tabId) {
    try {
      if (!this.attachedTabs.has(tabId)) {
        logger.warn(`Tab ${tabId} not attached`);
        return;
      }

      logger.info(`Detaching DevTools from tab ${tabId}`);
      
      await chrome.debugger.detach({ tabId });
      this.attachedTabs.delete(tabId);
      
      logger.info(`Successfully detached from tab ${tabId}`);
      
    } catch (error) {
      logger.error(`Failed to detach from tab ${tabId}:`, error);
    }
  }

  async handleDebuggerEvent(source, method, params) {
    try {
      const tabId = source.tabId;
      
      if (!this.attachedTabs.has(tabId)) {
        return; // Not tracking this tab
      }

      // Update activity
      const tabInfo = this.attachedTabs.get(tabId);
      tabInfo.lastActivity = Date.now();

      // Handle different event types
      switch (method) {
        case 'Network.webSocketFrameReceived':
          await this.handleWebSocketFrame(tabId, params, 'received');
          break;
          
        case 'Network.webSocketFrameSent':
          await this.handleWebSocketFrame(tabId, params, 'sent');
          break;
          
        case 'Network.responseReceived':
          await this.handleResponseReceived(tabId, params);
          break;
          
        case 'Network.loadingFinished':
          await this.handleLoadingFinished(tabId, params);
          break;
          
        case 'Runtime.consoleAPICalled':
          await this.handleConsoleMessage(tabId, params);
          break;
          
        default:
          // Ignore other events
          break;
      }
      
    } catch (error) {
      logger.error('Error handling debugger event:', error);
    }
  }

  async handleWebSocketFrame(tabId, params, direction) {
    try {
      const { requestId, timestamp, response } = params;
      
      if (!response || !response.payloadData) {
        return;
      }

      // Get request details
      const requestDetails = await this.getRequestDetails(tabId, requestId);
      if (!requestDetails) {
        return;
      }

      // Check if this is a chat-related WebSocket
      if (!this.isChatWebSocket(requestDetails.url)) {
        return;
      }

      // Parse the payload
      const message = this.parseWebSocketPayload(response.payloadData, requestDetails.url, direction);
      if (!message) {
        return;
      }

      // Update tab stats
      const tabInfo = this.attachedTabs.get(tabId);
      tabInfo.messageCount++;

      logger.info(`WebSocket ${direction} message captured from tab ${tabId}`);

      // Notify handlers
      this.messageHandlers.forEach(handler => {
        try {
          handler(message, {
            tabId,
            source: 'devtools',
            type: 'websocket',
            direction,
            url: requestDetails.url
          });
        } catch (error) {
          logger.error('Error in WebSocket message handler:', error);
        }
      });

    } catch (error) {
      logger.error('Error handling WebSocket frame:', error);
    }
  }

  async handleResponseReceived(tabId, params) {
    try {
      const { requestId, response } = params;
      
      if (!response || !response.url) {
        return;
      }

      // Check if this is a chat-related response
      if (!this.isChatResponse(response.url, response.mimeType)) {
        return;
      }

      // Store response info for later processing
      const tabInfo = this.attachedTabs.get(tabId);
      if (!tabInfo.responses) {
        tabInfo.responses = new Map();
      }
      
      tabInfo.responses.set(requestId, {
        url: response.url,
        mimeType: response.mimeType,
        status: response.status,
        receivedAt: Date.now()
      });

    } catch (error) {
      logger.error('Error handling response received:', error);
    }
  }

  async handleLoadingFinished(tabId, params) {
    try {
      const { requestId } = params;
      
      const tabInfo = this.attachedTabs.get(tabId);
      if (!tabInfo || !tabInfo.responses || !tabInfo.responses.has(requestId)) {
        return;
      }

      const responseInfo = tabInfo.responses.get(requestId);
      
      // Get response body
      try {
        const bodyResult = await chrome.debugger.sendCommand({ tabId }, "Network.getResponseBody", { requestId });
        
        if (bodyResult && bodyResult.body) {
          const message = this.parseResponseBody(bodyResult.body, responseInfo);
          if (message) {
            logger.info(`Response body captured from tab ${tabId}`);
            
            // Notify handlers
            this.messageHandlers.forEach(handler => {
              try {
                handler(message, {
                  tabId,
                  source: 'devtools',
                  type: 'response',
                  url: responseInfo.url
                });
              } catch (error) {
                logger.error('Error in response message handler:', error);
              }
            });
          }
        }
      } catch (bodyError) {
        // Response body might not be available (e.g., for streaming responses)
        logger.debug('Could not get response body:', bodyError);
      }

      // Clean up
      tabInfo.responses.delete(requestId);

    } catch (error) {
      logger.error('Error handling loading finished:', error);
    }
  }

  async handleConsoleMessage(tabId, params) {
    try {
      const { type, args } = params;
      
      // Look for chat-related console messages
      if (type === 'log' || type === 'info') {
        for (const arg of args) {
          if (arg.type === 'string' && this.isChatConsoleMessage(arg.value)) {
            const message = this.parseConsoleMessage(arg.value, tabId);
            if (message) {
              logger.info(`Console message captured from tab ${tabId}`);
              
              // Notify handlers
              this.messageHandlers.forEach(handler => {
                try {
                  handler(message, {
                    tabId,
                    source: 'devtools',
                    type: 'console',
                    consoleType: type
                  });
                } catch (error) {
                  logger.error('Error in console message handler:', error);
                }
              });
            }
          }
        }
      }

    } catch (error) {
      logger.error('Error handling console message:', error);
    }
  }

  async getRequestDetails(tabId, requestId) {
    try {
      // This would require storing request details when they're received
      // For now, we'll use a simplified approach
      return {
        url: 'unknown',
        method: 'GET'
      };
    } catch (error) {
      logger.error('Error getting request details:', error);
      return null;
    }
  }

  isChatWebSocket(url) {
    if (!url) return false;
    
    const chatPatterns = [
      /discord\.com.*gateway/,
      /telegram\.org.*websocket/,
      /slack\.com.*rtm/,
      /whatsapp\.com.*websocket/,
      /circle\.so.*websocket/,
      /websocket.*chat/,
      /websocket.*message/
    ];
    
    return chatPatterns.some(pattern => pattern.test(url));
  }

  isChatResponse(url, mimeType) {
    if (!url) return false;
    
    // Check URL patterns
    const chatPatterns = [
      /discord\.com.*api.*messages/,
      /telegram\.org.*api.*messages/,
      /slack\.com.*api.*conversations/,
      /whatsapp\.com.*api.*messages/,
      /circle\.so.*api.*messages/,
      /api.*messages/,
      /api.*chat/
    ];
    
    if (!chatPatterns.some(pattern => pattern.test(url))) {
      return false;
    }
    
    // Check MIME type
    return mimeType && mimeType.includes('application/json');
  }

  isChatConsoleMessage(message) {
    if (!message || typeof message !== 'string') return false;
    
    const text = message.toLowerCase();
    return text.includes('message') || 
           text.includes('chat') || 
           text.includes('discord') ||
           text.includes('telegram') ||
           text.includes('slack');
  }

  parseWebSocketPayload(payloadData, url, direction) {
    try {
      // Try to parse as JSON
      const data = JSON.parse(payloadData);
      
      // Check if this looks like a chat message
      if (this.hasMessageStructure(data)) {
        return {
          id: data.id || data.message_id || Date.now().toString(),
          author: data.author || data.user || data.sender || 'Unknown',
          content: data.content || data.text || data.message || '',
          timestamp: data.timestamp || data.created_at || new Date().toISOString(),
          attachments: data.attachments || [],
          platform: this.detectPlatform(url),
          source: 'devtools-websocket',
          direction
        };
      }
      
    } catch (error) {
      // If not JSON, check for text patterns
      const text = String(payloadData).toLowerCase();
      if (text.includes('message') || text.includes('chat')) {
        return {
          id: Date.now().toString(),
          author: 'Unknown',
          content: payloadData,
          timestamp: new Date().toISOString(),
          attachments: [],
          platform: this.detectPlatform(url),
          source: 'devtools-websocket',
          direction
        };
      }
    }
    
    return null;
  }

  parseResponseBody(body, responseInfo) {
    try {
      const data = JSON.parse(body);
      
      // Extract messages from response
      const messages = this.extractMessagesFromResponse(data, responseInfo.url);
      
      if (messages.length > 0) {
        // Return the first message for now (could be modified to return all)
        return messages[0];
      }
      
    } catch (error) {
      logger.debug('Could not parse response body as JSON:', error);
    }
    
    return null;
  }

  parseConsoleMessage(message, tabId) {
    try {
      // Try to parse as JSON
      const data = JSON.parse(message);
      
      if (this.hasMessageStructure(data)) {
        return {
          id: data.id || data.message_id || Date.now().toString(),
          author: data.author || data.user || data.sender || 'Unknown',
          content: data.content || data.text || data.message || '',
          timestamp: data.timestamp || data.created_at || new Date().toISOString(),
          attachments: data.attachments || [],
          platform: 'unknown',
          source: 'devtools-console'
        };
      }
      
    } catch (error) {
      // If not JSON, check for text patterns
      if (this.isChatConsoleMessage(message)) {
        return {
          id: Date.now().toString(),
          author: 'Unknown',
          content: message,
          timestamp: new Date().toISOString(),
          attachments: [],
          platform: 'unknown',
          source: 'devtools-console'
        };
      }
    }
    
    return null;
  }

  extractMessagesFromResponse(data, url) {
    const messages = [];
    
    // Try to find messages in common data structures
    const possibleMessageArrays = [
      data.messages,
      data.data,
      data.results,
      data.items,
      data.content
    ];

    for (const array of possibleMessageArrays) {
      if (Array.isArray(array)) {
        array.forEach(item => {
          if (item.content || item.text || item.message) {
            messages.push({
              id: item.id || item.message_id || Date.now().toString(),
              author: item.author || item.user || item.sender || 'Unknown',
              content: item.content || item.text || item.message || '',
              timestamp: item.timestamp || item.created_at || new Date().toISOString(),
              attachments: item.attachments || [],
              platform: this.detectPlatform(url),
              source: 'devtools-response'
            });
          }
        });
        break; // Use first valid array found
      }
    }
    
    return messages;
  }

  hasMessageStructure(data) {
    if (!data || typeof data !== 'object') return false;
    
    // Check for common message fields
    const messageFields = ['content', 'text', 'message', 'body'];
    const authorFields = ['author', 'user', 'sender', 'from', 'username'];
    const timestampFields = ['timestamp', 'time', 'date', 'created_at'];
    
    const hasContent = messageFields.some(field => data[field]);
    const hasAuthor = authorFields.some(field => data[field]);
    const hasTimestamp = timestampFields.some(field => data[field]);
    
    return hasContent || (hasAuthor && hasTimestamp);
  }

  detectPlatform(url) {
    if (!url) return 'unknown';
    
    if (/discord\.com/.test(url)) return 'discord';
    if (/telegram\.org/.test(url)) return 'telegram';
    if (/slack\.com/.test(url)) return 'slack';
    if (/whatsapp\.com/.test(url)) return 'whatsapp';
    if (/circle\.so/.test(url)) return 'circle';
    
    return 'unknown';
  }

  handleDebuggerDetach(source, reason) {
    const tabId = source.tabId;
    logger.info(`DevTools detached from tab ${tabId}, reason: ${reason}`);
    
    if (this.attachedTabs.has(tabId)) {
      this.attachedTabs.delete(tabId);
    }
  }

  // Handler management
  addMessageHandler(handler) {
    this.messageHandlers.push(handler);
  }

  removeMessageHandler(handler) {
    const index = this.messageHandlers.indexOf(handler);
    if (index > -1) {
      this.messageHandlers.splice(index, 1);
    }
  }

  clearMessageHandlers() {
    this.messageHandlers = [];
  }

  // Control methods
  async stop() {
    try {
      logger.info('Stopping DevTools capture');
      
      this.isActive = false;
      
      // Detach from all tabs
      for (const tabId of this.attachedTabs.keys()) {
        try {
          await this.detachFromTab(tabId);
        } catch (error) {
          logger.error(`Error detaching from tab ${tabId}:`, error);
        }
      }
      
      this.attachedTabs.clear();
      
      logger.info('DevTools capture stopped');
      
    } catch (error) {
      logger.error('Error stopping DevTools capture:', error);
    }
  }

  getStats() {
    return {
      isActive: this.isActive,
      attachedTabs: Array.from(this.attachedTabs.keys()),
      totalMessages: Array.from(this.attachedTabs.values()).reduce((sum, tab) => sum + tab.messageCount, 0)
    };
  }
}

export default DevToolsCapture;



