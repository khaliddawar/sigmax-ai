import { PLATFORMS } from '../shared/constants.js';
import { extractText, formatTimestamp } from '../shared/utils.js';
import { createLogger } from '../shared/logger.js';

const logger = createLogger('MessageParser');

class MessageParser {
  constructor(platform) {
    this.platform = platform;
    this.platformConfig = PLATFORMS[platform.toUpperCase()] || null;
  }

  parse(element) {
    try {
      if (!element) {
        return null;
      }
      
      // Use platform-specific parser if available
      const platformParser = this.getPlatformParser();
      if (platformParser) {
        return platformParser(element);
      }
      
      // Fallback to generic parser
      return this.genericParse(element);
    } catch (error) {
      logger.error('Error parsing message:', error);
      return null;
    }
  }

  getPlatformParser() {
    switch (this.platform) {
      case 'discord':
        return this.parseDiscord.bind(this);
      case 'telegram':
        return this.parseTelegram.bind(this);
      case 'slack':
        return this.parseSlack.bind(this);
      case 'whatsapp':
        return this.parseWhatsApp.bind(this);
      default:
        return null;
    }
  }

  parseDiscord(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};
      
      // Extract author
      const authorElement = element.querySelector(selectors.author || '[class*="username-"]');
      const author = authorElement?.textContent?.trim() || 'Unknown';
      
      // Extract content
      const contentElement = element.querySelector(selectors.content || '[class*="messageContent-"]');
      const content = this.extractMessageContent(contentElement);
      
      // Extract timestamp
      const timeElement = element.querySelector(selectors.timestamp || 'time[datetime]');
      const timestamp = timeElement?.getAttribute('datetime') || 
                       timeElement?.textContent || 
                       new Date().toISOString();
      
      // Extract channel
      const channelElement = document.querySelector(selectors.channel || '[class*="title-"] h1');
      const channel = channelElement?.textContent?.trim() || 'Unknown Channel';
      
      // Extract message ID
      const messageId = element.id || element.getAttribute('data-message-id') || null;
      
      // Check for attachments
      const attachments = this.extractAttachments(element);
      
      // Check for reactions
      const reactions = this.extractReactions(element);
      
      // Check if it's a reply
      const isReply = element.querySelector('[class*="repliedMessage-"]') !== null;
      
      return {
        messageId,
        author,
        content,
        timestamp: formatTimestamp(timestamp),
        channel,
        attachments,
        reactions,
        isReply,
        raw: element.outerHTML
      };
    } catch (error) {
      logger.error('Error parsing Discord message:', error);
      return this.genericParse(element);
    }
  }

  parseTelegram(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};

      // Prefer modern Web Telegram structure
      const translatable = element.querySelector('.translatable-message');
      const strongName = translatable?.querySelector('strong');

      // Extract author with multiple fallbacks
      let author = strongName?.textContent?.trim() ||
                   element.querySelector(selectors.author || '.message-title')?.textContent?.trim() ||
                   'Unknown';

      // Early skip for system-style entries: <strong>Unknown</strong> + hashtag
      if (author === 'Unknown' && translatable?.querySelector('a.anchor-hashtag')) {
        logger.debug('Skipping Telegram system message (Unknown + hashtag)');
        return null;
      }

      // Extract content from translatable-message (preferred) or fallback to message-text
      let content = '';
      if (translatable) {
        // Clone and remove time/emoji nodes from content extraction
        const clone = translatable.cloneNode(true);
        // Remove <em> time
        clone.querySelectorAll('em').forEach((n) => n.remove());
        content = this.extractMessageContent(clone);
      }
      if (!content) {
        const contentElement = element.querySelector(selectors.content || '.message-text');
        content = this.extractMessageContent(contentElement);
      }

      // Normalize content to handle leading emojis before checks
      const normalized = (content || '').replace(/^[^A-Za-z]+/, '');

      // Skip Telegram system messages like "Unknown in #general"
      if (author === 'Unknown' && /^(Unknown\s+in\s+#)/i.test(normalized)) {
        logger.debug('Skipping Telegram system message with unknown author');
        return null;
      }

      // Timestamp: prefer outer time containers
      let timestamp = new Date().toISOString();
      const timeInline = translatable?.querySelector('em')?.textContent?.trim();
      const timeFromTitle = element.querySelector('.time-inner')?.getAttribute('title') ||
                            element.querySelector(selectors.timestamp || '.message-time')?.textContent?.trim();
      timestamp = formatTimestamp(timeFromTitle || timeInline || timestamp);

      // Channel: use header if available
      const channelElement = document.querySelector(selectors.channel || '.chat-info-name');
      const channel = channelElement?.textContent?.trim() || 'Unknown Chat';

      // Media detection
      const hasMedia = element.querySelector('.message-media, [class*="media"]') !== null;

      return {
        author,
        content,
        timestamp,
        channel,
        hasMedia,
        raw: element.outerHTML
      };
    } catch (error) {
      logger.error('Error parsing Telegram message:', error);
      return this.genericParse(element);
    }
  }

  parseSlack(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};
      
      // Extract author
      const authorElement = element.querySelector(selectors.author || '[data-qa="message_sender"]');
      const author = authorElement?.textContent?.trim() || 'Unknown';
      
      // Extract content
      const contentElement = element.querySelector(selectors.content || '[data-qa="message_content"]');
      const content = this.extractMessageContent(contentElement);
      
      // Extract timestamp
      const timeElement = element.querySelector(selectors.timestamp || '[data-qa="message_time"]');
      const timestamp = timeElement?.getAttribute('data-ts') || 
                       timeElement?.textContent || 
                       new Date().toISOString();
      
      // Extract channel
      const channelElement = document.querySelector(selectors.channel || '[data-qa="channel_name"]');
      const channel = channelElement?.textContent?.trim() || 'Unknown Channel';
      
      // Check for thread
      const isThread = element.querySelector('[data-qa="thread_message"]') !== null;
      
      // Extract reactions
      const reactions = this.extractSlackReactions(element);
      
      return {
        author,
        content,
        timestamp: formatTimestamp(timestamp),
        channel,
        isThread,
        reactions,
        raw: element.outerHTML
      };
    } catch (error) {
      logger.error('Error parsing Slack message:', error);
      return this.genericParse(element);
    }
  }

  parseWhatsApp(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};
      
      // WhatsApp stores author and time in data-pre-plain-text attribute
      const copyableElement = element.querySelector('[data-pre-plain-text]');
      const prePlainText = copyableElement?.getAttribute('data-pre-plain-text') || '';
      
      // Parse pre-plain-text format: "[time, date] author: "
      const match = prePlainText.match(/\[(.+?)\]\s*(.+?):\s*/);
      const timestamp = match ? match[1] : new Date().toISOString();
      const author = match ? match[2] : 'Unknown';
      
      // Extract content
      const contentElement = element.querySelector(selectors.content || '[class*="copyable-text"] span');
      const content = this.extractMessageContent(contentElement);
      
      // Extract channel/chat name
      const channelElement = document.querySelector(selectors.channel || '[class*="chat-title"]');
      const channel = channelElement?.textContent?.trim() || 'Unknown Chat';
      
      // Check for media
      const hasImage = element.querySelector('img[src*="blob:"]') !== null;
      const hasVideo = element.querySelector('video') !== null;
      const hasAudio = element.querySelector('audio') !== null;
      
      return {
        author,
        content,
        timestamp: formatTimestamp(timestamp),
        channel,
        hasMedia: hasImage || hasVideo || hasAudio,
        mediaType: hasImage ? 'image' : hasVideo ? 'video' : hasAudio ? 'audio' : null,
        raw: element.outerHTML
      };
    } catch (error) {
      logger.error('Error parsing WhatsApp message:', error);
      return this.genericParse(element);
    }
  }

  genericParse(element) {
    try {
      // Try common patterns
      const content = this.extractMessageContent(element);
      
      // Try to find author
      const authorPatterns = [
        '[class*="author"]',
        '[class*="username"]',
        '[class*="sender"]',
        '[class*="from"]',
        '[data-author]'
      ];
      
      let author = 'Unknown';
      for (const pattern of authorPatterns) {
        const authorElement = element.querySelector(pattern);
        if (authorElement?.textContent) {
          author = authorElement.textContent.trim();
          break;
        }
      }
      
      // Try to find timestamp
      const timePatterns = [
        'time[datetime]',
        '[class*="time"]',
        '[class*="timestamp"]',
        '[data-timestamp]'
      ];
      
      let timestamp = new Date().toISOString();
      for (const pattern of timePatterns) {
        const timeElement = element.querySelector(pattern);
        if (timeElement) {
          timestamp = timeElement.getAttribute('datetime') || 
                     timeElement.getAttribute('data-timestamp') ||
                     timeElement.textContent || 
                     timestamp;
          break;
        }
      }
      
      return {
        author,
        content,
        timestamp: formatTimestamp(timestamp),
        channel: 'Unknown',
        raw: element.outerHTML
      };
    } catch (error) {
      logger.error('Error in generic parse:', error);
      return null;
    }
  }

  extractMessageContent(element) {
    if (!element) {
      return '';
    }
    
    // Clone element to avoid modifying the original
    const clone = element.cloneNode(true);
    
    // Remove any quote/reply elements
    const quotes = clone.querySelectorAll('[class*="quote"], [class*="reply"]');
    quotes.forEach((quote) => quote.remove());
    
    // Get text content
    let content = extractText(clone.innerHTML);
    
    // Clean up excessive whitespace
    content = content.replace(/\s+/g, ' ').trim();
    
    return content;
  }

  extractAttachments(element) {
    const attachments = [];
    
    // Look for images
    const images = element.querySelectorAll('img[src]:not([class*="emoji"]):not([class*="avatar"])');
    images.forEach((img) => {
      attachments.push({
        type: 'image',
        url: img.src,
        alt: img.alt || null
      });
    });
    
    // Look for videos
    const videos = element.querySelectorAll('video[src]');
    videos.forEach((video) => {
      attachments.push({
        type: 'video',
        url: video.src
      });
    });
    
    // Look for file attachments
    const files = element.querySelectorAll('[class*="attachment"], [data-type="file"]');
    files.forEach((file) => {
      const fileName = file.querySelector('[class*="filename"]')?.textContent || 
                      file.textContent || 
                      'Unknown File';
      attachments.push({
        type: 'file',
        name: fileName
      });
    });
    
    return attachments.length > 0 ? attachments : null;
  }

  extractReactions(element) {
    const reactions = [];
    
    const reactionElements = element.querySelectorAll('[class*="reaction"], [class*="emoji-reaction"]');
    reactionElements.forEach((reaction) => {
      const emoji = reaction.querySelector('[class*="emoji"]')?.textContent || 
                   reaction.textContent?.trim() || 
                   null;
      const count = reaction.querySelector('[class*="count"]')?.textContent || '1';
      
      if (emoji) {
        reactions.push({
          emoji,
          count: parseInt(count, 10) || 1
        });
      }
    });
    
    return reactions.length > 0 ? reactions : null;
  }

  extractSlackReactions(element) {
    const reactions = [];
    
    const reactionElements = element.querySelectorAll('[data-qa="reaction"]');
    reactionElements.forEach((reaction) => {
      const emoji = reaction.querySelector('[data-qa="reaction_emoji"]')?.textContent || null;
      const count = reaction.querySelector('[data-qa="reaction_count"]')?.textContent || '1';
      
      if (emoji) {
        reactions.push({
          emoji,
          count: parseInt(count, 10) || 1
        });
      }
    });
    
    return reactions.length > 0 ? reactions : null;
  }
}

export default MessageParser;