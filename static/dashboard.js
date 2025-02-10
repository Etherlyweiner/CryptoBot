class Dashboard {
    constructor() {
        this.state = {
            isInitialized: false,
            lastUpdate: null,
            updateInterval: 5000,  // 5 seconds
            chartPeriod: '1d',     // 1 day default
            selectedStrategy: null,
            selectedToken: null
        };

        // Chart configurations
        this.charts = {
            pnl: null,
            volume: null,
            strategies: null,
            tokens: null
        };
    }

    async initialize() {
        try {
            // Initialize charts
            await this.initializeCharts();
            
            // Start update loop
            this.startUpdateLoop();
            
            // Initialize event listeners
            this.setupEventListeners();
            
            this.state.isInitialized = true;
            Logger.log('INFO', 'Dashboard initialized');
            return true;
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize dashboard', error);
            return false;
        }
    }

    async initializeCharts() {
        // Initialize P&L chart
        this.charts.pnl = new Chart(
            document.getElementById('pnl-chart').getContext('2d'),
            this.getPnLChartConfig()
        );

        // Initialize volume chart
        this.charts.volume = new Chart(
            document.getElementById('volume-chart').getContext('2d'),
            this.getVolumeChartConfig()
        );

        // Initialize strategy performance chart
        this.charts.strategies = new Chart(
            document.getElementById('strategy-chart').getContext('2d'),
            this.getStrategyChartConfig()
        );

        // Initialize token performance chart
        this.charts.tokens = new Chart(
            document.getElementById('token-chart').getContext('2d'),
            this.getTokenChartConfig()
        );
    }

    startUpdateLoop() {
        setInterval(() => this.updateDashboard(), this.state.updateInterval);
    }

    setupEventListeners() {
        // Period selector
        document.getElementById('period-selector').addEventListener('change', (e) => {
            this.state.chartPeriod = e.target.value;
            this.updateDashboard();
        });

        // Strategy selector
        document.getElementById('strategy-selector').addEventListener('change', (e) => {
            this.state.selectedStrategy = e.target.value;
            this.updateStrategyView();
        });

        // Token selector
        document.getElementById('token-selector').addEventListener('change', (e) => {
            this.state.selectedToken = e.target.value;
            this.updateTokenView();
        });
    }

    async updateDashboard() {
        try {
            // Get latest performance data
            const stats = await window.tradingBot.performanceAnalytics.updateStats();
            
            // Update summary metrics
            this.updateSummaryMetrics(stats);
            
            // Update charts
            this.updateCharts(stats);
            
            // Update alerts
            this.updateAlerts();
            
            this.state.lastUpdate = Date.now();
        } catch (error) {
            Logger.log('ERROR', 'Failed to update dashboard', error);
        }
    }

    updateSummaryMetrics(stats) {
        // Update total P&L
        document.getElementById('total-pnl').textContent = 
            this.formatCurrency(stats.profitLoss);

        // Update win rate
        document.getElementById('win-rate').textContent = 
            this.formatPercentage(stats.winRate);

        // Update volume
        document.getElementById('total-volume').textContent = 
            this.formatCurrency(stats.volume);

        // Update trade count
        document.getElementById('trade-count').textContent = 
            stats.totalTrades.toString();
    }

    updateCharts(stats) {
        // Update P&L chart
        this.updatePnLChart(stats);
        
        // Update volume chart
        this.updateVolumeChart(stats);
        
        // Update strategy performance chart
        this.updateStrategyChart(stats);
        
        // Update token performance chart
        this.updateTokenChart(stats);
    }

    updateAlerts() {
        const alertsContainer = document.getElementById('alerts-container');
        alertsContainer.innerHTML = '';

        const alerts = window.tradingBot.performanceAnalytics.state.alerts;
        
        for (const alert of alerts) {
            const alertElement = document.createElement('div');
            alertElement.className = `alert alert-${alert.severity.toLowerCase()}`;
            alertElement.innerHTML = `
                <strong>${alert.type}:</strong> ${alert.message}
                <small>${this.formatTimestamp(alert.timestamp)}</small>
            `;
            alertsContainer.appendChild(alertElement);
        }
    }

    // Chart configuration getters
    getPnLChartConfig() {
        return {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Profit/Loss',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
    }

    getVolumeChartConfig() {
        return {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Volume',
                    data: [],
                    backgroundColor: 'rgb(54, 162, 235)'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
    }

    getStrategyChartConfig() {
        return {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgb(255, 99, 132)',
                        'rgb(54, 162, 235)',
                        'rgb(255, 206, 86)'
                    ]
                }]
            },
            options: {
                responsive: true
            }
        };
    }

    getTokenChartConfig() {
        return {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Token Performance',
                    data: [],
                    backgroundColor: 'rgb(75, 192, 192)'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
    }

    // Helper methods
    formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    }

    formatPercentage(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2
        }).format(value);
    }

    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }
}

// Export dashboard
window.Dashboard = Dashboard;
