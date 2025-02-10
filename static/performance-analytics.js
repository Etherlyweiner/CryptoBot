class PerformanceAnalytics {
    constructor(tradingBot) {
        this.bot = tradingBot;
        this.state = {
            trades: [],
            dailyStats: new Map(),
            strategyStats: new Map(),
            tokenStats: new Map(),
            riskMetrics: new Map(),
            alerts: []
        };

        // Performance thresholds
        this.thresholds = {
            profitTarget: 0.02,        // 2% target per trade
            maxDrawdown: -0.1,         // 10% maximum drawdown
            minWinRate: 0.5,           // 50% minimum win rate
            maxLossStreak: 3,          // Maximum consecutive losses
            volumeThreshold: 10000,    // Minimum volume in SOL
            alertTimeout: 3600000      // 1 hour alert timeout
        };
    }

    async initialize() {
        try {
            // Start performance monitoring
            this.startMonitoring();
            
            Logger.log('INFO', 'Performance analytics initialized');
            return true;
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize performance analytics', error);
            return false;
        }
    }

    startMonitoring() {
        // Update stats every minute
        setInterval(() => this.updateStats(), 60000);
        
        // Check alerts every 5 minutes
        setInterval(() => this.checkAlerts(), 300000);
        
        // Generate daily report at midnight
        this.scheduleDailyReport();
    }

    async recordTrade(trade) {
        try {
            // Add trade to history
            this.state.trades.push({
                ...trade,
                timestamp: Date.now()
            });

            // Update statistics
            await this.updateTradeStats(trade);
            await this.updateStrategyStats(trade);
            await this.updateTokenStats(trade);
            await this.updateRiskMetrics(trade);

            // Check for alerts
            await this.checkTradeAlerts(trade);

            Logger.log('INFO', 'Trade recorded', { trade });
        } catch (error) {
            Logger.log('ERROR', 'Failed to record trade', error);
        }
    }

    async updateStats() {
        try {
            const stats = {
                timestamp: Date.now(),
                totalTrades: this.state.trades.length,
                profitLoss: this.calculateTotalPnL(),
                winRate: this.calculateWinRate(),
                drawdown: this.calculateDrawdown(),
                volume: this.calculateVolume(),
                strategies: this.getStrategyStats(),
                tokens: this.getTokenStats(),
                risk: this.getRiskMetrics()
            };

            // Update daily stats
            const today = new Date().toISOString().split('T')[0];
            this.state.dailyStats.set(today, stats);

            return stats;
        } catch (error) {
            Logger.log('ERROR', 'Failed to update stats', error);
            throw error;
        }
    }

    async checkAlerts() {
        try {
            const currentStats = await this.updateStats();
            const alerts = [];

            // Check profit/loss alerts
            if (currentStats.profitLoss < this.thresholds.maxDrawdown) {
                alerts.push({
                    type: 'RISK',
                    severity: 'HIGH',
                    message: 'Maximum drawdown exceeded',
                    value: currentStats.profitLoss
                });
            }

            // Check win rate alerts
            if (currentStats.winRate < this.thresholds.minWinRate) {
                alerts.push({
                    type: 'PERFORMANCE',
                    severity: 'MEDIUM',
                    message: 'Win rate below threshold',
                    value: currentStats.winRate
                });
            }

            // Check volume alerts
            if (currentStats.volume < this.thresholds.volumeThreshold) {
                alerts.push({
                    type: 'VOLUME',
                    severity: 'LOW',
                    message: 'Trading volume below threshold',
                    value: currentStats.volume
                });
            }

            // Process alerts
            await this.processAlerts(alerts);
        } catch (error) {
            Logger.log('ERROR', 'Failed to check alerts', error);
        }
    }

    async processAlerts(newAlerts) {
        try {
            for (const alert of newAlerts) {
                // Check if similar alert exists
                const existingAlert = this.state.alerts.find(
                    a => a.type === alert.type && 
                        Date.now() - a.timestamp < this.thresholds.alertTimeout
                );

                if (!existingAlert) {
                    // Add new alert
                    this.state.alerts.push({
                        ...alert,
                        timestamp: Date.now(),
                        status: 'NEW'
                    });

                    // Trigger alert handler
                    await this.handleAlert(alert);
                }
            }

            // Clean up old alerts
            this.state.alerts = this.state.alerts.filter(
                alert => Date.now() - alert.timestamp < this.thresholds.alertTimeout
            );
        } catch (error) {
            Logger.log('ERROR', 'Failed to process alerts', error);
        }
    }

    async handleAlert(alert) {
        try {
            // Log alert
            Logger.log('ALERT', alert.message, alert);

            // Take action based on severity
            switch (alert.severity) {
                case 'HIGH':
                    // Stop trading and notify
                    await this.bot.stopTrading();
                    break;
                case 'MEDIUM':
                    // Adjust risk parameters
                    await this.bot.riskManager.adjustRiskParameters(alert);
                    break;
                case 'LOW':
                    // Just notify
                    break;
            }

            // Update UI if available
            this.updateDashboard();
        } catch (error) {
            Logger.log('ERROR', 'Failed to handle alert', error);
        }
    }

    scheduleDailyReport() {
        const scheduleNextReport = () => {
            const now = new Date();
            const tomorrow = new Date(now);
            tomorrow.setDate(tomorrow.getDate() + 1);
            tomorrow.setHours(0, 0, 0, 0);

            const timeUntilMidnight = tomorrow - now;
            setTimeout(() => {
                this.generateDailyReport();
                scheduleNextReport();
            }, timeUntilMidnight);
        };

        scheduleNextReport();
    }

    async generateDailyReport() {
        try {
            const stats = await this.updateStats();
            const report = {
                date: new Date().toISOString().split('T')[0],
                summary: {
                    totalTrades: stats.totalTrades,
                    profitLoss: stats.profitLoss,
                    winRate: stats.winRate,
                    volume: stats.volume
                },
                strategies: stats.strategies,
                tokens: stats.tokens,
                risk: stats.risk,
                alerts: this.state.alerts
            };

            Logger.log('INFO', 'Daily report generated', report);
            return report;
        } catch (error) {
            Logger.log('ERROR', 'Failed to generate daily report', error);
            throw error;
        }
    }

    // Helper methods for calculations
    calculateTotalPnL() {
        return this.state.trades.reduce((total, trade) => total + (trade.profit || 0), 0);
    }

    calculateWinRate() {
        const winningTrades = this.state.trades.filter(trade => trade.profit > 0);
        return winningTrades.length / this.state.trades.length || 0;
    }

    calculateDrawdown() {
        let peak = 0;
        let drawdown = 0;
        let runningPnL = 0;

        for (const trade of this.state.trades) {
            runningPnL += (trade.profit || 0);
            peak = Math.max(peak, runningPnL);
            drawdown = Math.min(drawdown, runningPnL - peak);
        }

        return drawdown;
    }

    calculateVolume() {
        const last24h = Date.now() - 86400000;
        return this.state.trades
            .filter(trade => trade.timestamp > last24h)
            .reduce((total, trade) => total + (trade.amount || 0), 0);
    }

    getStrategyStats() {
        return Object.fromEntries(this.state.strategyStats);
    }

    getTokenStats() {
        return Object.fromEntries(this.state.tokenStats);
    }

    getRiskMetrics() {
        return Object.fromEntries(this.state.riskMetrics);
    }

    updateDashboard() {
        // Implementation for updating UI dashboard
        // This would be implemented based on the UI framework being used
    }
}

// Export performance analytics
window.PerformanceAnalytics = PerformanceAnalytics;
