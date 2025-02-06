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

// Trading settings handler
function setupTradingSettings() {
    const updateSetting = (id, property) => {
        const input = document.getElementById(id);
        input.value = tradingBot.settings[property];
        input.addEventListener('change', (e) => {
            const value = parseFloat(e.target.value);
            if (!isNaN(value)) {
                tradingBot.settings[property] = value;
            }
        });
    };
    
    updateSetting('tradeSize', 'tradeSize');
    updateSetting('maxSlippage', 'maxSlippage');
    updateSetting('profitTarget', 'profitTarget');
    updateSetting('stopLoss', 'stopLoss');
}

// Update positions display
function updatePositionsDisplay() {
    const positionsList = document.getElementById('positionsList');
    const positions = Array.from(tradingBot.positions.entries());
    
    if (positions.length === 0) {
        positionsList.innerHTML = '<div class="no-positions" role="row">No active positions</div>';
        return;
    }
    
    positionsList.innerHTML = positions.map(([address, position]) => `
        <div class="position-row" role="row">
            <div role="cell">${position.symbol}</div>
            <div role="cell">$${position.entryPrice.toFixed(6)}</div>
            <div role="cell">$${position.currentPrice ? position.currentPrice.toFixed(6) : '...'}</div>
            <div role="cell" class="${position.profitLoss >= 0 ? 'profit' : 'loss'}">
                ${position.profitLoss ? position.profitLoss.toFixed(2) : '0.00'}%
            </div>
            <div role="cell">
                <button onclick="tradingBot.closePosition('${address}')" 
                        class="close-position"
                        aria-label="Close position for ${position.symbol}">
                    Close
                </button>
            </div>
        </div>
    `).join('');
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
            
            setupTradingSettings();
            updatePositionsDisplay();
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
