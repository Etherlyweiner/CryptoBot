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
            // Initialize Solana connection with Helius RPC endpoints
            const rpcEndpoints = [
                'https://staked.helius-rpc.com?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c',
                'https://mainnet.helius-rpc.com/?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c',
                'https://myrta-kxo6n1-fast-mainnet.helius-rpc.com',
                'https://eclipse.helius-rpc.com/'
            ];

            const wsEndpoint = 'wss://mainnet.helius-rpc.com/?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c';

            for (const endpoint of rpcEndpoints) {
                try {
                    const connection = new solanaWeb3.Connection(
                        endpoint,
                        { 
                            commitment: 'confirmed',
                            wsEndpoint: wsEndpoint,
                            confirmTransactionInitialTimeout: 60000,
                            disableRetryOnRateLimit: false
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

            // Check for any available wallet
            let attempts = 0;
            while (attempts < 10) {
                attempts++;
                if (window.phantom?.solana || window.solana || window.solflare) {
                    break;
                }
                console.log(`Checking for wallet (attempt ${attempts}/10)`);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            // Get the wallet provider
            if (window.phantom?.solana) {
                this.provider = window.phantom.solana;
                console.log('Using Phantom wallet');
            } else if (window.solana) {
                this.provider = window.solana;
                console.log('Using Solana wallet');
            } else if (window.solflare) {
                this.provider = window.solflare;
                console.log('Using Solflare wallet');
            } else {
                throw new Error('No wallet found. Please install Phantom, Solflare, or another Solana wallet.');
            }

            // Setup listeners
            this.provider.on('connect', (publicKey) => {
                console.log('Wallet connected:', publicKey.toBase58());
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

            this.provider.on('accountChanged', (publicKey) => {
                if (publicKey) {
                    console.log('Wallet account changed:', publicKey.toBase58());
                } else {
                    console.log('Wallet account changed: disconnected');
                    this.connected = false;
                    if (this.onStatusUpdate) {
                        this.onStatusUpdate('disconnected');
                    }
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

            if (!this.provider) {
                throw new Error('No wallet provider available');
            }

            // Try to reconnect if already connected
            try {
                const resp = await this.provider.connect();
                console.log('Wallet connected:', resp.publicKey.toBase58());
                this.connected = true;
                return resp;
            } catch (err) {
                console.error('Connection error:', err);
                // If connection fails, try to disconnect first
                try {
                    await this.provider.disconnect();
                } catch (e) {
                    console.warn('Disconnect error:', e);
                }
                // Then try to connect again
                const resp = await this.provider.connect();
                console.log('Wallet connected after retry:', resp.publicKey.toBase58());
                this.connected = true;
                return resp;
            }
        } catch (error) {
            console.error('Failed to connect wallet:', error);
            this.connected = false;
            throw error;
        }
    }

    async disconnect() {
        try {
            if (this.provider && this.connected) {
                await this.provider.disconnect();
                this.connected = false;
            }
        } catch (error) {
            console.error('Failed to disconnect wallet:', error);
            throw error;
        }
    }

    isConnected() {
        return this.connected;
    }

    getProvider() {
        return this.provider;
    }

    getConnection() {
        return this.connection;
    }
}

// Initialize wallet manager
window.walletManager = new WalletManager();

// Check if wallet is ready for trading
async function checkTradingReadiness() {
    try {
        // Check wallet connection
        if (!window.walletManager.isConnected()) {
            throw new Error('Wallet not connected');
        }

        // Check RPC connection
        const connection = window.walletManager.getConnection();
        if (!connection) {
            throw new Error('No RPC connection');
        }

        // Get wallet balance
        const provider = window.walletManager.getProvider();
        const publicKey = provider.publicKey;
        const balance = await connection.getBalance(publicKey);
        
        // Check minimum balance (0.1 SOL)
        if (balance < 0.1 * 1e9) {
            throw new Error('Insufficient balance (minimum 0.1 SOL required)');
        }

        // All checks passed
        return {
            ready: true,
            publicKey: publicKey.toBase58(),
            balance: balance / 1e9
        };

    } catch (error) {
        console.error('Trading readiness check failed:', error);
        return {
            ready: false,
            error: error.message
        };
    }
}
