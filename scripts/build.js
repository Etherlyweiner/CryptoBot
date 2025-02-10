const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class SystemBuild {
    constructor() {
        this.distDir = path.join(__dirname, '../dist');
        this.sourceDir = path.join(__dirname, '..');
    }

    async build() {
        console.log('Building CryptoBot...');

        try {
            // 1. Clean build directory
            await this.cleanBuild();

            // 2. Install dependencies
            await this.installDependencies();

            // 3. Compile code
            await this.compile();

            // 4. Copy static files
            await this.copyStaticFiles();

            // 5. Create production config
            await this.createProductionConfig();

            console.log('Build completed successfully');
            return true;
        } catch (error) {
            console.error('Build failed:', error);
            return false;
        }
    }

    async cleanBuild() {
        console.log('Cleaning build directory...');

        // Remove existing dist directory
        if (fs.existsSync(this.distDir)) {
            fs.rmSync(this.distDir, { recursive: true });
        }

        // Create new dist directory
        fs.mkdirSync(this.distDir);
    }

    async installDependencies() {
        console.log('Installing dependencies...');

        // Install production dependencies
        execSync('npm ci --production', {
            stdio: 'inherit',
            cwd: this.sourceDir
        });
    }

    async compile() {
        console.log('Compiling code...');

        // Copy server files
        this.copyFile('server.js');
        this.copyFile('run_server.py');

        // Copy static files
        this.copyDirectory('static');

        // Copy tests
        this.copyDirectory('tests');

        // Copy scripts
        this.copyDirectory('scripts');

        // Copy docs
        this.copyDirectory('docs');
    }

    async copyStaticFiles() {
        console.log('Copying static files...');

        // Copy configuration files
        this.copyFile('package.json');
        this.copyFile('package-lock.json');
        this.copyFile('.env.example');

        // Copy documentation
        this.copyFile('README.md');
        this.copyFile('LICENSE');
    }

    async createProductionConfig() {
        console.log('Creating production configuration...');

        const prodConfig = {
            environment: 'production',
            server: {
                port: process.env.PORT || 3000,
                host: '0.0.0.0'
            },
            security: {
                ssl: true,
                rateLimit: {
                    windowMs: 15 * 60 * 1000,
                    max: 100
                }
            },
            trading: {
                maxPositionSize: 1000,
                maxDailyLoss: 100,
                maxTradesPerDay: 10
            },
            monitoring: {
                enabled: true,
                interval: 60000
            }
        };

        // Write production config
        fs.writeFileSync(
            path.join(this.distDir, 'config/production.js'),
            `module.exports = ${JSON.stringify(prodConfig, null, 2)};`
        );
    }

    copyFile(filename) {
        const source = path.join(this.sourceDir, filename);
        const dest = path.join(this.distDir, filename);

        if (fs.existsSync(source)) {
            // Create directory if it doesn't exist
            const dir = path.dirname(dest);
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }

            fs.copyFileSync(source, dest);
        }
    }

    copyDirectory(dirname) {
        const source = path.join(this.sourceDir, dirname);
        const dest = path.join(this.distDir, dirname);

        if (fs.existsSync(source)) {
            // Create directory if it doesn't exist
            if (!fs.existsSync(dest)) {
                fs.mkdirSync(dest, { recursive: true });
            }

            // Copy all files in directory
            const files = fs.readdirSync(source);
            for (const file of files) {
                const sourcePath = path.join(source, file);
                const destPath = path.join(dest, file);

                if (fs.statSync(sourcePath).isDirectory()) {
                    this.copyDirectory(path.join(dirname, file));
                } else {
                    fs.copyFileSync(sourcePath, destPath);
                }
            }
        }
    }
}

// Run build script
if (require.main === module) {
    const systemBuild = new SystemBuild();
    systemBuild.build().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = SystemBuild;
