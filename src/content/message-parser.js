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
      case 'circle':
        return this.parseCircle.bind(this);
      case 'webchat':
        return this.parseWebChat.bind(this);
      default:
        return null;
    }
  }

  parseDiscord(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};
      
      // Try multiple selectors for author (Discord changes these frequently)
      const authorSelectors = (selectors.author || '[class*="username-"]').split(',').map(s => s.trim());
      let author = 'Unknown';
      for (const selector of authorSelectors) {
        const authorElement = element.querySelector(selector);
        if (authorElement?.textContent?.trim()) {
          author = authorElement.textContent.trim();
          break;
        }
      }
      
      // Try multiple selectors for content
      const contentSelectors = (selectors.content || '[class*="messageContent-"]').split(',').map(s => s.trim());
      let content = '';
      for (const selector of contentSelectors) {
        const contentElement = element.querySelector(selector);
        if (contentElement) {
          content = this.extractMessageContent(contentElement);
          if (content) break;
        }
      }
      
      // If no content found, try to get all text content from the message
      if (!content) {
        // Look for any text that's not the author or timestamp
        const textNodes = element.querySelectorAll('[class*="markup-"], [class*="text-"], [id^="message-content-"]');
        for (const node of textNodes) {
          const text = node.textContent?.trim();
          if (text && text !== author) {
            content = text;
            break;
          }
        }
      }
      
      // Extract timestamp - try multiple approaches
      const timeSelectors = (selectors.timestamp || 'time[datetime]').split(',').map(s => s.trim());
      let timestamp = new Date().toISOString();
      for (const selector of timeSelectors) {
        const timeElement = element.querySelector(selector);
        if (timeElement) {
          timestamp = timeElement.getAttribute('datetime') || 
                     timeElement.getAttribute('aria-label') ||
                     timeElement.textContent || 
                     timestamp;
          break;
        }
      }
      
      // Extract channel
      const channelSelectors = (selectors.channel || '[class*="title-"] h1').split(',').map(s => s.trim());
      let channel = 'Unknown Channel';
      for (const selector of channelSelectors) {
        const channelElement = document.querySelector(selector);
        if (channelElement?.textContent?.trim()) {
          channel = channelElement.textContent.trim();
          break;
        }
      }
      
      // Extract message ID - Discord messages often have IDs in various attributes
      const messageId = element.id || 
                       element.getAttribute('data-message-id') || 
                       element.getAttribute('id') ||
                       element.querySelector('[id^="message-"]')?.id ||
                       null;
      
      // Check for attachments (images, files, etc.)
      const attachments = this.extractAttachments(element);
      if (attachments.length > 0 && !content) {
        content = '[Attachment]';
      }
      
      // Check for reactions
      const reactions = this.extractReactions(element);
      
      // Check if it's a reply
      const isReply = element.querySelector('[class*="repliedMessage-"], [class*="replyBar-"]') !== null;
      
      const result = {
        messageId,
        author,
        content,
        timestamp: formatTimestamp(timestamp),
        channel,
        attachments,
        reactions,
        isReply
      };
      
      logger.debug('Parsed Discord message:', result);
      return result;
    } catch (error) {
      logger.error('Error parsing Discord message:', error);
      return this.genericParse(element);
    }
  }

  parseTelegram(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};
      
      // Extract author
      const authorElement = element.querySelector(selectors.author || '.message-title');
      const author = authorElement?.textContent?.trim() || 'Unknown';
      
      // Extract content
      const contentElement = element.querySelector(selectors.content || '.message-text');
      const content = this.extractMessageContent(contentElement);
      
      // Extract timestamp
      const timeElement = element.querySelector(selectors.timestamp || '.message-time');
      const timestamp = timeElement?.textContent?.trim() || new Date().toISOString();
      
      // Extract channel
      const channelElement = document.querySelector(selectors.channel || '.chat-info-name');
      const channel = channelElement?.textContent?.trim() || 'Unknown Chat';
      
      // Check for media
      const hasMedia = element.querySelector('.message-media') !== null;
      
      return {
        author,
        content,
        timestamp: formatTimestamp(timestamp),
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
      
      // Extract content - try multiple selectors for current WhatsApp
      const contentElement = element.querySelector('[class*="selectable-text"]') || 
                            element.querySelector('[class*="copyable-text"] span') ||
                            element.querySelector('span[dir="ltr"]');
      const content = this.extractMessageContent(contentElement) || 
                     element.textContent?.replace(/\d{1,2}:\d{2}\s?(am|pm)/gi, '').replace(/msg-dblcheck/g, '').trim();
      
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

  parseCircle(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};

      // Extract message ID from element with multiple fallbacks
      const messageId = element.id ||
                       element.getAttribute('data-message-id') ||
                       element.getAttribute('data-id') ||
                       element.getAttribute('data-post-id') ||
                       `circle-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      // Enhanced author extraction with multiple fallbacks
      let author = 'Unknown';
      const authorSelectors = selectors.author.split(', ');
      for (const selector of authorSelectors) {
        const authorElement = element.querySelector(selector.trim());
        if (authorElement) {
          const authorText = authorElement.textContent?.trim() || '';
          // Handle different Circle.so author formats
          if (selector.includes('number-of-replies')) {
            // For replies button, extract username from text like "John Doe replied"
            author = authorText.replace(/\s+(replied|commented|posted).*$/i, '').trim();
          } else {
            // For direct author elements
            author = authorText.split(' ')[0] || authorText;
          }
          if (author && author !== 'Unknown') break;
        }
      }

      // Enhanced content extraction with rich text support
      let content = '';
      const contentSelectors = selectors.content.split(', ');
      for (const selector of contentSelectors) {
        const contentElement = element.querySelector(selector.trim());
        if (contentElement) {
          // Handle TipTap/ProseMirror rich text editor
          const proseMirrorContent = contentElement.querySelector('.tiptap.ProseMirror, .ProseMirror, [contenteditable="true"]');
          if (proseMirrorContent) {
            content = this.extractCircleRichContent(proseMirrorContent);
          } else {
            content = this.extractMessageContent(contentElement);
          }
          if (content && content.trim()) break;
        }
      }

      // Enhanced timestamp extraction
      let timestamp = new Date().toISOString();
      const timestampSelectors = selectors.timestamp.split(', ');
      for (const selector of timestampSelectors) {
        const timestampElement = element.querySelector(selector.trim());
        if (timestampElement) {
          const timeText = timestampElement.textContent?.trim() ||
                          timestampElement.getAttribute('datetime') ||
                          timestampElement.getAttribute('title');
          if (timeText) {
            timestamp = this.parseCircleTimestamp(timeText);
            break;
          }
        }
      }

      // Extract channel/space name with fallbacks
      let channel = 'Unknown Space';
      const channelSelectors = selectors.channel.split(', ');
      for (const selector of channelSelectors) {
        const channelElement = document.querySelector(selector.trim());
        if (channelElement?.textContent?.trim()) {
          channel = channelElement.textContent.trim();
          break;
        }
      }

      // Enhanced attachment extraction
      const attachments = this.extractCircleAttachments(element);

      // Enhanced reaction extraction
      const reactions = this.extractCircleReactions(element);

      // Check for replies/threads with multiple indicators
      const hasReplies = element.querySelector('[data-testid="replies-block"], [class*="replies"], [class*="thread"]') !== null;
      const replyCount = this.extractReplyCount(element);

      // Extract additional Circle.so specific metadata
      const metadata = this.extractCircleMetadata(element);

      return {
        messageId,
        author,
        content,
        timestamp,
        channel,
        attachments,
        reactions,
        hasReplies,
        replyCount,
        metadata,
        platform: 'circle',
        raw: element.outerHTML.length > 5000 ? element.outerHTML.substring(0, 5000) + '...' : element.outerHTML
      };
    } catch (error) {
      logger.error('Error parsing Circle message:', error);
      return this.genericParse(element);
    }
  }

  parseWebChat(element) {
    try {
      const selectors = this.platformConfig?.selectors || {};
      
      // Extract message ID
      const messageId = element.id || 
                       element.getAttribute('data-message-id') || 
                       element.getAttribute('data-id');
      
      // Extract author - try multiple common selectors
      const authorSelectors = (selectors.author || '[data-testid="number-of-replies"], .message-author, [class*="author"], [class*="username"]').split(',').map(s => s.trim());
      let author = 'Unknown';
      for (const selector of authorSelectors) {
        const authorElement = element.querySelector(selector);
        if (authorElement?.textContent?.trim()) {
          author = authorElement.textContent.trim().split(' ')[0] || 'Unknown';
          break;
        }
      }
      
      // Extract content - try multiple selectors
      const contentSelectors = (selectors.content || '[data-testid="message-text"], .message-content, [class*="message-text"], [class*="content"]').split(',').map(s => s.trim());
      let content = '';
      for (const selector of contentSelectors) {
        const contentElement = element.querySelector(selector);
        if (contentElement) {
          // Check for rich text editors like TipTap
          const richTextContent = contentElement.querySelector('.tiptap, .ProseMirror, [contenteditable]');
          if (richTextContent) {
            content = this.extractMessageContent(richTextContent);
          } else {
            content = this.extractMessageContent(contentElement);
          }
          if (content) break;
        }
      }
      
      // Extract timestamp
      const timestampSelectors = (selectors.timestamp || '.text-timestamp, .message-time, [class*="timestamp"], time').split(',').map(s => s.trim());
      let timestamp = new Date().toISOString();
      for (const selector of timestampSelectors) {
        const timestampElement = element.querySelector(selector);
        if (timestampElement) {
          const timeText = timestampElement.getAttribute('datetime') || 
                          timestampElement.textContent?.trim();
          if (timeText) {
            timestamp = formatTimestamp(timeText);
            break;
          }
        }
      }
      
      // Extract channel
      const channelSelectors = (selectors.channel || '[data-testid="space-title-name"], .channel-name, [class*="channel"]').split(',').map(s => s.trim());
      let channel = 'Unknown Channel';
      for (const selector of channelSelectors) {
        const channelElement = document.querySelector(selector);
        if (channelElement?.textContent?.trim()) {
          channel = channelElement.textContent.trim();
          break;
        }
      }
      
      // Extract attachments
      const attachments = this.extractAttachments(element);
      
      // Extract reactions
      const reactions = this.extractReactions(element);
      
      return {
        messageId,
        author,
        content,
        timestamp,
        channel,
        attachments,
        reactions,
        raw: element.outerHTML
      };
    } catch (error) {
      logger.error('Error parsing web chat message:', error);
      return this.genericParse(element);
    }
  }

  genericParse(element) {
    try {
      // First check for data attributes (most reliable)
      const author = element.querySelector('[data-author]')?.getAttribute('data-author') ||
                    element.querySelector('.message-author')?.getAttribute('data-author') ||
                    element.querySelector('.message-author')?.textContent?.trim() ||
                    element.querySelector('[class*="author"]')?.textContent?.trim() ||
                    element.querySelector('[class*="username"]')?.textContent?.trim() ||
                    'Unknown';
      
      const content = element.querySelector('[data-content]')?.getAttribute('data-content') ||
                     element.querySelector('.message-content')?.getAttribute('data-content') ||
                     element.querySelector('.message-content')?.textContent?.trim() ||
                     element.querySelector('[class*="content"]')?.textContent?.trim() ||
                     this.extractMessageContent(element);
      
      const channel = element.querySelector('[data-channel]')?.getAttribute('data-channel') ||
                     element.querySelector('.message-channel')?.textContent?.trim() ||
                     element.querySelector('[class*="channel"]')?.textContent?.trim() ||
                     'general';
      
      // Try to find timestamp - be more careful here
      let timestamp = null;
      const timeElement = element.querySelector('[data-time]') ||
                         element.querySelector('.message-time') ||
                         element.querySelector('time[datetime]') ||
                         element.querySelector('[class*="time"]');
      
      if (timeElement) {
        // Try different attributes and methods
        timestamp = timeElement.getAttribute('datetime') || 
                   timeElement.getAttribute('data-time') ||
                   timeElement.textContent?.trim();
      }
      
      // Skip if no content
      if (!content || content.trim().length === 0) {
        logger.debug('Skipping message with no content');
        return null;
      }
      
      // Use formatTimestamp which now handles errors
      const formattedTimestamp = formatTimestamp(timestamp);
      
      return {
        author,
        content,
        timestamp: formattedTimestamp,
        channel,
        raw: element.outerHTML
      };
    } catch (error) {
      logger.error('Error in generic parse:', error);
      // Return a basic message structure instead of null to avoid breaking the flow
      try {
        const fallbackContent = element.textContent?.trim();
        if (fallbackContent) {
          return {
            author: 'Unknown',
            content: fallbackContent.substring(0, 200),
            timestamp: new Date().toISOString(),
            channel: 'unknown',
            raw: ''
          };
        }
      } catch (e) {
        // If even fallback fails, return null
      }
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
    
    return attachments.length > 0 ? attachments : [];
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
    
    return reactions.length > 0 ? reactions : [];
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
    
    return reactions.length > 0 ? reactions : [];
  }

  extractCircleAttachments(element) {
    const attachments = [];
    
    // Look for Circle.so attachment images (from webui.txt structure)
    // These are in buttons with specific classes and contain images
    const attachmentButtons = element.querySelectorAll('button[class*="cursor-pointer"][class*="border-tertiary"]');
    attachmentButtons.forEach((button) => {
      const img = button.querySelector('img[alt="Attachment image"]');
      if (img && img.src) {
        // Try to get context from surrounding text
        const messageText = element.textContent || '';
        const context = this.generateImageContext(messageText, 'attachment');
        
        attachments.push({
          type: 'image',
          url: img.src,
          alt: img.alt || 'Shared Image',
          context: context,
          thumbnail: img.src,
          isAttachment: true
        });
      }
    });
    
    // Also look for any other images that might be shared (not profile pictures)
    const images = element.querySelectorAll('img[src]:not([class*="user-image"]):not([data-testid="user-image"])');
    images.forEach((img) => {
      // Skip profile images, icons, and already captured attachment images
      if (img.src && 
          !img.src.includes('favicon') && 
          !img.src.includes('icon') &&
          !img.src.includes('avatar') &&
          !img.closest('[data-testid="user-image-container"]') &&
          !attachments.some(att => att.url === img.src)) {
        
        // Try to get context from surrounding text
        const messageText = element.textContent || '';
        const context = this.generateImageContext(messageText, 'chart');
        
        attachments.push({
          type: 'image',
          url: img.src,
          alt: img.alt || 'Shared Image',
          context: context,
          thumbnail: img.src,
          isAttachment: false
        });
      }
    });
    
    // Look for link previews (like the Gumroad and YouTube links in webui.txt)
    const linkPreviews = element.querySelectorAll('a[href][target="_blank"]');
    linkPreviews.forEach((link) => {
      if (link.href && link.href !== window.location.href) {
        const linkTitle = link.querySelector('.text-dark')?.textContent?.trim() || 
                         link.textContent?.trim() || 
                         'Link Preview';
        const linkDescription = link.querySelector('.text-light')?.textContent?.trim() || null;
        const linkImage = link.querySelector('img')?.src || null;
        
        attachments.push({
          type: 'link',
          url: link.href,
          title: linkTitle,
          description: linkDescription,
          image: linkImage
        });
      }
    });
    
    // Look for file attachments
    const fileElements = element.querySelectorAll('[class*="attachment"], [data-type="file"]');
    fileElements.forEach((file) => {
      const fileName = file.textContent?.trim() || 'Unknown File';
      if (fileName && fileName !== 'Unknown File') {
        attachments.push({
          type: 'file',
          name: fileName
        });
      }
    });
    
    return attachments.length > 0 ? attachments : [];
  }

  extractCircleReactions(element) {
    const reactions = [];
    
    // Circle reactions are usually in buttons with emoji and count
    const reactionElements = element.querySelectorAll('[data-testid="reaction-content"], button[class*="reaction"]');
    reactionElements.forEach((reaction) => {
      const reactionText = reaction.textContent?.trim() || '';
      // Circle reactions often have format like "👍1" or "❤️3"
      const match = reactionText.match(/^(.+?)(\d+)$/);
      if (match) {
        const emoji = match[1].trim();
        const count = parseInt(match[2], 10) || 1;
        if (emoji) {
          reactions.push({
            emoji,
            count
          });
        }
      }
    });
    
    return reactions.length > 0 ? reactions : [];
  }

  generateImageContext(messageText, imageType) {
    /**
     * Generate context for images based on message content
     */
    if (!messageText) return `${imageType === 'chart' ? 'Trading Chart' : 'Shared Image'}`;

    // Extract ticker symbols for context
    const tickerMatches = messageText.match(/\$?[A-Z]{1,5}\b/g);
    const tickers = tickerMatches ? tickerMatches.slice(0, 3).join(', ') : '';

    // Look for time-related words
    const timeWords = messageText.match(/\b(daily|weekly|monthly|hourly|5min|15min|1h|4h|breakout|setup)\b/gi);
    const timeContext = timeWords ? timeWords[0] : '';

    // Build context
    let context = '';
    if (tickers) {
      context += tickers;
      if (timeContext) {
        context += ` ${timeContext}`;
      }
      context += ' Chart';
    } else if (timeContext) {
      context += `${timeContext} Chart`;
    } else {
      context = imageType === 'chart' ? 'Trading Chart' : 'Shared Image';
    }

    return context;
  }

  // Circle.so specific helper methods
  extractCircleRichContent(element) {
    /**
     * Extract content from Circle.so's TipTap/ProseMirror rich text editor
     */
    if (!element) return '';

    // Clone to avoid modifying original
    const clone = element.cloneNode(true);

    // Remove any editor UI elements
    const editorElements = clone.querySelectorAll('[class*="editor-"], [class*="toolbar-"], [class*="menu-"]');
    editorElements.forEach(el => el.remove());

    // Handle mentions
    const mentions = clone.querySelectorAll('[data-mention], [class*="mention"]');
    mentions.forEach(mention => {
      const name = mention.textContent || mention.getAttribute('data-mention-name') || '@user';
      mention.textContent = `@${name}`;
    });

    // Handle links
    const links = clone.querySelectorAll('a[href]');
    links.forEach(link => {
      const href = link.getAttribute('href');
      const text = link.textContent || href;
      link.textContent = `${text} (${href})`;
    });

    return this.extractMessageContent(clone);
  }

  parseCircleTimestamp(timeText) {
    /**
     * Parse Circle.so timestamp formats
     */
    if (!timeText) return new Date().toISOString();

    try {
      // Handle relative times like "2 minutes ago", "1 hour ago"
      const relativeMatch = timeText.match(/(\d+)\s+(second|minute|hour|day|week)s?\s+ago/i);
      if (relativeMatch) {
        const amount = parseInt(relativeMatch[1]);
        const unit = relativeMatch[2].toLowerCase();
        const now = new Date();

        switch (unit) {
          case 'second': now.setSeconds(now.getSeconds() - amount); break;
          case 'minute': now.setMinutes(now.getMinutes() - amount); break;
          case 'hour': now.setHours(now.getHours() - amount); break;
          case 'day': now.setDate(now.getDate() - amount); break;
          case 'week': now.setDate(now.getDate() - (amount * 7)); break;
        }

        return now.toISOString();
      }

      // Handle time formats like "2:30 PM", "14:30"
      const timeMatch = timeText.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
      if (timeMatch) {
        const today = new Date();
        let hours = parseInt(timeMatch[1]);
        const minutes = parseInt(timeMatch[2]);
        const period = timeMatch[3]?.toUpperCase();

        if (period === 'PM' && hours !== 12) hours += 12;
        if (period === 'AM' && hours === 12) hours = 0;

        today.setHours(hours, minutes, 0, 0);
        return today.toISOString();
      }

      // Try parsing as standard date
      const date = new Date(timeText);
      if (!isNaN(date.getTime())) {
        return date.toISOString();
      }

      return new Date().toISOString();
    } catch (error) {
      return new Date().toISOString();
    }
  }

  extractReplyCount(element) {
    /**
     * Extract reply count from Circle.so elements
     */
    const replyElements = element.querySelectorAll('[data-testid="replies-block"], [class*="replies"], [class*="reply-count"]');
    for (const replyEl of replyElements) {
      const text = replyEl.textContent || '';
      const match = text.match(/(\d+)\s*repl(y|ies)/i);
      if (match) {
        return parseInt(match[1]);
      }
    }
    return 0;
  }

  extractCircleMetadata(element) {
    /**
     * Extract Circle.so specific metadata
     */
    const metadata = {};

    // Check if it's a pinned message
    if (element.querySelector('[class*="pinned"], [data-testid*="pin"]')) {
      metadata.isPinned = true;
    }

    // Check for message type (post, comment, etc.)
    const messageType = element.getAttribute('data-message-type') ||
                       element.getAttribute('data-post-type') ||
                       (element.closest('[data-testid="post"]') ? 'post' : 'comment');
    if (messageType) {
      metadata.messageType = messageType;
    }

    // Extract space/community info
    const spaceElement = element.closest('[data-space-id], [data-community-id]');
    if (spaceElement) {
      metadata.spaceId = spaceElement.getAttribute('data-space-id') ||
                        spaceElement.getAttribute('data-community-id');
    }

    // Check for moderation flags
    if (element.querySelector('[class*="moderated"], [class*="flagged"]')) {
      metadata.isModerated = true;
    }

    // Extract edit information
    const editedElement = element.querySelector('[class*="edited"], [title*="edited"]');
    if (editedElement) {
      metadata.isEdited = true;
      metadata.editedAt = editedElement.getAttribute('title') || editedElement.textContent;
    }

    return metadata;
  }
}

export default MessageParser;