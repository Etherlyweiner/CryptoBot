class RPCManager {
    constructor() {
        this.connections = new Map();
        this.healthStatus = new Map();
        this.currentProvider = null;
        this.isMonitoring = false;
    }

    async initialize() {
        try {
            // Initialize all RPC connections
            for (const [network, providers] of Object.entries(window.BOT_CONFIG.RPC)) {
                for (const [name, config] of Object.entries(providers)) {
                    const connection = new window.solanaWeb3.Connection(
                        config.url,
                        {
                            commitment: 'confirmed',
                            wsEndpoint: config.wsUrl,
                            confirmTransactionInitialTimeout: 60000
                        }
                    );
                    this.connections.set(name, {
                        connection,
                        config,
                        health: {
                            lastCheck: Date.now(),
                            failures: 0,
                            latency: 0
                        }
                    });
                }
            }

            // Start health monitoring
            await this.startHealthMonitoring();
            
            // Get initial best connection
            await this.updateCurrentProvider();
            
            Logger.log('INFO', 'RPC Manager initialized successfully');
            return true;
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize RPC Manager', error);
            return false;
        }
    }

    async checkHealth(providerName) {
        const provider = this.connections.get(providerName);
        if (!provider) return false;

        try {
            const startTime = performance.now();
            await provider.connection.getSlot();
            const endTime = performance.now();

            provider.health.latency = endTime - startTime;
            provider.health.lastCheck = Date.now();
            provider.health.failures = 0;

            this.healthStatus.set(providerName, {
                healthy: true,
                latency: provider.health.latency,
                timestamp: provider.health.lastCheck
            });

            return true;
        } catch (error) {
            provider.health.failures++;
            this.healthStatus.set(providerName, {
                healthy: false,
                error: error.message,
                failures: provider.health.failures,
                timestamp: Date.now()
            });

            Logger.log('WARN', `RPC health check failed for ${providerName}`, {
                failures: provider.health.failures,
                error: error.message
            });

            return false;
        }
    }

    async startHealthMonitoring() {
        if (this.isMonitoring) return;

        this.isMonitoring = true;
        const interval = window.BOT_CONFIG.HEALTH.interval;

        const monitor = async () => {
            if (!this.isMonitoring) return;

            for (const [name] of this.connections) {
                await this.checkHealth(name);
            }

            await this.updateCurrentProvider();
            setTimeout(monitor, interval);
        };

        monitor();
    }

    async updateCurrentProvider() {
        let bestProvider = null;
        let bestLatency = Infinity;

        for (const [name, provider] of this.connections) {
            const health = this.healthStatus.get(name);
            if (health?.healthy && health.latency < bestLatency) {
                bestProvider = name;
                bestLatency = health.latency;
            }
        }

        if (bestProvider && bestProvider !== this.currentProvider) {
            this.currentProvider = bestProvider;
            Logger.log('INFO', `Switched to RPC provider: ${bestProvider}`, {
                latency: bestLatency
            });
        }

        return this.getCurrentConnection();
    }

    getCurrentConnection() {
        if (!this.currentProvider) {
            throw new Error('No healthy RPC connection available');
        }
        return this.connections.get(this.currentProvider).connection;
    }

    getHealthStatus() {
        return Object.fromEntries(this.healthStatus);
    }

    async shutdown() {
        this.isMonitoring = false;
        this.connections.clear();
        this.healthStatus.clear();
        this.currentProvider = null;
        Logger.log('INFO', 'RPC Manager shutdown complete');
    }
}

// Create singleton instance
window.rpcManager = new RPCManager();
