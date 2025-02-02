// Solana wallet connection
const EXPECTED_WALLET = '8jqv2AKPGYwojLRHQZLokkYdtHycs8HAVGDMqZUvTByB';

class WalletManager {
    constructor() {
        this.provider = null;
        this._connectHandlers = [];
        this._disconnectHandlers = [];
        this._balanceHandlers = [];
        this._init();
    }

    async _init() {
        try {
            await this._detectWallet();
            this._setupListeners();
            console.log('Wallet manager initialized');
        } catch (error) {
            console.error('Wallet initialization failed:', error);
            throw error;
        }
    }

    async _detectWallet(retries = 10) {
        return new Promise((resolve, reject) => {
            const check = (attempt = 0) => {
                const provider = window.phantom?.solana || window.solana;
                
                if (provider) {
                    console.log('Phantom provider found:', provider);
                    this.provider = provider;
                    resolve(provider);
                } else if (attempt < retries) {
                    console.log(`Attempt ${attempt + 1}: Waiting for Phantom...`);
                    setTimeout(() => check(attempt + 1), 1000);
                } else {
                    const error = new Error('Phantom wallet not detected. Please install Phantom extension.');
                    console.error(error);
                    reject(error);
                }
            };
            check();
        });
    }

    _setupListeners() {
        if (!this.provider) return;

        this.provider.on('connect', (...args) => {
            console.log('Wallet connected:', ...args);
            this._connectHandlers.forEach(handler => handler(...args));
            this.updateBalance();
        });

        this.provider.on('disconnect', (...args) => {
            console.log('Wallet disconnected:', ...args);
            this._disconnectHandlers.forEach(handler => handler(...args));
        });

        this.provider.on('accountChanged', () => {
            console.log('Account changed, updating balance');
            this.updateBalance();
        });
    }

    onConnect(handler) {
        this._connectHandlers.push(handler);
    }

    onDisconnect(handler) {
        this._disconnectHandlers.push(handler);
    }

    onBalanceChange(handler) {
        this._balanceHandlers.push(handler);
    }

    async connect() {
        try {
            if (!this.provider) {
                throw new Error('Wallet provider not initialized');
            }

            if (this.provider.isConnected) {
                console.log('Wallet already connected');
                return this.getWalletInfo();
            }

            console.log('Requesting wallet connection...');
            const response = await this.provider.connect();
            console.log('Connection response:', response);
            
            return await this.getWalletInfo();
        } catch (error) {
            console.error('Connection failed:', error);
            throw new Error(`Wallet connection failed: ${error.message}`);
        }
    }

    async disconnect() {
        try {
            await this.provider?.disconnect();
            console.log('Wallet disconnected successfully');
        } catch (error) {
            console.error('Disconnect failed:', error);
            throw error;
        }
    }

    async getWalletInfo() {
        try {
            if (!this.provider?.publicKey) {
                throw new Error('Wallet not connected');
            }

            const connection = new solanaWeb3.Connection(
                "https://api.mainnet-beta.solana.com",
                'confirmed'
            );

            const balance = await connection.getBalance(this.provider.publicKey);
            const info = {
                publicKey: this.provider.publicKey.toString(),
                balance: balance / 1e9, // Convert lamports to SOL
                network: 'mainnet-beta'
            };

            console.log('Wallet info:', info);
            return info;
        } catch (error) {
            console.error('Failed to get wallet info:', error);
            throw error;
        }
    }

    async updateBalance() {
        try {
            const info = await this.getWalletInfo();
            this._balanceHandlers.forEach(handler => handler(info.balance));
            return info.balance;
        } catch (error) {
            console.error('Balance update failed:', error);
            throw error;
        }
    }

    isConnected() {
        return this.provider?.isConnected || false;
    }

    async signTransaction(transaction) {
        try {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }
            
            console.log('Requesting transaction signature...');
            const signed = await this.provider.signTransaction(transaction);
            console.log('Transaction signed successfully');
            return signed;
        } catch (error) {
            console.error('Transaction signing failed:', error);
            throw error;
        }
    }

    async signMessage(message) {
        try {
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const encodedMessage = new TextEncoder().encode(message);
            console.log('Requesting message signature...');
            const { signature } = await this.provider.signMessage(encodedMessage);
            console.log('Message signed successfully');
            return signature;
        } catch (error) {
            console.error('Message signing failed:', error);
            throw error;
        }
    }
}

const walletManager = new WalletManager();

// Check if wallet is ready for trading
const checkTradingReadiness = async () => {
    try {
        const walletStatus = await walletManager.connect();
        
        if (!walletStatus) {
            return {
                ready: false,
                message: 'Wallet not connected',
                details: 'Please connect your wallet'
            };
        }
        
        // Check minimum balance (0.1 SOL)
        const minBalance = 0.1;
        if (walletStatus.balance < minBalance) {
            return {
                ready: false,
                message: `Insufficient balance: ${walletStatus.balance} SOL`,
                details: `Minimum required: ${minBalance} SOL`
            };
        }
        
        return {
            ready: true,
            message: 'Ready for trading',
            balance: walletStatus.balance,
            publicKey: walletStatus.publicKey,
            username: 'etherly'
        };
    } catch (error) {
        return {
            ready: false,
            message: 'Error checking wallet status',
            details: error.message
        };
    }
};
