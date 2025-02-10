// Base Strategy class that all strategies will extend
class Strategy {
    constructor(name, config = {}) {
        this.name = name;
        this.config = {
            timeframe: '5m',
            minVolume: 10000,
            minLiquidity: 50000,
            ...config
        };
        
        this.state = {
            active: false,
            lastUpdate: null,
            signals: new Map(),
            performance: {
                totalTrades: 0,
                winningTrades: 0,
                losingTrades: 0,
                totalProfit: 0,
                maxDrawdown: 0
            }
        };
    }

    async initialize() {
        try {
            this.state.active = true;
            this.state.lastUpdate = Date.now();
            Logger.log('INFO', `Strategy ${this.name} initialized`);
            return true;
        } catch (error) {
            Logger.log('ERROR', `Failed to initialize strategy ${this.name}`, error);
            return false;
        }
    }

    async updateSignals(marketData) {
        throw new Error('updateSignals must be implemented by strategy');
    }

    async validateSignal(signal) {
        throw new Error('validateSignal must be implemented by strategy');
    }

    async getPosition(token) {
        throw new Error('getPosition must be implemented by strategy');
    }
}

// Momentum Strategy implementation
class MomentumStrategy extends Strategy {
    constructor(config = {}) {
        super('Momentum', {
            rsiPeriod: 14,
            rsiOverbought: 70,
            rsiOversold: 30,
            emaPeriod: 20,
            volumeMultiplier: 2,
            ...config
        });
    }

    async updateSignals(marketData) {
        try {
            const signals = new Map();
            
            for (const [token, data] of Object.entries(marketData)) {
                // Calculate technical indicators
                const rsi = await this.calculateRSI(data.prices, this.config.rsiPeriod);
                const ema = await this.calculateEMA(data.prices, this.config.emaPeriod);
                const volumeMA = await this.calculateVolumeMA(data.volumes);
                
                // Generate signal based on conditions
                let signal = null;
                
                // Oversold condition with volume confirmation
                if (rsi < this.config.rsiOversold && 
                    data.price > ema && 
                    data.volume > volumeMA * this.config.volumeMultiplier) {
                    signal = {
                        type: 'BUY',
                        strength: (this.config.rsiOversold - rsi) / this.config.rsiOversold,
                        indicators: { rsi, ema, volumeMA }
                    };
                }
                // Overbought condition
                else if (rsi > this.config.rsiOverbought && data.price < ema) {
                    signal = {
                        type: 'SELL',
                        strength: (rsi - this.config.rsiOverbought) / (100 - this.config.rsiOverbought),
                        indicators: { rsi, ema, volumeMA }
                    };
                }
                
                if (signal) {
                    signals.set(token, signal);
                }
            }
            
            this.state.signals = signals;
            this.state.lastUpdate = Date.now();
            
            return signals;
        } catch (error) {
            Logger.log('ERROR', 'Failed to update momentum signals', error);
            throw error;
        }
    }

    async validateSignal(signal) {
        try {
            // Basic signal validation
            if (!signal || !signal.type || !signal.strength) {
                return false;
            }
            
            // Check signal strength
            if (signal.strength < 0.3) { // Minimum 30% strength required
                return false;
            }
            
            // Check technical indicators
            const { rsi, ema, volumeMA } = signal.indicators;
            
            if (signal.type === 'BUY') {
                return rsi < this.config.rsiOversold && signal.price > ema;
            } else if (signal.type === 'SELL') {
                return rsi > this.config.rsiOverbought && signal.price < ema;
            }
            
            return false;
        } catch (error) {
            Logger.log('ERROR', 'Signal validation failed', error);
            return false;
        }
    }

    // Technical indicator calculations
    async calculateRSI(prices, period) {
        try {
            // RSI calculation implementation
            return 50; // Placeholder
        } catch (error) {
            Logger.log('ERROR', 'RSI calculation failed', error);
            throw error;
        }
    }

    async calculateEMA(prices, period) {
        try {
            // EMA calculation implementation
            return prices[prices.length - 1]; // Placeholder
        } catch (error) {
            Logger.log('ERROR', 'EMA calculation failed', error);
            throw error;
        }
    }

    async calculateVolumeMA(volumes) {
        try {
            // Volume Moving Average calculation
            return volumes[volumes.length - 1]; // Placeholder
        } catch (error) {
            Logger.log('ERROR', 'Volume MA calculation failed', error);
            throw error;
        }
    }
}

// Mean Reversion Strategy implementation
class MeanReversionStrategy extends Strategy {
    constructor(config = {}) {
        super('MeanReversion', {
            bollingerPeriod: 20,
            bollingerStdDev: 2,
            minDeviation: 0.02,
            maxDeviation: 0.1,
            ...config
        });
    }

    async updateSignals(marketData) {
        try {
            const signals = new Map();
            
            for (const [token, data] of Object.entries(marketData)) {
                // Calculate Bollinger Bands
                const bands = await this.calculateBollingerBands(
                    data.prices,
                    this.config.bollingerPeriod,
                    this.config.bollingerStdDev
                );
                
                // Calculate deviation from mean
                const deviation = (data.price - bands.middle) / bands.middle;
                
                let signal = null;
                
                // Price below lower band
                if (deviation < -this.config.minDeviation && 
                    deviation > -this.config.maxDeviation) {
                    signal = {
                        type: 'BUY',
                        strength: Math.abs(deviation) / this.config.maxDeviation,
                        indicators: { ...bands, deviation }
                    };
                }
                // Price above upper band
                else if (deviation > this.config.minDeviation && 
                         deviation < this.config.maxDeviation) {
                    signal = {
                        type: 'SELL',
                        strength: deviation / this.config.maxDeviation,
                        indicators: { ...bands, deviation }
                    };
                }
                
                if (signal) {
                    signals.set(token, signal);
                }
            }
            
            this.state.signals = signals;
            this.state.lastUpdate = Date.now();
            
            return signals;
        } catch (error) {
            Logger.log('ERROR', 'Failed to update mean reversion signals', error);
            throw error;
        }
    }

    async validateSignal(signal) {
        try {
            if (!signal || !signal.type || !signal.strength) {
                return false;
            }
            
            const { deviation } = signal.indicators;
            
            // Validate deviation is within acceptable range
            if (Math.abs(deviation) < this.config.minDeviation || 
                Math.abs(deviation) > this.config.maxDeviation) {
                return false;
            }
            
            return true;
        } catch (error) {
            Logger.log('ERROR', 'Signal validation failed', error);
            return false;
        }
    }

    async calculateBollingerBands(prices, period, stdDev) {
        try {
            // Bollinger Bands calculation implementation
            const middle = prices[prices.length - 1];
            return {
                upper: middle * (1 + 0.02),
                middle: middle,
                lower: middle * (1 - 0.02)
            }; // Placeholder
        } catch (error) {
            Logger.log('ERROR', 'Bollinger Bands calculation failed', error);
            throw error;
        }
    }
}

// Export strategy classes
window.Strategy = Strategy;
window.MomentumStrategy = MomentumStrategy;
window.MeanReversionStrategy = MeanReversionStrategy;
