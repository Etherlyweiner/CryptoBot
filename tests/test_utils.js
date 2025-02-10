class TestUtils {
    static async createMockConnection() {
        return {
            getSlot: async () => 100,
            getBalance: async () => 1000000000, // 1 SOL
            getRecentBlockhash: async () => ({
                blockhash: 'mock-blockhash',
                lastValidBlockHeight: 1000
            }),
            sendRawTransaction: async (tx) => 'mock-signature',
            confirmTransaction: async () => ({ value: { err: null } })
        };
    }

    static async createMockWallet() {
        return {
            publicKey: { toBase58: () => 'mock-public-key' },
            signTransaction: async (tx) => tx,
            signAllTransactions: async (txs) => txs,
            connect: async () => true,
            disconnect: async () => true,
            isConnected: true
        };
    }

    static createMockMarketData() {
        return {
            'mock-token-1': {
                price: 1.0,
                volume: 100000,
                prices: Array(100).fill(1.0).map((p, i) => p + Math.sin(i/10) * 0.1),
                volumes: Array(100).fill(100000),
                timestamp: Date.now()
            },
            'mock-token-2': {
                price: 2.0,
                volume: 200000,
                prices: Array(100).fill(2.0).map((p, i) => p + Math.cos(i/10) * 0.2),
                volumes: Array(100).fill(200000),
                timestamp: Date.now()
            }
        };
    }

    static async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    static createMockTransaction() {
        return {
            add: () => {},
            sign: () => {},
            serialize: () => new Uint8Array(32),
            recentBlockhash: 'mock-blockhash',
            feePayer: { toBase58: () => 'mock-public-key' }
        };
    }

    static async mockNetworkRequest(endpoint, data = null) {
        await this.sleep(100); // Simulate network latency
        
        switch (endpoint) {
            case 'price':
                return { price: 1.0, timestamp: Date.now() };
            case 'volume':
                return { volume: 100000, timestamp: Date.now() };
            case 'quote':
                return {
                    inAmount: 1000000,
                    outAmount: 990000,
                    fee: 1000,
                    priceImpact: 0.01
                };
            default:
                throw new Error(`Unknown endpoint: ${endpoint}`);
        }
    }

    static generateTestCases() {
        return {
            validTrades: [
                {
                    token: 'mock-token-1',
                    amount: 1.0,
                    side: 'BUY',
                    price: 1.0,
                    timestamp: Date.now()
                },
                {
                    token: 'mock-token-2',
                    amount: 0.5,
                    side: 'SELL',
                    price: 2.0,
                    timestamp: Date.now()
                }
            ],
            invalidTrades: [
                {
                    token: 'invalid-token',
                    amount: -1.0,
                    side: 'INVALID',
                    price: 0,
                    timestamp: Date.now()
                },
                {
                    token: 'mock-token-1',
                    amount: 1000000, // Too large
                    side: 'BUY',
                    price: 1.0,
                    timestamp: Date.now()
                }
            ],
            marketConditions: {
                normal: {
                    volatility: 0.1,
                    volume: 100000,
                    liquidity: 1000000
                },
                volatile: {
                    volatility: 0.5,
                    volume: 500000,
                    liquidity: 100000
                },
                illiquid: {
                    volatility: 0.2,
                    volume: 10000,
                    liquidity: 10000
                }
            }
        };
    }

    static async mockStrategySignals() {
        return new Map([
            ['mock-token-1', {
                type: 'BUY',
                strength: 0.8,
                indicators: {
                    rsi: 25,
                    ema: 1.0,
                    volume: 100000
                }
            }],
            ['mock-token-2', {
                type: 'SELL',
                strength: 0.7,
                indicators: {
                    rsi: 75,
                    ema: 2.1,
                    volume: 200000
                }
            }]
        ]);
    }

    static createTestEnvironment() {
        return {
            connection: this.createMockConnection(),
            wallet: this.createMockWallet(),
            marketData: this.createMockMarketData(),
            testCases: this.generateTestCases(),
            signals: this.mockStrategySignals()
        };
    }
}

// Export test utilities
if (typeof module !== 'undefined') {
    module.exports = TestUtils;
} else {
    window.TestUtils = TestUtils;
}
