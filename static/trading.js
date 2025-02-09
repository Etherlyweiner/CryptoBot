// Trading Logic
const { JUPITER_API, RPC_ENDPOINT, SOL_MINT } = window.CONSTANTS || {};

if (!JUPITER_API || !RPC_ENDPOINT || !SOL_MINT) {
    console.error('Required constants are not defined. Make sure constants are loaded before this script.');
}

class TradingBot {
    constructor() {
        this.isRunning = false;
        this.connection = null;
        this.wallet = null;
        this.currentToken = null;
        this.entryPrice = null;
        this.lastPrice = null;
        this.tradeHistory = [];
        
        // Trading settings
        this.settings = {
            checkInterval: 30000, // Check price every 30 seconds
            buyThreshold: 5, // Buy if price increases by 5%
            sellThreshold: -3, // Sell if price drops by 3%
            maxSlippage: 5, // Maximum slippage tolerance
            tradeSize: 0.1, // Trade size in SOL
            stopLoss: -10, // Stop loss percentage
            takeProfit: 20, // Take profit percentage
            maxActiveTokens: 3 // Maximum number of tokens to trade simultaneously
        };

        // Price tracking
        this.priceTracking = {
            tokens: new Map(), // Map of token address to price data
            entryPrices: new Map() // Entry prices for active trades
        };
    }

    async initialize() {
        try {
            if (!window.solanaWeb3) {
                console.error('Solana Web3 not loaded');
                return;
            }
            
            this.connection = new window.solanaWeb3.Connection(RPC_ENDPOINT);
            console.log('Connected to Solana network');
            this.loadSettings();
            this.setupEventListeners();
        } catch (error) {
            console.error('Failed to initialize trading bot:', error);
        }
    }

    loadSettings() {
        // Load settings from UI
        const elements = ['trade-size', 'buy-threshold', 'sell-threshold', 'stop-loss', 'take-profit'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                const key = id.replace(/-./g, x => x[1].toUpperCase());
                this.settings[key] = parseFloat(element.value);
            }
        });
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
                });
            }
        });
    }

    async connectWallet() {
        try {
            if (!window.solana || !window.solana.isPhantom) {
                throw new Error('Phantom wallet is not installed');
            }

            const resp = await window.solana.connect();
            this.wallet = resp.publicKey;
            console.log('Wallet connected:', this.wallet.toString());
            
            // Update UI
            document.getElementById('wallet-status').textContent = 
                `Wallet: ${this.wallet.toString().slice(0, 4)}...${this.wallet.toString().slice(-4)}`;
            document.getElementById('start-bot').disabled = false;
            
        } catch (error) {
            console.error('Failed to connect wallet:', error);
            document.getElementById('wallet-status').textContent = 'Wallet: Error';
        }
    }

    async start() {
        if (!this.wallet) {
            console.error('Please connect wallet first');
            return;
        }

        this.isRunning = true;
        document.getElementById('bot-status').textContent = 'Bot: Running';
        
        // Start monitoring loop
        this.monitoringLoop();
    }

    stop() {
        this.isRunning = false;
        document.getElementById('bot-status').textContent = 'Bot: Stopped';
    }

    async monitoringLoop() {
        while (this.isRunning) {
            try {
                await this.checkPriceAndTrade();
                await new Promise(resolve => setTimeout(resolve, this.settings.checkInterval));
            } catch (error) {
                console.error('Error in monitoring loop:', error);
            }
        }
    }

    async checkPriceAndTrade() {
        const tokenAddress = document.getElementById('token-address').value;
        if (!tokenAddress) return;

        try {
            // Get current price from Jupiter
            const price = await this.getTokenPrice(tokenAddress);
            if (!price) return;

            this.lastPrice = price;

            // If we don't have a position, check for buy opportunity
            if (!this.currentToken) {
                if (this.shouldBuy(price)) {
                    await this.executeBuy(tokenAddress, price);
                }
            }
            // If we have a position, check for sell conditions
            else if (this.currentToken === tokenAddress) {
                if (this.shouldSell(price)) {
                    await this.executeSell(tokenAddress, price);
                }
            }

        } catch (error) {
            console.error('Error checking price and trading:', error);
        }
    }

    async getTokenPrice(tokenAddress) {
        if (!JUPITER_API) {
            console.error('JUPITER_API constant is not defined');
            return null;
        }

        try {
            const response = await fetch(`${JUPITER_API}/price?ids=${tokenAddress}`);
            const data = await response.json();
            return parseFloat(data.data[tokenAddress].price);
        } catch (error) {
            console.error('Error getting token price:', error);
            return null;
        }
    }

    shouldBuy(currentPrice) {
        if (!this.lastPrice) return false;
        const priceChange = ((currentPrice - this.lastPrice) / this.lastPrice) * 100;
        return priceChange >= this.settings.buyThreshold;
    }

    shouldSell(currentPrice) {
        if (!this.entryPrice) return false;
        
        const priceChange = ((currentPrice - this.entryPrice) / this.entryPrice) * 100;
        
        // Check stop loss
        if (priceChange <= this.settings.stopLoss) {
            console.log('Stop loss triggered');
            return true;
        }
        
        // Check take profit
        if (priceChange >= this.settings.takeProfit) {
            console.log('Take profit triggered');
            return true;
        }
        
        // Check sell threshold
        if (priceChange <= this.settings.sellThreshold) {
            console.log('Sell threshold triggered');
            return true;
        }
        
        return false;
    }

    async executeBuy(tokenAddress, price) {
        try {
            const amountInSol = this.settings.tradeSize;
            
            // Get Jupiter quote
            const quote = await this.getJupiterQuote(SOL_MINT, tokenAddress, amountInSol);
            if (!quote) return;

            // Execute swap through Phantom
            const txid = await this.executeJupiterSwap(quote);
            if (!txid) return;

            // Update state
            this.currentToken = tokenAddress;
            this.entryPrice = price;

            // Log trade
            this.logTrade({
                type: 'BUY',
                token: tokenAddress,
                price: price,
                amount: amountInSol,
                txid: txid
            });

        } catch (error) {
            console.error('Error executing buy:', error);
        }
    }

    async executeSell(tokenAddress, price) {
        try {
            // Get token balance
            const balance = await this.getTokenBalance(tokenAddress);
            if (!balance) return;

            // Get Jupiter quote
            const quote = await this.getJupiterQuote(tokenAddress, SOL_MINT, balance);
            if (!quote) return;

            // Execute swap through Phantom
            const txid = await this.executeJupiterSwap(quote);
            if (!txid) return;

            // Update state
            this.currentToken = null;
            this.entryPrice = null;

            // Log trade
            this.logTrade({
                type: 'SELL',
                token: tokenAddress,
                price: price,
                amount: balance,
                txid: txid
            });

        } catch (error) {
            console.error('Error executing sell:', error);
        }
    }

    async getJupiterQuote(inputMint, outputMint, amount) {
        if (!JUPITER_API) {
            console.error('JUPITER_API constant is not defined');
            return null;
        }

        try {
            const response = await fetch(`${JUPITER_API}/quote?inputMint=${inputMint}&outputMint=${outputMint}&amount=${amount}&slippageBps=50`);
            return await response.json();
        } catch (error) {
            console.error('Error getting Jupiter quote:', error);
            return null;
        }
    }

    async executeJupiterSwap(quote) {
        try {
            // Send transaction through Phantom
            const tx = quote.swapTransaction;
            const signedTx = await window.solana.signTransaction(tx);
            const txid = await this.connection.sendRawTransaction(signedTx.serialize());
            await this.connection.confirmTransaction(txid);
            return txid;
        } catch (error) {
            console.error('Error executing Jupiter swap:', error);
            return null;
        }
    }

    async getTokenBalance(tokenAddress) {
        try {
            const response = await this.connection.getTokenAccountsByOwner(this.wallet, {
                mint: new window.solanaWeb3.PublicKey(tokenAddress)
            });
            if (response.value.length === 0) return 0;
            const balance = await this.connection.getTokenAccountBalance(response.value[0].pubkey);
            return parseFloat(balance.value.amount);
        } catch (error) {
            console.error('Error getting token balance:', error);
            return 0;
        }
    }

    logTrade(trade) {
        this.tradeHistory.push({
            ...trade,
            timestamp: new Date().toISOString()
        });

        // Update UI
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
