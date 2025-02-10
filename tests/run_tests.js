class TestRunner {
    constructor() {
        this.startTime = null;
        this.endTime = null;
    }

    async runAllTests() {
        this.startTime = Date.now();
        console.log('=== Starting Test Suite ===\n');

        try {
            // Run unit tests
            console.log('Running Unit Tests...');
            const unitTests = new UnitTests();
            await unitTests.runAll();

            // Run integration tests
            console.log('\nRunning Integration Tests...');
            const integrationTests = new IntegrationTests();
            await integrationTests.runAll();

            // Generate test report
            this.endTime = Date.now();
            this.generateTestReport(unitTests, integrationTests);

        } catch (error) {
            console.error('Test suite failed:', error);
        }
    }

    generateTestReport(unitTests, integrationTests) {
        const duration = (this.endTime - this.startTime) / 1000;

        console.log('\n=== Test Suite Summary ===');
        console.log(`Duration: ${duration.toFixed(2)} seconds`);
        console.log('\nUnit Tests:');
        console.log(`- Passed: ${unitTests.testResults.passed}`);
        console.log(`- Failed: ${unitTests.testResults.failed}`);
        console.log(`- Skipped: ${unitTests.testResults.skipped}`);
        
        console.log('\nIntegration Tests:');
        console.log(`- Passed: ${integrationTests.testResults.passed}`);
        console.log(`- Failed: ${integrationTests.testResults.failed}`);
        console.log(`- Skipped: ${integrationTests.testResults.skipped}`);

        const totalTests = (unitTests.testResults.passed + unitTests.testResults.failed + 
            unitTests.testResults.skipped + integrationTests.testResults.passed + 
            integrationTests.testResults.failed + integrationTests.testResults.skipped);
        
        const totalPassed = unitTests.testResults.passed + integrationTests.testResults.passed;
        const totalFailed = unitTests.testResults.failed + integrationTests.testResults.failed;
        
        console.log('\nTotal Results:');
        console.log(`- Total Tests: ${totalTests}`);
        console.log(`- Total Passed: ${totalPassed}`);
        console.log(`- Total Failed: ${totalFailed}`);
        console.log(`- Success Rate: ${((totalPassed / totalTests) * 100).toFixed(2)}%`);

        if (unitTests.testResults.failures.length > 0 || 
            integrationTests.testResults.failures.length > 0) {
            console.log('\nTest Failures:');
            
            if (unitTests.testResults.failures.length > 0) {
                console.log('\nUnit Test Failures:');
                unitTests.testResults.failures.forEach(failure => {
                    console.log(`- ${failure.suite}: ${failure.error}`);
                });
            }
            
            if (integrationTests.testResults.failures.length > 0) {
                console.log('\nIntegration Test Failures:');
                integrationTests.testResults.failures.forEach(failure => {
                    console.log(`- ${failure.suite}: ${failure.error}`);
                });
            }
        }

        // Save test results to file
        this.saveTestResults(unitTests, integrationTests);
    }

    async saveTestResults(unitTests, integrationTests) {
        const results = {
            timestamp: new Date().toISOString(),
            duration: (this.endTime - this.startTime) / 1000,
            unitTests: unitTests.testResults,
            integrationTests: integrationTests.testResults,
            summary: {
                totalTests: (unitTests.testResults.passed + unitTests.testResults.failed + 
                    unitTests.testResults.skipped + integrationTests.testResults.passed + 
                    integrationTests.testResults.failed + integrationTests.testResults.skipped),
                totalPassed: unitTests.testResults.passed + integrationTests.testResults.passed,
                totalFailed: unitTests.testResults.failed + integrationTests.testResults.failed,
                successRate: ((unitTests.testResults.passed + integrationTests.testResults.passed) / 
                    (unitTests.testResults.passed + unitTests.testResults.failed + 
                    unitTests.testResults.skipped + integrationTests.testResults.passed + 
                    integrationTests.testResults.failed + integrationTests.testResults.skipped) * 100)
            }
        };

        try {
            const fs = require('fs');
            const path = require('path');
            
            // Create test-results directory if it doesn't exist
            const resultsDir = path.join(__dirname, 'test-results');
            if (!fs.existsSync(resultsDir)) {
                fs.mkdirSync(resultsDir);
            }
            
            // Save results to JSON file
            const filename = path.join(resultsDir, 
                `test-results-${new Date().toISOString().replace(/:/g, '-')}.json`);
            
            fs.writeFileSync(filename, JSON.stringify(results, null, 2));
            console.log(`\nTest results saved to: ${filename}`);
        } catch (error) {
            console.error('Failed to save test results:', error);
        }
    }
}

// Export test runner
if (typeof module !== 'undefined') {
    module.exports = TestRunner;
} else {
    window.TestRunner = TestRunner;
}

// Run tests if this is the main module
if (require.main === module) {
    const runner = new TestRunner();
    runner.runAllTests().catch(console.error);
}
