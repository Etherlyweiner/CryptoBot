// Token discovery and monitoring
class TokenDiscovery {
    constructor() {
        this.initialized = false;
        this.initPromise = null;
        this.trendingTokens = new Map();
        this.monitoredTokens = new Map();
        this.updateInterval = 60000; // 1 minute
        this.maxMonitoredTokens = 10;
    }

    async initialize() {
        if (this.initPromise) {
            return this.initPromise;
        }

        this.initPromise = (async () => {
            try {
                await this.updateTrendingTokens();
                this.initialized = true;
                this.startMonitoring();
            } catch (error) {
                console.error('Failed to initialize token discovery:', error);
                throw error;
            }
        })();

        return this.initPromise;
    }

    async updateTrendingTokens() {
        try {
            const response = await fetch('https://public-api.birdeye.so/public/trending_tokens', {
                headers: {
                    'x-chain': 'solana',
                    'x-api-key': window.CONSTANTS.BIRDEYE_API_KEY
                }
            });

            if (!response.ok) {
                throw new Error(`Birdeye API error: ${response.status}`);
            }

            const data = await response.json();
            const tokens = data.data?.sort((a, b) => b.volume_24h - a.volume_24h).slice(0, 10) || [];

            // Update trending tokens map
            this.trendingTokens.clear();
            tokens.forEach(token => {
                this.trendingTokens.set(token.address, {
                    address: token.address,
                    name: token.name,
                    symbol: token.symbol,
                    price: token.price,
                    volume24h: token.volume_24h,
                    priceChange24h: token.price_change_24h
                });
            });

            this.updateTokenList();
        } catch (error) {
            console.error('Failed to fetch trending tokens:', error);
            throw error;
        }
    }

    startMonitoring() {
        setInterval(() => {
            this.updateTrendingTokens().catch(console.error);
            this.updateMonitoredTokens().catch(console.error);
        }, this.updateInterval);
    }

    async updateMonitoredTokens() {
        for (const [address, token] of this.monitoredTokens) {
            try {
                const response = await fetch(`https://public-api.birdeye.so/public/price?address=${address}`, {
                    headers: {
                        'x-chain': 'solana',
                        'x-api-key': window.CONSTANTS.BIRDEYE_API_KEY
                    }
                });

                if (!response.ok) {
                    throw new Error(`Birdeye API error: ${response.status}`);
                }

                const data = await response.json();
                const newPrice = data.data?.value;
                
                if (newPrice) {
                    const priceChange = ((newPrice - token.price) / token.price) * 100;
                    this.monitoredTokens.set(address, {
                        ...token,
                        price: newPrice,
                        priceChange24h: priceChange
                    });
                }
            } catch (error) {
                console.error(`Failed to update token ${address}:`, error);
            }
        }

        this.updateTokenList();
    }

    updateTokenList() {
        const container = document.getElementById('token-list');
        if (!container) return;

        let html = '';

        // Add trending tokens
        for (const token of this.trendingTokens.values()) {
            const isMonitored = this.monitoredTokens.has(token.address);
            html += this.createTokenHtml(token, isMonitored);
        }

        container.innerHTML = html;

        // Add event listeners
        container.querySelectorAll('.monitor-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const address = e.target.dataset.address;
                const token = this.trendingTokens.get(address);
                if (token) {
                    if (this.monitoredTokens.has(address)) {
                        this.monitoredTokens.delete(address);
                        e.target.textContent = 'Monitor';
                    } else if (this.monitoredTokens.size < this.maxMonitoredTokens) {
                        this.monitoredTokens.set(address, token);
                        e.target.textContent = 'Unmonitor';
                    }
                }
            });
        });
    }

    createTokenHtml(token, isMonitored) {
        const priceChangeClass = token.priceChange24h >= 0 ? 'positive' : 'negative';
        return `
            <div class="token-item">
                <div class="token-info">
                    <div class="token-name">${token.symbol}</div>
                    <div class="token-address">${token.address.slice(0, 4)}...${token.address.slice(-4)}</div>
                </div>
                <div class="token-metrics">
                    <div>$${token.price.toFixed(6)}</div>
                    <div class="${priceChangeClass}">${token.priceChange24h.toFixed(2)}%</div>
                </div>
                <button class="monitor-btn" data-address="${token.address}">
                    ${isMonitored ? 'Unmonitor' : 'Monitor'}
                </button>
            </div>
        `;
    }
}

// Initialize token discovery
window.tokenDiscovery = new TokenDiscovery();
