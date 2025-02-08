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
            if (window.solanaWeb3 && window.JupiterAg) {
                console.log('All dependencies loaded successfully');
                return true;
            }

            // Log which dependencies are missing
            if (!window.solanaWeb3) console.log('Waiting for Solana Web3...');
            if (!window.JupiterAg) console.log('Waiting for Jupiter SDK...');
            
            await new Promise(resolve => setTimeout(resolve, waitTime));
            attempts++;
            console.log(`Dependency check attempt ${attempts}/${maxAttempts}`);
        }

        const missing = [];
        if (!window.solanaWeb3) missing.push('Solana Web3');
        if (!window.JupiterAg) missing.push('Jupiter SDK');
        
        throw new Error(`Failed to load dependencies: ${missing.join(', ')}`);
    }

    async initialize() {
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
            for (const endpoint of endpoints) {
                try {
                    this.connection = new window.solanaWeb3.Connection(endpoint);
                    await this.connection.getVersion();
                    console.log(`Connected to Solana endpoint: ${endpoint}`);
                    break;
                } catch (error) {
                    console.warn(`Failed to connect to ${endpoint}, trying next endpoint...`);
                }
            }

            if (!this.connection) {
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
        } catch (error) {
            console.error('Failed to initialize Jupiter:', error);
            throw error;
        }
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
