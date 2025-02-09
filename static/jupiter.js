// Jupiter DEX integration using REST API
class JupiterDEX {
    constructor() {
        console.log('Jupiter instance created');
        this.initialized = false;
        this.connection = null;
        this.initPromise = null;
        this.tokenList = null;
    }

    async waitForDependencies() {
        const maxAttempts = 30;
        const waitTime = 500;
        let attempts = 0;

        // First wait for CryptoBot namespace
        while (!window.CryptoBot && attempts < 10) {
            await new Promise(resolve => setTimeout(resolve, waitTime));
            attempts++;
        }

        if (!window.CryptoBot) {
            throw new Error('CryptoBot namespace not initialized');
        }

        attempts = 0;
        while (attempts < maxAttempts) {
            if (window.solanaWeb3) {
                console.log('✓ All dependencies loaded successfully');
                return true;
            }

            // Log missing dependencies
            if (!window.solanaWeb3) console.log('Waiting for Solana Web3...');
            
            await new Promise(resolve => setTimeout(resolve, waitTime));
            attempts++;
            console.log(`Dependency check attempt ${attempts}/${maxAttempts}`);
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
                console.log('Initializing Jupiter DEX...');
                
                await this.waitForDependencies();

                // Initialize Jupiter connection with fallback endpoints
                const endpoints = window.CryptoBot.config.rpcEndpoints;

                // Try each endpoint until one works
                let connected = false;
                for (const endpoint of endpoints) {
                    try {
                        this.connection = new window.solanaWeb3.Connection(endpoint);
                        const version = await this.connection.getVersion();
                        console.log(`✓ Connected to Solana endpoint: ${endpoint}`, version);
                        connected = true;
                        break;
                    } catch (error) {
                        console.warn(`Failed to connect to ${endpoint}, trying next endpoint...`);
                    }
                }

                if (!connected) {
                    throw new Error('Failed to connect to any Solana endpoint');
                }

                // Load token list
                await this.loadTokenList();

                this.initialized = true;
                console.log('✓ Jupiter DEX initialized successfully');
                return true;
            } catch (error) {
                console.error('Failed to initialize Jupiter:', error);
                this.initPromise = null; // Allow retry on failure
                throw error;
            }
        })();

        return this.initPromise;
    }

    async loadTokenList() {
        try {
            const response = await fetch('https://token.jup.ag/all');
            this.tokenList = await response.json();
            console.log(`✓ Loaded ${this.tokenList.length} tokens`);
        } catch (error) {
            console.error('Failed to load token list:', error);
            throw error;
        }
    }

    async getQuote(inputMint, outputMint, amount, slippage = null) {
        if (!this.initialized) {
            await this.initialize();
        }

        try {
            const slippageBps = slippage ? Math.floor(slippage * 100) : window.CryptoBot.config.defaultSlippage;
            
            // Build quote request URL
            const params = new URLSearchParams({
                inputMint,
                outputMint,
                amount,
                slippageBps,
                feeBps: 0,
                onlyDirectRoutes: false,
                asLegacyTransaction: false
            });

            const response = await fetch(`${window.CryptoBot.config.jupiterApi}/quote?${params}`);
            if (!response.ok) {
                throw new Error(`Quote request failed: ${response.statusText}`);
            }

            const quote = await response.json();
            return quote;
        } catch (error) {
            console.error('Failed to get quote:', error);
            throw error;
        }
    }

    async executeSwap(route, wallet) {
        if (!this.initialized) {
            await this.initialize();
        }

        try {
            // Get serialized transactions
            const swapResponse = await fetch(`${window.CryptoBot.config.jupiterApi}/swap`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    route,
                    userPublicKey: wallet.publicKey.toString(),
                    wrapUnwrapSOL: true,
                    asLegacyTransaction: false
                })
            });

            if (!swapResponse.ok) {
                throw new Error(`Swap request failed: ${swapResponse.statusText}`);
            }

            const swapResult = await swapResponse.json();
            const { swapTransaction } = swapResult;

            // Sign and send the transaction
            const tx = window.solanaWeb3.Transaction.from(
                Buffer.from(swapTransaction, 'base64')
            );

            const signature = await wallet.signAndSendTransaction(tx);
            console.log('Swap executed successfully:', signature);
            return signature;
        } catch (error) {
            console.error('Failed to execute swap:', error);
            throw error;
        }
    }

    async getTokenList() {
        if (!this.tokenList) {
            await this.loadTokenList();
        }
        return this.tokenList;
    }
}

// Initialize and export Jupiter instance
window.jupiter = new JupiterDEX();
