/**
 * Discovers and tracks tokens for trading.
 */
class TokenDiscovery {
    constructor(config) {
        this.config = config;
        this.initialized = false;
        this.logger = new Logger('TokenDiscovery');
        this.watchlist = new Set();
        this.tokenInfo = new Map();
        
        // Initialize settings from config
        const discovery = config.discovery || {};
        this.settings = {
            minMarketCap: discovery.min_market_cap_usd || 1000000,
            minDailyVolume: discovery.min_daily_volume_usd || 100000,
            maxPriceImpact: discovery.max_price_impact_percent || 2.0,
            blacklistedTokens: discovery.blacklisted_tokens || []
        };
        
        // Cache settings
        this.cache = {
            validityDuration: 5 * 60 * 1000, // 5 minutes
            lastUpdate: null
        };
    }

    /**
     * Initialize token discovery.
     */
    async initialize() {
        try {
            this.logger.info('Initializing token discovery...');

            // Initial token discovery
            await this.updateWatchlist();

            this.initialized = true;
            this.logger.info('Token discovery initialized');
            return true;

        } catch (error) {
            this.logger.error('Failed to initialize token discovery:', error);
            throw error;
        }
    }

    /**
     * Update watchlist with new tokens.
     */
    async updateWatchlist() {
        try {
            const now = Date.now();
            if (this.cache.lastUpdate && now - this.cache.lastUpdate < this.cache.validityDuration) {
                return;
            }

            this.logger.info('Updating token watchlist...');

            // Get top tokens by market cap
            const tokens = await this.fetchTopTokens();

            // Filter tokens based on criteria
            const validTokens = await this.filterTokens(tokens);

            // Update watchlist
            this.watchlist = new Set(validTokens);
            this.cache.lastUpdate = now;

            this.logger.info(`Updated watchlist with ${this.watchlist.size} tokens`);

        } catch (error) {
            this.logger.error('Failed to update watchlist:', error);
            throw error;
        }
    }

    /**
     * Fetch top tokens by market cap.
     */
    async fetchTopTokens() {
        try {
            const response = await fetch(this.config.apis.birdeye.base_url + '/tokens/list', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data.tokens || [];

        } catch (error) {
            this.logger.error('Failed to fetch top tokens:', error);
            throw error;
        }
    }

    /**
     * Filter tokens based on criteria.
     */
    async filterTokens(tokens) {
        try {
            const validTokens = [];

            for (const token of tokens) {
                // Skip blacklisted tokens
                if (this.settings.blacklistedTokens.includes(token.address)) {
                    continue;
                }

                // Check market cap
                if (token.marketCap < this.settings.minMarketCap) {
                    continue;
                }

                // Check volume
                if (token.volume24h < this.settings.minDailyVolume) {
                    continue;
                }

                // Check price impact
                const priceImpact = await this.getPriceImpact(token.address);
                if (priceImpact > this.settings.maxPriceImpact) {
                    continue;
                }

                validTokens.push(token.address);
                this.tokenInfo.set(token.address, {
                    symbol: token.symbol,
                    name: token.name,
                    decimals: token.decimals,
                    marketCap: token.marketCap,
                    volume24h: token.volume24h,
                    lastUpdate: Date.now()
                });
            }

            return validTokens;

        } catch (error) {
            this.logger.error('Failed to filter tokens:', error);
            throw error;
        }
    }

    /**
     * Get price impact for a token.
     */
    async getPriceImpact(tokenAddress) {
        try {
            const response = await fetch(this.config.apis.jupiter.base_url + '/price', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                params: {
                    inputMint: 'So11111111111111111111111111111111111111112', // SOL
                    outputMint: tokenAddress,
                    amount: '1000000000' // 1 SOL in lamports
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data.priceImpactPct || 0;

        } catch (error) {
            this.logger.error('Failed to get price impact:', error);
            return Infinity;
        }
    }

    /**
     * Get current watchlist.
     */
    getWatchlist() {
        return Array.from(this.watchlist);
    }

    /**
     * Get token info.
     */
    getTokenInfo(tokenAddress) {
        return this.tokenInfo.get(tokenAddress);
    }

    /**
     * Close token discovery.
     */
    async close() {
        this.initialized = false;
        this.watchlist.clear();
        this.tokenInfo.clear();
        this.logger.info('Token discovery closed');
    }
}

// Export for Node.js and browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TokenDiscovery;
} else {
    window.TokenDiscovery = TokenDiscovery;
}
