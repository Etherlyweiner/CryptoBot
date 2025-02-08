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
            // Check if dependencies are loaded
            const solanaLoaded = typeof window.solanaWeb3 !== 'undefined';
            const jupiterLoaded = typeof window.Jupiter !== 'undefined';
            
            if (solanaLoaded && jupiterLoaded) {
                console.log('All dependencies loaded successfully');
                return true;
            }

            // Log which dependencies are missing
            if (!solanaLoaded) console.log('Waiting for Solana Web3...');
            if (!jupiterLoaded) console.log('Waiting for Jupiter SDK...');
            
            await new Promise(resolve => setTimeout(resolve, waitTime));
            attempts++;
            console.log(`Dependency check attempt ${attempts}/${maxAttempts}`);
        }

        // If we get here, something didn't load
        const missing = [];
        if (typeof window.solanaWeb3 === 'undefined') missing.push('Solana Web3');
        if (typeof window.Jupiter === 'undefined') missing.push('Jupiter SDK');
        
        throw new Error(`Failed to load dependencies: ${missing.join(', ')}`);
    }

    async initialize() {
        try {
            console.log('Initializing Jupiter DEX...');
            
            // Wait for dependencies with detailed error reporting
            await this.waitForDependencies();

            // Initialize Jupiter connection with fallback endpoints
            const endpoints = [
                'https://api.mainnet-beta.solana.com',
                'https://solana-api.projectserum.com',
                'https://rpc.ankr.com/solana'
            ];

            let connectionError;
            for (const endpoint of endpoints) {
                try {
                    console.log(`Attempting to connect to ${endpoint}...`);
                    this.connection = new window.solanaWeb3.Connection(endpoint, {
                        commitment: 'confirmed',
                        wsEndpoint: endpoint.replace('https', 'wss')
                    });
                    await this.connection.getLatestBlockhash();
                    console.log(`Successfully connected to ${endpoint}`);
                    break;
                } catch (error) {
                    console.warn(`Failed to connect to ${endpoint}:`, error);
                    connectionError = error;
                }
            }

            if (!this.connection) {
                throw connectionError || new Error('Failed to connect to any Solana endpoint');
            }

            // Initialize Jupiter with retries
            console.log('Initializing Jupiter SDK...');
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
                    console.log('Jupiter SDK initialized successfully');
                    break;
                } catch (err) {
                    jupiterInitAttempts++;
                    console.warn(`Jupiter initialization attempt ${jupiterInitAttempts}/3 failed:`, err);
                    if (jupiterInitAttempts === 3) throw err;
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            }

            this.initialized = true;
            console.log('Jupiter DEX initialization complete');
            return true;
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
