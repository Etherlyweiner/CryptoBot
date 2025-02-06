// Core trading bot functionality
class TradingBot {
    constructor() {
        this.active = false;
        this.positions = new Map();
        this.settings = {
            tradeSize: 0.1,
            maxSlippage: 1.0,
            profitTarget: 10.0,
            stopLoss: 5.0
        };
        this.onStatusUpdate = null;
        this.initialized = false;
    }

    start() {
        this.active = true;
        if (this.onStatusUpdate) this.onStatusUpdate();
    }

    stop() {
        this.active = false;
        if (this.onStatusUpdate) this.onStatusUpdate();
    }

    async closePosition(address) {
        if (!this.positions.has(address)) return;
        
        try {
            // Close position logic here
            this.positions.delete(address);
            if (this.onStatusUpdate) this.onStatusUpdate();
        } catch (error) {
            console.error('Error closing position:', error);
            showError('Failed to close position: ' + error.message);
        }
    }

    updateSetting(property, value) {
        if (property in this.settings) {
            const numValue = parseFloat(value);
            if (!isNaN(numValue)) {
                this.settings[property] = numValue;
                return true;
            }
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
        'stop-loss': 'stopLoss'
    };

    Object.entries(settingsMap).forEach(([elementId, settingKey]) => {
        const input = document.getElementById(elementId);
        if (input) {
            // Set initial value
            const currentValue = tradingBot.settings[settingKey];
            if (typeof currentValue !== 'undefined') {
                input.value = currentValue;
            }

            // Add change listener
            input.addEventListener('change', (e) => {
                const success = tradingBot.updateSetting(settingKey, e.target.value);
                if (!success) {
                    showError(`Invalid value for ${elementId.replace('-', ' ')}`);
                    // Reset to last valid value
                    e.target.value = tradingBot.settings[settingKey];
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
