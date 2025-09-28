import { createLogger } from '../shared/logger.js';

const logger = createLogger('PlatformFilters');

export function shouldSkipMessage(message) {
  try {
    if (!message) return false;

    const platform = (message.platform || '').toLowerCase();
    const author = (message.author || '').trim();
    const content = (message.content || '').trim();
    const normalized = content.replace(/^[^A-Za-z]+/, '');

    // Filter messages with "Unknown" authors on Circle.so
    if (platform === 'circle' && author === 'Unknown') {
      logger.debug(`Filtered Circle.so message with Unknown author: "${content.substring(0, 50)}..."`);
      return true;
    }

    // Filter specific patterns that indicate non-message UI elements
    if (platform === 'circle') {
      // Skip status messages, notifications, or UI elements
      if (/^(Unknown\s+in\s+#|Status:|Notification:|System:|Loading|Error)/i.test(normalized)) {
        logger.debug(`Filtered Circle.so system/UI element: "${content.substring(0, 50)}..."`);
        return true;
      }
      
      // Skip very short content that's likely UI text
      if (content.length < 10 && author === 'Unknown') {
        logger.debug(`Filtered Circle.so short unknown content: "${content}"`);
        return true;
      }
    }

    return false;
  } catch (error) {
    logger.error('Error in shouldSkipMessage:', error);
    return false;
  }
}

export default { shouldSkipMessage };


