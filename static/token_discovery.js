// Token Discovery and Monitoring
const { BIRDEYE_API, DEXSCREENER_API, JUPITER_API } = window.CONSTANTS;

class TokenDiscovery {
    constructor() {
        this.knownTokens = new Set();
        this.trendingTokens = [];
        this.newListings = [];
        this.lastScanTime = null;
        this.scanInterval = 60000; // Scan every minute
        this.minLiquidity = 1000; // Minimum liquidity in USD
        this.minVolume = 1000; // Minimum 24h volume in USD
    }

    async initialize() {
        console.log('Initializing token discovery...');
        await this.loadKnownTokens();
        this.startScanning();
    }

    async loadKnownTokens() {
        try {
            // Load tokens from Jupiter API
            const response = await fetch(JUPITER_API);
            const tokens = await response.json();
            tokens.forEach(token => this.knownTokens.add(token.address));
            console.log(`Loaded ${this.knownTokens.size} known tokens`);
        } catch (error) {
            console.error('Failed to load known tokens:', error);
        }
    }

    startScanning() {
        console.log('Starting token scanner...');
        this.scanTokens();
        setInterval(() => this.scanTokens(), this.scanInterval);
    }

    async scanTokens() {
        try {
            await Promise.all([
                this.scanBirdeyeTrending(),
                this.scanDexScreener(),
                this.detectNewListings()
            ]);

            // Update UI with new findings
            this.updateTokenList();
            
        } catch (error) {
            console.error('Token scanning error:', error);
        }
    }

    async scanBirdeyeTrending() {
        try {
            const response = await fetch(`${BIRDEYE_API}/trending`, {
                headers: { 'x-chain': 'solana' }
            });
            const data = await response.json();
            
            // Filter and sort trending tokens
            this.trendingTokens = data.data
                .filter(token => 
                    token.liquidity >= this.minLiquidity &&
                    token.volume24h >= this.minVolume
                )
                .sort((a, b) => b.priceChange24h - a.priceChange24h);

            console.log(`Found ${this.trendingTokens.length} trending tokens`);
        } catch (error) {
            console.error('Failed to scan Birdeye trending:', error);
        }
    }

    async scanDexScreener() {
        try {
            const response = await fetch(`${DEXSCREENER_API}/solana`);
            const data = await response.json();
            
            // Process and filter tokens
            const validTokens = data.pairs
                .filter(pair => 
                    pair.liquidity?.usd >= this.minLiquidity &&
                    pair.volume?.h24 >= this.minVolume
                )
                .map(pair => ({
                    address: pair.baseToken.address,
                    symbol: pair.baseToken.symbol,
                    name: pair.baseToken.name,
                    liquidity: pair.liquidity.usd,
                    volume24h: pair.volume.h24,
                    priceChange24h: pair.priceChange.h24,
                    createdAt: pair.pairCreatedAt
                }));

            // Update new listings
            this.processNewListings(validTokens);
        } catch (error) {
            console.error('Failed to scan DexScreener:', error);
        }
    }

    processNewListings(tokens) {
        const currentTime = Date.now();
        const newTokens = tokens.filter(token => {
            const tokenAge = currentTime - token.createdAt;
            const isNew = tokenAge <= 24 * 60 * 60 * 1000; // Less than 24 hours old
            return isNew && !this.knownTokens.has(token.address);
        });

        if (newTokens.length > 0) {
            this.newListings = [...newTokens, ...this.newListings]
                .slice(0, 50); // Keep only top 50 new listings
            console.log(`Found ${newTokens.length} new token listings`);
        }
    }

    async detectNewListings() {
        try {
            const response = await fetch(`${BIRDEYE_API}/pairs/created/last24h`, {
                headers: { 'x-chain': 'solana' }
            });
            const data = await response.json();
            
            // Process new pairs and add to newListings if they meet criteria
            const newPairs = data.data
                .filter(pair => 
                    pair.liquidity >= this.minLiquidity &&
                    !this.knownTokens.has(pair.tokenAddress)
                )
                .map(pair => ({
                    address: pair.tokenAddress,
                    symbol: pair.symbol,
                    name: pair.name,
                    liquidity: pair.liquidity,
                    createdAt: pair.createdAt
                }));

            this.processNewListings(newPairs);
        } catch (error) {
            console.error('Failed to detect new listings:', error);
        }
    }

    updateTokenList() {
        const tokenList = document.getElementById('discovered-tokens');
        if (!tokenList) return;

        // Clear existing list
        tokenList.innerHTML = '';

        // Add trending tokens
        if (this.trendingTokens.length > 0) {
            const trendingSection = document.createElement('div');
            trendingSection.innerHTML = '<h3>🔥 Trending Tokens</h3>';
            this.trendingTokens.slice(0, 5).forEach(token => {
                const tokenItem = this.createTokenListItem(token, 'trending');
                trendingSection.appendChild(tokenItem);
            });
            tokenList.appendChild(trendingSection);
        }

        // Add new listings
        if (this.newListings.length > 0) {
            const newSection = document.createElement('div');
            newSection.innerHTML = '<h3>🆕 New Listings</h3>';
            this.newListings.slice(0, 5).forEach(token => {
                const tokenItem = this.createTokenListItem(token, 'new');
                newSection.appendChild(tokenItem);
            });
            tokenList.appendChild(newSection);
        }
    }

    createTokenListItem(token, type) {
        const item = document.createElement('div');
        item.className = 'token-item';
        
        const priceChange = token.priceChange24h 
            ? `<span class="${token.priceChange24h >= 0 ? 'positive' : 'negative'}">
                ${token.priceChange24h.toFixed(2)}%
               </span>`
            : '';

        item.innerHTML = `
            <div class="token-info">
                <div class="token-name">${token.symbol} ${type === 'new' ? '🆕' : ''}</div>
                <div class="token-address">${token.address.slice(0, 4)}...${token.address.slice(-4)}</div>
            </div>
            <div class="token-metrics">
                ${priceChange}
                <button onclick="selectToken('${token.address}')">Select</button>
            </div>
        `;
        return item;
    }

    getTopTokens(type = 'trending', limit = 5) {
        if (type === 'trending') {
            return this.trendingTokens.slice(0, limit);
        } else if (type === 'new') {
            return this.newListings.slice(0, limit);
        }
        return [];
    }
}

// Initialize token discovery
window.tokenDiscovery = new TokenDiscovery();

// Function to select token for trading
function selectToken(address) {
    document.getElementById('token-address').value = address;
    // Trigger any necessary updates
    if (window.updateTokenInfo) {
        window.updateTokenInfo(address);
    }
}
