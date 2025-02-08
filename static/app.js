// Initialize global variables
let walletConnected = false;
let jupiter = null;
let tradingBot = null;

class TradingBot {
    constructor() {
        this.isTrading = false;
        this.positions = [];
        this.settings = null;
        this.tradeInterval = null;
        console.log('Trading bot initialized');
    }

    async initialize() {
        try {
            // Initialize Jupiter if not already initialized
            if (!window.jupiter) {
                throw new Error('Jupiter instance not found');
            }

            if (!window.jupiter.initialized) {
                await window.jupiter.initialize();
            }

            jupiter = window.jupiter;
            return true;
        } catch (error) {
            console.error('Failed to initialize trading bot:', error);
            throw error;
        }
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
        
        // Start trading loop with error handling
        this.tradeInterval = setInterval(() => {
            this.executeTrade().catch(error => {
                console.error('Trade execution error:', error);
                showMessage('error-message', `Trade error: ${error.message}`, 'alert');
                this.stopTrading();
            });
        }, settings.interval * 1000);

        showMessage('success-message', 'Trading started successfully', 'status');
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
            togglePanel('trading-panel', true);
        } else {
            connectButton.textContent = 'Connect Wallet';
            walletStatus.textContent = 'Not Connected';
            walletStatus.className = 'status disconnected';
            togglePanel('trading-panel', false);
        }
    }
}

function togglePanel(panelId, show) {
    const panel = document.getElementById(panelId);
    if (panel) {
        if (show) {
            panel.setAttribute('role', 'region');
        } else {
            panel.removeAttribute('role');
        }
    }
}

function showMessage(messageId, text, type = 'status') {
    const message = document.getElementById(messageId);
    if (message) {
        message.textContent = text;
        message.setAttribute('role', type);
    }
}

function hideMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.textContent = '';
    }
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM loaded, initializing trading bot...');
    
    // Initialize trading bot
    async function initializeTradingBot() {
        try {
            console.log('Initializing trading bot...');
            
            // Create trading bot instance
            tradingBot = new TradingBot();
            
            // Initialize trading bot
            await tradingBot.initialize().catch(error => {
                console.error('Failed to initialize trading bot:', error);
            });
            
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
    
    await initializeTradingBot();
    
    // Set up wallet status handler
    if (window.walletManager) {
        window.walletManager.onWalletStatusChange = updateWalletStatus;
    }
    
    // Initialize trading controls
    initializeTradingControls();
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
    const positionsElement = document.getElementById('positions');
    if (positionsElement && tradingBot.positions.length > 0) {
        const positionsHtml = tradingBot.positions.map(pos => `
            <div class="position">
                <span>${new Date(pos.time).toLocaleString()}</span>
                <span>${pos.type}</span>
                <span>${pos.price.toFixed(4)}</span>
                <span>${pos.amount.toFixed(4)}</span>
                <span class="status ${pos.status}">${pos.status}</span>
            </div>
        `).join('');
        positionsElement.innerHTML = positionsHtml;
    }
}

function initializeTradingControls() {
    console.log('Initializing trading controls...');
    
    const tradingPanel = document.getElementById('trading-panel');
    const startTradingButton = document.getElementById('start-trading');
    const autoTradingCheckbox = document.getElementById('auto-trading');
    const tradingPairSelect = document.getElementById('trading-pair');
    const tradingAmountInput = document.getElementById('trading-amount');
    const tradingIntervalInput = document.getElementById('trading-interval');
    
    if (!tradingPanel || !startTradingButton || !autoTradingCheckbox || 
        !tradingPairSelect || !tradingAmountInput || !tradingIntervalInput) {
        console.error('Required trading control elements not found');
        return;
    }
    
    console.log('Trading control elements found');
    
    // Initially hide trading panel
    togglePanel('trading-panel', false);
    
    // Enable/disable trading button based on form validity
    function updateTradingButton() {
        const isValid = tradingPairSelect.value && 
                       tradingAmountInput.value >= 0.1 &&
                       tradingIntervalInput.value >= 10;
        startTradingButton.disabled = !isValid;
    }
    
    // Add event listeners
    tradingPairSelect.addEventListener('change', updateTradingButton);
    tradingAmountInput.addEventListener('input', updateTradingButton);
    tradingIntervalInput.addEventListener('input', updateTradingButton);
    
    startTradingButton.addEventListener('click', async () => {
        try {
            startTradingButton.disabled = true;
            showMessage('success-message', 'Starting trading...', 'status');
            
            // Validate settings
            const settings = validateSettings();
            if (!settings) {
                startTradingButton.disabled = false;
                return;
            }
            
            // Start trading
            await tradingBot.startTrading(settings);
            
        } catch (error) {
            console.error('Trading error:', error);
            showMessage('error-message', `Trading error: ${error.message}`, 'alert');
            startTradingButton.disabled = false;
        }
    });
    
    console.log('Trading controls initialized');
}

function showPanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.setAttribute('aria-expanded', 'true');
    }
}

function hidePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.setAttribute('aria-expanded', 'false');
    }
}

function showMessage(messageId, text) {
    const message = document.getElementById(messageId);
    if (message) {
        message.textContent = text;
    }
}

function hideMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.textContent = '';
    }
}
