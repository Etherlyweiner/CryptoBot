// Optimized logging system
class Logger {
    static maxLogs = 100;
    static logQueue = [];
    static logContainer = null;
    static colors = {
        INFO: '#4CAF50',
        ERROR: '#f44336',
        TRADE: '#2196F3',
        PRICE: '#FF9800'
    };

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

    static createLogElement(entry) {
        const logElement = document.createElement('div');
        logElement.className = `log-entry ${entry.type.toLowerCase()}`;
        
        const time = new Date(entry.timestamp).toLocaleTimeString();
        logElement.innerHTML = `
            <span class="timestamp">${time}</span>
            <span class="type">${entry.type}</span>
            <span class="message">${entry.message}</span>
            ${entry.data ? `<pre class="data">${JSON.stringify(entry.data, null, 2)}</pre>` : ''}
        `;
        
        return logElement;
    }

    static clear() {
        if (Logger.logContainer) {
            Logger.logContainer.innerHTML = '';
        }
        window.botLogs = [];
    }
}

// Initialize logger after DOM load
document.addEventListener('DOMContentLoaded', () => {
    Logger.initialize();
});
