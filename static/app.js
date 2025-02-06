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
            }
        };
        this.onStatusUpdate = null;
        this.initialized = false;
        this.autoTradingInterval = null;
    }

    start() {
        this.active = true;
        if (this.settings.autoTrading.enabled) {
            this.startAutoTrading();
        }
        if (this.onStatusUpdate) this.onStatusUpdate();
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
            this.stopAutoTrading();
            return;
        }

        try {
            // Check if we can open new positions
            if (this.positions.size >= this.settings.autoTrading.maxPositions) {
                console.log('Maximum positions reached');
                return;
            }

            // Get market data from Jupiter
            const marketData = await window.jupiter.getMarketData();
            if (!marketData) {
                console.warn('No market data available');
                return;
            }

            // Find trading opportunities
            const opportunity = await this.findTradingOpportunity(marketData);
            if (opportunity) {
                await this.executeTrade(opportunity);
            }

            // Check existing positions
            await this.checkExistingPositions();

        } catch (error) {
            console.error('Auto trading error:', error);
            showError('Auto trading error: ' + error.message);
        }
    }

    async findTradingOpportunity(marketData) {
        // Implement your trading strategy here
        // This is a placeholder implementation
        const tokens = marketData.tokens || [];
        
        for (const token of tokens) {
            // Check token metrics (volume, liquidity, etc.)
            if (this.isGoodTradeOpportunity(token)) {
                return {
                    token: token.address,
                    action: 'buy',
                    amount: this.settings.tradeSize
                };
            }
        }
        
        return null;
    }

    isGoodTradeOpportunity(token) {
        // Implement your token evaluation logic here
        // This is a placeholder implementation
        const minLiquidity = 1000; // Minimum liquidity in SOL
        const minVolume = 100; // Minimum 24h volume in SOL
        
        return token.liquidity >= minLiquidity && 
               token.volume24h >= minVolume;
    }

    async executeTrade(opportunity) {
        try {
            if (opportunity.action === 'buy') {
                await window.jupiter.swap({
                    inputToken: 'SOL',
                    outputToken: opportunity.token,
                    amount: opportunity.amount,
                    slippage: this.settings.maxSlippage
                });
            } else {
                await window.jupiter.swap({
                    inputToken: opportunity.token,
                    outputToken: 'SOL',
                    amount: opportunity.amount,
                    slippage: this.settings.maxSlippage
                });
            }
            
            updatePositionsDisplay();
            
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
                
                // Check if we should close the position
                if (pnlPercent >= this.settings.profitTarget || 
                    pnlPercent <= -this.settings.stopLoss) {
                    await this.closePosition(address);
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
        'max-positions': 'autoTrading.maxPositions'
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
