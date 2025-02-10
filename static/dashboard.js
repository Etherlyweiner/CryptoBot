/**
 * Dashboard functionality
 */
class Dashboard {
    constructor() {
        this.logger = new Logger('Dashboard');
        this.updateInterval = 5000; // 5 seconds
        this.isRunning = false;
        this.bot = null;
        
        // Initialize UI
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeUI();
            this.initializeBot();
        });
    }
    
    initializeUI() {
        // Get UI elements
        this.elements = {
            connectWallet: document.getElementById('connect-wallet'),
            startBot: document.getElementById('start-bot'),
            walletStatus: document.getElementById('wallet-status'),
            botStatus: document.getElementById('bot-status'),
            totalTrades: document.getElementById('total-trades'),
            winRate: document.getElementById('win-rate'),
            totalPL: document.getElementById('total-pl'),
            portfolioValue: document.getElementById('portfolio-value'),
            tradeSize: document.getElementById('trade-size'),
            stopLoss: document.getElementById('stop-loss'),
            takeProfit: document.getElementById('take-profit'),
            positionsTable: document.getElementById('positions-table'),
            tradesTable: document.getElementById('trades-table')
        };

        // Add event listeners
        this.elements.connectWallet.addEventListener('click', () => this.connectWallet());
        this.elements.startBot.addEventListener('click', () => this.toggleBot());
        this.elements.tradeSize.addEventListener('change', () => this.updateSettings());
        this.elements.stopLoss.addEventListener('change', () => this.updateSettings());
        this.elements.takeProfit.addEventListener('change', () => this.updateSettings());

        this.logger.info('UI initialized');
    }

    async initializeBot() {
        try {
            // Create bot instance
            this.bot = new CryptoBot({
                tradeSize: parseFloat(this.elements.tradeSize.value),
                stopLoss: parseFloat(this.elements.stopLoss.value),
                takeProfit: parseFloat(this.elements.takeProfit.value)
            });

            // Initialize bot
            await this.bot.initialize();
            this.logger.info('Bot initialized');

            // Start update loop
            this.startUpdateLoop();

        } catch (error) {
            this.logger.error('Failed to initialize bot:', error);
            this.updateStatus('Error: ' + error.message);
        }
    }

    startUpdateLoop() {
        setInterval(() => this.update(), this.updateInterval);
    }

    async update() {
        if (!this.bot) return;

        try {
            // Update wallet status
            const isConnected = this.bot.walletManager.isConnected();
            this.elements.walletStatus.textContent = `Wallet: ${isConnected ? 'Connected' : 'Not Connected'}`;
            this.elements.startBot.disabled = !isConnected;

            // Update bot status
            this.elements.botStatus.textContent = `Bot: ${this.isRunning ? 'Running' : 'Stopped'}`;

            // Update performance metrics
            const analytics = this.bot.analytics.getSummary();
            this.elements.totalTrades.textContent = analytics.metrics.totalTrades;
            this.elements.winRate.textContent = (analytics.metrics.winRate * 100).toFixed(1) + '%';
            this.elements.totalPL.textContent = analytics.metrics.totalProfitLoss.toFixed(4) + ' SOL';
            this.elements.portfolioValue.textContent = analytics.risk.portfolioValue.toFixed(4) + ' SOL';

            // Update positions table
            this.updatePositionsTable(analytics.positions);

            // Update trades table
            this.updateTradesTable(analytics.recentTrades);

        } catch (error) {
            this.logger.error('Failed to update dashboard:', error);
        }
    }

    updatePositionsTable(positions) {
        this.elements.positionsTable.innerHTML = positions.map(pos => `
            <tr>
                <td class="px-6 py-4">${pos.token}</td>
                <td class="px-6 py-4">${pos.entryPrice.toFixed(4)}</td>
                <td class="px-6 py-4">${pos.currentPrice.toFixed(4)}</td>
                <td class="px-6 py-4">${pos.size.toFixed(4)}</td>
                <td class="px-6 py-4 ${pos.profitLoss >= 0 ? 'text-green-500' : 'text-red-500'}">
                    ${pos.profitLoss.toFixed(4)}
                </td>
            </tr>
        `).join('');
    }

    updateTradesTable(trades) {
        this.elements.tradesTable.innerHTML = trades.map(trade => `
            <tr>
                <td class="px-6 py-4">${new Date(trade.timestamp).toLocaleString()}</td>
                <td class="px-6 py-4">${trade.token}</td>
                <td class="px-6 py-4">${trade.side}</td>
                <td class="px-6 py-4">${trade.price.toFixed(4)}</td>
                <td class="px-6 py-4">${trade.size.toFixed(4)}</td>
                <td class="px-6 py-4 ${trade.profitLoss >= 0 ? 'text-green-500' : 'text-red-500'}">
                    ${trade.profitLoss ? trade.profitLoss.toFixed(4) : '-'}
                </td>
            </tr>
        `).join('');
    }

    async connectWallet() {
        try {
            if (!this.bot) {
                throw new Error('Bot not initialized');
            }

            const connected = await this.bot.walletManager.connect();
            if (connected) {
                this.logger.info('Wallet connected');
                this.elements.connectWallet.textContent = 'Disconnect Wallet';
                this.elements.startBot.disabled = false;
            }

        } catch (error) {
            this.logger.error('Failed to connect wallet:', error);
            this.updateStatus('Error: ' + error.message);
        }
    }

    async toggleBot() {
        try {
            if (!this.bot) {
                throw new Error('Bot not initialized');
            }

            if (this.isRunning) {
                await this.bot.stop();
                this.isRunning = false;
                this.elements.startBot.textContent = 'Start Bot';
                this.logger.info('Bot stopped');
            } else {
                await this.bot.start();
                this.isRunning = true;
                this.elements.startBot.textContent = 'Stop Bot';
                this.logger.info('Bot started');
            }

        } catch (error) {
            this.logger.error('Failed to toggle bot:', error);
            this.updateStatus('Error: ' + error.message);
        }
    }

    updateSettings() {
        if (!this.bot) return;

        const settings = {
            tradeSize: parseFloat(this.elements.tradeSize.value),
            stopLoss: parseFloat(this.elements.stopLoss.value),
            takeProfit: parseFloat(this.elements.takeProfit.value)
        };

        this.bot.updateSettings(settings);
        this.logger.info('Settings updated:', settings);
    }

    updateStatus(message) {
        this.elements.botStatus.textContent = message;
    }
}

// Initialize dashboard
const dashboard = new Dashboard();
