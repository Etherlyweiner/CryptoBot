// Jupiter DEX integration
class JupiterDEX {
    constructor() {
        console.log('Jupiter instance created');
        this.initialized = false;
        this.connection = null;
        this.jupiter = null;
    }

    async waitForDependencies() {
        const maxAttempts = 20;
        const waitTime = 500;
        let attempts = 0;

        while (attempts < maxAttempts) {
            if (window.Jupiter && window.solanaWeb3) {
                return true;
            }
            await new Promise(resolve => setTimeout(resolve, waitTime));
            attempts++;
            console.log(`Waiting for dependencies... Attempt ${attempts}/${maxAttempts}`);
        }
        return false;
    }

    async initialize() {
        try {
            console.log('Initializing Jupiter DEX...');
            
            // Wait for dependencies to be available
            const dependenciesLoaded = await this.waitForDependencies();
            if (!dependenciesLoaded) {
                throw new Error('Required dependencies not loaded after waiting');
            }

            // Initialize Jupiter connection
            const endpoint = 'https://api.mainnet-beta.solana.com';
            this.connection = new window.solanaWeb3.Connection(endpoint, {
                commitment: 'confirmed',
                wsEndpoint: 'wss://api.mainnet-beta.solana.com/'
            });

            // Initialize Jupiter with retries
            let jupiterInitAttempts = 0;
            while (jupiterInitAttempts < 3) {
                try {
                    this.jupiter = await window.Jupiter.load({
                        connection: this.connection,
                        cluster: 'mainnet-beta',
                        platformFeeAndAccounts: {
                            feeBps: 20,
                            feeAccounts: {}
                        }
                    });
                    break;
                } catch (err) {
                    jupiterInitAttempts++;
                    console.warn(`Jupiter initialization attempt ${jupiterInitAttempts} failed:`, err);
                    if (jupiterInitAttempts === 3) throw err;
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }

            this.initialized = true;
            console.log('Jupiter DEX initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Jupiter:', error);
            throw error;
        }
    }

    async testConnection() {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }
            
            // Test by getting a simple route
            const routes = await this.jupiter.computeRoutes({
                inputMint: NATIVE_MINT,
                outputMint: USDC_MINT,
                amount: JSBI.BigInt(100000), // 0.0001 SOL
                slippageBps: 50,
            });

            if (!routes || !routes.routesInfos) {
                throw new Error('Failed to compute routes');
            }

            console.log('Jupiter connection test successful');
            return true;
        } catch (error) {
            console.error('Jupiter connection test failed:', error);
            throw error;
        }
    }

    async getMarketData() {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }

            // Get token list
            const tokens = await this.jupiter.getTokenList();
            
            // Get market info for each token
            const marketData = {
                tokens: []
            };

            for (const token of tokens) {
                try {
                    const marketInfo = await this.jupiter.getMarketInfo(token.address);
                    if (marketInfo) {
                        marketData.tokens.push({
                            address: token.address,
                            symbol: token.symbol,
                            liquidity: marketInfo.liquidity,
                            volume24h: marketInfo.volume24h,
                            price: marketInfo.price
                        });
                    }
                } catch (err) {
                    console.warn(`Failed to get market info for token ${token.symbol}:`, err);
                }
            }

            return marketData;
        } catch (error) {
            console.error('Failed to get market data:', error);
            throw error;
        }
    }

    async getTokenMetadata(tokenAddress) {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }

            const token = await this.jupiter.getToken(tokenAddress);
            if (!token) {
                throw new Error('Token not found');
            }

            return {
                address: token.address,
                symbol: token.symbol,
                name: token.name,
                decimals: token.decimals,
                verified: token.verified || false
            };
        } catch (error) {
            console.error('Failed to get token metadata:', error);
            throw error;
        }
    }

    async getRecentTrades(tokenAddress) {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }

            const trades = await this.jupiter.getRecentTrades(tokenAddress);
            return trades.map(trade => ({
                price: trade.price,
                size: trade.size,
                side: trade.side,
                time: trade.time
            }));
        } catch (error) {
            console.error('Failed to get recent trades:', error);
            throw error;
        }
    }

    async calculatePriceImpact(tokenAddress, amount) {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }

            const route = await this.jupiter.computeRoutes({
                inputMint: NATIVE_MINT,
                outputMint: tokenAddress,
                amount: JSBI.BigInt(amount * 1e9), // Convert SOL to lamports
                slippageBps: 50,
            });

            if (!route || !route.routesInfos || route.routesInfos.length === 0) {
                throw new Error('No routes found');
            }

            return route.routesInfos[0].priceImpactPct;
        } catch (error) {
            console.error('Failed to calculate price impact:', error);
            throw error;
        }
    }

    async swap(params) {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }

            const { inputToken, outputToken, amount, slippage } = params;

            // Compute routes
            const routes = await this.jupiter.computeRoutes({
                inputMint: inputToken === 'SOL' ? NATIVE_MINT : inputToken,
                outputMint: outputToken === 'SOL' ? NATIVE_MINT : outputToken,
                amount: JSBI.BigInt(amount * 1e9), // Convert SOL to lamports
                slippageBps: slippage * 100,
            });

            if (!routes || !routes.routesInfos || routes.routesInfos.length === 0) {
                throw new Error('No routes found');
            }

            // Execute swap
            const result = await this.jupiter.exchange({
                routeInfo: routes.routesInfos[0],
            });

            return {
                success: true,
                inputAmount: amount,
                outputAmount: result.outputAmount / 1e9, // Convert lamports to SOL
                txId: result.txid
            };
        } catch (error) {
            console.error('Swap failed:', error);
            throw error;
        }
    }

    async getQuote(inputMint, outputMint, amount, slippage = 1) {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }

            const quote = await this.jupiter.computeRoutes({
                inputMint,
                outputMint,
                amount,
                slippageBps: slippage * 100,
            });

            return quote;
        } catch (error) {
            console.error('Failed to get quote:', error);
            throw error;
        }
    }

    async executeTrade(route) {
        try {
            if (!this.initialized) {
                throw new Error('Jupiter not initialized');
            }

            const { transactions } = await this.jupiter.exchange({
                routeInfo: route,
            });

            // Sign and send the transaction
            const signature = await window.walletManager.sendTransaction(
                transactions.transaction
            );

            return signature;
        } catch (error) {
            console.error('Failed to execute trade:', error);
            throw error;
        }
    }
}

// Initialize and export Jupiter instance
window.jupiter = new JupiterDEX();
