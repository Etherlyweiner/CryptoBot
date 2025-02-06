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
            
            // Use Helius RPC endpoint
            const rpcEndpoint = 'https://staked.helius-rpc.com?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c';
            
            // Initialize Jupiter SDK
            const quoteApi = new window.JupiterApi.QuoteApi({
                cluster: 'mainnet-beta',
                connection: new solanaWeb3.Connection(rpcEndpoint)
            });

            const swapApi = new window.JupiterApi.SwapApi({
                cluster: 'mainnet-beta',
                connection: new solanaWeb3.Connection(rpcEndpoint)
            });

            this.jupiter = {
                quoteApi,
                swapApi,
                connection: new solanaWeb3.Connection(rpcEndpoint)
            };

            this.initialized = true;
            console.log('Jupiter DEX initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Jupiter:', error);
            throw error;
        }
    }

    async getQuote(inputMint, outputMint, amount, slippageBps = 100) {
        try {
            if (!this.initialized) {
                await this.initialize();
            }

            const quoteResponse = await this.jupiter.quoteApi.getQuote({
                inputMint: inputMint.toString(),
                outputMint: outputMint.toString(),
                amount: amount.toString(),
                slippageBps: slippageBps.toString()
            });

            if (!quoteResponse.data) {
                throw new Error('No routes found');
            }

            const bestRoute = quoteResponse.data;
            return {
                inputAmount: amount,
                outputAmount: parseFloat(bestRoute.outAmount),
                priceImpactPct: parseFloat(bestRoute.priceImpactPct),
                routeInfo: bestRoute,
                fees: bestRoute.fees
            };

        } catch (error) {
            console.error('Failed to get quote:', error);
            throw error;
        }
    }

    async executeSwap(quote) {
        try {
            if (!this.initialized) {
                await this.initialize();
            }

            const swapResponse = await this.jupiter.swapApi.postSwap({
                route: quote.routeInfo,
                userPublicKey: window.walletManager.provider.publicKey.toString(),
                wrapUnwrapSOL: true
            });

            if (!swapResponse.data) {
                throw new Error('Failed to create swap transaction');
            }

            // Sign and send transaction
            const transaction = solanaWeb3.Transaction.from(
                Buffer.from(swapResponse.data.swapTransaction, 'base64')
            );

            const signature = await window.walletManager.provider.signAndSendTransaction(transaction);
            
            // Wait for confirmation
            const confirmation = await window.walletManager.connection.confirmTransaction(signature);
            
            if (confirmation.value.err) {
                throw new Error('Transaction failed to confirm');
            }

            return {
                success: true,
                txid: signature,
                inputAmount: quote.inputAmount,
                outputAmount: quote.outputAmount,
                priceImpact: quote.priceImpactPct
            };

        } catch (error) {
            console.error('Swap execution failed:', error);
            throw error;
        }
    }

    async getTokenBalance(tokenMint) {
        try {
            if (!window.walletManager.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const tokenAccount = await window.walletManager.connection.getParsedTokenAccountsByOwner(
                window.walletManager.provider.publicKey,
                { mint: new solanaWeb3.PublicKey(tokenMint) }
            );

            if (tokenAccount.value.length === 0) {
                return 0;
            }

            return tokenAccount.value[0].account.data.parsed.info.tokenAmount.uiAmount;

        } catch (error) {
            console.error('Failed to get token balance:', error);
            throw error;
        }
    }

    async getTokenPrice(tokenMint) {
        try {
            if (!this.initialized) {
                await this.initialize();
            }

            // Get quote for 1 SOL worth of tokens
            const quote = await this.getQuote(
                this.TOKENS.SOL,
                tokenMint,
                1e9 // 1 SOL in lamports
            );

            return quote.outputAmount;

        } catch (error) {
            console.error('Failed to get token price:', error);
            throw error;
        }
    }
}
