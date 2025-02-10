/**
 * Tracks and analyzes trading performance.
 */
class Analytics {
    constructor(config) {
        this.config = config;
        this.initialized = false;
        this.logger = new Logger('Analytics');
        
        // Performance metrics
        this.metrics = {
            totalTrades: 0,
            successfulTrades: 0,
            failedTrades: 0,
            totalProfitLoss: 0,
            winRate: 0,
            averageReturn: 0,
            sharpeRatio: 0,
            maxDrawdown: 0
        };
        
        // Trade history
        this.trades = [];
        this.positions = new Map();
        
        // Risk metrics
        this.risk = {
            portfolioValue: 0,
            exposurePercent: 0,
            dailyVolatility: 0,
            valueAtRisk: 0
        };
    }

    /**
     * Initialize analytics.
     */
    async initialize() {
        try {
            this.logger.info('Initializing analytics...');

            // Load historical data if available
            await this.loadHistory();

            this.initialized = true;
            this.logger.info('Analytics initialized');
            return true;

        } catch (error) {
            this.logger.error('Failed to initialize analytics:', error);
            throw error;
        }
    }

    /**
     * Load trading history.
     */
    async loadHistory() {
        try {
            // Load from local storage
            const history = localStorage.getItem('tradingHistory');
            if (history) {
                this.trades = JSON.parse(history);
                this.logger.info(`Loaded ${this.trades.length} historical trades`);
            }

            // Calculate initial metrics
            await this.updateMetrics();

        } catch (error) {
            this.logger.error('Failed to load history:', error);
            throw error;
        }
    }

    /**
     * Record a new trade.
     */
    async recordTrade(trade) {
        try {
            // Add timestamp
            trade.timestamp = Date.now();

            // Calculate profit/loss
            if (trade.exitPrice && trade.entryPrice) {
                const profitLoss = trade.side === 'buy' ?
                    (trade.exitPrice - trade.entryPrice) / trade.entryPrice :
                    (trade.entryPrice - trade.exitPrice) / trade.entryPrice;
                trade.profitLoss = profitLoss * trade.amount;
            }

            // Add to history
            this.trades.push(trade);

            // Update positions
            if (trade.side === 'buy') {
                this.positions.set(trade.token, trade);
            } else {
                this.positions.delete(trade.token);
            }

            // Save to local storage
            localStorage.setItem('tradingHistory', JSON.stringify(this.trades));

            // Update metrics
            await this.updateMetrics();

            this.logger.info('Trade recorded:', trade);

        } catch (error) {
            this.logger.error('Failed to record trade:', error);
            throw error;
        }
    }

    /**
     * Update performance metrics.
     */
    async updateMetrics() {
        try {
            // Basic metrics
            this.metrics.totalTrades = this.trades.length;
            this.metrics.successfulTrades = this.trades.filter(t => t.profitLoss > 0).length;
            this.metrics.failedTrades = this.trades.filter(t => t.profitLoss < 0).length;
            
            // Win rate
            this.metrics.winRate = this.metrics.totalTrades > 0 ?
                this.metrics.successfulTrades / this.metrics.totalTrades : 0;
            
            // Total P/L
            this.metrics.totalProfitLoss = this.trades.reduce((sum, t) => sum + (t.profitLoss || 0), 0);
            
            // Average return
            this.metrics.averageReturn = this.metrics.totalTrades > 0 ?
                this.metrics.totalProfitLoss / this.metrics.totalTrades : 0;
            
            // Calculate Sharpe ratio
            const returns = this.trades.map(t => t.profitLoss || 0);
            const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
            const stdDev = Math.sqrt(returns.reduce((sq, n) => sq + Math.pow(n - avgReturn, 2), 0) / returns.length);
            this.metrics.sharpeRatio = stdDev !== 0 ? avgReturn / stdDev : 0;
            
            // Calculate max drawdown
            let peak = 0;
            let maxDrawdown = 0;
            let runningPL = 0;
            for (const trade of this.trades) {
                runningPL += trade.profitLoss || 0;
                if (runningPL > peak) {
                    peak = runningPL;
                }
                const drawdown = (peak - runningPL) / peak;
                if (drawdown > maxDrawdown) {
                    maxDrawdown = drawdown;
                }
            }
            this.metrics.maxDrawdown = maxDrawdown;

            this.logger.info('Metrics updated');

        } catch (error) {
            this.logger.error('Failed to update metrics:', error);
            throw error;
        }
    }

    /**
     * Get performance summary.
     */
    getSummary() {
        return {
            metrics: this.metrics,
            risk: this.risk,
            positions: Array.from(this.positions.values()),
            recentTrades: this.trades.slice(-10)
        };
    }

    /**
     * Get open positions.
     */
    getPositions() {
        return Array.from(this.positions.values());
    }

    /**
     * Close analytics.
     */
    async close() {
        this.initialized = false;
        this.trades = [];
        this.positions.clear();
        this.logger.info('Analytics closed');
    }
}

// Export for Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Analytics;
} else {
    window.Analytics = Analytics;
}
