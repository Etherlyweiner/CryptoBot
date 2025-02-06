// Solana wallet connection
const EXPECTED_WALLET = '7YTZcHQGJuReSDrQVvPCAj8qyxPzaUexHdKcswrumoyc';

class WalletManager {
    constructor() {
        this.provider = null;
        this.connection = null;
        this.jupiter = null;  
        this._connectHandlers = [];
        this._disconnectHandlers = [];
        this._balanceHandlers = [];
        this._tokenBalanceHandlers = new Map();
        this._init();
    }

    async _init() {
        try {
            console.log('Initializing WalletManager...');
            await this._detectWallet();
            console.log('Wallet detected:', this.provider);
            
            this.connection = new solanaWeb3.Connection(
                'https://staked.helius-rpc.com?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c',
                'confirmed'
            );
            console.log('Solana connection established');
            
            this.jupiter = new JupiterDEX();  
            console.log('Jupiter DEX initialized');
            
            this._setupListeners();
            console.log('Wallet manager initialized successfully');
        } catch (error) {
            console.error('Wallet initialization failed:', error);
            throw error;
        }
    }

    async _detectWallet(retries = 10) {
        return new Promise((resolve, reject) => {
            const check = (attempt = 0) => {
                console.log(`Checking for Phantom wallet (attempt ${attempt + 1}/${retries})`);
                
                // Check for both window.solana and window.phantom
                const provider = window?.phantom?.solana || window?.solana;
                
                if (provider) {
                    if (provider.isPhantom) {
                        console.log('Phantom wallet found:', provider);
                        this.provider = provider;
                        resolve(provider);
                    } else {
                        console.log('Found wallet provider but not Phantom:', provider);
                        if (attempt < retries) {
                            setTimeout(() => check(attempt + 1), 1000);
                        } else {
                            reject(new Error('Phantom wallet not found'));
                        }
                    }
                } else {
                    console.log('No wallet provider found yet');
                    if (attempt < retries) {
                        setTimeout(() => check(attempt + 1), 1000);
                    } else {
                        reject(new Error('No wallet provider found'));
                    }
                }
            };
            check();
        });
    }

    _setupListeners() {
        if (!this.provider) {
            console.error('Cannot setup listeners: provider not initialized');
            return;
        }

        console.log('Setting up wallet listeners');
        
        this.provider.on('connect', (...args) => {
            console.log('Wallet connected event:', args);
            this._connectHandlers.forEach(handler => handler(...args));
            this.updateBalance();
        });

        this.provider.on('disconnect', (...args) => {
            console.log('Wallet disconnected event:', args);
            this._disconnectHandlers.forEach(handler => handler(...args));
        });

        this.provider.on('accountChanged', (publicKey) => {
            console.log('Wallet account changed:', publicKey);
            if (publicKey) {
                this._connectHandlers.forEach(handler => handler(publicKey));
            } else {
                this._disconnectHandlers.forEach(handler => handler());
            }
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
            console.log('Attempting to connect wallet...');
            if (!this.provider) {
                throw new Error('Wallet provider not initialized');
            }

            if (this.isConnected()) {
                console.log('Wallet already connected');
                return await this.getWalletInfo();
            }

            console.log('Requesting wallet connection...');
            await this.provider.connect();
            console.log('Wallet connected successfully');

            return await this.getWalletInfo();
        } catch (error) {
            console.error('Wallet connection failed:', error);
            throw error;
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
            if (!this.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const publicKey = this.provider.publicKey.toString();
            console.log('Getting wallet info for:', publicKey);

            const balance = await this.connection.getBalance(this.provider.publicKey);
            const solBalance = balance / 1e9; // Convert lamports to SOL

            console.log('Wallet info retrieved:', {
                publicKey,
                balance: solBalance
            });

            return {
                publicKey,
                balance: solBalance,
                network: 'mainnet-beta'
            };
        } catch (error) {
            console.error('Failed to get wallet info:', error);
            throw error;
        }
    }

    async getTokenBalance(tokenMint) {
        try {
            if (!this.provider?.publicKey) {
                throw new Error('Wallet not connected');
            }

            const tokenAccounts = await this.connection.getParsedTokenAccountsByOwner(
                this.provider.publicKey,
                { mint: new solanaWeb3.PublicKey(tokenMint) }
            );

            let balance = 0;
            if (tokenAccounts.value.length > 0) {
                balance = tokenAccounts.value[0].account.data.parsed.info.tokenAmount.uiAmount;
            }

            return balance;
        } catch (error) {
            console.error(`Failed to get token balance for ${tokenMint}:`, error);
            throw error;
        }
    }

    onTokenBalanceChange(tokenMint, handler) {
        if (!this._tokenBalanceHandlers.has(tokenMint)) {
            this._tokenBalanceHandlers.set(tokenMint, []);
        }
        this._tokenBalanceHandlers.get(tokenMint).push(handler);
    }

    async updateTokenBalance(tokenMint) {
        try {
            const balance = await this.getTokenBalance(tokenMint);
            const handlers = this._tokenBalanceHandlers.get(tokenMint) || [];
            handlers.forEach(handler => handler(balance));
            return balance;
        } catch (error) {
            console.error(`Token balance update failed for ${tokenMint}:`, error);
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
        if (walletManager.jupiter && walletManager.jupiter.TOKENS) {  
            for (const [symbol, mint] of Object.entries(walletManager.jupiter.TOKENS)) {
                try {
                    const balance = await walletManager.getTokenBalance(mint);
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
