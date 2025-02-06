class WalletManager {
    constructor() {
        this.provider = null;
        this.connection = null;
        this.connected = false;
        this.onStatusUpdate = null;
        this.rpcEndpoints = [
            'https://staked.helius-rpc.com?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c',
            'https://mainnet.helius-rpc.com/?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c',
            'https://myrta-kxo6n1-fast-mainnet.helius-rpc.com',
            'https://eclipse.helius-rpc.com/',
            'https://api.mainnet-beta.solana.com', // Public fallback
            'https://solana-api.projectserum.com'  // Project Serum fallback
        ];
        this.wsEndpoints = [
            'wss://mainnet.helius-rpc.com/?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c',
            'wss://api.mainnet-beta.solana.com'
        ];
        this.currentEndpointIndex = 0;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this._init();  // Initialize on construction
    }

    async _init() {
        try {
            await this._establishConnection();
            await this._setupWalletProvider();
            console.log('Wallet manager initialized successfully');
            return true;
        } catch (error) {
            console.error('Wallet initialization failed:', error);
            throw error;
        }
    }

    async _establishConnection() {
        for (const endpoint of this.rpcEndpoints) {
            try {
                const connection = new solanaWeb3.Connection(
                    endpoint,
                    { 
                        commitment: 'confirmed',
                        wsEndpoint: this.wsEndpoints[0],
                        confirmTransactionInitialTimeout: 60000,
                        disableRetryOnRateLimit: false
                    }
                );
                
                // Test connection with multiple calls
                const [blockHeight, slot] = await Promise.all([
                    connection.getBlockHeight(),
                    connection.getSlot()
                ]);

                if (blockHeight > 0 && slot > 0) {
                    this.connection = connection;
                    console.log('Solana connection established to:', endpoint);
                    return true;
                }
            } catch (error) {
                console.warn(`Failed to connect to ${endpoint}, trying next...`, error);
            }
        }

        throw new Error('Failed to connect to any Solana RPC endpoint');
    }

    async _setupWalletProvider() {
        // Check for any available wallet with timeout
        const walletCheck = new Promise((resolve) => {
            let attempts = 0;
            const maxAttempts = 10;
            const checkInterval = setInterval(() => {
                attempts++;
                if (window.phantom?.solana || window.solana || window.solflare) {
                    clearInterval(checkInterval);
                    resolve(true);
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    resolve(false);
                }
                console.log(`Checking for wallet (attempt ${attempts}/${maxAttempts})`);
            }, 1000);
        });

        const hasWallet = await Promise.race([
            walletCheck,
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Wallet detection timeout')), 15000)
            )
        ]);

        if (!hasWallet) {
            throw new Error('No wallet found. Please install Phantom, Solflare, or another Solana wallet.');
        }

        // Get the wallet provider
        if (window.phantom?.solana) {
            this.provider = window.phantom.solana;
            console.log('Using Phantom wallet');
        } else if (window.solflare) {
            this.provider = window.solflare;
            console.log('Using Solflare wallet');
        } else if (window.solana) {
            this.provider = window.solana;
            console.log('Using Solana wallet');
        }

        if (!this.provider) {
            throw new Error('No wallet provider available');
        }

        // Setup wallet event listeners
        this._setupWalletListeners();
    }

    _setupWalletListeners() {
        // Remove any existing listeners
        this.provider.removeAllListeners?.();

        // Setup new listeners
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

        // Handle RPC connection errors
        if (this.connection) {
            this.connection.onAccountChange = () => {
                this._checkRPCConnection();
            };
        }
    }

    async _checkRPCConnection() {
        try {
            await this.connection.getRecentBlockhash();
        } catch (error) {
            console.warn('RPC connection error, attempting to reconnect...', error);
            this._handleRPCError();
        }
    }

    async _handleRPCError() {
        this.currentEndpointIndex = (this.currentEndpointIndex + 1) % this.rpcEndpoints.length;
        try {
            await this._establishConnection();
            console.log('Successfully reconnected to new RPC endpoint');
            this.reconnectAttempts = 0;
        } catch (error) {
            this.reconnectAttempts++;
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                console.log(`Reconnect attempt ${this.reconnectAttempts} failed, trying again...`);
                setTimeout(() => this._handleRPCError(), 2000 * Math.pow(2, this.reconnectAttempts));
            } else {
                console.error('Failed to reconnect after multiple attempts');
                this.reconnectAttempts = 0;
                if (this.onStatusUpdate) {
                    this.onStatusUpdate('error');
                }
            }
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
                // Then try to connect again with exponential backoff
                let attempts = 0;
                const maxAttempts = 3;
                while (attempts < maxAttempts) {
                    try {
                        const resp = await this.provider.connect();
                        console.log('Wallet connected after retry:', resp.publicKey.toBase58());
                        this.connected = true;
                        return resp;
                    } catch (retryErr) {
                        attempts++;
                        if (attempts === maxAttempts) throw retryErr;
                        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempts)));
                    }
                }
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
            }
            this.connected = false;
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
        if (!window.walletManager) {
            throw new Error('Wallet manager not initialized');
        }

        if (!window.walletManager.isConnected()) {
            throw new Error('Wallet not connected');
        }

        const connection = window.walletManager.getConnection();
        if (!connection) {
            throw new Error('No Solana connection available');
        }

        // Test RPC connection
        try {
            await connection.getRecentBlockhash();
        } catch (error) {
            throw new Error('RPC connection error: ' + error.message);
        }

        // Check if Jupiter is initialized
        if (!window.jupiter?.initialized) {
            throw new Error('Jupiter DEX not initialized');
        }

        return true;
    } catch (error) {
        console.error('Trading readiness check failed:', error);
        return false;
    }
}
