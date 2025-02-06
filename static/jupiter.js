// Jupiter DEX Integration
class JupiterDEX {
    constructor() {
        this.jupiter = null;
        this.initialized = false;
        this.connection = new solanaWeb3.Connection('https://staked.helius-rpc.com?api-key=74d34f4f-e88d-4da1-8178-01ef5749372c');
        this.TOKENS = {
            SOL: 'So11111111111111111111111111111111111111112',  // Wrapped SOL
            BONK: 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  // BONK
            WIF: 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',   // WIF (dogwifhat)
            MYRO: 'HhJpBhRRn4g56VsyLuT8DL5Bv31HkXqsrahTTUCZeZg4',  // MYRO
            POPCAT: 'p0pCat7gYwwtHrXs8EFUKKiuZPUGHthVbRsxQKQ8Yw8'   // POPCAT
        };
        this.DEFAULT_SLIPPAGE = 100; // 1% slippage for memecoins
        this.PRIORITY_FEE = 100000; // 0.0001 SOL priority fee
    }

    async initialize() {
        try {
            console.log('Initializing Jupiter DEX...');
            
            // Load Jupiter API
            this.jupiter = new Jupiter.Load({
                connection: this.connection,
                cluster: 'mainnet-beta',
                user: walletManager.provider,
                platformFeeAndAccounts: {
                    feeBps: 50,  // 0.5% fee
                    feeAccounts: {
                        // Your fee account for collecting trading fees
                        [this.TOKENS.SOL]: 'etherlyweiner'
                    }
                }
            });

            await this.jupiter.init();
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

            const quote = await this.jupiter.quoteSwap({
                inputMint,
                outputMint,
                amount,
                slippageBps,
                onlyDirectRoutes: false
            });

            return {
                inputAmount: amount,
                outputAmount: quote.outAmount,
                priceImpactPct: quote.priceImpactPct,
                routeInfo: quote.routeInfo,
                fees: quote.fees
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

            const result = await this.jupiter.exchange({
                routeInfo: quote.routeInfo
            });

            // Wait for transaction confirmation
            const confirmation = await this.connection.confirmTransaction(result.txid);
            
            if (confirmation.value.err) {
                throw new Error('Transaction failed to confirm');
            }

            return {
                success: true,
                txid: result.txid,
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
            if (!walletManager.isConnected()) {
                throw new Error('Wallet not connected');
            }

            const tokenAccount = await this.jupiter.getTokenAccountInfo(
                walletManager.provider.publicKey,
                tokenMint
            );

            return tokenAccount ? tokenAccount.balance : 0;

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

    // Get token address by symbol
    getTokenAddress(symbol) {
        return this.TOKENS[symbol.toUpperCase()] || null;
    }

    // Get token list from Jupiter
    async getTokenList() {
        try {
            const response = await fetch('https://token.jup.ag/all');
            const tokens = await response.json();
            return tokens;
        } catch (error) {
            console.error('Error fetching token list:', error);
            throw error;
        }
    }

    // Get quote for token swap
    async getQuoteLegacy(inputMint, outputMint, amount, slippageBps = this.DEFAULT_SLIPPAGE) {
        try {
            // Convert token symbols to addresses if needed
            const fromToken = this.getTokenAddress(inputMint) || inputMint;
            const toToken = this.getTokenAddress(outputMint) || outputMint;
            
            const response = await fetch(
                `https://quote-api.jup.ag/v6/quote?inputMint=${fromToken}&outputMint=${toToken}&amount=${amount}&slippageBps=${slippageBps}`
            );
            
            if (!response.ok) {
                throw new Error('Failed to get quote: ' + await response.text());
            }
            
            const quote = await response.json();
            
            // Add human-readable information
            return {
                ...quote,
                inputToken: inputMint,
                outputToken: outputMint,
                inputAmount: amount / 1e9,  // Convert from lamports to SOL
                outputAmount: quote.outAmount / Math.pow(10, quote.outputDecimals),
                priceImpactPct: quote.priceImpactPct,
                slippage: slippageBps / 100
            };
        } catch (error) {
            console.error('Error getting quote:', error);
            throw error;
        }
    }

    // Execute swap transaction
    async executeSwapLegacy(wallet, inputMint, outputMint, amount, slippageBps = this.DEFAULT_SLIPPAGE) {
        try {
            // 1. Get quote
            const quote = await this.getQuoteLegacy(inputMint, outputMint, amount, slippageBps);
            
            // 2. Get serialized transactions
            const swapRequestBody = {
                quoteResponse: quote,
                userPublicKey: wallet.publicKey,
                wrapAndUnwrapSol: true,
                computeUnitPriceMicroLamports: this.PRIORITY_FEE,  // Add priority fee
                asLegacyTransaction: false  // Use versioned transactions
            };
            
            const swapResponse = await fetch('https://quote-api.jup.ag/v6/swap', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(swapRequestBody)
            });
            
            if (!swapResponse.ok) {
                throw new Error('Failed to prepare swap: ' + await swapResponse.text());
            }

            const swapResult = await swapResponse.json();
            const { swapTransaction } = swapResult;
            
            // 3. Execute transaction
            const swapTransactionBuf = Buffer.from(swapTransaction, 'base64');
            const transaction = solanaWeb3.Transaction.from(swapTransactionBuf);
            
            // 4. Sign and execute
            const signedTx = await wallet.signTransaction(transaction);
            const txid = await this.connection.sendRawTransaction(signedTx.serialize());
            
            // 5. Wait for confirmation
            const confirmation = await this.connection.confirmTransaction(txid);
            
            if (confirmation.value.err) {
                throw new Error('Transaction failed: ' + JSON.stringify(confirmation.value.err));
            }
            
            return {
                success: true,
                txid,
                quote,
                confirmation
            };
        } catch (error) {
            console.error('Error executing swap:', error);
            throw error;
        }
    }

    // Monitor token price changes
    async monitorPrice(tokenMint, callback, interval = 10000) {
        let lastPrice = await this.getTokenPrice(tokenMint);
        callback(lastPrice.price, 0, lastPrice);

        return setInterval(async () => {
            try {
                const currentPrice = await this.getTokenPrice(tokenMint);
                const priceChange = ((currentPrice.price - lastPrice.price) / lastPrice.price) * 100;
                callback(currentPrice.price, priceChange, currentPrice);
                lastPrice = currentPrice;
            } catch (error) {
                console.error('Error monitoring price:', error);
            }
        }, interval);
    }
}
