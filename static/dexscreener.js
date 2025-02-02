// DexScreener Integration
class DexScreener {
    constructor() {
        this.API_BASE = 'https://api.dexscreener.com/latest';
    }

    // Get token information by contract address
    async getTokenInfo(address) {
        try {
            const response = await fetch(`${this.API_BASE}/dex/tokens/${address}`);
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
            const response = await fetch(`${this.API_BASE}/dex/pairs/solana/${pairAddress}`);
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
            const response = await fetch(`${this.API_BASE}/dex/search/?q=${query}`);
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
            const response = await fetch(`${this.API_BASE}/dex/trending`);
            const data = await response.json();
            return data.pairs.filter(pair => pair.chainId === 'solana');
        } catch (error) {
            console.error('Error fetching trending tokens:', error);
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

    // Get token metrics
    async getTokenMetrics(address) {
        try {
            const data = await this.getTokenInfo(address);
            if (!data.pairs || data.pairs.length === 0) {
                throw new Error('No trading pairs found for this token');
            }

            // Get the most liquid pair
            const mainPair = data.pairs.reduce((prev, current) => {
                return (prev.liquidity?.usd || 0) > (current.liquidity?.usd || 0) ? prev : current;
            });

            return {
                price: mainPair.priceUsd,
                priceChange24h: mainPair.priceChange.h24,
                volume24h: mainPair.volume.h24,
                liquidity: mainPair.liquidity.usd,
                marketCap: mainPair.fdv,
                pairAddress: mainPair.pairAddress,
                dexId: mainPair.dexId,
                url: `https://dexscreener.com/solana/${mainPair.pairAddress}`
            };
        } catch (error) {
            console.error('Error getting token metrics:', error);
            throw error;
        }
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
