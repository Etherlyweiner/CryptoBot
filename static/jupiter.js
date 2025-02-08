// Jupiter DEX integration
class JupiterDEX {
    constructor() {
        console.log('Jupiter instance created');
        this.initialized = false;
        this.connection = null;
        this.jupiter = null;
        this.initPromise = null;
    }

    async waitForDependencies() {
        const maxAttempts = 30; // Increased from 20
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
            const deps = window.CryptoBot.dependencies;
            if (deps.solanaWeb3 && deps.jupiterAg) {
                console.log('All dependencies loaded successfully');
                return true;
            }

            // Log missing dependencies
            if (!deps.solanaWeb3) console.log('Waiting for Solana Web3...');
            if (!deps.jupiterAg) console.log('Waiting for Jupiter SDK...');
            
            await new Promise(resolve => setTimeout(resolve, waitTime));
            attempts++;
            console.log(`Dependency check attempt ${attempts}/${maxAttempts}`);
        }

        const missing = [];
        const deps = window.CryptoBot.dependencies;
        if (!deps.solanaWeb3) missing.push('Solana Web3');
        if (!deps.jupiterAg) missing.push('Jupiter SDK');
        
        throw new Error(`Failed to load dependencies: ${missing.join(', ')}`);
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
                const endpoints = [
                    'https://api.mainnet-beta.solana.com',
                    'https://solana-mainnet.rpc.extrnode.com',
                    'https://api.metaplex.solana.com'
                ];

                // Try each endpoint until one works
                let connected = false;
                for (const endpoint of endpoints) {
                    try {
                        this.connection = new window.solanaWeb3.Connection(endpoint);
                        await this.connection.getVersion();
                        console.log(`Connected to Solana endpoint: ${endpoint}`);
                        connected = true;
                        break;
                    } catch (error) {
                        console.warn(`Failed to connect to ${endpoint}, trying next endpoint...`);
                    }
                }

                if (!connected) {
                    throw new Error('Failed to connect to any Solana endpoint');
                }

                // Initialize Jupiter with the latest SDK version
                this.jupiter = await window.JupiterAg.Jupiter.load({
                    connection: this.connection,
                    cluster: 'mainnet-beta',
                    env: 'mainnet-beta',
                    defaultSlippageBps: 100 // 1%
                });

                this.initialized = true;
                console.log('Jupiter DEX initialized successfully');
                return true;
            } catch (error) {
                console.error('Failed to initialize Jupiter:', error);
                this.initPromise = null; // Allow retry on failure
                throw error;
            }
        })();

        return this.initPromise;
    }

    async getQuote(inputMint, outputMint, amount, slippage = 1) {
        if (!this.initialized) {
            throw new Error('Jupiter DEX not initialized');
        }

        try {
            const routes = await this.jupiter.computeRoutes({
                inputMint,
                outputMint,
                amount,
                slippageBps: slippage * 100,
                forceFetch: true
            });

            if (!routes || !routes.routesInfos || routes.routesInfos.length === 0) {
                throw new Error('No routes found');
            }

            return routes.routesInfos[0];
        } catch (error) {
            console.error('Failed to get quote:', error);
            throw error;
        }
    }

    async executeSwap(wallet, route) {
        if (!this.initialized) {
            throw new Error('Jupiter DEX not initialized');
        }

        try {
            const { transactions } = await this.jupiter.exchange({
                routeInfo: route,
                userPublicKey: wallet.publicKey,
                wrapUnwrapSOL: true
            });

            const { setupTransaction, swapTransaction, cleanupTransaction } = transactions;

            // Helper function to send and confirm transaction
            const sendAndConfirm = async (transaction) => {
                if (!transaction) return;
                
                try {
                    const signedTx = await wallet.signTransaction(transaction);
                    const txid = await this.connection.sendRawTransaction(signedTx.serialize());
                    await this.connection.confirmTransaction(txid);
                    console.log(`Transaction confirmed: ${txid}`);
                    return txid;
                } catch (error) {
                    console.error('Transaction failed:', error);
                    throw error;
                }
            };

            // Execute transactions in sequence
            if (setupTransaction) await sendAndConfirm(setupTransaction);
            const swapTxid = await sendAndConfirm(swapTransaction);
            if (cleanupTransaction) await sendAndConfirm(cleanupTransaction);

            return swapTxid;
        } catch (error) {
            console.error('Failed to execute swap:', error);
            throw error;
        }
    }
}

// Initialize and export Jupiter instance
window.jupiter = new JupiterDEX();
