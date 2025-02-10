class WalletSecurity {
    constructor() {
        this.state = {
            isInitialized: false,
            walletConnected: false,
            lastActivity: null,
            pendingTransactions: new Map(),
            approvedAddresses: new Set(),
            securityLevel: 'high'
        };

        // Security settings
        this.settings = {
            inactivityTimeout: 30 * 60 * 1000,    // 30 minutes
            maxPendingTx: 5,                      // Maximum pending transactions
            minConfirmations: 2,                  // Minimum confirmations needed
            maxTransactionSize: 100,              // In SOL
            requireHardwareWallet: true,          // Require hardware wallet
            autoLockEnabled: true,                // Auto-lock after inactivity
            whitelistOnly: true                   // Only allow whitelisted addresses
        };

        // Initialize security features
        this.initialize();
    }

    async initialize() {
        try {
            // Set up wallet connection listener
            window.solana?.on('connect', () => this.handleWalletConnect());
            window.solana?.on('disconnect', () => this.handleWalletDisconnect());

            // Start security monitoring
            this.startSecurityMonitoring();

            this.state.isInitialized = true;
            Logger.log('INFO', 'Wallet security initialized');
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize wallet security', error);
            throw error;
        }
    }

    startSecurityMonitoring() {
        // Monitor wallet activity
        setInterval(() => this.checkWalletActivity(), 60000);

        // Monitor pending transactions
        setInterval(() => this.checkPendingTransactions(), 30000);

        // Auto-lock check
        if (this.settings.autoLockEnabled) {
            setInterval(() => this.checkAutoLock(), 60000);
        }
    }

    async validateWallet() {
        if (!window.solana?.isConnected) {
            return { valid: false, reason: 'Wallet not connected' };
        }

        // Check if hardware wallet when required
        if (this.settings.requireHardwareWallet) {
            const isHardwareWallet = await this.isHardwareWallet();
            if (!isHardwareWallet) {
                return { valid: false, reason: 'Hardware wallet required' };
            }
        }

        return { valid: true };
    }

    async validateTransaction(transaction, destination) {
        try {
            // Check wallet status
            const walletStatus = await this.validateWallet();
            if (!walletStatus.valid) {
                return walletStatus;
            }

            // Check pending transactions
            if (this.pendingTransactions.size >= this.settings.maxPendingTx) {
                return { valid: false, reason: 'Too many pending transactions' };
            }

            // Validate destination
            if (this.settings.whitelistOnly && !this.approvedAddresses.has(destination)) {
                return { valid: false, reason: 'Destination not whitelisted' };
            }

            // Check transaction size
            const txSize = await this.getTransactionSize(transaction);
            if (txSize > this.settings.maxTransactionSize) {
                return { valid: false, reason: 'Transaction size too large' };
            }

            return { valid: true };
        } catch (error) {
            Logger.log('ERROR', 'Transaction validation failed', error);
            return { valid: false, reason: 'Validation error' };
        }
    }

    async signTransaction(transaction) {
        try {
            // Validate transaction first
            const validation = await this.validateTransaction(transaction);
            if (!validation.valid) {
                throw new Error(validation.reason);
            }

            // Add to pending transactions
            const txId = transaction.signature?.[0]?.toString();
            if (txId) {
                this.pendingTransactions.set(txId, {
                    timestamp: Date.now(),
                    status: 'pending',
                    confirmations: 0
                });
            }

            // Update last activity
            this.updateActivity();

            return await window.solana.signTransaction(transaction);
        } catch (error) {
            Logger.log('ERROR', 'Failed to sign transaction', error);
            throw error;
        }
    }

    updateActivity() {
        this.state.lastActivity = Date.now();
    }

    async checkWalletActivity() {
        if (!this.state.walletConnected) return;

        const inactiveTime = Date.now() - this.state.lastActivity;
        if (inactiveTime > this.settings.inactivityTimeout) {
            await this.lockWallet();
        }
    }

    async checkPendingTransactions() {
        for (const [txId, tx] of this.pendingTransactions) {
            try {
                const status = await this.getTransactionStatus(txId);
                if (status.confirmations >= this.settings.minConfirmations) {
                    this.pendingTransactions.delete(txId);
                } else {
                    this.pendingTransactions.set(txId, {
                        ...tx,
                        status: status.status,
                        confirmations: status.confirmations
                    });
                }
            } catch (error) {
                Logger.log('ERROR', `Failed to check transaction ${txId}`, error);
            }
        }
    }

    async lockWallet() {
        try {
            await window.solana?.disconnect();
            this.state.walletConnected = false;
            Logger.log('INFO', 'Wallet locked due to inactivity');
        } catch (error) {
            Logger.log('ERROR', 'Failed to lock wallet', error);
        }
    }

    // Event handlers
    handleWalletConnect() {
        this.state.walletConnected = true;
        this.updateActivity();
        Logger.log('INFO', 'Wallet connected');
    }

    handleWalletDisconnect() {
        this.state.walletConnected = false;
        Logger.log('INFO', 'Wallet disconnected');
    }

    // Helper methods
    async isHardwareWallet() {
        // Implementation to detect hardware wallet
        return true; // Placeholder
    }

    async getTransactionSize(transaction) {
        // Implementation to calculate transaction size
        return 1; // Placeholder
    }

    async getTransactionStatus(txId) {
        // Implementation to get transaction status
        return {
            status: 'confirmed',
            confirmations: 2
        }; // Placeholder
    }
}

// Export the wallet security manager
window.WalletSecurity = WalletSecurity;
