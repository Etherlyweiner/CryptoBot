// Initialize Jupiter API globally
window.JupiterApi = {
    QuoteApi: class QuoteApi {
        constructor(config) {
            this.cluster = config.cluster;
            this.connection = config.connection;
        }
        
        async getQuote(params) {
            const { inputMint, outputMint, amount, slippageBps } = params;
            try {
                const response = await fetch(`https://quote-api.jup.ag/v6/quote?inputMint=${inputMint}&outputMint=${outputMint}&amount=${amount}&slippageBps=${slippageBps}`, {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                return { data };
            } catch (error) {
                console.error('Error getting quote:', error);
                throw error;
            }
        }
    },
    SwapApi: class SwapApi {
        constructor(config) {
            this.cluster = config.cluster;
            this.connection = config.connection;
        }
        
        async postSwap(params) {
            try {
                const response = await fetch('https://quote-api.jup.ag/v6/swap', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ...params,
                        computeUnitPriceMicroLamports: 1000 // Priority fee
                    })
                });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                return { data };
            } catch (error) {
                console.error('Error posting swap:', error);
                throw error;
            }
        }
    }
};
