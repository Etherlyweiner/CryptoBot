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
            // Wait for CryptoBot namespace
            if (!window.CryptoBot) {
                throw new Error('CryptoBot namespace not initialized');
            }

            // Wait for dependencies
            const maxAttempts = 30;
            const waitTime = 500;
            let attempts = 0;

            while (attempts < maxAttempts) {
                const deps = window.CryptoBot.dependencies;
                if (deps.solanaWeb3 && deps.jupiterAg) {
                    break;
                }
                await new Promise(resolve => setTimeout(resolve, waitTime));
                attempts++;
            }

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
        }, this.settings.interval);
    }

    stopTrading() {
        if (this.tradeInterval) {
            clearInterval(this.tradeInterval);
        }
        this.isTrading = false;
        this.settings = null;
    }

    async executeTrade() {
        if (!this.isTrading || !this.settings) {
            return;
        }

        // Execute trade logic here
        try {
            // Get market data
            const quote = await jupiter.getQuote(
                this.settings.inputToken,
                this.settings.outputToken,
                this.settings.amount,
                this.settings.slippage
            );

            if (!quote) {
                throw new Error('Failed to get quote');
            }

            // Execute trade if conditions are met
            const result = await jupiter.executeSwap(window.wallet, quote);
            
            // Record trade
            this.positions.push({
                timestamp: Date.now(),
                inputToken: this.settings.inputToken,
                outputToken: this.settings.outputToken,
                amount: this.settings.amount,
                txId: result
            });

            // Update display
            this.updatePositionsDisplay();
            
        } catch (error) {
            console.error('Trade execution failed:', error);
            throw error;
        }
    }

    updatePositionsDisplay() {
        const positionsElement = document.getElementById('positions');
        if (positionsElement && this.positions.length > 0) {
            const positionsHtml = this.positions.map(pos => `
                <div class="position">
                    <span>${new Date(pos.timestamp).toLocaleString()}</span>
                    <span>${pos.inputToken}</span>
                    <span>${pos.outputToken}</span>
                    <span>${pos.amount.toFixed(4)}</span>
                    <span class="status">${pos.txId}</span>
                </div>
            `).join('');
            positionsElement.innerHTML = positionsHtml;
        }
    }
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM loaded, initializing trading bot...');
    
    try {
        // Initialize trading bot
        tradingBot = new TradingBot();
        await tradingBot.initialize();
        
        // Initialize trading controls
        await initializeTradingControls();
        
        console.log('Trading bot initialized successfully');
    } catch (error) {
        console.error('Failed to initialize:', error);
        showError(`Initialization failed: ${error.message}`);
    }
});

// Initialize trading controls
async function initializeTradingControls() {
    console.log('Initializing trading controls...');
    
    const elements = {
        inputToken: document.getElementById('inputToken'),
        outputToken: document.getElementById('outputToken'),
        amount: document.getElementById('amount'),
        slippage: document.getElementById('slippage'),
        quoteBtn: document.getElementById('quoteBtn'),
        swapBtn: document.getElementById('swapBtn')
    };

    // Verify all elements exist
    for (const [key, element] of Object.entries(elements)) {
        if (!element) {
            throw new Error(`Required element not found: ${key}`);
        }
    }

    console.log('Trading control elements found');

    // Add event listeners
    elements.quoteBtn.addEventListener('click', async () => {
        try {
            const quote = await jupiter.getQuote(
                elements.inputToken.value,
                elements.outputToken.value,
                parseFloat(elements.amount.value),
                parseFloat(elements.slippage.value)
            );
            
            if (quote) {
                elements.swapBtn.disabled = false;
                showSuccess('Quote received successfully');
            }
        } catch (error) {
            console.error('Failed to get quote:', error);
            showError(`Failed to get quote: ${error.message}`);
        }
    });

    elements.swapBtn.addEventListener('click', async () => {
        try {
            if (!window.wallet) {
                throw new Error('Wallet not connected');
            }

            const quote = await jupiter.getQuote(
                elements.inputToken.value,
                elements.outputToken.value,
                parseFloat(elements.amount.value),
                parseFloat(elements.slippage.value)
            );

            if (quote) {
                const result = await jupiter.executeSwap(window.wallet, quote);
                showSuccess(`Swap executed successfully: ${result}`);
            }
        } catch (error) {
            console.error('Failed to execute swap:', error);
            showError(`Failed to execute swap: ${error.message}`);
        }
    });

    console.log('Trading controls initialized');
}

// Helper functions
function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
}

function showSuccess(message) {
    const statusElement = document.getElementById('statusMessage');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.style.display = 'block';
        setTimeout(() => {
            statusElement.style.display = 'none';
        }, 5000);
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
