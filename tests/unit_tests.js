class UnitTests {
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
        console.log('Starting Unit Tests...');
        
        // Create test environment
        const env = await TestUtils.createTestEnvironment();
        
        try {
            // RPC Manager Tests
            await this.testRpcManager(env);
            
            // Risk Manager Tests
            await this.testRiskManager(env);
            
            // Wallet Security Tests
            await this.testWalletSecurity(env);
            
            // Strategy Tests
            await this.testStrategies(env);
            
            // Performance Analytics Tests
            await this.testPerformanceAnalytics(env);
            
            // Trading System Tests
            await this.testTradingSystem(env);
            
        } catch (error) {
            console.error('Test suite failed:', error);
            this.testResults.failures.push({
                suite: 'Global',
                error: error.message
            });
        }

        this.reportResults();
    }

    async testRpcManager(env) {
        console.log('\nTesting RPC Manager...');
        
        try {
            const rpcManager = new window.RpcManager();
            
            // Test initialization
            assert(await rpcManager.initialize(), 'RPC Manager initialization failed');
            
            // Test connection management
            const connection = rpcManager.getCurrentConnection();
            assert(connection, 'Failed to get current connection');
            
            // Test failover
            await rpcManager.handleConnectionFailure();
            const newConnection = rpcManager.getCurrentConnection();
            assert(newConnection, 'Failover connection not established');
            
            this.testResults.passed += 3;
        } catch (error) {
            this.recordFailure('RpcManager', error);
        }
    }

    async testRiskManager(env) {
        console.log('\nTesting Risk Manager...');
        
        try {
            const riskManager = new window.RiskManager();
            
            // Test position sizing
            const position = await riskManager.calculatePositionSize(1.0, 0.1);
            assert(position > 0, 'Invalid position size calculation');
            
            // Test risk limits
            const { validTrades, invalidTrades } = env.testCases;
            
            for (const trade of validTrades) {
                assert(await riskManager.validateTrade(trade), 'Valid trade rejected');
            }
            
            for (const trade of invalidTrades) {
                assert(!(await riskManager.validateTrade(trade)), 'Invalid trade accepted');
            }
            
            this.testResults.passed += validTrades.length + invalidTrades.length + 1;
        } catch (error) {
            this.recordFailure('RiskManager', error);
        }
    }

    async testWalletSecurity(env) {
        console.log('\nTesting Wallet Security...');
        
        try {
            const walletSecurity = new window.WalletSecurity();
            
            // Test transaction validation
            const validTx = TestUtils.createMockTransaction();
            assert(await walletSecurity.validateTransaction(validTx), 'Valid transaction rejected');
            
            // Test inactivity monitoring
            await TestUtils.sleep(100);
            assert(!walletSecurity.isInactive(), 'False inactivity detection');
            
            this.testResults.passed += 2;
        } catch (error) {
            this.recordFailure('WalletSecurity', error);
        }
    }

    async testStrategies(env) {
        console.log('\nTesting Trading Strategies...');
        
        try {
            const strategyExecutor = new window.StrategyExecutor();
            await strategyExecutor.initialize();
            
            // Test signal generation
            const signals = await strategyExecutor.generateSignals(env.marketData);
            assert(signals.size > 0, 'No trading signals generated');
            
            // Test strategy switching
            const strategies = strategyExecutor.getStrategies();
            for (const strategy of strategies) {
                assert(await strategyExecutor.switchStrategy(strategy.name), 
                    `Failed to switch to ${strategy.name} strategy`);
            }
            
            this.testResults.passed += strategies.length + 1;
        } catch (error) {
            this.recordFailure('Strategies', error);
        }
    }

    async testPerformanceAnalytics(env) {
        console.log('\nTesting Performance Analytics...');
        
        try {
            const analytics = new window.PerformanceAnalytics();
            
            // Test trade recording
            const { validTrades } = env.testCases;
            for (const trade of validTrades) {
                await analytics.recordTrade(trade);
            }
            
            // Test performance metrics
            const stats = await analytics.updateStats();
            assert(stats.totalTrades === validTrades.length, 'Trade count mismatch');
            assert(typeof stats.profitLoss === 'number', 'Invalid P&L calculation');
            assert(typeof stats.winRate === 'number', 'Invalid win rate calculation');
            
            this.testResults.passed += 3;
        } catch (error) {
            this.recordFailure('PerformanceAnalytics', error);
        }
    }

    async testTradingSystem(env) {
        console.log('\nTesting Trading System...');
        
        try {
            const tradingBot = new window.TradingBot();
            
            // Test initialization
            assert(await tradingBot.initialize(), 'Trading system initialization failed');
            
            // Test market data retrieval
            const marketData = await tradingBot.getMarketData();
            assert(marketData, 'Failed to retrieve market data');
            
            // Test trade execution
            const { validTrades } = env.testCases;
            const trade = validTrades[0];
            const txId = await tradingBot.executeTrade(
                trade.token,
                trade.amount,
                trade.side
            );
            assert(txId, 'Trade execution failed');
            
            this.testResults.passed += 3;
        } catch (error) {
            this.recordFailure('TradingSystem', error);
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
        console.log('\n=== Test Results ===');
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

// Export unit tests
if (typeof module !== 'undefined') {
    module.exports = UnitTests;
} else {
    window.UnitTests = UnitTests;
}
