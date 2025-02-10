/**
 * Logging system with both static and instance methods.
 */
class Logger {
    static maxLogs = 100;
    static logQueue = [];
    static logContainer = null;
    static colors = {
        INFO: '#4CAF50',
        ERROR: '#f44336',
        WARN: '#FF9800',
        DEBUG: '#2196F3'
    };

    constructor(name) {
        this.name = name;
    }

    /**
     * Initialize the logger.
     */
    static initialize() {
        Logger.logContainer = document.getElementById('bot-logs');
        if (Logger.logContainer) {
            // Create a document fragment for better performance
            const fragment = document.createDocumentFragment();
            Logger.logQueue.forEach(entry => {
                fragment.appendChild(Logger.createLogElement(entry));
            });
            Logger.logContainer.appendChild(fragment);
            Logger.logQueue = [];
        }
    }

    /**
     * Create a log element.
     */
    static createLogElement(entry) {
        const div = document.createElement('div');
        div.className = 'log-entry';
        div.style.color = Logger.colors[entry.type] || '#fff';
        div.textContent = `[${entry.timestamp}] [${entry.type}] ${entry.message}`;
        if (entry.data) {
            div.title = JSON.stringify(entry.data, null, 2);
        }
        return div;
    }

    /**
     * Log a message.
     */
    static log(type, message, data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = { timestamp, type, message, data };

        // Console logging with color
        console.log(
            `%c[${type}] ${timestamp}\n${message}`,
            `color: ${Logger.colors[type] || '#fff'}`,
            data ? data : ''
        );

        // Store in log history
        if (!window.botLogs) window.botLogs = [];
        window.botLogs.push(logEntry);

        // Update UI
        if (Logger.logContainer) {
            const logElement = Logger.createLogElement(logEntry);
            Logger.logContainer.insertBefore(logElement, Logger.logContainer.firstChild);

            // Keep only last N logs in UI
            while (Logger.logContainer.children.length > Logger.maxLogs) {
                Logger.logContainer.removeChild(Logger.logContainer.lastChild);
            }
        } else {
            Logger.logQueue.push(logEntry);
        }
    }

    /**
     * Log an info message.
     */
    info(message, data = null) {
        Logger.log('INFO', `[${this.name}] ${message}`, data);
    }

    /**
     * Log an error message.
     */
    error(message, error = null) {
        const errorData = error ? {
            message: error.message,
            stack: error.stack
        } : null;
        Logger.log('ERROR', `[${this.name}] ${message}`, errorData);
    }

    /**
     * Log a warning message.
     */
    warn(message, data = null) {
        Logger.log('WARN', `[${this.name}] ${message}`, data);
    }

    /**
     * Log a debug message.
     */
    debug(message, data = null) {
        Logger.log('DEBUG', `[${this.name}] ${message}`, data);
    }
}

// Initialize logger after DOM load
document.addEventListener('DOMContentLoaded', () => {
    Logger.initialize();
});

// Export for Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Logger;
} else {
    window.Logger = Logger;
}
