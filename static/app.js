// Core trading bot functionality
class TradingBot {
    constructor() {
        this.active = false;
        this.positions = new Map();
        this.settings = {
            tradeSize: 0.1,
            maxSlippage: 1.0,
            profitTarget: 10.0,
            stopLoss: 5.0,
            autoTrading: {
                enabled: false,
                interval: 5,
                maxPositions: 3
            },
            riskManagement: {
                maxDailyLoss: 5.0, // Maximum daily loss percentage
                maxPositionSize: 1.0, // Maximum position size in SOL
                minLiquidity: 1000, // Minimum liquidity in SOL
                minVolume: 100, // Minimum 24h volume in SOL
                maxSlippageImpact: 2.0, // Maximum price impact percentage
                cooldownPeriod: 300, // Seconds to wait after a loss
                lastLossTimestamp: 0
            }
        };
        this.onStatusUpdate = null;
        this.initialized = false;
        this.autoTradingInterval = null;
        this.dailyStats = {
            totalPnL: 0,
            tradeCount: 0,
            winCount: 0,
            lossCount: 0,
            startTime: Date.now(),
            lastReset: Date.now()
        };
    }

    resetDailyStats() {
        const now = Date.now();
        // Only reset if it's been more than 24 hours
        if (now - this.dailyStats.lastReset >= 24 * 60 * 60 * 1000) {
            this.dailyStats = {
                totalPnL: 0,
                tradeCount: 0,
                winCount: 0,
                lossCount: 0,
                startTime: now,
                lastReset: now
            };
            console.log('Daily stats reset');
        }
    }

    async start() {
        try {
            console.log('Starting trading bot...');
            this.active = true;
            
            // Initialize RPC connection with fallback
            const rpcEndpoints = [
                'https://staked.helius-rpc.com?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c',
                'https://api.mainnet-beta.solana.com',
                'https://solana-api.projectserum.com'
            ];
            
            let connected = false;
            for (const endpoint of rpcEndpoints) {
                try {
                    console.log('Attempting to connect to RPC endpoint:', endpoint);
                    await window.walletManager.initializeConnection(endpoint);
                    connected = true;
                    console.log('Connected to RPC endpoint:', endpoint);
                    break;
                } catch (error) {
                    console.warn('Failed to connect to RPC endpoint:', endpoint, error);
                }
            }
            
            if (!connected) {
                throw new Error('Failed to connect to any RPC endpoint');
            }

            // Initialize Jupiter
            console.log('Initializing Jupiter...');
            if (!window.jupiter) {
                throw new Error('Jupiter not initialized');
            }
            await window.jupiter.testConnection();
            console.log('Jupiter connection test successful');

            // Check wallet connection
            console.log('Checking wallet connection...');
            if (!window.walletManager || !window.walletManager.isConnected()) {
                throw new Error('Wallet not connected');
            }
            console.log('Wallet connection verified');

            if (this.settings.autoTrading.enabled) {
                console.log('Auto trading enabled, starting...');
                this.startAutoTrading();
            } else {
                console.log('Auto trading not enabled');
            }
            
            if (this.onStatusUpdate) this.onStatusUpdate();
            console.log('Trading bot started successfully');
            
        } catch (error) {
            console.error('Failed to start trading bot:', error);
            throw error;
        }
    }

    stop() {
        this.active = false;
        this.stopAutoTrading();
        if (this.onStatusUpdate) this.onStatusUpdate();
    }

    startAutoTrading() {
        if (this.autoTradingInterval) {
            clearInterval(this.autoTradingInterval);
        }

        // Convert minutes to milliseconds
        const interval = this.settings.autoTrading.interval * 60 * 1000;
        
        this.autoTradingInterval = setInterval(async () => {
            await this.executeAutoTrade();
        }, interval);

        console.log('Auto trading started with interval:', this.settings.autoTrading.interval, 'minutes');
    }

    stopAutoTrading() {
        if (this.autoTradingInterval) {
            clearInterval(this.autoTradingInterval);
            this.autoTradingInterval = null;
            console.log('Auto trading stopped');
        }
    }

    async executeAutoTrade() {
        if (!this.active || !this.settings.autoTrading.enabled) {
            console.log('Auto trading disabled or bot inactive');
            this.stopAutoTrading();
            return;
        }

        try {
            console.log('Executing auto trade...');
            // Reset daily stats if needed
            this.resetDailyStats();

            // Check daily loss limit
            if (this.dailyStats.totalPnL <= -this.settings.riskManagement.maxDailyLoss) {
                console.log('Daily loss limit reached. Stopping auto trading.');
                this.stopAutoTrading();
                showError('Daily loss limit reached. Auto trading stopped.');
                return;
            }

            // Check cooldown period after a loss
            const now = Date.now();
            if (now - this.settings.riskManagement.lastLossTimestamp < 
                this.settings.riskManagement.cooldownPeriod * 1000) {
                console.log('In cooldown period after loss');
                return;
            }

            // Check if we can open new positions
            if (this.positions.size >= this.settings.autoTrading.maxPositions) {
                console.log('Maximum positions reached');
                return;
            }

            // Get market data from Jupiter
            console.log('Fetching market data...');
            const marketData = await window.jupiter.getMarketData();
            if (!marketData) {
                console.warn('No market data available');
                return;
            }
            console.log('Market data received:', marketData);

            // Find trading opportunities
            console.log('Searching for trading opportunities...');
            const opportunity = await this.findTradingOpportunity(marketData);
            if (opportunity) {
                console.log('Trading opportunity found:', opportunity);
                await this.executeTrade(opportunity);
            } else {
                console.log('No trading opportunities found');
            }

            // Check existing positions
            console.log('Checking existing positions...');
            await this.checkExistingPositions();

        } catch (error) {
            console.error('Auto trading error:', error);
            showError('Auto trading error: ' + error.message);
        }
    }

    async findTradingOpportunity(marketData) {
        const { minLiquidity, minVolume, maxSlippageImpact } = this.settings.riskManagement;
        const tokens = marketData.tokens || [];
        
        for (const token of tokens) {
            // Check token metrics
            if (await this.isGoodTradeOpportunity(token)) {
                // Calculate optimal position size
                const positionSize = Math.min(
                    this.settings.tradeSize,
                    this.settings.riskManagement.maxPositionSize,
                    token.liquidity * 0.01 // Limit to 1% of liquidity
                );

                // Check price impact
                const priceImpact = await window.jupiter.calculatePriceImpact(token.address, positionSize);
                if (priceImpact > maxSlippageImpact) {
                    console.log('Price impact too high:', priceImpact);
                    continue;
                }

                return {
                    token: token.address,
                    action: 'buy',
                    amount: positionSize
                };
            }
        }
        
        return null;
    }

    async isGoodTradeOpportunity(token) {
        const { minLiquidity, minVolume } = this.settings.riskManagement;
        
        // Basic liquidity and volume checks
        if (token.liquidity < minLiquidity || token.volume24h < minVolume) {
            return false;
        }

        try {
            // Get token metadata
            const metadata = await window.jupiter.getTokenMetadata(token.address);
            if (!metadata) return false;

            // Check if token is verified
            if (!metadata.verified) {
                console.log('Token not verified:', token.address);
                return false;
            }

            // Get recent trades
            const recentTrades = await window.jupiter.getRecentTrades(token.address);
            if (!recentTrades || recentTrades.length === 0) return false;

            // Calculate price volatility
            const prices = recentTrades.map(trade => trade.price);
            const volatility = this.calculateVolatility(prices);
            if (volatility > 50) { // More than 50% volatility is too risky
                console.log('Token too volatile:', volatility);
                return false;
            }

            // Check buy/sell ratio
            const buyCount = recentTrades.filter(trade => trade.side === 'buy').length;
            const sellCount = recentTrades.length - buyCount;
            const buyRatio = buyCount / recentTrades.length;
            if (buyRatio < 0.4) { // Less than 40% buys might indicate selling pressure
                console.log('High selling pressure detected');
                return false;
            }

            return true;

        } catch (error) {
            console.error('Error checking trade opportunity:', error);
            return false;
        }
    }

    calculateVolatility(prices) {
        if (!prices || prices.length < 2) return 0;
        
        const returns = [];
        for (let i = 1; i < prices.length; i++) {
            returns.push((prices[i] - prices[i-1]) / prices[i-1] * 100);
        }
        
        const mean = returns.reduce((a, b) => a + b) / returns.length;
        const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length;
        return Math.sqrt(variance);
    }

    async executeTrade(opportunity) {
        try {
            const { token, action, amount } = opportunity;
            
            // Final risk checks before execution
            const currentPrice = await window.jupiter.getTokenPrice(token);
            const priceImpact = await window.jupiter.calculatePriceImpact(token, amount);
            
            if (priceImpact > this.settings.riskManagement.maxSlippageImpact) {
                console.log('Aborting trade: Price impact too high');
                return;
            }

            // Execute the trade
            const result = await window.jupiter.swap({
                inputToken: action === 'buy' ? 'SOL' : token,
                outputToken: action === 'buy' ? token : 'SOL',
                amount: amount,
                slippage: this.settings.maxSlippage
            });

            if (result.success) {
                // Update position tracking
                if (action === 'buy') {
                    this.positions.set(token, {
                        amount: result.outputAmount,
                        entryPrice: currentPrice,
                        timestamp: Date.now()
                    });
                }

                // Update trading stats
                this.dailyStats.tradeCount++;
                updatePositionsDisplay();
                
                // Announce trade to screen readers
                const announcement = document.getElementById('trading-announcements');
                if (announcement) {
                    announcement.textContent = `Successfully ${action}ed ${amount} SOL worth of token`;
                }
            }
            
        } catch (error) {
            console.error('Trade execution error:', error);
            showError('Failed to execute trade: ' + error.message);
        }
    }

    async checkExistingPositions() {
        for (const [address, position] of this.positions.entries()) {
            try {
                const currentPrice = await window.jupiter.getTokenPrice(address);
                const pnlPercent = ((currentPrice - position.entryPrice) / position.entryPrice) * 100;
                
                // Update daily PnL
                const positionValue = position.amount * currentPrice;
                const pnlValue = positionValue - (position.amount * position.entryPrice);
                this.dailyStats.totalPnL += pnlValue;

                // Check if we should close the position
                if (pnlPercent >= this.settings.profitTarget) {
                    await this.closePosition(address);
                    this.dailyStats.winCount++;
                } else if (pnlPercent <= -this.settings.stopLoss) {
                    await this.closePosition(address);
                    this.dailyStats.lossCount++;
                    this.settings.riskManagement.lastLossTimestamp = Date.now();
                }
                
            } catch (error) {
                console.error('Error checking position:', error);
            }
        }
    }

    async closePosition(address) {
        if (!this.positions.has(address)) return;
        
        try {
            const position = this.positions.get(address);
            await window.jupiter.swap({
                inputToken: address,
                outputToken: 'SOL',
                amount: position.amount,
                slippage: this.settings.maxSlippage
            });
            
            this.positions.delete(address);
            updatePositionsDisplay();
            
            if (this.onStatusUpdate) this.onStatusUpdate();
            
        } catch (error) {
            console.error('Error closing position:', error);
            showError('Failed to close position: ' + error.message);
        }
    }

    updateSetting(property, value) {
        const numValue = parseFloat(value);
        
        // Handle auto trading settings
        if (property === 'autoTrading.enabled') {
            this.settings.autoTrading.enabled = value === true;
            if (this.active && this.settings.autoTrading.enabled) {
                this.startAutoTrading();
            } else {
                this.stopAutoTrading();
            }
            return true;
        }
        
        if (property === 'autoTrading.interval') {
            if (!isNaN(numValue) && numValue >= 1 && numValue <= 1440) {
                this.settings.autoTrading.interval = numValue;
                if (this.active && this.settings.autoTrading.enabled) {
                    this.startAutoTrading(); // Restart with new interval
                }
                return true;
            }
            return false;
        }
        
        if (property === 'autoTrading.maxPositions') {
            if (!isNaN(numValue) && numValue >= 1 && numValue <= 10) {
                this.settings.autoTrading.maxPositions = numValue;
                return true;
            }
            return false;
        }
        
        // Handle regular settings
        if (property in this.settings && !isNaN(numValue)) {
            this.settings[property] = numValue;
            return true;
        }
        
        return false;
    }
}

// Initialize global variables
let walletConnected = false;
let jupiter = null;
const tradingBot = new TradingBot();

// Status update handler
function updateWalletStatus(status) {
    walletConnected = status === 'connected';
    
    // Safely get elements with fallbacks
    const connectButton = document.getElementById('connect-wallet');
    const walletStatus = document.getElementById('wallet-status');
    const tradingPanel = document.querySelector('.trading-panel');
    
    // Only proceed if elements exist
    if (connectButton && walletStatus && tradingPanel) {
        if (walletConnected) {
            connectButton.textContent = 'Connected';
            connectButton.disabled = true;
            walletStatus.textContent = 'Connected';
            walletStatus.className = 'status success';
            tradingPanel.style.display = 'block';
            
            // Initialize trading settings after connection
            setupTradingSettings();
            
            // Announce to screen readers
            const announcement = document.getElementById('trading-announcements');
            if (announcement) {
                announcement.textContent = 'Wallet connected successfully. Trading panel is now available.';
            }
        } else {
            connectButton.textContent = 'Connect Wallet';
            connectButton.disabled = false;
            walletStatus.textContent = 'Not connected';
            walletStatus.className = 'status';
            tradingPanel.style.display = 'none';
            
            // Announce to screen readers
            const announcement = document.getElementById('trading-announcements');
            if (announcement) {
                announcement.textContent = 'Wallet disconnected. Please connect your wallet to start trading.';
            }
        }
    } else {
        console.warn('Some UI elements are missing:', {
            connectButton: !!connectButton,
            walletStatus: !!walletStatus,
            tradingPanel: !!tradingPanel
        });
    }
}

// Error handling
function showError(message) {
    const errorDiv = document.querySelector('.error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Announce error to screen readers
        const announcement = document.getElementById('trading-announcements');
        if (announcement) {
            announcement.textContent = 'Error: ' + message;
        }
        
        // Hide after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
}

// Trading settings handler
function setupTradingSettings() {
    const settingsMap = {
        'max-slippage': 'maxSlippage',
        'trade-size': 'tradeSize',
        'profit-target': 'profitTarget',
        'stop-loss': 'stopLoss',
        'auto-trading-enabled': 'autoTrading.enabled',
        'trading-interval': 'autoTrading.interval',
        'max-positions': 'autoTrading.maxPositions',
        'max-daily-loss': 'riskManagement.maxDailyLoss',
        'max-position-size': 'riskManagement.maxPositionSize',
        'min-liquidity': 'riskManagement.minLiquidity',
        'min-volume': 'riskManagement.minVolume',
        'max-slippage-impact': 'riskManagement.maxSlippageImpact',
        'cooldown-period': 'riskManagement.cooldownPeriod'
    };

    Object.entries(settingsMap).forEach(([elementId, settingKey]) => {
        const input = document.getElementById(elementId);
        if (input) {
            // Set initial value
            const currentValue = settingKey.includes('.')
                ? settingKey.split('.').reduce((obj, key) => obj[key], tradingBot.settings)
                : tradingBot.settings[settingKey];

            if (typeof currentValue !== 'undefined') {
                if (input.type === 'checkbox') {
                    input.checked = currentValue;
                } else {
                    input.value = currentValue;
                }
            }

            // Add change listener
            input.addEventListener('change', (e) => {
                const value = input.type === 'checkbox' ? e.target.checked : e.target.value;
                const success = tradingBot.updateSetting(settingKey, value);
                if (!success) {
                    showError(`Invalid value for ${elementId.replace('-', ' ')}`);
                    // Reset to last valid value
                    if (input.type === 'checkbox') {
                        input.checked = currentValue;
                    } else {
                        input.value = currentValue;
                    }
                } else {
                    // Announce setting change to screen readers
                    const announcement = document.getElementById('trading-announcements');
                    if (announcement) {
                        announcement.textContent = `${elementId.replace('-', ' ')} updated to ${value}`;
                    }
                }
            });
        } else {
            console.warn(`Setting input not found: ${elementId}`);
        }
    });
}

// Update positions display
function updatePositionsDisplay() {
    const positionsList = document.getElementById('positions-list');
    if (!positionsList) {
        console.warn('Positions list element not found');
        return;
    }

    const positions = Array.from(tradingBot.positions.entries());
    const template = document.getElementById('position-row-template');
    
    // Clear existing positions except the "no positions" message
    const existingPositions = positionsList.querySelectorAll('.position-row');
    existingPositions.forEach(row => row.remove());

    if (positions.length === 0) {
        const noPositionsRow = document.createElement('div');
        noPositionsRow.role = 'row';
        noPositionsRow.className = 'no-positions';
        const cell = document.createElement('div');
        cell.role = 'cell';
        cell.textContent = 'No active positions';
        noPositionsRow.appendChild(cell);
        positionsList.appendChild(noPositionsRow);
        return;
    }

    positions.forEach(([address, position]) => {
        if (template) {
            const clone = template.content.cloneNode(true);
            // Fill in position data
            clone.querySelector('.token-name').textContent = position.symbol || address;
            clone.querySelector('.token-amount').textContent = position.amount;
            clone.querySelector('.entry-price').textContent = position.entryPrice;
            clone.querySelector('.current-price').textContent = position.currentPrice;
            clone.querySelector('.pnl').textContent = position.pnl;
            
            const closeButton = clone.querySelector('.close-position');
            if (closeButton) {
                closeButton.addEventListener('click', () => tradingBot.closePosition(address));
            }
            
            positionsList.appendChild(clone);
        }
    });
}

// Trading bot status updates
tradingBot.onStatusUpdate = () => {
    const botStatusSpan = document.getElementById('botStatus');
    const startButton = document.getElementById('startBot');
    const stopButton = document.getElementById('stopBot');
    
    botStatusSpan.textContent = tradingBot.active ? 'Active' : 'Inactive';
    startButton.disabled = tradingBot.active;
    stopButton.disabled = !tradingBot.active;
    
    document.getElementById('activeTrades').textContent = tradingBot.positions.size;
    updatePositionsDisplay();
};

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    const connectButton = document.getElementById('connect-wallet');
    if (connectButton) {
        connectButton.addEventListener('click', connectWallet);
    }

    // Wait for wallet manager to be available
    const checkWalletManager = setInterval(() => {
        if (window.walletManager) {
            clearInterval(checkWalletManager);
            
            // Set up wallet status updates
            window.walletManager.onStatusUpdate = updateWalletStatus;
            
            // Check initial connection status
            updateWalletStatus(window.walletManager.isConnected() ? 'connected' : 'disconnected');
        }
    }, 100);
    
    // Add keyboard navigation
    document.addEventListener('keydown', (e) => {
        // Escape key closes any open dialogs or panels
        if (e.key === 'Escape') {
            const statusDiv = document.getElementById('status');
            if (statusDiv.style.display === 'block') {
                statusDiv.style.display = 'none';
            }
        }
    });
});

// Wallet connection handler
async function connectWallet() {
    const connectButton = document.getElementById('connect-wallet');
    if (!connectButton) {
        console.error('Connect wallet button not found');
        return;
    }

    try {
        connectButton.disabled = true;
        connectButton.textContent = 'Connecting...';
        
        await window.walletManager.connect();
        
        if (!jupiter) {
            jupiter = new JupiterDEX();
            await jupiter.initialize();
        }
        
    } catch (error) {
        console.error('Failed to connect wallet:', error);
        showError('Failed to connect wallet: ' + error.message);
        if (connectButton) {
            connectButton.disabled = false;
            connectButton.textContent = 'Connect Wallet';
        }
    }
}

// Trading control event listeners
document.getElementById('start-trading').addEventListener('click', async () => {
    console.log('Start trading button clicked');
    try {
        // Validate settings before starting
        const settings = validateSettings();
        console.log('Validated settings:', settings);
        if (!settings) {
            showError('Please check your trading settings');
            return;
        }

        // Update UI
        document.getElementById('start-trading').disabled = true;
        document.getElementById('stop-trading').disabled = false;
        document.getElementById('trading-status').textContent = 'Trading Status: Starting...';
        
        // Apply settings to bot
        Object.assign(tradingBot.settings, settings);
        console.log('Applied settings to bot:', tradingBot.settings);
        
        // Start the bot
        await tradingBot.start();
        console.log('Bot started successfully');
        
        // Update status
        document.getElementById('trading-status').textContent = 'Trading Status: Active';
        showSuccess('Autonomous trading started successfully');
        
        // Start checking for trading opportunities
        tradingBot.startAutoTrading();
        console.log('Auto trading started');
        
        // Disable settings while trading
        disableSettings(true);
        
    } catch (error) {
        console.error('Failed to start trading:', error);
        showError('Failed to start trading: ' + error.message);
        
        // Reset UI
        document.getElementById('start-trading').disabled = false;
        document.getElementById('stop-trading').disabled = true;
        document.getElementById('trading-status').textContent = 'Trading Status: Stopped';
        disableSettings(false);
    }
});

document.getElementById('stop-trading').addEventListener('click', () => {
    try {
        // Stop the bot
        tradingBot.stop();
        
        // Update UI
        document.getElementById('start-trading').disabled = false;
        document.getElementById('stop-trading').disabled = true;
        document.getElementById('trading-status').textContent = 'Trading Status: Stopped';
        showSuccess('Trading stopped successfully');
        
        // Re-enable settings
        disableSettings(false);
        
    } catch (error) {
        console.error('Failed to stop trading:', error);
        showError('Failed to stop trading: ' + error.message);
    }
});

function validateSettings() {
    // Get all settings
    const settings = {
        tradeSize: parseFloat(document.getElementById('trade-size').value),
        maxSlippage: parseFloat(document.getElementById('max-slippage').value),
        profitTarget: parseFloat(document.getElementById('profit-target').value),
        stopLoss: parseFloat(document.getElementById('stop-loss').value),
        autoTrading: {
            enabled: document.getElementById('auto-trading-enabled').checked,
            interval: parseInt(document.getElementById('trading-interval').value),
            maxPositions: parseInt(document.getElementById('max-positions').value)
        },
        riskManagement: {
            maxDailyLoss: parseFloat(document.getElementById('max-daily-loss').value),
            maxPositionSize: parseFloat(document.getElementById('max-position-size').value),
            minLiquidity: parseFloat(document.getElementById('min-liquidity').value),
            minVolume: parseFloat(document.getElementById('min-volume').value),
            maxSlippageImpact: parseFloat(document.getElementById('max-slippage-impact').value),
            cooldownPeriod: parseInt(document.getElementById('cooldown-period').value)
        }
    };

    // Validate all settings are numbers and within reasonable ranges
    if (isNaN(settings.tradeSize) || settings.tradeSize <= 0) return false;
    if (isNaN(settings.maxSlippage) || settings.maxSlippage <= 0 || settings.maxSlippage > 100) return false;
    if (isNaN(settings.profitTarget) || settings.profitTarget <= 0) return false;
    if (isNaN(settings.stopLoss) || settings.stopLoss <= 0) return false;
    if (isNaN(settings.autoTrading.interval) || settings.autoTrading.interval < 1) return false;
    if (isNaN(settings.autoTrading.maxPositions) || settings.autoTrading.maxPositions < 1) return false;
    
    // Validate risk management settings
    const rm = settings.riskManagement;
    if (isNaN(rm.maxDailyLoss) || rm.maxDailyLoss <= 0 || rm.maxDailyLoss > 100) return false;
    if (isNaN(rm.maxPositionSize) || rm.maxPositionSize <= 0) return false;
    if (isNaN(rm.minLiquidity) || rm.minLiquidity <= 0) return false;
    if (isNaN(rm.minVolume) || rm.minVolume <= 0) return false;
    if (isNaN(rm.maxSlippageImpact) || rm.maxSlippageImpact <= 0 || rm.maxSlippageImpact > 100) return false;
    if (isNaN(rm.cooldownPeriod) || rm.cooldownPeriod < 0) return false;

    return settings;
}

function disableSettings(disabled) {
    // Disable/enable all input fields while trading
    const inputs = document.querySelectorAll('.settings-group input');
    inputs.forEach(input => {
        input.disabled = disabled;
    });
}

function showSuccess(message) {
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.className = 'success';
        statusElement.setAttribute('aria-live', 'polite');
    }
}

function showError(message) {
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.className = 'error';
        statusElement.setAttribute('aria-live', 'assertive');
    }
}
