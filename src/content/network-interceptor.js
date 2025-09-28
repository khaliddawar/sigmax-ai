/**
 * Network Interceptor for Message Capture
 * 
 * This module intercepts network requests to capture messages at the API level,
 * providing the most reliable capture method for platforms that use AJAX/fetch.
 */

import { createLogger } from '../shared/logger.js';
import { shouldSkipMessage } from './platform-filters.js';

const logger = createLogger('NetworkInterceptor');

class NetworkInterceptor {
  constructor() {
    this.originalFetch = window.fetch;
    this.originalXHROpen = XMLHttpRequest.prototype.open;
    this.originalXHRSend = XMLHttpRequest.prototype.send;
    this.originalWebSocket = window.WebSocket;
    this.originalEventSource = window.EventSource;
    this.messageHandlers = [];
    this.isActive = false;
    this.websocketConnections = new Map();
    this.sseConnections = new Map();
  }

  start() {
    if (this.isActive) {
      logger.warn('Network interceptor already active');
      return;
    }

    logger.info('Starting network interceptor');
    this.isActive = true;

    // Intercept fetch requests
    this.interceptFetch();
    
    // Intercept XMLHttpRequest
    this.interceptXHR();
    
    // Intercept WebSocket connections
    this.interceptWebSocket();
    
    // Intercept Server-Sent Events
    this.interceptEventSource();
  }

  stop() {
    if (!this.isActive) {
      return;
    }

    logger.info('Stopping network interceptor');
    this.isActive = false;

    // Restore original methods
    window.fetch = this.originalFetch;
    XMLHttpRequest.prototype.open = this.originalXHROpen;
    XMLHttpRequest.prototype.send = this.originalXHRSend;
    window.WebSocket = this.originalWebSocket;
    window.EventSource = this.originalEventSource;
    
    // Close tracked connections
    this.websocketConnections.forEach(ws => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });
    this.websocketConnections.clear();
    
    this.sseConnections.forEach(sse => {
      if (sse.readyState === EventSource.OPEN) {
        sse.close();
      }
    });
    this.sseConnections.clear();
  }

  interceptFetch() {
    const self = this;
    
    window.fetch = async function(...args) {
      const [resource, config] = args;
      const url = typeof resource === 'string' ? resource : resource.url;
      
      try {
        const response = await self.originalFetch.apply(this, args);
        
        // Clone response to avoid consuming it
        const clonedResponse = response.clone();
        
        // Check if this is a message-related request
        if (self.isMessageRequest(url)) {
          self.handleResponse(url, clonedResponse, 'fetch');
        }
        
        return response;
      } catch (error) {
        logger.error('Fetch interceptor error:', error);
        throw error;
      }
    };
  }

  interceptXHR() {
    const self = this;
    
    XMLHttpRequest.prototype.open = function(method, url, ...args) {
      this._interceptedUrl = url;
      this._interceptedMethod = method;
      return self.originalXHROpen.apply(this, [method, url, ...args]);
    };

    XMLHttpRequest.prototype.send = function(data) {
      const xhr = this;
      const url = xhr._interceptedUrl;
      const method = xhr._interceptedMethod;

      // Add response handler
      const originalOnReadyStateChange = xhr.onreadystatechange;
      xhr.onreadystatechange = function() {
        if (originalOnReadyStateChange) {
          originalOnReadyStateChange.apply(this, arguments);
        }

        if (xhr.readyState === 4 && xhr.status >= 200 && xhr.status < 300) {
          if (self.isMessageRequest(url)) {
            self.handleXHRResponse(url, xhr);
          }
        }
      };

      return self.originalXHRSend.apply(this, [data]);
    };
  }

  isMessageRequest(url) {
    if (!url) return false;

    const messagePatterns = [
      // Discord
      /discord\.com\/api\/v\d+\/channels\/\d+\/messages/,
      /discordapp\.com\/api\/v\d+\/channels\/\d+\/messages/,
      
      // Telegram
      /telegram\.org\/api\/v\d+\/messages/,
      /web\.telegram\.org\/api\/v\d+\/messages/,
      
      // WhatsApp
      /whatsapp\.com\/api\/messages/,
      /web\.whatsapp\.com\/api\/messages/,
      
      // Slack
      /slack\.com\/api\/conversations\.history/,
      /slack\.com\/api\/chat\.postMessage/,
      
      // Circle.so
      /circle\.so\/api\/messages/,
      /members\.\w+\.com\/api\/messages/,
      
      // Generic patterns
      /\/api\/.*messages/,
      /\/api\/.*chat/,
      /\/api\/.*conversation/,
      /\/messages/,
      /\/chat/
    ];

    return messagePatterns.some(pattern => pattern.test(url));
  }

  async handleResponse(url, response, type) {
    try {
      const contentType = response.headers.get('content-type');
      
      if (!contentType || !contentType.includes('application/json')) {
        return;
      }

      const data = await response.json();
      
      // Extract messages from response
      const messages = this.extractMessagesFromResponse(data, url);
      
      if (messages.length > 0) {
        const filtered = messages.filter((m) => !shouldSkipMessage(m));
        if (filtered.length === 0) return;
        logger.info(`Captured ${filtered.length} messages from ${type} request to ${url}`);
        
        // Notify handlers
        this.messageHandlers.forEach(handler => {
          try {
            handler(filtered, { url, type, source: 'network' });
          } catch (error) {
            logger.error('Error in message handler:', error);
          }
        });
      }
    } catch (error) {
      logger.error('Error handling response:', error);
    }
  }

  handleXHRResponse(url, xhr) {
    try {
      const contentType = xhr.getResponseHeader('content-type');
      
      if (!contentType || !contentType.includes('application/json')) {
        return;
      }

      const data = JSON.parse(xhr.responseText);
      
      // Extract messages from response
      const messages = this.extractMessagesFromResponse(data, url);
      
      if (messages.length > 0) {
        const filtered = messages.filter((m) => !shouldSkipMessage(m));
        if (filtered.length === 0) return;
        logger.info(`Captured ${filtered.length} messages from XHR request to ${url}`);
        
        // Notify handlers
        this.messageHandlers.forEach(handler => {
          try {
            handler(filtered, { url, type: 'xhr', source: 'network' });
          } catch (error) {
            logger.error('Error in message handler:', error);
          }
        });
      }
    } catch (error) {
      logger.error('Error handling XHR response:', error);
    }
  }

  extractMessagesFromResponse(data, url) {
    const messages = [];

    // Platform-specific extraction logic
    if (this.isDiscordRequest(url)) {
      messages.push(...this.extractDiscordMessages(data));
    } else if (this.isTelegramRequest(url)) {
      messages.push(...this.extractTelegramMessages(data));
    } else if (this.isWhatsAppRequest(url)) {
      messages.push(...this.extractWhatsAppMessages(data));
    } else if (this.isSlackRequest(url)) {
      messages.push(...this.extractSlackMessages(data));
    } else if (this.isCircleRequest(url)) {
      messages.push(...this.extractCircleMessages(data));
    } else {
      // Generic extraction
      messages.push(...this.extractGenericMessages(data));
    }

    return messages;
  }

  // Platform detection methods
  isDiscordRequest(url) {
    return /discord\.com|discordapp\.com/.test(url);
  }

  isTelegramRequest(url) {
    return /telegram\.org|web\.telegram\.org/.test(url);
  }

  isWhatsAppRequest(url) {
    return /whatsapp\.com|web\.whatsapp\.com/.test(url);
  }

  isSlackRequest(url) {
    return /slack\.com/.test(url);
  }

  isCircleRequest(url) {
    return /circle\.so|members\.\w+\.com/.test(url);
  }

  // Platform-specific message extraction
  extractDiscordMessages(data) {
    const messages = [];
    
    if (Array.isArray(data)) {
      data.forEach(msg => {
        if (msg.content || msg.embeds?.length > 0) {
          messages.push({
            id: msg.id,
            author: msg.author?.username || 'Unknown',
            content: msg.content || '',
            timestamp: msg.timestamp,
            attachments: msg.attachments || [],
            embeds: msg.embeds || [],
            platform: 'discord'
          });
        }
      });
    }
    
    return messages;
  }

  extractTelegramMessages(data) {
    const messages = [];
    
    if (data.result && Array.isArray(data.result)) {
      data.result.forEach(msg => {
        if (msg.message) {
          messages.push({
            id: msg.message.message_id,
            author: msg.message.from?.username || 'Unknown',
            content: msg.message.text || '',
            timestamp: new Date(msg.message.date * 1000).toISOString(),
            attachments: msg.message.photo || msg.message.document ? [msg.message.photo || msg.message.document] : [],
            platform: 'telegram'
          });
        }
      });
    }
    
    return messages;
  }

  extractWhatsAppMessages(data) {
    const messages = [];
    
    if (data.messages && Array.isArray(data.messages)) {
      data.messages.forEach(msg => {
        messages.push({
          id: msg.id,
          author: msg.sender || 'Unknown',
          content: msg.body || '',
          timestamp: msg.timestamp,
          attachments: msg.media ? [msg.media] : [],
          platform: 'whatsapp'
        });
      });
    }
    
    return messages;
  }

  extractSlackMessages(data) {
    const messages = [];
    
    if (data.messages && Array.isArray(data.messages)) {
      data.messages.forEach(msg => {
        messages.push({
          id: msg.ts,
          author: msg.user || 'Unknown',
          content: msg.text || '',
          timestamp: new Date(parseFloat(msg.ts) * 1000).toISOString(),
          attachments: msg.attachments || [],
          platform: 'slack'
        });
      });
    }
    
    return messages;
  }

  extractCircleMessages(data) {
    const messages = [];
    
    if (data.messages && Array.isArray(data.messages)) {
      data.messages.forEach(msg => {
        messages.push({
          id: msg.id,
          author: msg.author?.name || 'Unknown',
          content: msg.content || '',
          timestamp: msg.created_at,
          attachments: msg.attachments || [],
          platform: 'circle'
        });
      });
    }
    
    return messages;
  }

  extractGenericMessages(data) {
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
              platform: 'generic'
            });
          }
        });
        break; // Use first valid array found
      }
    }
    
    return messages;
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

  // WebSocket interception
  interceptWebSocket() {
    const self = this;
    
    window.WebSocket = class extends this.originalWebSocket {
      constructor(url, protocols) {
        super(url, protocols);
        this._interceptedUrl = url;
        
        // Track this connection
        self.websocketConnections.set(this, {
          url,
          startTime: Date.now(),
          messages: []
        });
        
        // Intercept messages
        this.addEventListener('message', (event) => {
          self.handleWebSocketMessage(this, event.data, 'received');
        });
        
        // Intercept sends
        const originalSend = this.send;
        this.send = function(data) {
          self.handleWebSocketMessage(this, data, 'sent');
          return originalSend.call(this, data);
        };
        
        logger.info(`WebSocket connection intercepted: ${url}`);
      }
    };
  }

  // EventSource (SSE) interception
  interceptEventSource() {
    const self = this;
    
    window.EventSource = class extends this.originalEventSource {
      constructor(url, eventSourceInitDict) {
        super(url, eventSourceInitDict);
        this._interceptedUrl = url;
        
        // Track this connection
        self.sseConnections.set(this, {
          url,
          startTime: Date.now(),
          messages: []
        });
        
        // Intercept all events
        this.addEventListener('message', (event) => {
          self.handleSSEMessage(this, event);
        });
        
        // Intercept custom events
        this.addEventListener('open', (event) => {
          logger.info(`SSE connection opened: ${url}`);
        });
        
        this.addEventListener('error', (event) => {
          logger.warn(`SSE connection error: ${url}`, event);
        });
        
        logger.info(`EventSource connection intercepted: ${url}`);
      }
    };
  }

  handleWebSocketMessage(ws, data, direction) {
    try {
      const connection = this.websocketConnections.get(ws);
      if (!connection) return;
      
      // Check if this looks like a chat message
      if (this.isChatWebSocketMessage(connection.url, data)) {
        const message = this.parseWebSocketMessage(data, connection.url, direction);
        if (message) {
          connection.messages.push(message);
          
          logger.info(`WebSocket ${direction} message captured from ${connection.url}`);
          
          // Notify handlers
          this.messageHandlers.forEach(handler => {
            try {
              handler([message], { 
                url: connection.url, 
                type: 'websocket', 
                direction,
                source: 'network' 
              });
            } catch (error) {
              logger.error('Error in WebSocket message handler:', error);
            }
          });
        }
      }
    } catch (error) {
      logger.error('Error handling WebSocket message:', error);
    }
  }

  handleSSEMessage(sse, event) {
    try {
      const connection = this.sseConnections.get(sse);
      if (!connection) return;
      
      // Check if this looks like a chat message
      if (this.isChatSSEMessage(connection.url, event.data)) {
        const message = this.parseSSEMessage(event, connection.url);
        if (message) {
          connection.messages.push(message);
          
          logger.info(`SSE message captured from ${connection.url}`);
          
          // Notify handlers
          this.messageHandlers.forEach(handler => {
            try {
              handler([message], { 
                url: connection.url, 
                type: 'sse', 
                source: 'network' 
              });
            } catch (error) {
              logger.error('Error in SSE message handler:', error);
            }
          });
        }
      }
    } catch (error) {
      logger.error('Error handling SSE message:', error);
    }
  }

  isChatWebSocketMessage(url, data) {
    if (!url || !data) return false;
    
    // Check URL patterns
    const chatPatterns = [
      /discord\.com.*gateway/,
      /telegram\.org.*websocket/,
      /slack\.com.*rtm/,
      /whatsapp\.com.*websocket/,
      /circle\.so.*websocket/,
      /websocket.*chat/,
      /websocket.*message/
    ];
    
    if (!chatPatterns.some(pattern => pattern.test(url))) {
      return false;
    }
    
    // Check data content
    try {
      const parsed = typeof data === 'string' ? JSON.parse(data) : data;
      return this.hasMessageStructure(parsed);
    } catch {
      // If not JSON, check for text patterns
      const text = String(data).toLowerCase();
      return text.includes('message') || text.includes('chat') || text.includes('content');
    }
  }

  isChatSSEMessage(url, data) {
    if (!url || !data) return false;
    
    // Check URL patterns
    const chatPatterns = [
      /discord\.com.*events/,
      /telegram\.org.*stream/,
      /slack\.com.*events/,
      /whatsapp\.com.*stream/,
      /circle\.so.*events/,
      /events.*chat/,
      /stream.*message/
    ];
    
    if (!chatPatterns.some(pattern => pattern.test(url))) {
      return false;
    }
    
    // Check data content
    try {
      const parsed = JSON.parse(data);
      return this.hasMessageStructure(parsed);
    } catch {
      // If not JSON, check for text patterns
      const text = String(data).toLowerCase();
      return text.includes('message') || text.includes('chat') || text.includes('content');
    }
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

  parseWebSocketMessage(data, url, direction) {
    try {
      const parsed = typeof data === 'string' ? JSON.parse(data) : data;
      
      // Platform-specific parsing
      if (this.isDiscordRequest(url)) {
        return this.parseDiscordWebSocketMessage(parsed, direction);
      } else if (this.isTelegramRequest(url)) {
        return this.parseTelegramWebSocketMessage(parsed, direction);
      } else if (this.isSlackRequest(url)) {
        return this.parseSlackWebSocketMessage(parsed, direction);
      } else {
        return this.parseGenericWebSocketMessage(parsed, url, direction);
      }
    } catch (error) {
      logger.error('Error parsing WebSocket message:', error);
      return null;
    }
  }

  parseSSEMessage(event, url) {
    try {
      const data = JSON.parse(event.data);
      
      // Platform-specific parsing
      if (this.isDiscordRequest(url)) {
        return this.parseDiscordSSEMessage(data);
      } else if (this.isTelegramRequest(url)) {
        return this.parseTelegramSSEMessage(data);
      } else if (this.isSlackRequest(url)) {
        return this.parseSlackSSEMessage(data);
      } else {
        return this.parseGenericSSEMessage(data, url);
      }
    } catch (error) {
      logger.error('Error parsing SSE message:', error);
      return null;
    }
  }

  // Platform-specific WebSocket message parsers
  parseDiscordWebSocketMessage(data, direction) {
    if (data.t === 'MESSAGE_CREATE' && data.d) {
      return {
        id: data.d.id,
        author: data.d.author?.username || 'Unknown',
        content: data.d.content || '',
        timestamp: data.d.timestamp,
        attachments: data.d.attachments || [],
        embeds: data.d.embeds || [],
        platform: 'discord',
        source: 'websocket',
        direction
      };
    }
    return null;
  }

  parseTelegramWebSocketMessage(data, direction) {
    if (data.message) {
      return {
        id: data.message.message_id,
        author: data.message.from?.username || 'Unknown',
        content: data.message.text || '',
        timestamp: new Date(data.message.date * 1000).toISOString(),
        attachments: data.message.photo || data.message.document ? [data.message.photo || data.message.document] : [],
        platform: 'telegram',
        source: 'websocket',
        direction
      };
    }
    return null;
  }

  parseSlackWebSocketMessage(data, direction) {
    if (data.type === 'message' && data.text) {
      return {
        id: data.ts,
        author: data.user || 'Unknown',
        content: data.text || '',
        timestamp: new Date(parseFloat(data.ts) * 1000).toISOString(),
        attachments: data.attachments || [],
        platform: 'slack',
        source: 'websocket',
        direction
      };
    }
    return null;
  }

  parseGenericWebSocketMessage(data, url, direction) {
    if (this.hasMessageStructure(data)) {
      return {
        id: data.id || data.message_id || Date.now().toString(),
        author: data.author || data.user || data.sender || 'Unknown',
        content: data.content || data.text || data.message || '',
        timestamp: data.timestamp || data.created_at || new Date().toISOString(),
        attachments: data.attachments || [],
        platform: 'generic',
        source: 'websocket',
        direction
      };
    }
    return null;
  }

  // Platform-specific SSE message parsers
  parseDiscordSSEMessage(data) {
    if (data.type === 'MESSAGE_CREATE' && data.data) {
      return {
        id: data.data.id,
        author: data.data.author?.username || 'Unknown',
        content: data.data.content || '',
        timestamp: data.data.timestamp,
        attachments: data.data.attachments || [],
        embeds: data.data.embeds || [],
        platform: 'discord',
        source: 'sse'
      };
    }
    return null;
  }

  parseTelegramSSEMessage(data) {
    if (data.message) {
      return {
        id: data.message.message_id,
        author: data.message.from?.username || 'Unknown',
        content: data.message.text || '',
        timestamp: new Date(data.message.date * 1000).toISOString(),
        attachments: data.message.photo || data.message.document ? [data.message.photo || data.message.document] : [],
        platform: 'telegram',
        source: 'sse'
      };
    }
    return null;
  }

  parseSlackSSEMessage(data) {
    if (data.type === 'message' && data.text) {
      return {
        id: data.ts,
        author: data.user || 'Unknown',
        content: data.text || '',
        timestamp: new Date(parseFloat(data.ts) * 1000).toISOString(),
        attachments: data.attachments || [],
        platform: 'slack',
        source: 'sse'
      };
    }
    return null;
  }

  parseGenericSSEMessage(data, url) {
    if (this.hasMessageStructure(data)) {
      return {
        id: data.id || data.message_id || Date.now().toString(),
        author: data.author || data.user || data.sender || 'Unknown',
        content: data.content || data.text || data.message || '',
        timestamp: data.timestamp || data.created_at || new Date().toISOString(),
        attachments: data.attachments || [],
        platform: 'generic',
        source: 'sse'
      };
    }
    return null;
  }
}

export default NetworkInterceptor;
