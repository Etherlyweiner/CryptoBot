class SystemIntegrationTest {
    constructor() {
        this.results = {
            passed: 0,
            failed: 0,
            errors: []
        };
    }

    async runAll() {
        console.log('Starting System Integration Tests...\n');

        try {
            // Test system initialization
            await this.testSystemInitialization();

            // Test RPC failover
            await this.testRPCFailover();

            // Test wallet integration
            await this.testWalletIntegration();

            // Test trading workflow
            await this.testTradingWorkflow();

            // Test risk management
            await this.testRiskManagement();

            // Test performance monitoring
            await this.testPerformanceMonitoring();

            // Test error handling
            await this.testErrorHandling();

            // Generate report
            this.generateReport();

        } catch (error) {
            console.error('System integration tests failed:', error);
            this.results.errors.push({
                component: 'SystemIntegrationTest',
                error: error.message
            });
        }
    }

    async testSystemInitialization() {
        console.log('Testing System Initialization...');

        try {
            // Initialize trading bot
            const tradingBot = new window.TradingBot();
            assert(await tradingBot.initialize(), 'Trading bot initialization failed');

            // Verify component initialization
            assert(tradingBot.rpcManager, 'RPC Manager not initialized');
            assert(tradingBot.walletSecurity, 'Wallet Security not initialized');
            assert(tradingBot.riskManager, 'Risk Manager not initialized');
            assert(tradingBot.strategyExecutor, 'Strategy Executor not initialized');
            assert(tradingBot.performanceAnalytics, 'Performance Analytics not initialized');

            // Verify configurations loaded
            assert(tradingBot.settings, 'Settings not loaded');
            assert(tradingBot.state.connection, 'RPC connection not established');

            this.results.passed += 7;
            console.log('✓ System initialization tests passed\n');
        } catch (error) {
            this.results.failed++;
            this.results.errors.push({
                component: 'SystemInitialization',
                error: error.message
            });
            console.error('✗ System initialization tests failed:', error, '\n');
        }
    }

    async testRPCFailover() {
        console.log('Testing RPC Failover...');

        try {
            const rpcManager = new window.RpcManager();
            await rpcManager.initialize();

            // Test primary connection
            const primaryConnection = rpcManager.getCurrentConnection();
            assert(primaryConnection, 'Primary RPC connection failed');

            // Simulate primary connection failure
            await rpcManager.handleConnectionFailure();

            // Verify failover
            const backupConnection = rpcManager.getCurrentConnection();
            assert(backupConnection, 'Backup RPC connection failed');
            assert(backupConnection !== primaryConnection, 'Failover not working');

            this.results.passed += 3;
            console.log('✓ RPC failover tests passed\n');
        } catch (error) {
            this.results.failed++;
            this.results.errors.push({
                component: 'RPCFailover',
                error: error.message
            });
            console.error('✗ RPC failover tests failed:', error, '\n');
        }
    }

    async testWalletIntegration() {
        console.log('Testing Wallet Integration...');

        try {
            const walletSecurity = new window.WalletSecurity();
            const mockWallet = await TestUtils.createMockWallet();

            // Test wallet connection
            assert(await walletSecurity.connect(mockWallet), 'Wallet connection failed');

            // Test transaction signing
            const mockTx = TestUtils.createMockTransaction();
            assert(await walletSecurity.signTransaction(mockTx), 'Transaction signing failed');

            // Test security checks
            assert(await walletSecurity.validateTransaction(mockTx), 'Transaction validation failed');
            assert(!walletSecurity.isInactive(), 'False inactivity detection');

            this.results.passed += 4;
            console.log('✓ Wallet integration tests passed\n');
        } catch (error) {
            this.results.failed++;
            this.results.errors.push({
                component: 'WalletIntegration',
                error: error.message
            });
            console.error('✗ Wallet integration tests failed:', error, '\n');
        }
    }

    async testTradingWorkflow() {
        console.log('Testing Trading Workflow...');

        try {
            const tradingBot = new window.TradingBot();
            await tradingBot.initialize();

            // Test market data retrieval
            const marketData = await tradingBot.getMarketData();
            assert(marketData, 'Market data retrieval failed');

            // Test signal generation
            const signals = await tradingBot.strategyExecutor.generateSignals(marketData);
            assert(signals.size > 0, 'Signal generation failed');

            // Test trade execution
            for (const [token, signal] of signals) {
                if (signal.type === 'BUY' || signal.type === 'SELL') {
                    const txId = await tradingBot.executeTrade(
                        token,
                        1.0,
                        signal.type
                    );
                    assert(txId, `Trade execution failed for ${token}`);
                }
            }

            this.results.passed += 2 + signals.size;
            console.log('✓ Trading workflow tests passed\n');
        } catch (error) {
            this.results.failed++;
            this.results.errors.push({
                component: 'TradingWorkflow',
                error: error.message
            });
            console.error('✗ Trading workflow tests failed:', error, '\n');
        }
    }

    async testRiskManagement() {
        console.log('Testing Risk Management...');

        try {
            const riskManager = new window.RiskManager();
            const testCases = TestUtils.generateTestCases();

            // Test position sizing
            const position = await riskManager.calculatePositionSize(1.0, 0.1);
            assert(position > 0, 'Position sizing calculation failed');

            // Test trade validation
            for (const trade of testCases.validTrades) {
                assert(await riskManager.validateTrade(trade), 'Valid trade rejected');
            }

            for (const trade of testCases.invalidTrades) {
                assert(!(await riskManager.validateTrade(trade)), 'Invalid trade accepted');
            }

            // Test risk metrics
            const metrics = riskManager.getRiskMetrics();
            assert(metrics, 'Risk metrics not available');

            this.results.passed += 2 + testCases.validTrades.length + testCases.invalidTrades.length;
            console.log('✓ Risk management tests passed\n');
        } catch (error) {
            this.results.failed++;
            this.results.errors.push({
                component: 'RiskManagement',
                error: error.message
            });
            console.error('✗ Risk management tests failed:', error, '\n');
        }
    }

    async testPerformanceMonitoring() {
        console.log('Testing Performance Monitoring...');

        try {
            const analytics = new window.PerformanceAnalytics();
            await analytics.initialize();

            // Test trade recording
            const testCases = TestUtils.generateTestCases();
            for (const trade of testCases.validTrades) {
                await analytics.recordTrade(trade);
            }

            // Test performance metrics
            const stats = await analytics.updateStats();
            assert(stats.totalTrades === testCases.validTrades.length, 'Trade count mismatch');
            assert(typeof stats.profitLoss === 'number', 'Invalid P&L calculation');
            assert(typeof stats.winRate === 'number', 'Invalid win rate calculation');

            // Test alerts
            await analytics.checkAlerts();
            assert(Array.isArray(analytics.state.alerts), 'Alert system not functioning');

            this.results.passed += 4;
            console.log('✓ Performance monitoring tests passed\n');
        } catch (error) {
            this.results.failed++;
            this.results.errors.push({
                component: 'PerformanceMonitoring',
                error: error.message
            });
            console.error('✗ Performance monitoring tests failed:', error, '\n');
        }
    }

    async testErrorHandling() {
        console.log('Testing Error Handling...');

        try {
            const tradingBot = new window.TradingBot();
            await tradingBot.initialize();

            // Test RPC error handling
            const rpcError = await tradingBot.rpcManager.handleConnectionFailure();
            assert(rpcError === undefined, 'RPC error handling failed');

            // Test transaction error handling
            const invalidTx = TestUtils.createMockTransaction();
            invalidTx.sign = () => { throw new Error('Signature failed'); };
            
            try {
                await tradingBot.walletSecurity.signTransaction(invalidTx);
                assert(false, 'Transaction error handling failed');
            } catch (error) {
                assert(error.message === 'Signature failed', 'Unexpected error message');
            }

            // Test strategy error handling
            const invalidMarketData = null;
            try {
                await tradingBot.strategyExecutor.generateSignals(invalidMarketData);
                assert(false, 'Strategy error handling failed');
            } catch (error) {
                assert(error, 'Strategy should throw error for invalid data');
            }

            this.results.passed += 3;
            console.log('✓ Error handling tests passed\n');
        } catch (error) {
            this.results.failed++;
            this.results.errors.push({
                component: 'ErrorHandling',
                error: error.message
            });
            console.error('✗ Error handling tests failed:', error, '\n');
        }
    }

    generateReport() {
        console.log('=== System Integration Test Report ===');
        console.log(`Total Tests: ${this.results.passed + this.results.failed}`);
        console.log(`Passed: ${this.results.passed}`);
        console.log(`Failed: ${this.results.failed}`);
        console.log(`Success Rate: ${(this.results.passed / (this.results.passed + this.results.failed) * 100).toFixed(2)}%`);

        if (this.results.errors.length > 0) {
            console.log('\nErrors:');
            this.results.errors.forEach(error => {
                console.log(`- ${error.component}: ${error.error}`);
            });
        }

        // Save results
        this.saveResults();
    }

    async saveResults() {
        try {
            const fs = require('fs');
            const path = require('path');
            
            const resultsDir = path.join(__dirname, 'test-results');
            if (!fs.existsSync(resultsDir)) {
                fs.mkdirSync(resultsDir);
            }
            
            const filename = path.join(resultsDir, 
                `system-integration-test-${new Date().toISOString().replace(/:/g, '-')}.json`);
            
            fs.writeFileSync(filename, JSON.stringify(this.results, null, 2));
            console.log(`\nTest results saved to: ${filename}`);
        } catch (error) {
            console.error('Failed to save test results:', error);
        }
    }
}

// Helper assertion function
function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

// Export system integration tests
if (typeof module !== 'undefined') {
    module.exports = SystemIntegrationTest;
} else {
    window.SystemIntegrationTest = SystemIntegrationTest;
}
