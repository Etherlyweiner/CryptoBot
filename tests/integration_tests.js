class IntegrationTests {
    constructor() {
        this.testResults = {
            passed: 0,
            failed: 0,
            skipped: 0,
            total: 0,
            failures: []
        };
    }

    async runAll() {
        console.log('Starting Integration Tests...');
        
        try {
            // Test complete trading workflow
            await this.testTradingWorkflow();
            
            // Test system recovery
            await this.testSystemRecovery();
            
            // Test multiple strategy execution
            await this.testMultiStrategyExecution();
            
            // Test performance monitoring
            await this.testPerformanceMonitoring();
            
            // Test risk management integration
            await this.testRiskManagementIntegration();
            
        } catch (error) {
            console.error('Integration test suite failed:', error);
            this.testResults.failures.push({
                suite: 'Global',
                error: error.message
            });
        }

        this.reportResults();
    }

    async testTradingWorkflow() {
        console.log('\nTesting Complete Trading Workflow...');
        
        try {
            // Initialize trading bot
            const tradingBot = new window.TradingBot();
            assert(await tradingBot.initialize(), 'Trading bot initialization failed');
            
            // Get market data
            const marketData = await tradingBot.getMarketData();
            assert(marketData, 'Market data retrieval failed');
            
            // Generate trading signals
            const signals = await tradingBot.strategyExecutor.generateSignals(marketData);
            assert(signals.size > 0, 'No trading signals generated');
            
            // Execute trades based on signals
            for (const [token, signal] of signals) {
                if (signal.type === 'BUY' || signal.type === 'SELL') {
                    const txId = await tradingBot.executeTrade(
                        token,
                        1.0, // Test amount
                        signal.type
                    );
                    assert(txId, `Trade execution failed for ${token}`);
                }
            }
            
            this.testResults.passed += 4;
        } catch (error) {
            this.recordFailure('TradingWorkflow', error);
        }
    }

    async testSystemRecovery() {
        console.log('\nTesting System Recovery...');
        
        try {
            const tradingBot = new window.TradingBot();
            
            // Test RPC failover
            await tradingBot.rpcManager.handleConnectionFailure();
            const newConnection = tradingBot.rpcManager.getCurrentConnection();
            assert(newConnection, 'RPC failover failed');
            
            // Test wallet reconnection
            await tradingBot.walletSecurity.disconnect();
            assert(await tradingBot.walletSecurity.reconnect(), 'Wallet reconnection failed');
            
            // Test strategy recovery
            const currentStrategy = tradingBot.strategyExecutor.getCurrentStrategy();
            await tradingBot.strategyExecutor.reset();
            assert(await tradingBot.strategyExecutor.switchStrategy(currentStrategy.name),
                'Strategy recovery failed');
            
            this.testResults.passed += 3;
        } catch (error) {
            this.recordFailure('SystemRecovery', error);
        }
    }

    async testMultiStrategyExecution() {
        console.log('\nTesting Multiple Strategy Execution...');
        
        try {
            const tradingBot = new window.TradingBot();
            const strategies = tradingBot.strategyExecutor.getStrategies();
            
            for (const strategy of strategies) {
                // Switch to strategy
                assert(await tradingBot.strategyExecutor.switchStrategy(strategy.name),
                    `Failed to switch to ${strategy.name}`);
                
                // Generate signals
                const signals = await tradingBot.strategyExecutor.generateSignals(
                    await tradingBot.getMarketData()
                );
                assert(signals.size > 0, `No signals generated for ${strategy.name}`);
                
                // Validate signals
                for (const [token, signal] of signals) {
                    assert(await tradingBot.riskManager.validateSignal(signal),
                        `Invalid signal generated for ${token}`);
                }
            }
            
            this.testResults.passed += strategies.length * 3;
        } catch (error) {
            this.recordFailure('MultiStrategyExecution', error);
        }
    }

    async testPerformanceMonitoring() {
        console.log('\nTesting Performance Monitoring Integration...');
        
        try {
            const tradingBot = new window.TradingBot();
            
            // Execute some test trades
            const testCases = TestUtils.generateTestCases();
            for (const trade of testCases.validTrades) {
                await tradingBot.executeTrade(
                    trade.token,
                    trade.amount,
                    trade.side
                );
            }
            
            // Verify performance tracking
            const stats = await tradingBot.performanceAnalytics.updateStats();
            assert(stats.totalTrades === testCases.validTrades.length,
                'Trade count mismatch in performance tracking');
            
            // Check alerts
            const alerts = tradingBot.performanceAnalytics.state.alerts;
            assert(Array.isArray(alerts), 'Alert system not functioning');
            
            // Verify dashboard updates
            assert(tradingBot.dashboard.state.lastUpdate > 0,
                'Dashboard not updating');
            
            this.testResults.passed += 4;
        } catch (error) {
            this.recordFailure('PerformanceMonitoring', error);
        }
    }

    async testRiskManagementIntegration() {
        console.log('\nTesting Risk Management Integration...');
        
        try {
            const tradingBot = new window.TradingBot();
            const testCases = TestUtils.generateTestCases();
            
            // Test risk validation integration
            for (const trade of testCases.validTrades) {
                assert(await tradingBot.riskManager.validateTrade(trade),
                    'Valid trade rejected by risk management');
            }
            
            for (const trade of testCases.invalidTrades) {
                assert(!(await tradingBot.riskManager.validateTrade(trade)),
                    'Invalid trade accepted by risk management');
            }
            
            // Test position sizing integration
            const position = await tradingBot.riskManager.calculatePositionSize(1.0, 0.1);
            assert(position > 0, 'Position sizing calculation failed');
            
            // Test risk metrics integration with performance analytics
            const riskMetrics = tradingBot.riskManager.getRiskMetrics();
            assert(riskMetrics, 'Risk metrics not available');
            
            this.testResults.passed += testCases.validTrades.length +
                testCases.invalidTrades.length + 2;
        } catch (error) {
            this.recordFailure('RiskManagementIntegration', error);
        }
    }

    recordFailure(suite, error) {
        console.error(`${suite} test failed:`, error);
        this.testResults.failures.push({
            suite,
            error: error.message
        });
        this.testResults.failed++;
    }

    reportResults() {
        console.log('\n=== Integration Test Results ===');
        console.log(`Passed: ${this.testResults.passed}`);
        console.log(`Failed: ${this.testResults.failed}`);
        console.log(`Skipped: ${this.testResults.skipped}`);
        console.log(`Total: ${this.testResults.passed + this.testResults.failed + this.testResults.skipped}`);
        
        if (this.testResults.failures.length > 0) {
            console.log('\nFailures:');
            this.testResults.failures.forEach(failure => {
                console.log(`- ${failure.suite}: ${failure.error}`);
            });
        }
    }
}

// Helper assertion function
function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

// Export integration tests
if (typeof module !== 'undefined') {
    module.exports = IntegrationTests;
} else {
    window.IntegrationTests = IntegrationTests;
}
