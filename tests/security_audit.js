class SecurityAudit {
    constructor() {
        this.results = {
            walletSecurity: [],
            apiSecurity: [],
            networkSecurity: [],
            dataSecurity: [],
            errors: []
        };
    }

    async runAll() {
        console.log('Starting Security Audit...\n');

        try {
            // Test wallet security
            await this.testWalletSecurity();

            // Test API security
            await this.testAPISecurity();

            // Test network security
            await this.testNetworkSecurity();

            // Test data security
            await this.testDataSecurity();

            // Test input validation
            await this.testInputValidation();

            // Test error handling
            await this.testSecurityErrorHandling();

            // Generate report
            this.generateReport();

        } catch (error) {
            console.error('Security audit failed:', error);
            this.results.errors.push({
                component: 'SecurityAudit',
                error: error.message
            });
        }
    }

    async testWalletSecurity() {
        console.log('Testing Wallet Security...');

        try {
            const walletSecurity = new window.WalletSecurity();
            const mockWallet = await TestUtils.createMockWallet();

            // Test wallet initialization
            const initResult = await this.testWalletInitialization(walletSecurity);
            this.results.walletSecurity.push(initResult);

            // Test transaction signing
            const signingResult = await this.testTransactionSigning(walletSecurity, mockWallet);
            this.results.walletSecurity.push(signingResult);

            // Test key management
            const keyResult = await this.testKeyManagement(walletSecurity);
            this.results.walletSecurity.push(keyResult);

            // Test wallet timeout
            const timeoutResult = await this.testWalletTimeout(walletSecurity);
            this.results.walletSecurity.push(timeoutResult);

            console.log('✓ Wallet security tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'WalletSecurity',
                error: error.message
            });
            console.error('✗ Wallet security tests failed:', error, '\n');
        }
    }

    async testAPISecurity() {
        console.log('Testing API Security...');

        try {
            // Test API authentication
            const authResult = await this.testAPIAuthentication();
            this.results.apiSecurity.push(authResult);

            // Test rate limiting
            const rateResult = await this.testRateLimiting();
            this.results.apiSecurity.push(rateResult);

            // Test API key rotation
            const rotationResult = await this.testAPIKeyRotation();
            this.results.apiSecurity.push(rotationResult);

            // Test request validation
            const validationResult = await this.testRequestValidation();
            this.results.apiSecurity.push(validationResult);

            console.log('✓ API security tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'APISecurity',
                error: error.message
            });
            console.error('✗ API security tests failed:', error, '\n');
        }
    }

    async testNetworkSecurity() {
        console.log('Testing Network Security...');

        try {
            // Test SSL/TLS configuration
            const sslResult = await this.testSSLConfiguration();
            this.results.networkSecurity.push(sslResult);

            // Test RPC connection security
            const rpcResult = await this.testRPCConnectionSecurity();
            this.results.networkSecurity.push(rpcResult);

            // Test WebSocket security
            const wsResult = await this.testWebSocketSecurity();
            this.results.networkSecurity.push(wsResult);

            // Test network isolation
            const isolationResult = await this.testNetworkIsolation();
            this.results.networkSecurity.push(isolationResult);

            console.log('✓ Network security tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'NetworkSecurity',
                error: error.message
            });
            console.error('✗ Network security tests failed:', error, '\n');
        }
    }

    async testDataSecurity() {
        console.log('Testing Data Security...');

        try {
            // Test data encryption
            const encryptionResult = await this.testDataEncryption();
            this.results.dataSecurity.push(encryptionResult);

            // Test secure storage
            const storageResult = await this.testSecureStorage();
            this.results.dataSecurity.push(storageResult);

            // Test data access controls
            const accessResult = await this.testDataAccessControls();
            this.results.dataSecurity.push(accessResult);

            // Test data sanitization
            const sanitizationResult = await this.testDataSanitization();
            this.results.dataSecurity.push(sanitizationResult);

            console.log('✓ Data security tests completed\n');
        } catch (error) {
            this.results.errors.push({
                component: 'DataSecurity',
                error: error.message
            });
            console.error('✗ Data security tests failed:', error, '\n');
        }
    }

    async testWalletInitialization(walletSecurity) {
        const testCases = [
            { name: 'Valid Initialization', wallet: TestUtils.createMockWallet() },
            { name: 'Invalid Wallet', wallet: null },
            { name: 'Missing Keys', wallet: TestUtils.createMockWalletWithoutKeys() }
        ];

        const results = [];
        for (const test of testCases) {
            try {
                await walletSecurity.initialize(test.wallet);
                results.push({
                    test: test.name,
                    status: 'passed'
                });
            } catch (error) {
                results.push({
                    test: test.name,
                    status: 'failed',
                    error: error.message
                });
            }
        }

        return {
            component: 'WalletInitialization',
            results
        };
    }

    async testTransactionSigning(walletSecurity, mockWallet) {
        const testCases = [
            { name: 'Valid Transaction', tx: TestUtils.createMockTransaction() },
            { name: 'Invalid Transaction', tx: null },
            { name: 'Malformed Transaction', tx: TestUtils.createMalformedTransaction() }
        ];

        const results = [];
        for (const test of testCases) {
            try {
                await walletSecurity.signTransaction(test.tx);
                results.push({
                    test: test.name,
                    status: 'passed'
                });
            } catch (error) {
                results.push({
                    test: test.name,
                    status: 'failed',
                    error: error.message
                });
            }
        }

        return {
            component: 'TransactionSigning',
            results
        };
    }

    async testKeyManagement(walletSecurity) {
        const testCases = [
            { name: 'Key Generation', fn: () => walletSecurity.generateKeys() },
            { name: 'Key Rotation', fn: () => walletSecurity.rotateKeys() },
            { name: 'Key Backup', fn: () => walletSecurity.backupKeys() }
        ];

        const results = [];
        for (const test of testCases) {
            try {
                await test.fn();
                results.push({
                    test: test.name,
                    status: 'passed'
                });
            } catch (error) {
                results.push({
                    test: test.name,
                    status: 'failed',
                    error: error.message
                });
            }
        }

        return {
            component: 'KeyManagement',
            results
        };
    }

    async testAPIAuthentication() {
        const testCases = [
            { name: 'Valid API Key', key: 'valid_key' },
            { name: 'Invalid API Key', key: 'invalid_key' },
            { name: 'Expired API Key', key: 'expired_key' }
        ];

        const results = [];
        for (const test of testCases) {
            try {
                const response = await fetch('/api/test', {
                    headers: { 'Authorization': `Bearer ${test.key}` }
                });
                results.push({
                    test: test.name,
                    status: response.ok ? 'passed' : 'failed',
                    statusCode: response.status
                });
            } catch (error) {
                results.push({
                    test: test.name,
                    status: 'failed',
                    error: error.message
                });
            }
        }

        return {
            component: 'APIAuthentication',
            results
        };
    }

    async testRateLimiting() {
        const requests = 20;
        const results = [];

        for (let i = 0; i < requests; i++) {
            try {
                const response = await fetch('/api/test');
                results.push({
                    request: i + 1,
                    status: response.ok ? 'passed' : 'failed',
                    statusCode: response.status
                });
            } catch (error) {
                results.push({
                    request: i + 1,
                    status: 'failed',
                    error: error.message
                });
            }
        }

        return {
            component: 'RateLimiting',
            results
        };
    }

    async testDataEncryption() {
        const testCases = [
            { name: 'Encrypt API Key', data: 'api_key_123' },
            { name: 'Encrypt Wallet Key', data: 'wallet_key_456' },
            { name: 'Encrypt Configuration', data: { key: 'value' } }
        ];

        const results = [];
        for (const test of testCases) {
            try {
                const encrypted = await window.encryption.encrypt(test.data);
                const decrypted = await window.encryption.decrypt(encrypted);
                
                results.push({
                    test: test.name,
                    status: JSON.stringify(test.data) === JSON.stringify(decrypted) ? 'passed' : 'failed'
                });
            } catch (error) {
                results.push({
                    test: test.name,
                    status: 'failed',
                    error: error.message
                });
            }
        }

        return {
            component: 'DataEncryption',
            results
        };
    }

    async testSecureStorage() {
        const testCases = [
            { name: 'Store API Key', key: 'apiKey', value: 'test_key' },
            { name: 'Store Wallet', key: 'wallet', value: { address: 'test_address' } },
            { name: 'Store Settings', key: 'settings', value: { theme: 'dark' } }
        ];

        const results = [];
        for (const test of testCases) {
            try {
                await window.secureStorage.set(test.key, test.value);
                const retrieved = await window.secureStorage.get(test.key);
                
                results.push({
                    test: test.name,
                    status: JSON.stringify(test.value) === JSON.stringify(retrieved) ? 'passed' : 'failed'
                });
            } catch (error) {
                results.push({
                    test: test.name,
                    status: 'failed',
                    error: error.message
                });
            }
        }

        return {
            component: 'SecureStorage',
            results
        };
    }

    generateReport() {
        console.log('=== Security Audit Report ===');

        // Wallet Security Report
        console.log('\nWallet Security Results:');
        this.results.walletSecurity.forEach(result => {
            console.log(`\n${result.component}:`);
            result.results.forEach(test => {
                console.log(`  ${test.test}: ${test.status}`);
                if (test.error) {
                    console.log(`    Error: ${test.error}`);
                }
            });
        });

        // API Security Report
        console.log('\nAPI Security Results:');
        this.results.apiSecurity.forEach(result => {
            console.log(`\n${result.component}:`);
            result.results.forEach(test => {
                console.log(`  ${test.test || `Request ${test.request}`}: ${test.status}`);
                if (test.statusCode) {
                    console.log(`    Status Code: ${test.statusCode}`);
                }
                if (test.error) {
                    console.log(`    Error: ${test.error}`);
                }
            });
        });

        // Network Security Report
        console.log('\nNetwork Security Results:');
        this.results.networkSecurity.forEach(result => {
            console.log(`\n${result.component}:`);
            result.results.forEach(test => {
                console.log(`  ${test.test}: ${test.status}`);
                if (test.error) {
                    console.log(`    Error: ${test.error}`);
                }
            });
        });

        // Data Security Report
        console.log('\nData Security Results:');
        this.results.dataSecurity.forEach(result => {
            console.log(`\n${result.component}:`);
            result.results.forEach(test => {
                console.log(`  ${test.test}: ${test.status}`);
                if (test.error) {
                    console.log(`    Error: ${test.error}`);
                }
            });
        });

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
                `security-audit-${new Date().toISOString().replace(/:/g, '-')}.json`);
            
            fs.writeFileSync(filename, JSON.stringify(this.results, null, 2));
            console.log(`\nAudit results saved to: ${filename}`);
        } catch (error) {
            console.error('Failed to save audit results:', error);
        }
    }
}

// Export security audit
if (typeof module !== 'undefined') {
    module.exports = SecurityAudit;
} else {
    window.SecurityAudit = SecurityAudit;
}
