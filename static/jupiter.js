class JupiterDEX {
    constructor() {
        this.jupiter = null;
        this.initialized = false;
        this.TOKENS = {
            SOL: 'So11111111111111111111111111111111111111112'
        };
    }

    async initialize() {
        try {
            console.log('Initializing Jupiter DEX...');
            
            if (!window.JupiterApi) {
                throw new Error('Jupiter API not loaded');
            }
            
            // Use Helius RPC endpoint
            const rpcEndpoint = 'https://staked.helius-rpc.com?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c';
            const connection = new solanaWeb3.Connection(rpcEndpoint);
            
            // Initialize Jupiter SDK
            this.jupiter = {
                quoteApi: new window.JupiterApi.QuoteApi({
                    cluster: 'mainnet-beta',
                    connection: connection
                }),
                swapApi: new window.JupiterApi.SwapApi({
                    cluster: 'mainnet-beta',
                    connection: connection
                }),
                connection: connection
            };

            // Test the connection
            try {
                await this.jupiter.connection.getRecentBlockhash();
                console.log('Jupiter connection test successful');
            } catch (error) {
                throw new Error('Failed to connect to Solana: ' + error.message);
            }

            this.initialized = true;
            console.log('Jupiter DEX initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Jupiter:', error);
            this.initialized = false;
            throw error;
        }
    }

    async getQuote(inputMint, outputMint, amount, slippageBps = 100) {
        try {
            if (!this.initialized) {
                await this.initialize();
            }

            if (!this.jupiter?.quoteApi) {
                throw new Error('Jupiter not initialized');
            }

            console.log('Getting quote:', {
                inputMint: inputMint.toString(),
                outputMint: outputMint.toString(),
                amount: amount.toString(),
                slippageBps
            });

            const quoteResponse = await this.jupiter.quoteApi.getQuote({
                inputMint: inputMint.toString(),
                outputMint: outputMint.toString(),
                amount: amount.toString(),
                slippageBps
            });

            return quoteResponse.data;
            
        } catch (error) {
            console.error('Failed to get quote:', error);
            throw error;
        }
    }

    async executeSwap(quote, wallet) {
        try {
            if (!this.initialized) {
                await this.initialize();
            }

            if (!this.jupiter?.swapApi) {
                throw new Error('Jupiter not initialized');
            }

            if (!wallet) {
                throw new Error('Wallet not connected');
            }

            console.log('Executing swap with quote:', quote);

            const swapResult = await this.jupiter.swapApi.postSwap({
                quoteResponse: quote,
                userPublicKey: wallet.publicKey.toString(),
                wrapUnwrapSOL: true,
                computeUnitPriceMicroLamports: 1000
            });

            return swapResult.data;
            
        } catch (error) {
            console.error('Failed to execute swap:', error);
            throw error;
        }
    }

    async getTokenPrice(mint) {
        try {
            if (!this.initialized) {
                await this.initialize();
            }

            // Get quote for token to USDC (6 decimals)
            const quote = await this.getQuote(
                mint,
                'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', // USDC
                1e9 // 1 token
            );

            // Convert to USD price
            const price = quote.outAmount / 1e6; // USDC has 6 decimals
            return price;
            
        } catch (error) {
            console.error('Failed to get token price:', error);
            throw error;
        }
    }
}

// Initialize Jupiter DEX globally
window.jupiter = new JupiterDEX();
