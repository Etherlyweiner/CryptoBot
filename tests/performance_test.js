class PerformanceTest {
    constructor() {
        this.results = {
            latency: [],
            throughput: [],
            resourceUsage: [],
            errors: []
        };
    }

    async runAll() {
        console.log('Starting Performance Tests...\n');

        try {
            // Test system latency
            await this.testLatency();

            // Test system throughput
            await this.testThroughput();

            // Test resource usage
            await this.testResourceUsage();

            // Test concurrent operations
            await this.testConcurrency();

            // Test memory management
            await this.testMemoryManagement();

            // Generate report
            this.generateReport();

        } catch (error) {
            console.error('Performance tests failed:', error);
            this.results.errors.push({
                component: 'PerformanceTest',
                error: error.message
            });
        }
    }

    async testLatency() {
        console.log('Testing System Latency...');

        try {
            const tradingBot = new window.TradingBot();
            await tradingBot.initialize();

            const operations = [
                { name: 'Market Data Retrieval', fn: () => tradingBot.getMarketData() },
                { name: 'Signal Generation', fn: () => tradingBot.strategyExecutor.generateSignals() },
                { name: 'Trade Execution', fn: () => tradingBot.executeMockTrade() },
                { name: 'Risk Calculation', fn: () => tradingBot.riskManager.calculateRisk() },
                { name: 'Performance Update', fn: () => tradingBot.performanceAnalytics.updateStats() }
            ];

            for (const op of operations) {
                const latencies = [];
                
                // Run each operation multiple times
                for (let i = 0; i < 10; i++) {
                    const start = performance.now();
                    await op.fn();
                    const end = performance.now();
                    latencies.push(end - start);
                }

                // Calculate statistics
                const avgLatency = latencies.reduce((a, b) => a + b) / latencies.length;
                const p95Latency = this.calculatePercentile(latencies, 95);
                const p99Latency = this.calculatePercentile(latencies, 99);

                this.results.latency.push({
                    operation: op.name,
                    average: avgLatency,
                    p95: p95Latency,
                    p99: p99Latency
                });
            }

            console.log('✓ Latency tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'Latency',
                error: error.message
            });
            console.error('✗ Latency tests failed:', error, '\n');
        }
    }

    async testThroughput() {
        console.log('Testing System Throughput...');

        try {
            const tradingBot = new window.TradingBot();
            await tradingBot.initialize();

            const operations = [
                { name: 'Market Data Processing', fn: this.testMarketDataThroughput.bind(this) },
                { name: 'Trade Processing', fn: this.testTradeThroughput.bind(this) },
                { name: 'Signal Processing', fn: this.testSignalThroughput.bind(this) }
            ];

            for (const op of operations) {
                const result = await op.fn(tradingBot);
                this.results.throughput.push({
                    operation: op.name,
                    ...result
                });
            }

            console.log('✓ Throughput tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'Throughput',
                error: error.message
            });
            console.error('✗ Throughput tests failed:', error, '\n');
        }
    }

    async testResourceUsage() {
        console.log('Testing Resource Usage...');

        try {
            const initialMemory = process.memoryUsage();
            const initialCPU = process.cpuUsage();

            const tradingBot = new window.TradingBot();
            await tradingBot.initialize();

            // Run a series of operations
            const operations = [
                () => tradingBot.getMarketData(),
                () => tradingBot.strategyExecutor.generateSignals(),
                () => tradingBot.executeMockTrade(),
                () => tradingBot.riskManager.calculateRisk(),
                () => tradingBot.performanceAnalytics.updateStats()
            ];

            for (const op of operations) {
                const start = {
                    memory: process.memoryUsage(),
                    cpu: process.cpuUsage()
                };

                await op();

                const end = {
                    memory: process.memoryUsage(),
                    cpu: process.cpuUsage(start.cpu)
                };

                this.results.resourceUsage.push({
                    operation: op.name,
                    memoryDelta: {
                        heapUsed: end.memory.heapUsed - start.memory.heapUsed,
                        heapTotal: end.memory.heapTotal - start.memory.heapTotal,
                        external: end.memory.external - start.memory.external
                    },
                    cpuDelta: {
                        user: end.cpu.user,
                        system: end.cpu.system
                    }
                });
            }

            console.log('✓ Resource usage tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'ResourceUsage',
                error: error.message
            });
            console.error('✗ Resource usage tests failed:', error, '\n');
        }
    }

    async testConcurrency() {
        console.log('Testing System Concurrency...');

        try {
            const tradingBot = new window.TradingBot();
            await tradingBot.initialize();

            const concurrentOperations = 10;
            const operations = [];

            // Create concurrent operations
            for (let i = 0; i < concurrentOperations; i++) {
                operations.push(
                    this.runConcurrentOperation(tradingBot, i)
                );
            }

            // Execute all operations concurrently
            const start = performance.now();
            await Promise.all(operations);
            const end = performance.now();

            this.results.concurrency = {
                operationCount: concurrentOperations,
                totalTime: end - start,
                averageTime: (end - start) / concurrentOperations
            };

            console.log('✓ Concurrency tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'Concurrency',
                error: error.message
            });
            console.error('✗ Concurrency tests failed:', error, '\n');
        }
    }

    async testMemoryManagement() {
        console.log('Testing Memory Management...');

        try {
            const tradingBot = new window.TradingBot();
            await tradingBot.initialize();

            const initialMemory = process.memoryUsage();
            const iterations = 100;

            // Run memory-intensive operations
            for (let i = 0; i < iterations; i++) {
                await tradingBot.getMarketData();
                await tradingBot.strategyExecutor.generateSignals();
                await tradingBot.performanceAnalytics.updateStats();

                if (i % 10 === 0) {
                    global.gc(); // Force garbage collection if available
                }
            }

            const finalMemory = process.memoryUsage();

            this.results.memoryManagement = {
                initialHeapUsed: initialMemory.heapUsed,
                finalHeapUsed: finalMemory.heapUsed,
                delta: finalMemory.heapUsed - initialMemory.heapUsed,
                iterations: iterations
            };

            console.log('✓ Memory management tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'MemoryManagement',
                error: error.message
            });
            console.error('✗ Memory management tests failed:', error, '\n');
        }
    }

    async testMarketDataThroughput(tradingBot) {
        const iterations = 100;
        const start = performance.now();

        for (let i = 0; i < iterations; i++) {
            await tradingBot.getMarketData();
        }

        const end = performance.now();
        const totalTime = end - start;

        return {
            operationsPerSecond: (iterations / totalTime) * 1000,
            totalTime,
            iterations
        };
    }

    async testTradeThroughput(tradingBot) {
        const iterations = 50;
        const start = performance.now();

        for (let i = 0; i < iterations; i++) {
            await tradingBot.executeMockTrade();
        }

        const end = performance.now();
        const totalTime = end - start;

        return {
            operationsPerSecond: (iterations / totalTime) * 1000,
            totalTime,
            iterations
        };
    }

    async testSignalThroughput(tradingBot) {
        const iterations = 100;
        const start = performance.now();

        for (let i = 0; i < iterations; i++) {
            await tradingBot.strategyExecutor.generateSignals();
        }

        const end = performance.now();
        const totalTime = end - start;

        return {
            operationsPerSecond: (iterations / totalTime) * 1000,
            totalTime,
            iterations
        };
    }

    async runConcurrentOperation(tradingBot, index) {
        try {
            await tradingBot.getMarketData();
            await tradingBot.strategyExecutor.generateSignals();
            await tradingBot.executeMockTrade();
            return { success: true, index };
        } catch (error) {
            return { success: false, index, error: error.message };
        }
    }

    calculatePercentile(array, percentile) {
        const sorted = array.slice().sort((a, b) => a - b);
        const pos = (sorted.length - 1) * percentile / 100;
        const base = Math.floor(pos);
        const rest = pos - base;

        if (sorted[base + 1] !== undefined) {
            return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
        } else {
            return sorted[base];
        }
    }

    generateReport() {
        console.log('=== Performance Test Report ===');

        // Latency Report
        console.log('\nLatency Results:');
        this.results.latency.forEach(result => {
            console.log(`${result.operation}:`);
            console.log(`  Average: ${result.average.toFixed(2)}ms`);
            console.log(`  P95: ${result.p95.toFixed(2)}ms`);
            console.log(`  P99: ${result.p99.toFixed(2)}ms`);
        });

        // Throughput Report
        console.log('\nThroughput Results:');
        this.results.throughput.forEach(result => {
            console.log(`${result.operation}:`);
            console.log(`  Operations/sec: ${result.operationsPerSecond.toFixed(2)}`);
            console.log(`  Total Time: ${result.totalTime.toFixed(2)}ms`);
        });

        // Resource Usage Report
        console.log('\nResource Usage Results:');
        this.results.resourceUsage.forEach(result => {
            console.log(`${result.operation}:`);
            console.log(`  Memory Delta:`);
            console.log(`    Heap Used: ${(result.memoryDelta.heapUsed / 1024 / 1024).toFixed(2)}MB`);
            console.log(`    Heap Total: ${(result.memoryDelta.heapTotal / 1024 / 1024).toFixed(2)}MB`);
            console.log(`  CPU Delta:`);
            console.log(`    User: ${(result.cpuDelta.user / 1000000).toFixed(2)}s`);
            console.log(`    System: ${(result.cpuDelta.system / 1000000).toFixed(2)}s`);
        });

        // Concurrency Report
        if (this.results.concurrency) {
            console.log('\nConcurrency Results:');
            console.log(`Operations: ${this.results.concurrency.operationCount}`);
            console.log(`Total Time: ${this.results.concurrency.totalTime.toFixed(2)}ms`);
            console.log(`Average Time per Operation: ${this.results.concurrency.averageTime.toFixed(2)}ms`);
        }

        // Memory Management Report
        if (this.results.memoryManagement) {
            console.log('\nMemory Management Results:');
            console.log(`Initial Heap: ${(this.results.memoryManagement.initialHeapUsed / 1024 / 1024).toFixed(2)}MB`);
            console.log(`Final Heap: ${(this.results.memoryManagement.finalHeapUsed / 1024 / 1024).toFixed(2)}MB`);
            console.log(`Delta: ${(this.results.memoryManagement.delta / 1024 / 1024).toFixed(2)}MB`);
        }

        // Error Report
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
                `performance-test-${new Date().toISOString().replace(/:/g, '-')}.json`);
            
            fs.writeFileSync(filename, JSON.stringify(this.results, null, 2));
            console.log(`\nTest results saved to: ${filename}`);
        } catch (error) {
            console.error('Failed to save test results:', error);
        }
    }
}

// Export performance tests
if (typeof module !== 'undefined') {
    module.exports = PerformanceTest;
} else {
    window.PerformanceTest = PerformanceTest;
}
