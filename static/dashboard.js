// Dashboard functionality

class Dashboard {
    constructor() {
        this.statusUpdateInterval = 1000; // 1 second
        this.performanceUpdateInterval = 5000; // 5 seconds
        this.isRunning = false;
        
        // Initialize UI
        this.initializeUI();
        
        // Start update loops
        this.startUpdateLoops();
    }
    
    initializeUI() {
        // Button handlers
        document.getElementById('startBtn').addEventListener('click', () => this.startBot());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopBot());
        
        // Initial updates
        this.updateStatus();
        this.updatePerformance();
        this.updatePositions();
    }
    
    startUpdateLoops() {
        // Regular status updates
        setInterval(() => this.updateStatus(), this.statusUpdateInterval);
        
        // Regular performance updates
        setInterval(() => {
            this.updatePerformance();
            this.updatePositions();
        }, this.performanceUpdateInterval);
    }
    
    async startBot() {
        try {
            const response = await fetch('/api/bot/start', {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('Failed to start bot');
            }
            
            this.log('Bot started successfully');
            this.isRunning = true;
            this.updateButtonStates();
            
        } catch (error) {
            this.log('Error starting bot: ' + error.message, 'error');
        }
    }
    
    async stopBot() {
        try {
            const response = await fetch('/api/bot/stop', {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('Failed to stop bot');
            }
            
            this.log('Bot stopped successfully');
            this.isRunning = false;
            this.updateButtonStates();
            
        } catch (error) {
            this.log('Error stopping bot: ' + error.message, 'error');
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/bot/status');
            const status = await response.json();
            
            if (status.error) {
                this.log(status.error, 'error');
                return;
            }
            
            // Update running state
            this.isRunning = status.is_running;
            this.updateButtonStates();
            
            // Log any errors
            if (status.last_error) {
                this.log(status.last_error, 'error');
            }
            
        } catch (error) {
            console.error('Error updating status:', error);
        }
    }
    
    async updatePerformance() {
        try {
            const response = await fetch('/api/performance');
            const performance = await response.json();
            
            if (performance.error) {
                console.error(performance.error);
                return;
            }
            
            // Update performance metrics
            document.getElementById('totalProfit').textContent = 
                performance.total_profit.toFixed(4) + ' SOL';
            document.getElementById('totalTrades').textContent = 
                performance.total_trades;
            document.getElementById('winRate').textContent = 
                performance.win_rate.toFixed(1) + '%';
            document.getElementById('dailyVolume').textContent = 
                performance.daily_volume.toFixed(4) + ' SOL';
            
        } catch (error) {
            console.error('Error updating performance:', error);
        }
    }
    
    async updatePositions() {
        try {
            const response = await fetch('/api/positions');
            const positions = await response.json();
            
            if (positions.error) {
                console.error(positions.error);
                return;
            }
            
            // Clear existing rows
            const table = document.getElementById('positionsTable');
            table.innerHTML = '';
            
            // Add position rows
            positions.forEach(position => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">${position.token}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${position.size.toFixed(4)}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${position.entry_price.toFixed(4)}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${position.current_price.toFixed(4)}</td>
                    <td class="px-6 py-4 whitespace-nowrap ${position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}">
                        ${position.pnl.toFixed(4)}
                    </td>
                `;
                table.appendChild(row);
            });
            
        } catch (error) {
            console.error('Error updating positions:', error);
        }
    }
    
    updateButtonStates() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        startBtn.disabled = this.isRunning;
        stopBtn.disabled = !this.isRunning;
        
        startBtn.classList.toggle('opacity-50', this.isRunning);
        stopBtn.classList.toggle('opacity-50', !this.isRunning);
    }
    
    log(message, type = 'info') {
        const log = document.getElementById('statusLog');
        const entry = document.createElement('div');
        
        entry.className = type === 'error' ? 'text-red-600' : 'text-gray-800';
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        
        log.insertBefore(entry, log.firstChild);
        
        // Limit log entries
        while (log.children.length > 100) {
            log.removeChild(log.lastChild);
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});
