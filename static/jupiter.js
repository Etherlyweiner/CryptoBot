// Jupiter DEX Integration
class JupiterDEX {
    constructor() {
        this.connection = new solanaWeb3.Connection('https://api.mainnet-beta.solana.com');
        
        // Token addresses
        this.TOKENS = {
            SOL: 'So11111111111111111111111111111111111111112',  // Wrapped SOL
            BONK: 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',  // BONK
            WIF: 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',   // WIF (dogwifhat)
            MYRO: 'HCgybxq5Upy8Mccihrp7EsmwwFqYZtrHrsmsKwtGXLgW',  // MYRO
            POPCAT: 'p0pCAt9Y6zw6YgNpkpNHWv2hNuLzrZ3q7pB3rHJGaZ'   // POPCAT
        };
        
        // Default settings
        this.DEFAULT_SLIPPAGE = 50; // 0.5%
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
    async getQuote(inputMint, outputMint, amount, slippageBps = this.DEFAULT_SLIPPAGE) {
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
    async executeSwap(wallet, inputMint, outputMint, amount, slippageBps = this.DEFAULT_SLIPPAGE) {
        try {
            // 1. Get quote
            const quote = await this.getQuote(inputMint, outputMint, amount, slippageBps);
            
            // 2. Get serialized transactions
            const swapRequestBody = {
                quoteResponse: quote,
                userPublicKey: wallet.publicKey,
                wrapAndUnwrapSol: true,
                computeUnitPriceMicroLamports: 1,  // Prioritize transaction
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

    // Get token price in SOL
    async getTokenPrice(tokenMint) {
        try {
            const amount = 1_000_000_000; // 1 SOL in lamports
            const quote = await this.getQuote('SOL', tokenMint, amount);
            return {
                price: quote.outputAmount,
                priceImpactPct: quote.priceImpactPct,
                timestamp: Date.now()
            };
        } catch (error) {
            console.error('Error getting token price:', error);
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
