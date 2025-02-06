// DexScreener Integration
class DexScreener {
    constructor() {
        this.baseUrl = 'https://api.dexscreener.com/latest';
        this.trendingCache = new Map();
        this.cacheTimeout = 60000; // 1 minute cache
    }

    // Get token information by contract address
    async getTokenInfo(address) {
        try {
            const response = await fetch(`${this.baseUrl}/dex/tokens/${address}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching token info:', error);
            throw error;
        }
    }

    // Get pair information
    async getPairInfo(pairAddress) {
        try {
            const response = await fetch(`${this.baseUrl}/dex/pairs/solana/${pairAddress}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching pair info:', error);
            throw error;
        }
    }

    // Search for tokens
    async searchTokens(query) {
        try {
            const response = await fetch(`${this.baseUrl}/dex/search/?q=${query}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error searching tokens:', error);
            throw error;
        }
    }

    // Get trending tokens on Solana
    async getTrendingTokens() {
        try {
            const now = Date.now();
            if (this.trendingCache.has('trending') && 
                now - this.trendingCache.get('trending').timestamp < this.cacheTimeout) {
                return this.trendingCache.get('trending').data;
            }

            const response = await fetch(`${this.baseUrl}/dex/tokens/SOL`);
            if (!response.ok) throw new Error('Failed to fetch trending tokens');
            
            const data = await response.json();
            const tokens = data.pairs
                .filter(pair => {
                    const priceUsd = parseFloat(pair.priceUsd);
                    const volume24h = parseFloat(pair.volume.h24);
                    return priceUsd && volume24h > 10000; // Min $10k daily volume
                })
                .sort((a, b) => parseFloat(b.volume.h24) - parseFloat(a.volume.h24))
                .slice(0, 10);

            const trending = tokens.map(token => ({
                symbol: token.baseToken.symbol,
                name: token.baseToken.name,
                address: token.baseToken.address,
                price: parseFloat(token.priceUsd),
                priceChange24h: parseFloat(token.priceChange.h24),
                volume24h: parseFloat(token.volume.h24),
                liquidity: parseFloat(token.liquidity.usd)
            }));

            this.trendingCache.set('trending', {
                timestamp: now,
                data: trending
            });

            return trending;
        } catch (error) {
            console.error('Error fetching trending tokens:', error);
            throw error;
        }
    }

    // Get token metrics
    async getTokenMetrics(address) {
        try {
            const response = await fetch(`${this.baseUrl}/dex/tokens/${address}`);
            if (!response.ok) throw new Error('Failed to fetch token metrics');
            
            const data = await response.json();
            const pair = data.pairs[0];
            
            return {
                price: parseFloat(pair.priceUsd),
                priceChange24h: parseFloat(pair.priceChange.h24),
                volume24h: parseFloat(pair.volume.h24),
                liquidity: parseFloat(pair.liquidity.usd),
                fdv: parseFloat(pair.fdv),
                transactions24h: pair.txns.h24.total
            };
        } catch (error) {
            console.error('Error fetching token metrics:', error);
            throw error;
        }
    }

    // Format price with appropriate decimals
    formatPrice(price) {
        if (price < 0.0001) return price.toExponential(4);
        if (price < 0.01) return price.toFixed(6);
        if (price < 1) return price.toFixed(4);
        return price.toFixed(2);
    }

    // Calculate price change color
    getPriceChangeColor(priceChange) {
        if (priceChange > 0) return '#4caf50';
        if (priceChange < 0) return '#f44336';
        return '#9e9e9e';
    }

    // Format market cap
    formatMarketCap(marketCap) {
        if (!marketCap) return 'N/A';
        if (marketCap >= 1e9) return `$${(marketCap / 1e9).toFixed(2)}B`;
        if (marketCap >= 1e6) return `$${(marketCap / 1e6).toFixed(2)}M`;
        if (marketCap >= 1e3) return `$${(marketCap / 1e3).toFixed(2)}K`;
        return `$${marketCap.toFixed(2)}`;
    }

    // Monitor pair for price updates
    async monitorPair(pairAddress, callback, interval = 30000) {
        let lastPrice = null;

        const updatePrice = async () => {
            try {
                const data = await this.getPairInfo(pairAddress);
                const pair = data.pairs[0];
                
                const metrics = {
                    price: parseFloat(pair.priceUsd),
                    priceChange24h: pair.priceChange.h24,
                    volume24h: pair.volume.h24,
                    liquidity: pair.liquidity.usd,
                    marketCap: pair.fdv,
                    lastUpdated: new Date(),
                    txns24h: {
                        buys: pair.txns.h24.buys,
                        sells: pair.txns.h24.sells
                    }
                };

                if (lastPrice !== null) {
                    metrics.priceChangeSinceLastUpdate = ((metrics.price - lastPrice) / lastPrice) * 100;
                }

                lastPrice = metrics.price;
                callback(metrics);
            } catch (error) {
                console.error('Error updating pair info:', error);
            }
        };

        // Initial update
        await updatePrice();

        // Set up interval for updates
        return setInterval(updatePrice, interval);
    }
}

// Initialize DexScreener
const dexscreener = new DexScreener();
