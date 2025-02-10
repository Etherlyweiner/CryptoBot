// Secure Configuration Manager
class ConfigManager {
    constructor() {
        this.config = null;
        this.lastFetch = null;
        this.fetchInterval = 5 * 60 * 1000; // 5 minutes
    }

    async initialize() {
        try {
            await this.fetchConfig();
            this.startConfigRefresh();
            return true;
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize config', error);
            return false;
        }
    }

    async fetchConfig() {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.config = await response.json();
            this.lastFetch = Date.now();
            return this.config;
        } catch (error) {
            Logger.log('ERROR', 'Failed to fetch config', error);
            throw error;
        }
    }

    startConfigRefresh() {
        setInterval(async () => {
            try {
                await this.fetchConfig();
            } catch (error) {
                Logger.log('WARN', 'Failed to refresh config', error);
            }
        }, this.fetchInterval);
    }

    getRpcEndpoints() {
        if (!this.config) return [];
        return this.config.rpc_endpoints;
    }

    getServiceUrl(service) {
        if (!this.config) return null;
        return this.config.services[service];
    }

    isConfigValid() {
        return this.config !== null && 
               Date.now() - this.lastFetch < this.fetchInterval * 2;
    }
}

// Constants that don't need to be secured
const CONSTANTS = {
    SOL_MINT: 'So11111111111111111111111111111111111111112',
    TRANSACTION_TIMEOUT: 60000,
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    JUPITER_API: 'https://quote-api.jup.ag/v6',
    BIRDEYE_API: 'https://public-api.birdeye.so'
};

// Create singleton instance
window.configManager = new ConfigManager();
window.CONSTANTS = CONSTANTS;
