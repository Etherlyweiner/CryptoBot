/**
 * Manages wallet connections and transactions.
 */
class WalletManager {
    constructor(config) {
        this.config = config;
        this.wallet = null;
        this.initialized = false;
        this.logger = new Logger('WalletManager');
        this.autoConnect = config.wallet?.auto_connect || false;
    }

    /**
     * Initialize wallet connection.
     */
    async initialize() {
        try {
            this.logger.info('Initializing wallet manager...');

            // Check if Phantom is installed
            if (!window.solana?.isPhantom) {
                throw new Error('Phantom wallet not installed');
            }

            // Try auto-connect if enabled
            if (this.autoConnect) {
                try {
                    await this.connect(true);
                } catch (error) {
                    this.logger.warn('Auto-connect failed:', error.message);
                }
            }

            this.initialized = true;
            this.logger.info('Wallet manager initialized');
            return true;

        } catch (error) {
            this.logger.error('Failed to initialize wallet manager:', error);
            throw error;
        }
    }

    /**
     * Connect to wallet.
     */
    async connect(silent = false) {
        try {
            let resp;
            if (silent) {
                try {
                    resp = await window.solana.connect({ onlyIfTrusted: true });
                } catch {
                    return false;
                }
            } else {
                resp = await window.solana.connect();
            }

            this.wallet = resp.publicKey;
            this.logger.info('Connected to wallet:', this.wallet.toString());

            // Update config with wallet address
            this.config.wallet.address = this.wallet.toString();

            return true;

        } catch (error) {
            this.logger.error('Failed to connect wallet:', error);
            throw error;
        }
    }

    /**
     * Disconnect from wallet.
     */
    async disconnect() {
        try {
            if (window.solana?.isConnected) {
                await window.solana.disconnect();
            }
            this.wallet = null;
            this.logger.info('Disconnected from wallet');

        } catch (error) {
            this.logger.error('Failed to disconnect wallet:', error);
            throw error;
        }
    }

    /**
     * Check if wallet is connected.
     */
    isConnected() {
        return this.wallet !== null && window.solana?.isConnected;
    }

    /**
     * Get wallet address.
     */
    getAddress() {
        return this.wallet?.toString() || null;
    }

    /**
     * Get wallet balance.
     */
    async getBalance() {
        try {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const connection = await this.getConnection();
            const balance = await connection.getBalance(this.wallet);
            return balance / 1e9; // Convert lamports to SOL

        } catch (error) {
            this.logger.error('Failed to get wallet balance:', error);
            throw error;
        }
    }

    /**
     * Sign and send transaction.
     */
    async signAndSendTransaction(transaction) {
        try {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }

            // Sign transaction
            const signed = await window.solana.signTransaction(transaction);

            // Send transaction
            const connection = await this.getConnection();
            const signature = await connection.sendRawTransaction(
                signed.serialize(),
                {
                    skipPreflight: false,
                    preflightCommitment: 'confirmed'
                }
            );

            // Confirm transaction
            const confirmation = await connection.confirmTransaction(signature);
            if (confirmation.value.err) {
                throw new Error(`Transaction failed: ${confirmation.value.err}`);
            }

            this.logger.info('Transaction confirmed:', signature);
            return signature;

        } catch (error) {
            this.logger.error('Failed to sign and send transaction:', error);
            throw error;
        }
    }

    /**
     * Close wallet manager.
     */
    async close() {
        try {
            if (this.isConnected()) {
                await this.disconnect();
            }
            this.initialized = false;
            this.logger.info('Wallet manager closed');

        } catch (error) {
            this.logger.error('Failed to close wallet manager:', error);
            throw error;
        }
    }

    /**
     * Get RPC connection.
     */
    async getConnection() {
        if (!window.rpcManager) {
            throw new Error('RPC Manager not initialized');
        }
        return window.rpcManager.getCurrentConnection();
    }
}

// Export for Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WalletManager;
} else {
    window.WalletManager = WalletManager;
}
