// Core trading bot functionality
class TradingBot {
    constructor() {
        this.isTrading = false;
        this.positions = [];
        this.settings = null;
        this.tradeInterval = null;
        console.log('Trading bot initialized');
    }

    async startTrading(settings) {
        if (this.isTrading) {
            throw new Error('Trading is already active');
        }

        if (!settings.enabled) {
            throw new Error('Auto trading is not enabled');
        }

        this.settings = settings;
        this.isTrading = true;
        
        // Start trading loop
        this.tradeInterval = setInterval(() => {
            this.executeTrade().catch(error => {
                console.error('Trade execution error:', error);
                if (this.onError) this.onError(error);
            });
        }, settings.interval * 1000);

        console.log('Trading started with settings:', settings);
    }

    stopTrading() {
        if (this.tradeInterval) {
            clearInterval(this.tradeInterval);
            this.tradeInterval = null;
        }
        this.isTrading = false;
        console.log('Trading stopped');
    }

    async executeTrade() {
        try {
            if (!jupiter || !jupiter.initialized) {
                throw new Error('Jupiter DEX not initialized');
            }

            // Execute trade logic here
            const trade = {
                time: Date.now(),
                type: 'BUY',
                price: 0,
                amount: 0,
                status: 'pending'
            };

            if (this.onTradeComplete) {
                this.onTradeComplete(trade);
            }

            this.positions.push(trade);
        } catch (error) {
            console.error('Trade execution failed:', error);
            throw error;
        }
    }
}

// Initialize global variables
let walletConnected = false;
let jupiter = null;
let tradingBot = null;

// Status update handler
function updateWalletStatus(status) {
    console.log('Wallet status update:', status);
    walletConnected = status;
    
    // Update UI elements
    const connectButton = document.getElementById('connect-wallet');
    const walletStatus = document.getElementById('wallet-status');
    const tradingPanel = document.getElementById('trading-panel');
    
    if (connectButton && walletStatus && tradingPanel) {
        if (status) {
            connectButton.textContent = 'Disconnect';
            walletStatus.textContent = 'Connected';
            walletStatus.className = 'status connected';
            tradingPanel.style.display = 'block';
        } else {
            connectButton.textContent = 'Connect Wallet';
            walletStatus.textContent = 'Not Connected';
            walletStatus.className = 'status disconnected';
            tradingPanel.style.display = 'none';
        }
    }
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing trading bot...');
    
    // Initialize trading bot
    function initializeTradingBot() {
        try {
            console.log('Initializing trading bot...');
            
            // Create trading bot instance
            tradingBot = new TradingBot();
            
            // Initialize Jupiter DEX if not already initialized
            if (!jupiter) {
                jupiter = new JupiterDEX();
                jupiter.initialize();
            }
            
            // Set up event handlers
            tradingBot.onTradeComplete = (trade) => {
                console.log('Trade completed:', trade);
                updatePositionsDisplay();
                showSuccess('Trade completed successfully');
            };
            
            tradingBot.onError = (error) => {
                console.error('Trading error:', error);
                showError(error.message || 'An error occurred during trading');
            };
            
            console.log('Trading bot initialized successfully');
            return true;
        } catch (error) {
            console.error('Failed to initialize trading bot:', error);
            showError('Failed to initialize trading bot: ' + error.message);
            return false;
        }
    }
    
    initializeTradingBot();
    
    // Set up wallet status handler
    if (window.walletManager) {
        window.walletManager.onWalletStatusChange = updateWalletStatus;
    }
    
    // Initialize trading controls
    initializeTradingControls();
    
    // Initialize wallet connection button
    const connectButton = document.getElementById('connect-wallet');
    if (connectButton) {
        connectButton.addEventListener('click', async () => {
            try {
                if (!walletConnected) {
                    await window.walletManager.connect();
                } else {
                    await window.walletManager.disconnect();
                }
            } catch (error) {
                console.error('Wallet connection error:', error);
                showError('Failed to connect wallet: ' + error.message);
            }
        });
    }
});

// Error handling
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
    console.error(message);
}

function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    if (successDiv) {
        successDiv.textContent = message;
        successDiv.style.display = 'block';
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 5000);
    }
    console.log(message);
}

function initializeTradingControls() {
    console.log('Initializing trading controls...');
    
    // Get trading control elements
    const startButton = document.getElementById('start-trading');
    const autoTradingCheckbox = document.getElementById('auto-trading');
    const tradingPairSelect = document.getElementById('trading-pair');
    const tradingAmountInput = document.getElementById('trading-amount');
    const tradingIntervalInput = document.getElementById('trading-interval');
    
    // Check if elements exist
    if (startButton && autoTradingCheckbox && tradingPairSelect && 
        tradingAmountInput && tradingIntervalInput) {
        console.log('Trading control elements found');
        
        // Start trading button click handler
        startButton.addEventListener('click', async () => {
            console.log('Start trading button clicked');
            
            try {
                // Validate settings
                const settings = validateSettings();
                
                console.log('Validated settings:', settings);
                
                // Apply settings to trading bot
                await tradingBot.startTrading(settings);
                
            } catch (error) {
                console.error('Failed to start trading:', error);
                showError(error.message);
            }
        });
        
        // Auto trading checkbox change handler
        autoTradingCheckbox.addEventListener('change', (e) => {
            tradingBot.settings.enabled = e.target.checked;
        });
        
        // Trading pair select change handler
        tradingPairSelect.addEventListener('change', (e) => {
            tradingBot.settings.tradingPair = e.target.value;
        });
        
        // Trading amount input change handler
        tradingAmountInput.addEventListener('change', (e) => {
            tradingBot.settings.amount = parseFloat(e.target.value);
        });
        
        // Trading interval input change handler
        tradingIntervalInput.addEventListener('change', (e) => {
            tradingBot.settings.interval = parseInt(e.target.value);
        });
        
        console.log('Trading controls initialized');
    } else {
        console.error('Some trading control elements are missing');
    }
}

function validateSettings() {
    const settings = {};
    let valid = true;
    
    // Get trading pair
    const tradingPairSelect = document.getElementById('trading-pair');
    if (tradingPairSelect && tradingPairSelect.value) {
        settings.tradingPair = tradingPairSelect.value;
    } else {
        showError('Please select a trading pair');
        valid = false;
    }
    
    // Get trading amount
    const amountInput = document.getElementById('trading-amount');
    if (amountInput && !isNaN(amountInput.value) && parseFloat(amountInput.value) > 0) {
        settings.amount = parseFloat(amountInput.value);
    } else {
        showError('Please enter a valid trading amount');
        valid = false;
    }
    
    // Get trading interval
    const intervalInput = document.getElementById('trading-interval');
    if (intervalInput && !isNaN(intervalInput.value) && parseInt(intervalInput.value) >= 10) {
        settings.interval = parseInt(intervalInput.value);
    } else {
        showError('Please enter a valid trading interval (minimum 10 seconds)');
        valid = false;
    }
    
    // Check auto trading enabled
    const autoTradingCheckbox = document.getElementById('auto-trading');
    if (autoTradingCheckbox) {
        settings.enabled = autoTradingCheckbox.checked;
    }
    
    return valid ? settings : null;
}

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

function disableSettings(disabled) {
    // Disable/enable all input fields while trading
    const inputs = document.querySelectorAll('.settings-group input');
    inputs.forEach(input => {
        input.disabled = disabled;
    });
}

function connectWallet() {
    const connectButton = document.getElementById('connect-wallet');
    if (!connectButton) {
        console.error('Connect wallet button not found');
        return;
    }

    try {
        connectButton.disabled = true;
        connectButton.textContent = 'Connecting...';
        
        window.walletManager.connect();
        
        if (!jupiter) {
            jupiter = new JupiterDEX();
            jupiter.initialize();
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
