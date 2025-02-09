// Constants
const JUPITER_API = 'https://quote-api.jup.ag/v6';
const BIRDEYE_API = 'https://public-api.birdeye.so/public';
const RPC_ENDPOINT = 'https://api.mainnet-beta.solana.com';
const SOL_MINT = 'So11111111111111111111111111111111111111112';

// Global state
let wallet = null;
let connection = null;
let isTrading = false;
let tradingInterval = null;
let currentTokenData = null;

// Trading settings
const settings = {
    checkInterval: 30000, // Check price every 30 seconds
    buyThreshold: 5, // Buy if price increases by 5% in last minute
    sellThreshold: -3, // Sell if price drops by 3%
    maxSlippage: 5, // Maximum slippage tolerance
    tradeSize: 0.1, // Trade size in SOL
    stopLoss: -10, // Stop loss percentage
    takeProfit: 20, // Take profit percentage
    maxActiveTokens: 3, // Maximum number of tokens to trade simultaneously
    minLiquidity: 10000, // Minimum liquidity in USD
};

// Price tracking
const priceTracking = {
    tokens: new Map(), // Map of token address to price data
    entryPrices: new Map(), // Entry prices for active trades
};

// Initialize Solana connection
async function initConnection() {
    try {
        connection = new solanaWeb3.Connection(RPC_ENDPOINT);
        console.log('✓ Connected to Solana');
        return true;
    } catch (error) {
        console.error('Failed to connect to Solana:', error);
        return false;
    }
}

// Connect wallet
async function connectWallet() {
    try {
        if (window.solana && window.solana.isPhantom) {
            const response = await window.solana.connect();
            wallet = response.publicKey;
            document.getElementById('wallet-status').textContent = 
                `Wallet: ${wallet.toString().slice(0, 4)}...${wallet.toString().slice(-4)}`;
            document.getElementById('start-bot').disabled = false;
            console.log('✓ Wallet connected:', wallet.toString());
            return true;
        } else {
            alert('Please install Phantom wallet!');
            return false;
        }
    } catch (error) {
        console.error('Failed to connect wallet:', error);
        return false;
    }
}

// Get token price and info
async function getTokenInfo(tokenAddress) {
    try {
        const response = await fetch(`${BIRDEYE_API}/token_info?address=${tokenAddress}`, {
            headers: { 'x-chain': 'solana' }
        });
        const data = await response.json();
        return data.data;
    } catch (error) {
        console.error('Failed to get token info:', error);
        throw error;
    }
}

// Get quote for token swap
async function getQuote(inputMint, outputMint, amount, slippage) {
    try {
        const params = new URLSearchParams({
            inputMint,
            outputMint,
            amount,
            slippageBps: slippage * 100,
            feeBps: 0,
            onlyDirectRoutes: false,
            asLegacyTransaction: false
        });

        const response = await fetch(`${JUPITER_API}/quote?${params}`);
        if (!response.ok) throw new Error('Quote request failed');
        
        return await response.json();
    } catch (error) {
        console.error('Failed to get quote:', error);
        throw error;
    }
}

// Execute token swap
async function executeSwap(route) {
    try {
        const swapResponse = await fetch(`${JUPITER_API}/swap`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                route,
                userPublicKey: wallet.toString(),
                wrapUnwrapSOL: true,
                asLegacyTransaction: false
            })
        });

        if (!swapResponse.ok) throw new Error('Swap request failed');
        
        const swapResult = await swapResponse.json();
        const { swapTransaction } = swapResult;

        // Sign and send transaction
        const tx = solanaWeb3.Transaction.from(Buffer.from(swapTransaction, 'base64'));
        const signature = await window.solana.signAndSendTransaction(tx);
        
        // Add trade to history
        addTradeToHistory({
            type: route.inputMint === SOL_MINT ? 'BUY' : 'SELL',
            amount: route.amount,
            signature,
            tokenAddress: route.inputMint === SOL_MINT ? route.outputMint : route.inputMint
        });

        return signature;
    } catch (error) {
        console.error('Failed to execute swap:', error);
        throw error;
    }
}

// Add trade to history
function addTradeToHistory(trade) {
    const tradesList = document.getElementById('trades-list');
    const tradeItem = document.createElement('div');
    tradeItem.className = 'trade-item';
    
    // Get token info if available
    const tokenInfo = window.tokenDiscovery?.trendingTokens.find(t => t.address === trade.tokenAddress);
    const tokenSymbol = tokenInfo ? tokenInfo.symbol : 'TOKEN';

    tradeItem.innerHTML = `
        <div>${trade.type} ${trade.amount} ${trade.type === 'BUY' ? 'SOL → ' + tokenSymbol : tokenSymbol + ' → SOL'}</div>
        <div><a href="https://solscan.io/tx/${trade.signature}" target="_blank">View on Solscan</a></div>
        <div>Time: ${new Date().toLocaleTimeString()}</div>
    `;
    tradesList.insertBefore(tradeItem, tradesList.firstChild);
}

// Update token price data
async function updateTokenPrice(tokenAddress) {
    try {
        const price = await getTokenInfo(tokenAddress);
        const priceData = priceTracking.tokens.get(tokenAddress) || {
            prices: [],
            lastUpdate: 0
        };

        priceData.prices.push({
            price: price.value,
            timestamp: Date.now()
        });

        // Keep only last hour of price data
        const oneHourAgo = Date.now() - 3600000;
        priceData.prices = priceData.prices.filter(p => p.timestamp > oneHourAgo);
        priceTracking.tokens.set(tokenAddress, priceData);

        return price.value;
    } catch (error) {
        console.error('Failed to update token price:', error);
        throw error;
    }
}

// Check if token meets trading criteria
function meetsTradeConditions(tokenAddress) {
    const priceData = priceTracking.tokens.get(tokenAddress);
    if (!priceData || priceData.prices.length < 2) return false;

    const latestPrice = priceData.prices[priceData.prices.length - 1].price;
    const oldestPrice = priceData.prices[0].price;
    const priceChange = ((latestPrice - oldestPrice) / oldestPrice) * 100;

    // Check if we have an active position
    const entryPrice = priceTracking.entryPrices.get(tokenAddress);
    if (entryPrice) {
        // Check stop loss and take profit
        const currentReturn = ((latestPrice - entryPrice) / entryPrice) * 100;
        if (currentReturn <= settings.stopLoss || currentReturn >= settings.takeProfit) {
            return 'SELL';
        }
    } else if (priceChange >= settings.buyThreshold) {
        return 'BUY';
    }

    return false;
}

// Main trading logic
async function checkAndTrade() {
    try {
        // Get trending tokens from discovery
        const trendingTokens = window.tokenDiscovery?.getTopTokens('trending', 5) || [];
        const newTokens = window.tokenDiscovery?.getTopTokens('new', 5) || [];
        
        // Combine and filter tokens
        const potentialTokens = [...trendingTokens, ...newTokens]
            .filter(token => token.liquidity >= settings.minLiquidity);

        // Update prices for all potential tokens
        for (const token of potentialTokens) {
            await updateTokenPrice(token.address);
            
            // Check trading conditions
            const action = meetsTradeConditions(token.address);
            
            if (action === 'BUY' && priceTracking.entryPrices.size < settings.maxActiveTokens) {
                // Execute buy
                const quote = await getQuote(
                    SOL_MINT,
                    token.address,
                    settings.tradeSize * 1e9,
                    settings.maxSlippage
                );
                const signature = await executeSwap(quote.data);
                
                // Record entry price
                const currentPrice = priceTracking.tokens.get(token.address).prices.slice(-1)[0].price;
                priceTracking.entryPrices.set(token.address, currentPrice);
                
                console.log(`🚀 Bought ${token.symbol || 'token'}: ${signature}`);
            }
            else if (action === 'SELL' && priceTracking.entryPrices.has(token.address)) {
                // Execute sell
                const quote = await getQuote(
                    token.address,
                    SOL_MINT,
                    settings.tradeSize * 1e9,
                    settings.maxSlippage
                );
                const signature = await executeSwap(quote.data);
                
                // Remove entry price
                priceTracking.entryPrices.delete(token.address);
                
                console.log(`🔻 Sold ${token.symbol || 'token'}: ${signature}`);
            }
        }
    } catch (error) {
        console.error('Trading error:', error);
        document.getElementById('error-message').textContent = `Error: ${error.message}`;
    }
}

// Start/Stop trading
function toggleTrading() {
    if (!isTrading) {
        // Start trading
        isTrading = true;
        document.getElementById('start-bot').textContent = 'Stop Bot';
        document.getElementById('bot-status').textContent = 'Bot: Running 🟢';
        
        // Initialize token discovery if not already done
        if (window.tokenDiscovery && !window.tokenDiscovery.lastScanTime) {
            window.tokenDiscovery.initialize();
        }
        
        // Initial check
        checkAndTrade();
        
        // Set up interval for regular checks
        tradingInterval = setInterval(checkAndTrade, settings.checkInterval);
    } else {
        // Stop trading
        isTrading = false;
        clearInterval(tradingInterval);
        document.getElementById('start-bot').textContent = 'Start Bot';
        document.getElementById('bot-status').textContent = 'Bot: Stopped 🔴';
    }
}

// Update settings from UI
function updateSettings() {
    const elements = {
        tradeSize: document.getElementById('trade-size'),
        buyThreshold: document.getElementById('buy-threshold'),
        sellThreshold: document.getElementById('sell-threshold'),
        stopLoss: document.getElementById('stop-loss'),
        takeProfit: document.getElementById('take-profit')
    };

    settings.tradeSize = parseFloat(elements.tradeSize.value) || settings.tradeSize;
    settings.buyThreshold = parseFloat(elements.buyThreshold.value) || settings.buyThreshold;
    settings.sellThreshold = parseFloat(elements.sellThreshold.value) || settings.sellThreshold;
    settings.stopLoss = parseFloat(elements.stopLoss.value) || settings.stopLoss;
    settings.takeProfit = parseFloat(elements.takeProfit.value) || settings.takeProfit;
}

// Initialize app
async function init() {
    if (await initConnection()) {
        // Add event listeners
        document.getElementById('connect-wallet').addEventListener('click', connectWallet);
        document.getElementById('start-bot').addEventListener('click', toggleTrading);
        
        // Add settings listeners
        document.querySelectorAll('.settings input').forEach(input => {
            input.addEventListener('change', updateSettings);
        });
    }
}

// Start the app
init();

class TradingBot {
    constructor() {
        this.isRunning = false;
        this.connection = null;
        this.wallet = null;
        this.currentToken = null;
        this.entryPrice = null;
        this.lastPrice = null;
        this.tradeHistory = [];
        this.settings = {
            tradeSize: 0.1,
            buyThreshold: 5,
            sellThreshold: -3,
            stopLoss: -10,
            takeProfit: 20
        };
    }

    async initialize() {
        try {
            this.connection = new solanaWeb3.Connection(RPC_ENDPOINT);
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
            document.getElementById('wallet-status').textContent = 'Wallet: Connected';
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
                await new Promise(resolve => setTimeout(resolve, 30000)); // Check every 30 seconds
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
                mint: new solanaWeb3.PublicKey(tokenAddress)
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

// Initialize trading bot
window.tradingBot = new TradingBot();
window.tradingBot.initialize();
