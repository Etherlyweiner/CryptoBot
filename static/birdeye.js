class BirdeyeAPI {
    constructor() {
        this.API_KEY = '2c3a7a48574f4b9a9c14558377255e6d'; // Birdeye API key
        this.BASE_URL = 'https://public-api.birdeye.so';
        this.trendingTokens = new Map();
        this.newLaunches = new Map();
        this.priceUpdateCallbacks = new Set();
    }

    async fetchTrendingTokens() {
        try {
            const response = await fetch(`${this.BASE_URL}/public/trending_tokens`, {
                headers: {
                    'X-API-KEY': this.API_KEY,
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.data.tokens;
        } catch (error) {
            console.error('Error fetching trending tokens:', error);
            throw error;
        }
    }

    async fetchNewLaunches() {
        try {
            const response = await fetch(`${this.BASE_URL}/public/new_launches`, {
                headers: {
                    'X-API-KEY': this.API_KEY,
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.data.tokens;
        } catch (error) {
            console.error('Error fetching new launches:', error);
            throw error;
        }
    }

    async getTokenPrice(tokenAddress) {
        try {
            const response = await fetch(`${this.BASE_URL}/public/price?address=${tokenAddress}`, {
                headers: {
                    'X-API-KEY': this.API_KEY,
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return {
                price: data.data.value,
                timestamp: data.data.timestamp,
                priceChange24h: data.data.priceChange24h
            };
        } catch (error) {
            console.error('Error fetching token price:', error);
            throw error;
        }
    }

    async getTokenMetadata(tokenAddress) {
        try {
            const response = await fetch(`${this.BASE_URL}/public/token_metadata?address=${tokenAddress}`, {
                headers: {
                    'X-API-KEY': this.API_KEY,
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.data;
        } catch (error) {
            console.error('Error fetching token metadata:', error);
            throw error;
        }
    }

    onPriceUpdate(callback) {
        this.priceUpdateCallbacks.add(callback);
    }

    async startMonitoring(interval = 10000) {
        const updatePrices = async () => {
            try {
                // Fetch trending tokens
                const trendingTokens = await this.fetchTrendingTokens();
                for (const token of trendingTokens) {
                    const price = await this.getTokenPrice(token.address);
                    const metadata = await this.getTokenMetadata(token.address);
                    
                    const tokenInfo = {
                        ...token,
                        ...price,
                        ...metadata,
                        type: 'trending'
                    };
                    
                    this.trendingTokens.set(token.address, tokenInfo);
                }

                // Fetch new launches
                const newLaunches = await this.fetchNewLaunches();
                for (const token of newLaunches) {
                    const price = await this.getTokenPrice(token.address);
                    const metadata = await this.getTokenMetadata(token.address);
                    
                    const tokenInfo = {
                        ...token,
                        ...price,
                        ...metadata,
                        type: 'new_launch'
                    };
                    
                    this.newLaunches.set(token.address, tokenInfo);
                }

                // Notify callbacks
                const allTokens = {
                    trending: Array.from(this.trendingTokens.values()),
                    newLaunches: Array.from(this.newLaunches.values())
                };

                this.priceUpdateCallbacks.forEach(callback => {
                    try {
                        callback(allTokens);
                    } catch (error) {
                        console.error('Error in price update callback:', error);
                    }
                });

            } catch (error) {
                console.error('Error updating prices:', error);
            }
        };

        // Initial update
        await updatePrices();

        // Start periodic updates
        return setInterval(updatePrices, interval);
    }

    async analyzeTradingOpportunity(token) {
        const VOLUME_THRESHOLD = 10000; // $10k minimum volume
        const PRICE_CHANGE_THRESHOLD = 5; // 5% price change
        const LIQUIDITY_THRESHOLD = 50000; // $50k minimum liquidity

        try {
            // Get token metrics
            const price = await this.getTokenPrice(token.address);
            
            // Basic opportunity analysis
            const opportunity = {
                token: token.address,
                symbol: token.symbol,
                isOpportunity: false,
                reasons: [],
                metrics: {
                    price: price.price,
                    priceChange24h: price.priceChange24h,
                    volume24h: token.volume24h,
                    liquidity: token.liquidity
                }
            };

            // Check volume
            if (token.volume24h > VOLUME_THRESHOLD) {
                opportunity.reasons.push('High trading volume');
            }

            // Check price movement
            if (Math.abs(price.priceChange24h) > PRICE_CHANGE_THRESHOLD) {
                opportunity.reasons.push(`Significant price movement: ${price.priceChange24h.toFixed(2)}%`);
            }

            // Check liquidity
            if (token.liquidity > LIQUIDITY_THRESHOLD) {
                opportunity.reasons.push('Sufficient liquidity');
            }

            // New launch bonus
            if (token.type === 'new_launch') {
                opportunity.reasons.push('New token launch');
            }

            // Determine if this is a good opportunity
            opportunity.isOpportunity = opportunity.reasons.length >= 2;

            return opportunity;

        } catch (error) {
            console.error('Error analyzing trading opportunity:', error);
            throw error;
        }
    }
}
