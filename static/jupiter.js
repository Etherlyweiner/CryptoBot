// Jupiter DEX Integration
class JupiterDEX {
    constructor() {
        this.jupiter = null;
        this.initialized = false;
        this.TOKENS = {
            SOL: 'So11111111111111111111111111111111111111112',  // Wrapped SOL
            BONK: 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  // BONK
            WIF: 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',   // WIF (dogwifhat)
            MYRO: 'HhJpBhRRn4g56VsyLuT8DL5Bv31HkXqsrahTTUCZeZg4',  // MYRO
            POPCAT: 'p0pCat7gYwwtHrXs8EFUKKiuZPUGHthVbRsxQKQ8Yw8'   // POPCAT
        };
        this.DEFAULT_SLIPPAGE = 100; // 1% slippage for memecoins
        this.PRIORITY_FEE = 100000; // 0.0001 SOL priority fee
        this.priceMonitors = {};
    }

    async initialize() {
        try {
            console.log('Initializing Jupiter DEX...');
            
            // Initialize Jupiter SDK
            const quoteApi = new window.JupiterApi.QuoteApi({
                cluster: 'mainnet-beta'
            });

            const swapApi = new window.JupiterApi.SwapApi({
                cluster: 'mainnet-beta'
            });

            this.jupiter = {
                quoteApi,
                swapApi
            };

            this.initialized = true;
            console.log('Jupiter DEX initialized successfully');
            
            // Start monitoring prices
            await this.startPriceMonitoring();
            
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

    async startPriceMonitoring() {
        // Monitor prices for all tokens
        for (const [token, mint] of Object.entries(this.TOKENS)) {
            if (token === 'SOL') continue; // Skip SOL as it's our base currency
            
            let lastPrice = null;
            
            this.priceMonitors[token] = setInterval(async () => {
                try {
                    const currentPrice = await this.getTokenPrice(mint);
                    const priceChange = lastPrice ? ((currentPrice - lastPrice) / lastPrice) * 100 : 0;
                    
                    // Update UI
                    const priceElement = document.getElementById(`${token.toLowerCase()}Price`);
                    const changeElement = document.getElementById(`${token.toLowerCase()}Change`);
                    
                    if (priceElement) {
                        priceElement.textContent = currentPrice.toFixed(8);
                    }
                    
                    if (changeElement) {
                        changeElement.textContent = `${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}%`;
                        changeElement.className = `token-change ${priceChange >= 0 ? 'profit' : 'loss'}`;
                    }
                    
                    lastPrice = currentPrice;
                } catch (error) {
                    console.error('Error monitoring price:', error);
                }
            }, 10000); // Update every 10 seconds
        }
    }

    stopPriceMonitoring() {
        // Clear all price monitors
        for (const interval of Object.values(this.priceMonitors)) {
            clearInterval(interval);
        }
        this.priceMonitors = {};
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
            const txid = await window.walletManager.connection.sendRawTransaction(signedTx.serialize());
            
            // 5. Wait for confirmation
            const confirmation = await window.walletManager.connection.confirmTransaction(txid);
            
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
        
        return setInterval(async () => {
            try {
                const currentPrice = await this.getTokenPrice(tokenMint);
                const priceChange = ((currentPrice - lastPrice) / lastPrice) * 100;
                
                callback(currentPrice, priceChange, {
                    lastPrice,
                    timestamp: Date.now()
                });
                
                lastPrice = currentPrice;
            } catch (error) {
                console.error('Error monitoring price:', error);
            }
        }, interval);
    }
}
