// Token Discovery and Monitoring
const { BIRDEYE_API } = window.CONSTANTS || {};

if (!BIRDEYE_API) {
    console.error('Required constants are not defined. Make sure constants are loaded before this script.');
}

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
            const response = await fetch('https://token.jup.ag/all');
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
            await this.scanBirdeyeTrending();
            this.updateTokenList();
            
            if (this.lastScanTime) {
                const timeSinceLastScan = Date.now() - this.lastScanTime;
                console.log(`Token scan completed. Time since last scan: ${timeSinceLastScan}ms`);
            }
            this.lastScanTime = Date.now();
        } catch (error) {
            console.error('Error scanning tokens:', error);
        }
    }

    async scanBirdeyeTrending() {
        try {
            const response = await fetch(`${BIRDEYE_API}/trending_tokens?offset=0&limit=50`);
            const data = await response.json();
            
            if (data.success && data.data) {
                this.trendingTokens = data.data
                    .filter(token => {
                        const volume = parseFloat(token.volume24h || 0);
                        const liquidity = parseFloat(token.liquidity || 0);
                        return volume >= this.minVolume && liquidity >= this.minLiquidity;
                    })
                    .map(token => ({
                        address: token.address,
                        symbol: token.symbol,
                        name: token.name,
                        volume24h: token.volume24h,
                        liquidity: token.liquidity,
                        price: token.price,
                        priceChange24h: token.priceChange24h
                    }));
                console.log(`Found ${this.trendingTokens.length} trending tokens`);
            }
        } catch (error) {
            console.error('Error scanning Birdeye trending:', error);
        }
    }

    updateTokenList() {
        const tokenList = document.getElementById('token-list');
        if (!tokenList) return;

        tokenList.innerHTML = '';
        
        // Add trending tokens
        if (this.trendingTokens.length > 0) {
            const trendingSection = document.createElement('div');
            trendingSection.className = 'token-section';
            trendingSection.innerHTML = '<h3>Trending Tokens</h3>';
            
            this.trendingTokens.forEach(token => {
                const tokenElement = document.createElement('div');
                tokenElement.className = 'token-item';
                tokenElement.innerHTML = `
                    <div class="token-info">
                        <span class="token-symbol">${token.symbol}</span>
                        <span class="token-name">${token.name}</span>
                    </div>
                    <div class="token-metrics">
                        <span class="token-price">$${parseFloat(token.price).toFixed(6)}</span>
                        <span class="token-change ${token.priceChange24h >= 0 ? 'positive' : 'negative'}">
                            ${token.priceChange24h >= 0 ? '↑' : '↓'}${Math.abs(token.priceChange24h).toFixed(2)}%
                        </span>
                    </div>
                `;
                tokenElement.onclick = () => this.selectToken(token.address);
                trendingSection.appendChild(tokenElement);
            });
            
            tokenList.appendChild(trendingSection);
        }
    }

    selectToken(address) {
        const tokenInput = document.getElementById('token-address');
        if (tokenInput) {
            tokenInput.value = address;
            // Trigger any necessary updates
            if (window.updateTokenInfo) {
                window.updateTokenInfo(address);
            }
        }
    }
}

// Initialize token discovery after constants are loaded
document.addEventListener('DOMContentLoaded', () => {
    if (window.CONSTANTS) {
        window.tokenDiscovery = new TokenDiscovery();
        window.tokenDiscovery.initialize();
    } else {
        console.error('Constants not loaded. Waiting for constants...');
        const checkConstants = setInterval(() => {
            if (window.CONSTANTS) {
                window.tokenDiscovery = new TokenDiscovery();
                window.tokenDiscovery.initialize();
                clearInterval(checkConstants);
            }
        }, 100);
    }
});
