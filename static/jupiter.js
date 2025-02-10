// Jupiter DEX integration using REST API
class JupiterDEX {
    constructor() {
        this.initialized = false;
        this.connection = null;
        this.initPromise = null;
        this.tokenList = null;
    }

    async waitForDependencies() {
        const maxAttempts = 30;
        const waitTime = 500;
        let attempts = 0;

        while (attempts < maxAttempts) {
            if (window.solanaWeb3) {
                return true;
            }
            
            await new Promise(resolve => setTimeout(resolve, waitTime));
            attempts++;
        }

        throw new Error('Failed to load dependencies: Solana Web3');
    }

    async initialize() {
        // Only initialize once
        if (this.initPromise) {
            return this.initPromise;
        }

        this.initPromise = (async () => {
            try {
                await this.waitForDependencies();
                await this.loadTokenList();
                this.initialized = true;
            } catch (error) {
                console.error('Failed to initialize Jupiter:', error);
                throw error;
            }
        })();

        return this.initPromise;
    }

    async loadTokenList() {
        try {
            const response = await fetch('https://token.jup.ag/all');
            this.tokenList = await response.json();
            return this.tokenList;
        } catch (error) {
            console.error('Failed to load Jupiter token list:', error);
            throw error;
        }
    }

    async getQuote(inputMint, outputMint, amount, slippage = 0.5) {
        if (!this.initialized) {
            await this.initialize();
        }

        try {
            const endpoint = `${window.CryptoBot.config.jupiterApi}/quote`;
            const params = new URLSearchParams({
                inputMint,
                outputMint,
                amount,
                slippageBps: Math.floor(slippage * 100),
                onlyDirectRoutes: false
            });

            const response = await fetch(`${endpoint}?${params}`);
            if (!response.ok) {
                throw new Error(`Jupiter API error: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Failed to get Jupiter quote:', error);
            throw error;
        }
    }

    async executeSwap(quoteResponse, wallet) {
        if (!this.initialized) {
            await this.initialize();
        }

        if (!wallet) {
            throw new Error('Wallet not connected');
        }

        try {
            const { swapTransaction } = quoteResponse;
            const swapTransactionBuf = Buffer.from(swapTransaction, 'base64');
            
            // Sign and send transaction
            const transaction = window.solanaWeb3.Transaction.from(swapTransactionBuf);
            const signature = await wallet.signAndSendTransaction(transaction);
            
            return signature;
        } catch (error) {
            console.error('Failed to execute Jupiter swap:', error);
            throw error;
        }
    }
}

// Initialize and export Jupiter instance
window.jupiter = new JupiterDEX();
