const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class SystemStop {
    constructor() {
        this.pidFile = path.join(__dirname, '../.pid');
    }

    async stop() {
        console.log('Stopping CryptoBot...');

        try {
            // 1. Stop trading operations
            await this.stopTrading();

            // 2. Close open positions
            await this.closePositions();

            // 3. Save state
            await this.saveState();

            // 4. Stop processes
            await this.stopProcesses();

            console.log('CryptoBot stopped successfully');
            return true;
        } catch (error) {
            console.error('Failed to stop CryptoBot:', error);
            return false;
        }
    }

    async stopTrading() {
        console.log('Stopping trading operations...');
        
        try {
            // Send stop signal to trading system
            await fetch('http://localhost:3000/api/trading/stop', {
                method: 'POST'
            });

            // Wait for trades to complete
            await new Promise(resolve => setTimeout(resolve, 5000));

        } catch (error) {
            console.warn('Warning: Could not stop trading gracefully:', error);
        }
    }

    async closePositions() {
        console.log('Closing open positions...');
        
        try {
            // Get open positions
            const response = await fetch('http://localhost:3000/api/positions');
            const positions = await response.json();

            // Close each position
            for (const position of positions) {
                await fetch(`http://localhost:3000/api/positions/${position.id}/close`, {
                    method: 'POST'
                });
            }

        } catch (error) {
            console.warn('Warning: Could not close positions:', error);
        }
    }

    async saveState() {
        console.log('Saving system state...');
        
        try {
            // Save trading state
            await fetch('http://localhost:3000/api/state/save', {
                method: 'POST'
            });

            // Save performance metrics
            await fetch('http://localhost:3000/api/performance/save', {
                method: 'POST'
            });

        } catch (error) {
            console.warn('Warning: Could not save state:', error);
        }
    }

    async stopProcesses() {
        console.log('Stopping processes...');

        try {
            // Read PID file
            if (fs.existsSync(this.pidFile)) {
                const pid = fs.readFileSync(this.pidFile, 'utf8');
                
                // Kill process
                if (process.platform === 'win32') {
                    execSync(`taskkill /PID ${pid} /F`);
                } else {
                    execSync(`kill -15 ${pid}`);
                }

                // Remove PID file
                fs.unlinkSync(this.pidFile);
            }

            // Stop any remaining Node.js processes
            if (process.platform === 'win32') {
                execSync('taskkill /IM node.exe /F');
            } else {
                execSync('pkill -f "node server.js"');
            }

        } catch (error) {
            console.warn('Warning: Could not stop all processes:', error);
        }
    }
}

// Run stop script
if (require.main === module) {
    const systemStop = new SystemStop();
    systemStop.stop().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = SystemStop;
