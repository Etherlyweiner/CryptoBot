class TradingBot {
    constructor() {
        this.active = false;
        this.minLiquidity = 50000;  // $50k minimum liquidity
        this.minVolume = 10000;     // $10k minimum 24h volume
        this.maxSlippage = 1.0;     // 1% max slippage
        this.profitTarget = 5.0;    // 5% profit target
        this.stopLoss = -2.0;       // 2% stop loss
        this.tradeSize = 0.1;       // 0.1 SOL per trade
        this.positions = new Map();
        this.tradingInterval = null;
    }

    async start() {
        if (this.active) return;
        this.active = true;
        console.log('Trading bot started');
        this.tradingInterval = setInterval(() => this.checkTradingOpportunities(), 30000); // Check every 30 seconds
    }

    stop() {
        if (!this.active) return;
        this.active = false;
        if (this.tradingInterval) {
            clearInterval(this.tradingInterval);
            this.tradingInterval = null;
        }
        console.log('Trading bot stopped');
    }

    async checkTradingOpportunities() {
        if (!this.active || !walletManager.isConnected()) return;

        try {
            // Get trending tokens
            const trending = await dexscreener.getTrendingTokens();
            
            // Filter for potential opportunities
            const opportunities = trending.filter(token => 
                token.liquidity >= this.minLiquidity &&
                token.volume24h >= this.minVolume &&
                !this.positions.has(token.address)
            );

            for (const token of opportunities) {
                try {
                    // Get detailed metrics
                    const metrics = await dexscreener.getTokenMetrics(token.address);
                    
                    // Check if token meets our criteria
                    if (this.shouldTrade(metrics)) {
                        await this.executeTrade(token);
                    }
                } catch (error) {
                    console.warn(`Error analyzing ${token.symbol}:`, error);
                }
            }

            // Monitor existing positions
            await this.monitorPositions();

        } catch (error) {
            console.error('Error checking trading opportunities:', error);
        }
    }

    shouldTrade(metrics) {
        return metrics.liquidity >= this.minLiquidity &&
               metrics.volume24h >= this.minVolume &&
               Math.abs(metrics.priceChange24h) <= 30; // Avoid extremely volatile tokens
    }

    async executeTrade(token) {
        try {
            console.log(`Attempting to trade ${token.symbol}`);
            
            // Get quote from Jupiter
            const quote = await jupiter.getQuote(
                jupiter.TOKENS.SOL,
                token.address,
                this.tradeSize * 1e9, // Convert to lamports
                this.maxSlippage * 100 // Convert to basis points
            );

            if (!quote || !quote.data) {
                throw new Error('Failed to get quote');
            }

            // Execute swap
            const result = await jupiter.executeSwap(quote.data);
            
            if (result.success) {
                // Record the position
                this.positions.set(token.address, {
                    symbol: token.symbol,
                    entryPrice: token.price,
                    amount: quote.data.outAmount,
                    timestamp: Date.now()
                });
                
                console.log(`Successfully bought ${token.symbol}`);
                this.notifyTrade('buy', token, quote.data);
            }

        } catch (error) {
            console.error(`Failed to execute trade for ${token.symbol}:`, error);
        }
    }

    async monitorPositions() {
        for (const [address, position] of this.positions) {
            try {
                const metrics = await dexscreener.getTokenMetrics(address);
                const profitLoss = ((metrics.price - position.entryPrice) / position.entryPrice) * 100;

                // Check if we should sell
                if (profitLoss >= this.profitTarget || profitLoss <= this.stopLoss) {
                    await this.closePosition(address, position, metrics);
                }

            } catch (error) {
                console.warn(`Error monitoring position ${position.symbol}:`, error);
            }
        }
    }

    async closePosition(address, position, metrics) {
        try {
            console.log(`Attempting to sell ${position.symbol}`);
            
            // Get quote for selling back to SOL
            const quote = await jupiter.getQuote(
                address,
                jupiter.TOKENS.SOL,
                position.amount,
                this.maxSlippage * 100
            );

            if (!quote || !quote.data) {
                throw new Error('Failed to get quote');
            }

            // Execute swap
            const result = await jupiter.executeSwap(quote.data);
            
            if (result.success) {
                this.positions.delete(address);
                console.log(`Successfully sold ${position.symbol}`);
                this.notifyTrade('sell', { symbol: position.symbol, price: metrics.price }, quote.data);
            }

        } catch (error) {
            console.error(`Failed to close position for ${position.symbol}:`, error);
        }
    }

    notifyTrade(type, token, quoteData) {
        const message = {
            type,
            symbol: token.symbol,
            price: token.price,
            amount: type === 'buy' ? quoteData.outAmount : quoteData.inAmount,
            timestamp: new Date().toISOString()
        };

        // Update UI
        const statusDiv = document.getElementById('status');
        statusDiv.style.display = 'block';
        statusDiv.className = 'status success';
        statusDiv.innerHTML = `
            <h3>✅ ${type.toUpperCase()} Order Executed</h3>
            <p>Symbol: ${message.symbol}</p>
            <p>Price: $${message.price.toFixed(6)}</p>
            <p>Amount: ${(message.amount / 1e9).toFixed(4)} ${type === 'buy' ? token.symbol : 'SOL'}</p>
        `;
    }
}

// Initialize trading bot
const tradingBot = new TradingBot();
