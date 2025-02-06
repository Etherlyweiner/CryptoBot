class TradingBot {
    constructor() {
        this.isRunning = false;
        this.positions = new Map();
        this.birdeye = new BirdeyeAPI();
        this.jupiter = new JupiterDEX();
        
        // Trading settings
        this.tradeSize = 0.1; // SOL
        this.maxSlippage = 1; // 1%
        this.profitTarget = 10; // 10%
        this.stopLoss = 5; // 5%
        
        // Opportunity thresholds
        this.minVolume = 10000; // $10k
        this.minLiquidity = 50000; // $50k
        this.minPriceChange = 5; // 5%
    }

    async start() {
        if (this.isRunning) return;
        
        try {
            console.log('Starting trading bot...');
            this.isRunning = true;
            document.getElementById('botStatus').textContent = 'Active';
            document.getElementById('startBot').disabled = true;
            document.getElementById('stopBot').disabled = false;

            // Initialize price monitoring
            await this.birdeye.startMonitoring(10000); // 10s updates
            
            // Subscribe to price updates
            this.birdeye.onPriceUpdate(async (tokens) => {
                if (!this.isRunning) return;
                
                try {
                    // Analyze all tokens for opportunities
                    const allTokens = [...tokens.trending, ...tokens.newLaunches];
                    
                    for (const token of allTokens) {
                        const opportunity = await this.birdeye.analyzeTradingOpportunity(token);
                        
                        if (opportunity.isOpportunity) {
                            await this.evaluateAndTrade(opportunity);
                        }
                    }
                    
                    // Update positions
                    await this.updatePositions();
                    
                } catch (error) {
                    console.error('Error processing price update:', error);
                }
            });

        } catch (error) {
            console.error('Error starting trading bot:', error);
            this.stop();
        }
    }

    stop() {
        console.log('Stopping trading bot...');
        this.isRunning = false;
        document.getElementById('botStatus').textContent = 'Inactive';
        document.getElementById('startBot').disabled = false;
        document.getElementById('stopBot').disabled = true;
    }

    async evaluateAndTrade(opportunity) {
        try {
            // Check if we're already in a position for this token
            if (this.positions.has(opportunity.token)) {
                return;
            }

            // Get quote for the trade
            const quote = await this.jupiter.getQuote(
                this.jupiter.TOKENS.SOL,
                opportunity.token,
                this.tradeSize * 1e9 // Convert SOL to lamports
            );

            // Execute trade if the price impact is acceptable
            if (quote.priceImpactPct <= this.maxSlippage) {
                const result = await this.jupiter.executeSwap(quote);
                
                if (result.success) {
                    // Add position to tracking
                    this.positions.set(opportunity.token, {
                        symbol: opportunity.symbol,
                        entryPrice: opportunity.metrics.price,
                        amount: result.outputAmount,
                        stopLoss: opportunity.metrics.price * (1 - this.stopLoss / 100),
                        takeProfit: opportunity.metrics.price * (1 + this.profitTarget / 100),
                        timestamp: Date.now()
                    });

                    // Update UI
                    this.updatePositionsDisplay();
                    console.log(`Opened position in ${opportunity.symbol}`);
                }
            }

        } catch (error) {
            console.error('Error evaluating trade:', error);
        }
    }

    async updatePositions() {
        for (const [token, position] of this.positions.entries()) {
            try {
                // Get current price
                const price = await this.birdeye.getTokenPrice(token);
                
                // Check stop loss and take profit
                if (price.price <= position.stopLoss || price.price >= position.takeProfit) {
                    // Close position
                    const quote = await this.jupiter.getQuote(
                        token,
                        this.jupiter.TOKENS.SOL,
                        position.amount
                    );

                    const result = await this.jupiter.executeSwap(quote);
                    
                    if (result.success) {
                        // Calculate profit/loss
                        const profitLoss = (result.outputAmount / 1e9) - this.tradeSize;
                        
                        // Update total profit display
                        const totalProfitElement = document.getElementById('totalProfit');
                        const currentProfit = parseFloat(totalProfitElement.textContent);
                        totalProfitElement.textContent = (currentProfit + profitLoss).toFixed(4) + ' SOL';
                        
                        // Remove position
                        this.positions.delete(token);
                        
                        // Update UI
                        this.updatePositionsDisplay();
                        console.log(`Closed position in ${position.symbol} with P/L: ${profitLoss.toFixed(4)} SOL`);
                    }
                }
            } catch (error) {
                console.error('Error updating position:', error);
            }
        }

        // Update active trades count
        document.getElementById('activeTrades').textContent = this.positions.size;
    }

    updatePositionsDisplay() {
        const positionsList = document.getElementById('positionsList');
        positionsList.innerHTML = '';

        for (const [token, position] of this.positions.entries()) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${position.symbol}</td>
                <td>${position.entryPrice.toFixed(8)}</td>
                <td>${position.amount}</td>
                <td>${position.stopLoss.toFixed(8)}</td>
                <td>${position.takeProfit.toFixed(8)}</td>
                <td>
                    <button onclick="tradingBot.closePosition('${token}')">Close</button>
                </td>
            `;
            positionsList.appendChild(row);
        }
    }

    async closePosition(token) {
        try {
            const position = this.positions.get(token);
            if (!position) return;

            const quote = await this.jupiter.getQuote(
                token,
                this.jupiter.TOKENS.SOL,
                position.amount
            );

            const result = await this.jupiter.executeSwap(quote);
            
            if (result.success) {
                // Calculate profit/loss
                const profitLoss = (result.outputAmount / 1e9) - this.tradeSize;
                
                // Update total profit display
                const totalProfitElement = document.getElementById('totalProfit');
                const currentProfit = parseFloat(totalProfitElement.textContent);
                totalProfitElement.textContent = (currentProfit + profitLoss).toFixed(4) + ' SOL';
                
                // Remove position
                this.positions.delete(token);
                
                // Update UI
                this.updatePositionsDisplay();
                console.log(`Manually closed position in ${position.symbol} with P/L: ${profitLoss.toFixed(4)} SOL`);
            }

        } catch (error) {
            console.error('Error closing position:', error);
        }
    }
}
