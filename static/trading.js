// Trading Logic and State Management
class TradingBot {
    constructor() {
        // Core state
        this.state = {
            isRunning: false,
            wallet: null,
            connection: null,
            currentRpcIndex: 0
        };

        // Trading state
        this.trades = {
            active: new Map(),
            history: [],
            lastUpdate: null
        };

        // Settings with defaults
        this.settings = {
            checkInterval: 30000,
            buyThreshold: 5,
            sellThreshold: -3,
            maxSlippage: 5,
            tradeSize: 0.1,
            stopLoss: -10,
            takeProfit: 20,
            maxActiveTokens: 3,
            retryAttempts: 3,
            retryDelay: 1000
        };

        // Cache for performance
        this.cache = {
            prices: new Map(),
            balances: new Map(),
            lastPriceCheck: null,
            priceValidityDuration: 30000 // 30 seconds
        };

        // Initialize connection options
        this.rpcOptions = {
            commitment: 'confirmed',
            httpHeaders: {
                'x-api-key': window.CONSTANTS.HELIUS_API_KEY
            },
            confirmTransactionInitialTimeout: 60000,
            disableRetryOnRateLimit: false
        };

        // Bind methods for event listeners
        this.handleWalletConnect = this.handleWalletConnect.bind(this);
        this.handleWalletDisconnect = this.handleWalletDisconnect.bind(this);
        this.handleSettingsChange = this.handleSettingsChange.bind(this);
    }

    async initialize() {
        try {
            if (!window.solanaWeb3) {
                throw new Error('Solana Web3 not loaded');
            }

            // Initialize RPC manager first
            if (!await window.rpcManager.initialize()) {
                throw new Error('Failed to initialize RPC connections');
            }

            // Get initial connection
            this.state.connection = window.rpcManager.getCurrentConnection();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Load saved settings
            this.loadSettings();
            
            // Auto-connect if wallet was previously connected
            if (window.solana?.isPhantom) {
                const connected = await window.solana.isConnected;
                if (connected) {
                    await this.handleWalletConnect(true);
                }
            }

            Logger.log('INFO', 'Trading bot initialized', this.settings);
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize trading bot', error);
            throw error;
        }
    }

    async executeWithRetry(operation, maxRetries = 3, delay = 1000) {
        let lastError;
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                // Update connection before each attempt
                this.state.connection = window.rpcManager.getCurrentConnection();
                return await operation();
            } catch (error) {
                lastError = error;
                if (attempt < maxRetries) {
                    await new Promise(resolve => setTimeout(resolve, delay));
                    Logger.log('INFO', `Retry attempt ${attempt}/${maxRetries}`, { error: error.message });
                }
            }
        }
        throw lastError;
    }

    setupEventListeners() {
        // Wallet events
        const connectBtn = document.getElementById('connect-wallet');
        connectBtn?.addEventListener('click', () => this.handleWalletConnect());

        // Bot control events
        const startBtn = document.getElementById('start-bot');
        startBtn?.addEventListener('click', () => {
            if (this.state.isRunning) {
                this.stop();
                startBtn.textContent = 'Start Bot';
            } else {
                this.start();
                startBtn.textContent = 'Stop Bot';
            }
        });

        // Settings events
        const settingsInputs = ['trade-size', 'buy-threshold', 'sell-threshold', 'stop-loss', 'take-profit'];
        settingsInputs.forEach(id => {
            const element = document.getElementById(id);
            element?.addEventListener('change', this.handleSettingsChange);
        });

        // Wallet connection events
        if (window.solana) {
            window.solana.on('disconnect', this.handleWalletDisconnect);
            window.solana.on('accountChanged', this.handleWalletConnect);
        }
    }

    async handleWalletConnect(silent = false) {
        try {
            if (!window.solana?.isPhantom) {
                throw new Error('Phantom wallet not installed');
            }

            let resp;
            if (silent) {
                try {
                    resp = await window.solana.connect({ onlyIfTrusted: true });
                } catch {
                    return; // Not previously connected
                }
            } else {
                resp = await window.solana.connect();
            }

            this.state.wallet = resp.publicKey;
            
            // Verify connection with balance check
            const balance = await this.getSOLBalance();
            
            this.updateWalletUI(true, balance);
            Logger.log('INFO', 'Wallet connected', {
                address: this.state.wallet.toString(),
                balance
            });
        } catch (error) {
            this.updateWalletUI(false);
            Logger.log('ERROR', 'Failed to connect wallet', error);
            throw error;
        }
    }

    handleWalletDisconnect() {
        this.state.wallet = null;
        this.updateWalletUI(false);
        if (this.state.isRunning) {
            this.stop();
        }
        Logger.log('INFO', 'Wallet disconnected');
    }

    updateWalletUI(connected, balance = null) {
        const statusEl = document.getElementById('wallet-status');
        const startBtn = document.getElementById('start-bot');
        
        if (connected && this.state.wallet) {
            const address = this.state.wallet.toString();
            statusEl.textContent = `Wallet: ${address.slice(0, 4)}...${address.slice(-4)}`;
            if (balance !== null) {
                statusEl.textContent += ` (${balance.toFixed(4)} SOL)`;
            }
            startBtn.disabled = false;
        } else {
            statusEl.textContent = 'Wallet: Not Connected';
            startBtn.disabled = true;
        }
    }

    handleSettingsChange(event) {
        const key = event.target.id.replace(/-./g, x => x[1].toUpperCase());
        const value = parseFloat(event.target.value);
        if (!isNaN(value)) {
            this.settings[key] = value;
            Logger.log('INFO', 'Setting updated', { [key]: value });
        }
    }

    loadSettings() {
        const elements = ['trade-size', 'buy-threshold', 'sell-threshold', 'stop-loss', 'take-profit'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                const key = id.replace(/-./g, x => x[1].toUpperCase());
                const value = parseFloat(element.value);
                if (!isNaN(value)) {
                    this.settings[key] = value;
                }
            }
        });
    }

    async start() {
        if (!this.state.wallet) {
            Logger.log('ERROR', 'Please connect wallet first');
            return;
        }

        this.state.isRunning = true;
        document.getElementById('bot-status').textContent = 'Bot: Running';
        Logger.log('INFO', 'Trading bot started', {
            wallet: this.state.wallet.toString(),
            settings: this.settings
        });
        
        this.monitoringLoop();
    }

    stop() {
        this.state.isRunning = false;
        document.getElementById('bot-status').textContent = 'Bot: Stopped';
        Logger.log('INFO', 'Trading bot stopped');
    }

    async monitoringLoop() {
        while (this.state.isRunning) {
            try {
                await this.checkPriceAndTrade();
                await new Promise(resolve => setTimeout(resolve, this.settings.checkInterval));
            } catch (error) {
                Logger.log('ERROR', 'Error in monitoring loop', error);
                // Don't stop the bot on error, just continue
            }
        }
    }

    async getSOLBalance() {
        return this.executeWithRetry(async () => {
            const balance = await this.state.connection.getBalance(this.state.wallet);
            return balance / 1e9;
        });
    }
}

// Initialize trading bot
document.addEventListener('DOMContentLoaded', () => {
    window.tradingBot = new TradingBot();
    window.tradingBot.initialize().catch(console.error);
});
