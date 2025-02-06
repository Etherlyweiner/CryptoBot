class WalletManager {
    constructor() {
        this.provider = null;
        this.connection = null;
        this.connected = false;
        this.onStatusUpdate = null;
        this._init();  // Initialize on construction
    }

    async _init() {
        try {
            // Initialize Solana connection with fallback RPC endpoints
            const rpcEndpoints = [
                'https://solana-mainnet.rpc.extrnode.com',
                'https://mainnet.helius-rpc.com/?api-key=1d22a422-51a8-4df6-8f80-c32c34827429',
                'https://neat-hidden-sanctuary.solana-mainnet.discover.quiknode.pro/2af5315d336f9ae920028bbb6ba4a6e5dc652a03/',
                'https://solana-mainnet.g.alchemy.com/v2/demo'
            ];

            for (const endpoint of rpcEndpoints) {
                try {
                    const connection = new solanaWeb3.Connection(
                        endpoint,
                        { 
                            commitment: 'confirmed',
                            confirmTransactionInitialTimeout: 60000,
                            disableRetryOnRateLimit: false,
                            fetch: window.fetch
                        }
                    );
                    
                    // Test connection with a simple call
                    const blockHeight = await connection.getBlockHeight();
                    if (blockHeight > 0) {
                        this.connection = connection;
                        console.log('Solana connection established to:', endpoint);
                        break;
                    }
                } catch (error) {
                    console.warn(`Failed to connect to ${endpoint}, trying next...`);
                }
            }

            if (!this.connection) {
                throw new Error('Failed to connect to any Solana RPC endpoint');
            }

            // Wait for wallet to be available
            let attempts = 0;
            while (!window.solana && attempts < 10) {
                attempts++;
                console.log(`Checking for Phantom wallet (attempt ${attempts}/10)`);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            if (!window.solana) {
                throw new Error('Phantom wallet not found after 10 attempts');
            }

            console.log('Wallet detected:', window.solana);
            this.provider = window.solana;

            // Setup listeners
            this.provider.on('connect', () => {
                console.log('Wallet connected event');
                this.connected = true;
                if (this.onStatusUpdate) {
                    this.onStatusUpdate('connected');
                }
            });

            this.provider.on('disconnect', () => {
                console.log('Wallet disconnected');
                this.connected = false;
                if (this.onStatusUpdate) {
                    this.onStatusUpdate('disconnected');
                }
            });

            console.log('Wallet manager initialized successfully');
            return true;

        } catch (error) {
            console.error('Wallet initialization failed:', error);
            throw error;
        }
    }

    async connect() {
        try {
            console.log('Attempting to connect wallet...');
            
            if (!this.provider) {
                await this._init();
            }

            console.log('Requesting wallet connection...');
            await this.provider.connect();
            
            console.log('Wallet connected successfully');
            
            // Get wallet info
            return await this.getWalletInfo();

        } catch (error) {
            console.error('Failed to connect wallet:', error);
            throw error;
        }
    }

    async disconnect() {
        try {
            if (this.provider) {
                await this.provider.disconnect();
            }
            this.connected = false;
        } catch (error) {
            console.error('Failed to disconnect wallet:', error);
            throw error;
        }
    }

    isConnected() {
        return this.connected && this.provider && this.provider.isConnected;
    }

    async getWalletInfo() {
        try {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const publicKey = this.provider.publicKey.toString();
            console.log('Getting wallet info for:', publicKey);

            // Get SOL balance with retries
            let balance = 0;
            let retries = 3;
            
            while (retries > 0) {
                try {
                    balance = await this.connection.getBalance(
                        new solanaWeb3.PublicKey(publicKey),
                        'confirmed'
                    );
                    break;
                } catch (error) {
                    console.warn(`Failed to get balance, retries left: ${retries-1}`);
                    retries--;
                    if (retries === 0) throw error;
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }
            
            const solBalance = balance / solanaWeb3.LAMPORTS_PER_SOL;

            const info = {
                publicKey,
                balance: solBalance
            };

            console.log('Wallet info retrieved:', info);
            return info;

        } catch (error) {
            console.error('Failed to get wallet info:', error);
            throw error;
        }
    }
}

// Initialize wallet manager
window.walletManager = new WalletManager();

// Check if wallet is ready for trading
const checkTradingReadiness = async () => {
    try {
        const walletStatus = await window.walletManager.connect();
        
        if (!walletStatus) {
            return {
                ready: false,
                message: 'Wallet not connected',
                details: 'Please connect your wallet'
            };
        }
        
        // Check minimum balance (0.05 SOL for trading + fees)
        const minBalance = 0.05;
        if (walletStatus.balance < minBalance) {
            return {
                ready: false,
                message: `Insufficient balance: ${walletStatus.balance.toFixed(4)} SOL`,
                details: `Minimum required: ${minBalance} SOL (for trading + fees)`
            };
        }

        // Get token balances
        const tokenBalances = {};
        if (window.walletManager.jupiter && window.walletManager.jupiter.TOKENS) {  
            for (const [symbol, mint] of Object.entries(window.walletManager.jupiter.TOKENS)) {
                try {
                    const balance = await window.walletManager.getTokenBalance(mint);
                    if (balance > 0) {
                        tokenBalances[symbol] = balance;
                    }
                } catch (error) {
                    console.warn(`Failed to get ${symbol} balance:`, error);
                }
            }
        }
        
        return {
            ready: true,
            message: 'Ready for trading',
            balance: walletStatus.balance,
            tokenBalances,
            publicKey: walletStatus.publicKey,
            username: 'etherlyweiner'
        };
    } catch (error) {
        return {
            ready: false,
            message: 'Error checking wallet status',
            details: error.message
        };
    }
};
