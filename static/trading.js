// Trading Logic
const { JUPITER_API, RPC_ENDPOINTS, SOL_MINT } = window.CONSTANTS || {};

if (!JUPITER_API || !RPC_ENDPOINTS || !SOL_MINT) {
    console.error('Required constants are not defined. Make sure constants are loaded before this script.');
}

// Trading bot logger
class Logger {
    static log(type, message, data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            type,
            message,
            data
        };
        
        // Log to console with color
        const colors = {
            INFO: '#4CAF50',
            ERROR: '#f44336',
            TRADE: '#2196F3',
            PRICE: '#FF9800'
        };
        
        console.log(
            `%c[${type}] ${timestamp}\n${message}`,
            `color: ${colors[type] || '#fff'}`,
            data ? data : ''
        );

        // Store in log history
        if (!window.botLogs) window.botLogs = [];
        window.botLogs.push(logEntry);
        
        // Update UI if log container exists
        const logContainer = document.getElementById('bot-logs');
        if (logContainer) {
            const logElement = document.createElement('div');
            logElement.className = `log-entry ${type.toLowerCase()}`;
            logElement.innerHTML = `
                <span class="timestamp">${new Date(timestamp).toLocaleTimeString()}</span>
                <span class="type">${type}</span>
                <span class="message">${message}</span>
                ${data ? `<pre class="data">${JSON.stringify(data, null, 2)}</pre>` : ''}
            `;
            logContainer.insertBefore(logElement, logContainer.firstChild);
            
            // Keep only last 100 logs in UI
            if (logContainer.children.length > 100) {
                logContainer.removeChild(logContainer.lastChild);
            }
        }
    }
}

class TradingBot {
    constructor() {
        this.isRunning = false;
        this.connection = null;
        this.currentRpcIndex = 0;
        this.wallet = null;
        this.currentToken = null;
        this.entryPrice = null;
        this.lastPrice = null;
        this.tradeHistory = [];
        
        // Trading settings
        this.settings = {
            checkInterval: 30000,
            buyThreshold: 5,
            sellThreshold: -3,
            maxSlippage: 5,
            tradeSize: 0.1,
            stopLoss: -10,
            takeProfit: 20,
            maxActiveTokens: 3
        };

        // Price tracking
        this.priceTracking = {
            tokens: new Map(),
            entryPrices: new Map()
        };

        // RPC connection options
        this.rpcOptions = {
            commitment: 'confirmed',
            httpHeaders: {
                'Origin': window.location.origin
            },
            fetch: window.fetch,
            confirmTransactionInitialTimeout: 60000,
            disableRetryOnRateLimit: false
        };
    }

    async initialize() {
        try {
            if (!window.solanaWeb3) {
                Logger.log('ERROR', 'Solana Web3 not loaded');
                return;
            }
            
            await this.initializeConnection();
            this.loadSettings();
            this.setupEventListeners();
            Logger.log('INFO', 'Trading bot initialized', this.settings);
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize trading bot', error);
        }
    }

    async initializeConnection() {
        for (let i = 0; i < RPC_ENDPOINTS.length; i++) {
            try {
                const endpoint = RPC_ENDPOINTS[i];
                this.connection = new window.solanaWeb3.Connection(endpoint, {
                    commitment: 'confirmed',
                    httpHeaders: {
                        'Origin': window.location.origin
                    },
                    fetch: window.fetch,
                    confirmTransactionInitialTimeout: 60000,
                    disableRetryOnRateLimit: false
                });
                
                // Test the connection with retries
                let retries = 3;
                while (retries > 0) {
                    try {
                        await this.connection.getSlot();
                        this.currentRpcIndex = i;
                        Logger.log('INFO', 'Connected to Solana network', { endpoint });
                        return;
                    } catch (error) {
                        retries--;
                        if (retries === 0) throw error;
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
            } catch (error) {
                Logger.log('ERROR', `Failed to connect to RPC endpoint: ${RPC_ENDPOINTS[i]}`, error);
                continue;
            }
        }
        throw new Error('All RPC endpoints failed');
    }

    async fallbackToNextRpc() {
        const nextIndex = (this.currentRpcIndex + 1) % RPC_ENDPOINTS.length;
        try {
            const endpoint = RPC_ENDPOINTS[nextIndex];
            this.connection = new window.solanaWeb3.Connection(endpoint, {
                commitment: 'confirmed',
                httpHeaders: {
                    'Origin': window.location.origin
                },
                fetch: window.fetch,
                confirmTransactionInitialTimeout: 60000,
                disableRetryOnRateLimit: false
            });
            
            // Test the connection
            await this.connection.getSlot();
            
            this.currentRpcIndex = nextIndex;
            Logger.log('INFO', 'Switched to fallback RPC endpoint', { endpoint });
            return true;
        } catch (error) {
            Logger.log('ERROR', `Failed to switch to RPC endpoint: ${RPC_ENDPOINTS[nextIndex]}`, error);
            return false;
        }
    }

    async executeWithRpcFallback(operation) {
        const maxRetries = RPC_ENDPOINTS.length;
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await operation();
            } catch (error) {
                if (error.message.includes('403') || error.message.includes('429') || error.message.includes('timeout')) {
                    Logger.log('INFO', 'RPC error, attempting fallback', { error: error.message });
                    const success = await this.fallbackToNextRpc();
                    if (!success) {
                        throw new Error('All RPC endpoints failed');
                    }
                    continue;
                }
                throw error;
            }
        }
        throw new Error('Operation failed after all RPC retries');
    }

    async getSOLBalance() {
        return this.executeWithRpcFallback(async () => {
            const balance = await this.connection.getBalance(this.wallet);
            return balance / 1e9;
        });
    }

    loadSettings() {
        const elements = ['trade-size', 'buy-threshold', 'sell-threshold', 'stop-loss', 'take-profit'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                const key = id.replace(/-./g, x => x[1].toUpperCase());
                this.settings[key] = parseFloat(element.value);
            }
        });
        Logger.log('INFO', 'Settings loaded', this.settings);
    }

    setupEventListeners() {
        // Connect wallet button
        const connectButton = document.getElementById('connect-wallet');
        if (connectButton) {
            connectButton.addEventListener('click', () => this.connectWallet());
        }

        // Start/Stop bot button
        const startButton = document.getElementById('start-bot');
        if (startButton) {
            startButton.addEventListener('click', () => {
                if (this.isRunning) {
                    this.stop();
                    startButton.textContent = 'Start Bot';
                } else {
                    this.start();
                    startButton.textContent = 'Stop Bot';
                }
            });
        }

        // Settings inputs
        const elements = ['trade-size', 'buy-threshold', 'sell-threshold', 'stop-loss', 'take-profit'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => {
                    const key = id.replace(/-./g, x => x[1].toUpperCase());
                    this.settings[key] = parseFloat(element.value);
                    Logger.log('INFO', 'Setting updated', { [key]: this.settings[key] });
                });
            }
        });

        Logger.log('INFO', 'Event listeners set up');
    }

    async connectWallet() {
        try {
            if (!window.solana || !window.solana.isPhantom) {
                throw new Error('Phantom wallet is not installed');
            }

            const resp = await window.solana.connect();
            this.wallet = resp.publicKey;
            Logger.log('INFO', 'Wallet connected', {
                address: this.wallet.toString(),
                balance: await this.getSOLBalance()
            });
            
            document.getElementById('wallet-status').textContent = 
                `Wallet: ${this.wallet.toString().slice(0, 4)}...${this.wallet.toString().slice(-4)}`;
            document.getElementById('start-bot').disabled = false;
            
        } catch (error) {
            Logger.log('ERROR', 'Failed to connect wallet', error);
            document.getElementById('wallet-status').textContent = 'Wallet: Error';
        }
    }

    async start() {
        if (!this.wallet) {
            Logger.log('ERROR', 'Please connect wallet first');
            return;
        }

        this.isRunning = true;
        document.getElementById('bot-status').textContent = 'Bot: Running';
        Logger.log('INFO', 'Trading bot started', {
            wallet: this.wallet.toString(),
            settings: this.settings
        });
        
        // Start monitoring loop
        this.monitoringLoop();
    }

    stop() {
        this.isRunning = false;
        document.getElementById('bot-status').textContent = 'Bot: Stopped';
        Logger.log('INFO', 'Trading bot stopped');
    }

    async monitoringLoop() {
        while (this.isRunning) {
            try {
                await this.checkPriceAndTrade();
                await new Promise(resolve => setTimeout(resolve, this.settings.checkInterval));
            } catch (error) {
                Logger.log('ERROR', 'Error in monitoring loop', error);
            }
        }
    }

    async checkPriceAndTrade() {
        const tokenAddress = document.getElementById('token-address').value;
        if (!tokenAddress) return;

        try {
            const price = await this.getTokenPrice(tokenAddress);
            if (!price) return;

            Logger.log('PRICE', `Token ${tokenAddress} price: ${price} SOL`);
            this.lastPrice = price;

            if (!this.currentToken) {
                if (this.shouldBuy(price)) {
                    Logger.log('TRADE', 'Buy signal detected', {
                        token: tokenAddress,
                        price,
                        reason: 'Price increase above threshold'
                    });
                    await this.executeBuy(tokenAddress, price);
                }
            } else if (this.currentToken === tokenAddress) {
                if (this.shouldSell(price)) {
                    Logger.log('TRADE', 'Sell signal detected', {
                        token: tokenAddress,
                        price,
                        entryPrice: this.entryPrice,
                        profit: ((price - this.entryPrice) / this.entryPrice) * 100
                    });
                    await this.executeSell(tokenAddress, price);
                }
            }

        } catch (error) {
            Logger.log('ERROR', 'Error checking price and trading', error);
        }
    }

    async getTokenPrice(tokenAddress) {
        if (!JUPITER_API) {
            Logger.log('ERROR', 'JUPITER_API constant is not defined');
            return null;
        }

        try {
            const response = await fetch(`${JUPITER_API}/price?ids=${tokenAddress}`);
            const data = await response.json();
            return parseFloat(data.data[tokenAddress].price);
        } catch (error) {
            Logger.log('ERROR', 'Error getting token price', error);
            return null;
        }
    }

    shouldBuy(currentPrice) {
        if (!this.lastPrice) return false;
        const priceChange = ((currentPrice - this.lastPrice) / this.lastPrice) * 100;
        const shouldBuy = priceChange >= this.settings.buyThreshold;
        
        if (shouldBuy) {
            Logger.log('INFO', 'Buy condition met', {
                currentPrice,
                lastPrice: this.lastPrice,
                priceChange,
                threshold: this.settings.buyThreshold
            });
        }
        
        return shouldBuy;
    }

    shouldSell(currentPrice) {
        if (!this.entryPrice) return false;
        
        const priceChange = ((currentPrice - this.entryPrice) / this.entryPrice) * 100;
        
        // Check stop loss
        if (priceChange <= this.settings.stopLoss) {
            Logger.log('TRADE', 'Stop loss triggered', {
                currentPrice,
                entryPrice: this.entryPrice,
                loss: priceChange
            });
            return true;
        }
        
        // Check take profit
        if (priceChange >= this.settings.takeProfit) {
            Logger.log('TRADE', 'Take profit triggered', {
                currentPrice,
                entryPrice: this.entryPrice,
                profit: priceChange
            });
            return true;
        }
        
        // Check sell threshold
        if (priceChange <= this.settings.sellThreshold) {
            Logger.log('TRADE', 'Sell threshold triggered', {
                currentPrice,
                entryPrice: this.entryPrice,
                priceChange
            });
            return true;
        }
        
        return false;
    }

    async executeBuy(tokenAddress, price) {
        try {
            const amountInSol = this.settings.tradeSize;
            Logger.log('TRADE', 'Executing buy order', {
                token: tokenAddress,
                amount: amountInSol,
                price
            });
            
            // Get Jupiter quote
            const quote = await this.getJupiterQuote(SOL_MINT, tokenAddress, amountInSol);
            if (!quote) return;

            // Execute swap through Phantom
            const txid = await this.executeJupiterSwap(quote);
            if (!txid) return;

            // Update state
            this.currentToken = tokenAddress;
            this.entryPrice = price;

            Logger.log('TRADE', 'Buy order executed', {
                token: tokenAddress,
                amount: amountInSol,
                price,
                txid
            });

            // Log trade
            this.logTrade({
                type: 'BUY',
                token: tokenAddress,
                price: price,
                amount: amountInSol,
                txid: txid
            });

        } catch (error) {
            Logger.log('ERROR', 'Error executing buy', error);
        }
    }

    async executeSell(tokenAddress, price) {
        try {
            // Get token balance
            const balance = await this.getTokenBalance(tokenAddress);
            if (!balance) return;

            Logger.log('TRADE', 'Executing sell order', {
                token: tokenAddress,
                balance,
                price
            });

            // Get Jupiter quote
            const quote = await this.getJupiterQuote(tokenAddress, SOL_MINT, balance);
            if (!quote) return;

            // Execute swap through Phantom
            const txid = await this.executeJupiterSwap(quote);
            if (!txid) return;

            // Update state
            this.currentToken = null;
            this.entryPrice = null;

            Logger.log('TRADE', 'Sell order executed', {
                token: tokenAddress,
                amount: balance,
                price,
                txid
            });

            // Log trade
            this.logTrade({
                type: 'SELL',
                token: tokenAddress,
                price: price,
                amount: balance,
                txid: txid
            });

        } catch (error) {
            Logger.log('ERROR', 'Error executing sell', error);
        }
    }

    async getJupiterQuote(inputMint, outputMint, amount) {
        if (!JUPITER_API) {
            Logger.log('ERROR', 'JUPITER_API constant is not defined');
            return null;
        }

        try {
            const response = await fetch(`${JUPITER_API}/quote?inputMint=${inputMint}&outputMint=${outputMint}&amount=${amount}&slippageBps=50`);
            const quote = await response.json();
            Logger.log('INFO', 'Got Jupiter quote', quote);
            return quote;
        } catch (error) {
            Logger.log('ERROR', 'Error getting Jupiter quote', error);
            return null;
        }
    }

    async executeJupiterSwap(quote) {
        return this.executeWithRpcFallback(async () => {
            const tx = quote.swapTransaction;
            const signedTx = await window.solana.signTransaction(tx);
            const txid = await this.connection.sendRawTransaction(signedTx.serialize());
            await this.connection.confirmTransaction(txid);
            Logger.log('INFO', 'Jupiter swap executed', { txid });
            return txid;
        });
    }

    async getTokenBalance(tokenAddress) {
        return this.executeWithRpcFallback(async () => {
            const response = await this.connection.getTokenAccountsByOwner(this.wallet, {
                mint: new window.solanaWeb3.PublicKey(tokenAddress)
            });
            if (response.value.length === 0) return 0;
            const balance = await this.connection.getTokenAccountBalance(response.value[0].pubkey);
            Logger.log('INFO', 'Got token balance', {
                token: tokenAddress,
                balance: balance.value.amount
            });
            return parseFloat(balance.value.amount);
        });
    }

    logTrade(trade) {
        this.tradeHistory.push({
            ...trade,
            timestamp: new Date().toISOString()
        });

        Logger.log('TRADE', `${trade.type} trade logged`, trade);
        this.updateTradeHistory();
    }

    updateTradeHistory() {
        const tradesList = document.getElementById('trades-list');
        if (!tradesList) return;

        const trades = this.tradeHistory.slice().reverse();
        tradesList.innerHTML = trades.map(trade => `
            <div class="trade-item">
                <div>${trade.type} ${trade.token.slice(0, 4)}...${trade.token.slice(-4)}</div>
                <div>Price: ${trade.price.toFixed(6)} SOL</div>
                <div>Amount: ${trade.amount.toFixed(6)}</div>
                <div>Time: ${new Date(trade.timestamp).toLocaleString()}</div>
                <div>
                    <a href="https://solscan.io/tx/${trade.txid}" target="_blank">
                        View Transaction
                    </a>
                </div>
            </div>
        `).join('');
    }
}

// Initialize trading bot after page load
document.addEventListener('DOMContentLoaded', () => {
    window.tradingBot = new TradingBot();
    window.tradingBot.initialize();
});
