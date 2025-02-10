const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class Deployment {
    constructor() {
        this.startTime = new Date();
        this.logFile = path.join(__dirname, '../logs/deployment.log');
        this.ensureLogDirectory();
    }

    ensureLogDirectory() {
        const logDir = path.dirname(this.logFile);
        if (!fs.existsSync(logDir)) {
            fs.mkdirSync(logDir, { recursive: true });
        }
    }

    log(message) {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] ${message}\n`;
        console.log(message);
        fs.appendFileSync(this.logFile, logMessage);
    }

    async deploy() {
        try {
            this.log('Starting deployment process...');

            // 1. Run pre-deployment checks
            await this.preDeploymentChecks();

            // 2. Backup current state
            await this.backupCurrentState();

            // 3. Update configuration
            await this.updateConfiguration();

            // 4. Deploy application
            await this.deployApplication();

            // 5. Run post-deployment checks
            await this.postDeploymentChecks();

            // 6. Start trading system
            await this.startTradingSystem();

            this.log('Deployment completed successfully!');
            return true;
        } catch (error) {
            this.log(`Deployment failed: ${error.message}`);
            await this.rollback();
            return false;
        }
    }

    async preDeploymentChecks() {
        this.log('Running pre-deployment checks...');

        // Check system requirements
        this.checkSystemRequirements();

        // Verify environment variables
        this.verifyEnvironmentVariables();

        // Check dependencies
        this.checkDependencies();

        this.log('Pre-deployment checks completed');
    }

    checkSystemRequirements() {
        this.log('Checking system requirements...');
        
        // Check CPU cores
        const cpuCount = require('os').cpus().length;
        if (cpuCount < 4) {
            throw new Error('Insufficient CPU cores. Minimum 4 cores required.');
        }

        // Check available memory
        const totalMemory = require('os').totalmem();
        const minMemory = 8 * 1024 * 1024 * 1024; // 8GB
        if (totalMemory < minMemory) {
            throw new Error('Insufficient memory. Minimum 8GB required.');
        }

        // Check disk space
        const df = execSync('df -k /').toString();
        const available = parseInt(df.split('\n')[1].split(/\s+/)[3]) * 1024;
        if (available < 50 * 1024 * 1024 * 1024) { // 50GB
            throw new Error('Insufficient disk space. Minimum 50GB required.');
        }
    }

    verifyEnvironmentVariables() {
        this.log('Verifying environment variables...');
        
        const requiredVars = [
            'RPC_ENDPOINTS',
            'API_KEYS',
            'SECURITY_SETTINGS',
            'TRADING_PARAMETERS'
        ];

        const missing = requiredVars.filter(v => !process.env[v]);
        if (missing.length > 0) {
            throw new Error(`Missing environment variables: ${missing.join(', ')}`);
        }
    }

    checkDependencies() {
        this.log('Checking dependencies...');
        
        // Check Node.js version
        const nodeVersion = process.version;
        if (nodeVersion.split('.')[0] < 'v14') {
            throw new Error('Node.js version 14 or higher required');
        }

        // Check npm packages
        execSync('npm audit', { stdio: 'inherit' });
    }

    async backupCurrentState() {
        this.log('Creating backup...');
        
        const backupDir = path.join(__dirname, '../backups', 
            `backup-${new Date().toISOString().replace(/:/g, '-')}`);
        
        // Create backup directory
        fs.mkdirSync(backupDir, { recursive: true });

        // Backup configuration
        fs.copyFileSync(
            path.join(__dirname, '../config/config.js'),
            path.join(backupDir, 'config.js')
        );

        // Backup environment
        fs.copyFileSync(
            path.join(__dirname, '../.env'),
            path.join(backupDir, '.env')
        );

        this.log(`Backup created at ${backupDir}`);
    }

    async updateConfiguration() {
        this.log('Updating configuration...');
        
        // Load production configuration
        const prodConfig = require('../config/production.js');

        // Update configuration
        fs.writeFileSync(
            path.join(__dirname, '../config/config.js'),
            JSON.stringify(prodConfig, null, 2)
        );
    }

    async deployApplication() {
        this.log('Deploying application...');

        // Install production dependencies
        execSync('npm ci --production', { stdio: 'inherit' });

        // Build application
        execSync('npm run build', { stdio: 'inherit' });

        // Update permissions
        fs.chmodSync(path.join(__dirname, '../dist'), '755');
    }

    async postDeploymentChecks() {
        this.log('Running post-deployment checks...');

        // Run health check
        const healthCheck = require('../tests/health_check.js');
        await healthCheck.run();

        // Verify API endpoints
        await this.verifyAPIEndpoints();

        // Check database connections
        await this.checkDatabaseConnections();

        this.log('Post-deployment checks completed');
    }

    async verifyAPIEndpoints() {
        this.log('Verifying API endpoints...');
        
        const endpoints = [
            '/api/health',
            '/api/market',
            '/api/trade',
            '/api/performance'
        ];

        for (const endpoint of endpoints) {
            const response = await fetch(`http://localhost:3000${endpoint}`);
            if (!response.ok) {
                throw new Error(`API endpoint ${endpoint} check failed`);
            }
        }
    }

    async checkDatabaseConnections() {
        this.log('Checking database connections...');
        
        // Add database connection checks here
        // This is a placeholder for actual database checks
    }

    async startTradingSystem() {
        this.log('Starting trading system...');

        // Start the trading system
        execSync('npm run start:prod', { stdio: 'inherit' });

        // Verify system is running
        const response = await fetch('http://localhost:3000/api/health');
        if (!response.ok) {
            throw new Error('Trading system failed to start');
        }

        this.log('Trading system started successfully');
    }

    async rollback() {
        this.log('Rolling back deployment...');

        try {
            // Stop the trading system
            execSync('npm run stop', { stdio: 'inherit' });

            // Restore from backup
            const backups = fs.readdirSync(path.join(__dirname, '../backups'));
            const latestBackup = backups[backups.length - 1];

            if (latestBackup) {
                const backupDir = path.join(__dirname, '../backups', latestBackup);

                // Restore configuration
                fs.copyFileSync(
                    path.join(backupDir, 'config.js'),
                    path.join(__dirname, '../config/config.js')
                );

                // Restore environment
                fs.copyFileSync(
                    path.join(backupDir, '.env'),
                    path.join(__dirname, '../.env')
                );
            }

            this.log('Rollback completed');
        } catch (error) {
            this.log(`Rollback failed: ${error.message}`);
            throw error;
        }
    }
}

// Run deployment
if (require.main === module) {
    const deployment = new Deployment();
    deployment.deploy().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = Deployment;
