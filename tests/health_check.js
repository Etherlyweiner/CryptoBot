class HealthCheck {
    constructor() {
        this.results = {
            components: [],
            errors: []
        };
    }

    async run() {
        console.log('Running Health Check...\n');

        try {
            // Check system components
            await this.checkComponents();

            // Check connections
            await this.checkConnections();

            // Check performance
            await this.checkPerformance();

            // Check resources
            await this.checkResources();

            // Generate report
            this.generateReport();

            return this.results.errors.length === 0;
        } catch (error) {
            console.error('Health check failed:', error);
            this.results.errors.push({
                component: 'HealthCheck',
                error: error.message
            });
            return false;
        }
    }

    async checkComponents() {
        console.log('Checking System Components...');

        const components = [
            { name: 'TradingBot', check: this.checkTradingBot.bind(this) },
            { name: 'RpcManager', check: this.checkRpcManager.bind(this) },
            { name: 'WalletSecurity', check: this.checkWalletSecurity.bind(this) },
            { name: 'StrategyExecutor', check: this.checkStrategyExecutor.bind(this) },
            { name: 'RiskManager', check: this.checkRiskManager.bind(this) },
            { name: 'PerformanceAnalytics', check: this.checkPerformanceAnalytics.bind(this) }
        ];

        for (const component of components) {
            try {
                const status = await component.check();
                this.results.components.push({
                    name: component.name,
                    status: status ? 'healthy' : 'unhealthy'
                });
            } catch (error) {
                this.results.components.push({
                    name: component.name,
                    status: 'error',
                    error: error.message
                });
            }
        }
    }

    async checkTradingBot() {
        const tradingBot = new window.TradingBot();
        await tradingBot.initialize();
        return tradingBot.isHealthy();
    }

    async checkRpcManager() {
        const rpcManager = new window.RpcManager();
        await rpcManager.initialize();
        return rpcManager.isConnected();
    }

    async checkWalletSecurity() {
        const walletSecurity = new window.WalletSecurity();
        return walletSecurity.isSecure();
    }

    async checkStrategyExecutor() {
        const strategyExecutor = new window.StrategyExecutor();
        return strategyExecutor.isOperational();
    }

    async checkRiskManager() {
        const riskManager = new window.RiskManager();
        return riskManager.isActive();
    }

    async checkPerformanceAnalytics() {
        const analytics = new window.PerformanceAnalytics();
        return analytics.isTracking();
    }

    async checkConnections() {
        console.log('Checking Connections...');

        const connections = [
            { name: 'Primary RPC', url: process.env.PRIMARY_RPC },
            { name: 'Backup RPC', url: process.env.BACKUP_RPC },
            { name: 'API Server', url: 'http://localhost:3000/api/health' },
            { name: 'WebSocket', url: 'ws://localhost:3000/ws' }
        ];

        for (const conn of connections) {
            try {
                const status = await this.checkConnection(conn.url);
                this.results.components.push({
                    name: conn.name,
                    status: status ? 'connected' : 'disconnected'
                });
            } catch (error) {
                this.results.components.push({
                    name: conn.name,
                    status: 'error',
                    error: error.message
                });
            }
        }
    }

    async checkConnection(url) {
        if (url.startsWith('ws')) {
            return new Promise((resolve) => {
                const ws = new WebSocket(url);
                ws.onopen = () => {
                    ws.close();
                    resolve(true);
                };
                ws.onerror = () => resolve(false);
            });
        } else {
            const response = await fetch(url);
            return response.ok;
        }
    }

    async checkPerformance() {
        console.log('Checking Performance...');

        const metrics = [
            { name: 'API Latency', check: this.checkAPILatency.bind(this) },
            { name: 'Trade Execution', check: this.checkTradeExecution.bind(this) },
            { name: 'Memory Usage', check: this.checkMemoryUsage.bind(this) },
            { name: 'CPU Usage', check: this.checkCPUUsage.bind(this) }
        ];

        for (const metric of metrics) {
            try {
                const result = await metric.check();
                this.results.components.push({
                    name: metric.name,
                    ...result
                });
            } catch (error) {
                this.results.components.push({
                    name: metric.name,
                    status: 'error',
                    error: error.message
                });
            }
        }
    }

    async checkAPILatency() {
        const start = performance.now();
        await fetch('http://localhost:3000/api/health');
        const latency = performance.now() - start;

        return {
            status: latency < 100 ? 'good' : 'warning',
            value: `${latency.toFixed(2)}ms`
        };
    }

    async checkTradeExecution() {
        const tradingBot = new window.TradingBot();
        const start = performance.now();
        await tradingBot.executeMockTrade();
        const executionTime = performance.now() - start;

        return {
            status: executionTime < 1000 ? 'good' : 'warning',
            value: `${executionTime.toFixed(2)}ms`
        };
    }

    async checkMemoryUsage() {
        const used = process.memoryUsage().heapUsed / 1024 / 1024;
        return {
            status: used < 512 ? 'good' : 'warning',
            value: `${used.toFixed(2)}MB`
        };
    }

    async checkCPUUsage() {
        const startUsage = process.cpuUsage();
        await new Promise(resolve => setTimeout(resolve, 100));
        const endUsage = process.cpuUsage(startUsage);
        const totalUsage = (endUsage.user + endUsage.system) / 1000000;

        return {
            status: totalUsage < 50 ? 'good' : 'warning',
            value: `${totalUsage.toFixed(2)}%`
        };
    }

    async checkResources() {
        console.log('Checking Resources...');

        const resources = [
            { name: 'Disk Space', check: this.checkDiskSpace.bind(this) },
            { name: 'Database Space', check: this.checkDatabaseSpace.bind(this) },
            { name: 'Network Bandwidth', check: this.checkNetworkBandwidth.bind(this) },
            { name: 'System Load', check: this.checkSystemLoad.bind(this) }
        ];

        for (const resource of resources) {
            try {
                const result = await resource.check();
                this.results.components.push({
                    name: resource.name,
                    ...result
                });
            } catch (error) {
                this.results.components.push({
                    name: resource.name,
                    status: 'error',
                    error: error.message
                });
            }
        }
    }

    async checkDiskSpace() {
        const { execSync } = require('child_process');
        const df = execSync('df -k /').toString();
        const used = parseInt(df.split('\n')[1].split(/\s+/)[4].replace('%', ''));

        return {
            status: used < 80 ? 'good' : 'warning',
            value: `${used}% used`
        };
    }

    async checkDatabaseSpace() {
        // Placeholder for database space check
        return {
            status: 'good',
            value: 'Available'
        };
    }

    async checkNetworkBandwidth() {
        const start = performance.now();
        await fetch('http://localhost:3000/api/health');
        const bandwidth = performance.now() - start;

        return {
            status: bandwidth < 100 ? 'good' : 'warning',
            value: `${bandwidth.toFixed(2)}ms`
        };
    }

    async checkSystemLoad() {
        const os = require('os');
        const load = os.loadavg()[0];
        const cpus = os.cpus().length;

        return {
            status: load < cpus ? 'good' : 'warning',
            value: `${load.toFixed(2)}`
        };
    }

    generateReport() {
        console.log('=== Health Check Report ===\n');

        // Component Status
        console.log('Component Status:');
        this.results.components.forEach(component => {
            const status = component.status === 'healthy' ? '✓' : '✗';
            console.log(`${status} ${component.name}: ${component.status}`);
            if (component.value) {
                console.log(`  Value: ${component.value}`);
            }
            if (component.error) {
                console.log(`  Error: ${component.error}`);
            }
        });

        // Error Summary
        if (this.results.errors.length > 0) {
            console.log('\nErrors:');
            this.results.errors.forEach(error => {
                console.log(`- ${error.component}: ${error.error}`);
            });
        }

        // Overall Status
        const healthy = this.results.errors.length === 0 &&
            this.results.components.every(c => 
                c.status === 'healthy' || c.status === 'good' || c.status === 'connected');

        console.log(`\nOverall Status: ${healthy ? 'HEALTHY' : 'UNHEALTHY'}`);

        // Save report
        this.saveReport();
    }

    async saveReport() {
        try {
            const fs = require('fs');
            const path = require('path');
            
            const reportsDir = path.join(__dirname, 'health-reports');
            if (!fs.existsSync(reportsDir)) {
                fs.mkdirSync(reportsDir);
            }
            
            const filename = path.join(reportsDir, 
                `health-check-${new Date().toISOString().replace(/:/g, '-')}.json`);
            
            fs.writeFileSync(filename, JSON.stringify(this.results, null, 2));
            console.log(`\nHealth check report saved to: ${filename}`);
        } catch (error) {
            console.error('Failed to save health check report:', error);
        }
    }
}

// Export health check
if (typeof module !== 'undefined') {
    module.exports = HealthCheck;
} else {
    window.HealthCheck = HealthCheck;
}
