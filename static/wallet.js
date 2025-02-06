class WalletManager {
    constructor() {
        this.wallet = null;
        this.connection = null;
        this.initialized = false;
        this.onWalletStatusChange = null;
    }

    async initialize() {
        try {
            console.log('Initializing wallet manager...');
            
            // Check for Phantom wallet
            if (!window.solana || !window.solana.isPhantom) {
                throw new Error('Phantom wallet not found');
            }

            this.wallet = window.solana;
            this.initialized = true;
            console.log('Wallet manager initialized successfully');
            
            // Set up connection listeners
            this.wallet.on('connect', () => {
                console.log('Wallet connected:', this.wallet.publicKey.toString());
                if (this.onWalletStatusChange) {
                    this.onWalletStatusChange(true);
                }
            });

            this.wallet.on('disconnect', () => {
                console.log('Wallet disconnected');
                if (this.onWalletStatusChange) {
                    this.onWalletStatusChange(false);
                }
            });

            return true;
        } catch (error) {
            console.error('Failed to initialize wallet manager:', error);
            throw error;
        }
    }

    async initializeConnection(endpoint) {
        try {
            console.log('Initializing connection to:', endpoint);
            
            // Create connection
            this.connection = new solanaWeb3.Connection(endpoint, 'confirmed');
            
            // Test connection
            const version = await this.connection.getVersion();
            console.log('Connected to Solana:', version);

            // Initialize Jupiter with the connection
            if (window.jupiter) {
                await window.jupiter.initialize(this.connection);
            }

            return true;
        } catch (error) {
            console.error('Failed to initialize connection:', error);
            throw error;
        }
    }

    async connect() {
        try {
            if (!this.initialized) {
                await this.initialize();
            }

            if (!this.wallet) {
                throw new Error('Wallet not initialized');
            }

            // Connect wallet
            await this.wallet.connect();
            console.log('Wallet connected successfully');
            
            return true;
        } catch (error) {
            console.error('Failed to connect wallet:', error);
            throw error;
        }
    }

    async disconnect() {
        try {
            if (this.wallet) {
                await this.wallet.disconnect();
                console.log('Wallet disconnected successfully');
            }
        } catch (error) {
            console.error('Failed to disconnect wallet:', error);
            throw error;
        }
    }

    isConnected() {
        return this.wallet && this.wallet.isConnected;
    }

    getPublicKey() {
        if (!this.isConnected()) {
            throw new Error('Wallet not connected');
        }
        return this.wallet.publicKey;
    }

    async signTransaction(transaction) {
        try {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const signedTx = await this.wallet.signTransaction(transaction);
            return signedTx;
        } catch (error) {
            console.error('Failed to sign transaction:', error);
            throw error;
        }
    }

    async signAllTransactions(transactions) {
        try {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const signedTxs = await this.wallet.signAllTransactions(transactions);
            return signedTxs;
        } catch (error) {
            console.error('Failed to sign transactions:', error);
            throw error;
        }
    }
}

// Initialize and export wallet manager
window.walletManager = new WalletManager();
console.log('Wallet manager instance created');

// Check for wallet with retries
async function checkForWallet(retries = 10, interval = 1000) {
    console.log('Checking for wallet (attempt 1/' + retries + ')');
    
    for (let i = 0; i < retries; i++) {
        if (window.solana) {
            console.log('Using Phantom wallet');
            await window.walletManager.initialize();
            return;
        }
        if (i < retries - 1) {
            await new Promise(resolve => setTimeout(resolve, interval));
            console.log('Checking for wallet (attempt ' + (i + 2) + '/' + retries + ')');
        }
    }
    throw new Error('No compatible wallet found');
}

// Start wallet detection
checkForWallet().catch(console.error);
