class StrategyExecutor {
    constructor(tradingBot) {
        this.bot = tradingBot;
        this.strategies = new Map();
        this.activeStrategies = new Set();
        this.executionQueue = [];
        
        this.state = {
            isRunning: false,
            lastExecution: null,
            executionInterval: 60000, // 1 minute
            maxQueueSize: 10,
            minSignalStrength: 0.3
        };
        
        // Performance tracking
        this.performance = {
            totalExecutions: 0,
            successfulExecutions: 0,
            failedExecutions: 0,
            totalProfit: 0,
            winRate: 0
        };
    }

    async initialize() {
        try {
            // Initialize default strategies
            await this.registerStrategy(new window.MomentumStrategy());
            await this.registerStrategy(new window.MeanReversionStrategy());
            
            // Start execution loop
            this.startExecutionLoop();
            
            Logger.log('INFO', 'Strategy executor initialized');
            return true;
        } catch (error) {
            Logger.log('ERROR', 'Failed to initialize strategy executor', error);
            return false;
        }
    }

    async registerStrategy(strategy) {
        try {
            if (await strategy.initialize()) {
                this.strategies.set(strategy.name, strategy);
                Logger.log('INFO', `Strategy ${strategy.name} registered`);
                return true;
            }
            return false;
        } catch (error) {
            Logger.log('ERROR', `Failed to register strategy ${strategy.name}`, error);
            return false;
        }
    }

    async activateStrategy(strategyName) {
        if (this.strategies.has(strategyName)) {
            this.activeStrategies.add(strategyName);
            Logger.log('INFO', `Strategy ${strategyName} activated`);
            return true;
        }
        return false;
    }

    async deactivateStrategy(strategyName) {
        if (this.activeStrategies.has(strategyName)) {
            this.activeStrategies.delete(strategyName);
            Logger.log('INFO', `Strategy ${strategyName} deactivated`);
            return true;
        }
        return false;
    }

    startExecutionLoop() {
        if (this.state.isRunning) return;
        
        this.state.isRunning = true;
        
        const executeLoop = async () => {
            if (!this.state.isRunning) return;
            
            try {
                await this.processSignals();
                await this.executeQueuedTrades();
            } catch (error) {
                Logger.log('ERROR', 'Execution loop error', error);
            }
            
            setTimeout(executeLoop, this.state.executionInterval);
        };
        
        executeLoop();
    }

    async processSignals() {
        try {
            // Get market data
            const marketData = await this.bot.getMarketData();
            
            // Process each active strategy
            for (const strategyName of this.activeStrategies) {
                const strategy = this.strategies.get(strategyName);
                
                // Update signals
                const signals = await strategy.updateSignals(marketData);
                
                // Process valid signals
                for (const [token, signal] of signals.entries()) {
                    if (await this.validateSignal(strategy, signal)) {
                        await this.queueExecution(token, signal, strategy);
                    }
                }
            }
        } catch (error) {
            Logger.log('ERROR', 'Signal processing failed', error);
        }
    }

    async validateSignal(strategy, signal) {
        try {
            // Strategy-specific validation
            if (!await strategy.validateSignal(signal)) {
                return false;
            }
            
            // Check signal strength
            if (signal.strength < this.state.minSignalStrength) {
                return false;
            }
            
            // Risk validation through risk manager
            const riskCheck = await this.bot.riskManager.checkTradeViability(
                signal.token,
                signal.amount,
                signal.price
            );
            
            return riskCheck.viable;
        } catch (error) {
            Logger.log('ERROR', 'Signal validation failed', error);
            return false;
        }
    }

    async queueExecution(token, signal, strategy) {
        try {
            // Check queue size
            if (this.executionQueue.length >= this.state.maxQueueSize) {
                Logger.log('WARN', 'Execution queue full, skipping signal');
                return false;
            }
            
            // Calculate position size
            const positionSize = await this.bot.riskManager.calculatePositionSize(
                token,
                signal.price
            );
            
            // Add to execution queue
            this.executionQueue.push({
                token,
                signal,
                strategy: strategy.name,
                positionSize,
                timestamp: Date.now()
            });
            
            Logger.log('INFO', 'Trade execution queued', {
                token,
                type: signal.type,
                strategy: strategy.name
            });
            
            return true;
        } catch (error) {
            Logger.log('ERROR', 'Failed to queue execution', error);
            return false;
        }
    }

    async executeQueuedTrades() {
        while (this.executionQueue.length > 0) {
            const execution = this.executionQueue.shift();
            
            try {
                // Execute trade
                const result = await this.bot.executeTrade(
                    execution.token,
                    execution.positionSize,
                    execution.signal.type
                );
                
                // Update performance metrics
                this.updatePerformance(execution, result);
                
                Logger.log('INFO', 'Trade executed successfully', {
                    token: execution.token,
                    type: execution.signal.type,
                    strategy: execution.strategy,
                    result
                });
            } catch (error) {
                Logger.log('ERROR', 'Trade execution failed', error);
                this.performance.failedExecutions++;
            }
        }
    }

    updatePerformance(execution, result) {
        this.performance.totalExecutions++;
        
        if (result.success) {
            this.performance.successfulExecutions++;
            this.performance.totalProfit += result.profit;
        } else {
            this.performance.failedExecutions++;
        }
        
        this.performance.winRate = 
            this.performance.successfulExecutions / this.performance.totalExecutions;
    }

    getPerformanceStats() {
        return {
            ...this.performance,
            activeStrategies: Array.from(this.activeStrategies),
            queueSize: this.executionQueue.length,
            lastExecution: this.state.lastExecution
        };
    }
}

// Export strategy executor
window.StrategyExecutor = StrategyExecutor;
