// Logging utility with levels and formatting

const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

class Logger {
  constructor(name = 'SignalScope', level = LOG_LEVELS.INFO) {
    this.name = name;
    this.level = level;
    this.isDevelopment = true; // Default to development mode
  }

  _format(level, message, ...args) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${this.name}] [${level}]`;
    return [prefix, message, ...args];
  }

  _shouldLog(level) {
    return level >= this.level && (this.isDevelopment || level >= LOG_LEVELS.WARN);
  }

  debug(message, ...args) {
    if (this._shouldLog(LOG_LEVELS.DEBUG)) {
      console.log(...this._format('DEBUG', message, ...args));
    }
  }

  info(message, ...args) {
    if (this._shouldLog(LOG_LEVELS.INFO)) {
      console.log(...this._format('INFO', message, ...args));
    }
  }

  warn(message, ...args) {
    if (this._shouldLog(LOG_LEVELS.WARN)) {
      console.warn(...this._format('WARN', message, ...args));
    }
  }

  error(message, ...args) {
    if (this._shouldLog(LOG_LEVELS.ERROR)) {
      console.error(...this._format('ERROR', message, ...args));
    }
  }

  group(label) {
    if (this._shouldLog(LOG_LEVELS.DEBUG)) {
      console.group(`[${this.name}] ${label}`);
    }
  }

  groupEnd() {
    if (this._shouldLog(LOG_LEVELS.DEBUG)) {
      console.groupEnd();
    }
  }

  time(label) {
    if (this._shouldLog(LOG_LEVELS.DEBUG)) {
      console.time(`[${this.name}] ${label}`);
    }
  }

  timeEnd(label) {
    if (this._shouldLog(LOG_LEVELS.DEBUG)) {
      console.timeEnd(`[${this.name}] ${label}`);
    }
  }

  setLevel(level) {
    if (typeof level === 'string') {
      this.level = LOG_LEVELS[level.toUpperCase()] || LOG_LEVELS.INFO;
    } else {
      this.level = level;
    }
  }

  createChild(name) {
    return new Logger(`${this.name}:${name}`, this.level);
  }
}

// Export singleton instance and class
export const logger = new Logger();
export { Logger, LOG_LEVELS };

// Helper function to create module-specific loggers
export function createLogger(moduleName, level) {
  return new Logger(moduleName, level);
}