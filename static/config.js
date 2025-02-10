// RPC Configuration
const RPC_CONFIG = {
    PRIMARY: {
        HELIUS: {
            url: 'https://mainnet.helius-rpc.com',
            priority: 1,
            retryAttempts: 3,
            retryDelay: 1000
        },
        QUICKNODE: {
            url: 'https://api.quicknode.com/solana',
            priority: 2,
            retryAttempts: 3,
            retryDelay: 1000
        }
    },
    BACKUP: {
        ALCHEMY: {
            url: 'https://solana-mainnet.g.alchemy.com',
            priority: 3,
            retryAttempts: 2,
            retryDelay: 2000
        },
        PUBLIC: {
            url: 'https://api.mainnet-beta.solana.com',
            priority: 4,
            retryAttempts: 1,
            retryDelay: 3000
        }
    }
};

// Health Check Configuration
const HEALTH_CHECK = {
    interval: 30000,  // Check every 30 seconds
    timeout: 5000,    // RPC timeout
    threshold: 2      // Number of failures before failover
};

// Export configurations
window.BOT_CONFIG = {
    RPC: RPC_CONFIG,
    HEALTH: HEALTH_CHECK,
    CONSTANTS: {
        SOL_MINT: 'So11111111111111111111111111111111111111112',
        JUPITER_API: 'https://quote-api.jup.ag/v6',
        BIRDEYE_API: 'https://public-api.birdeye.so'
    }
};
