# CryptoBot Deployment Guide

## Deployment Options

### 1. Local Deployment

#### System Requirements

- CPU: 4+ cores
- RAM: 8GB minimum, 16GB recommended
- Storage: 50GB SSD
- OS: Windows 10/11, Ubuntu 20.04+, or macOS 12+
- Network: Stable internet connection with 10+ Mbps

#### Installation Steps

1. **System Preparation**
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y   # Ubuntu
   brew update && brew upgrade              # macOS
   
   # Install system dependencies
   sudo apt install python3-pip nodejs npm  # Ubuntu
   brew install python node                 # macOS
   ```

2. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/CryptoBot.git
   cd CryptoBot
   ```

3. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Unix
   .\venv\Scripts\activate   # Windows
   
   # Install dependencies
   pip install -r requirements.txt
   npm install
   ```

4. **Configuration**
   ```bash
   # Copy and edit environment file
   cp .env.example .env
   nano .env
   
   # Generate configuration
   python init_config.py
   ```

### 2. Docker Deployment

#### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

#### Steps

1. **Build Images**
   ```bash
   docker-compose build
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Monitor Logs**
   ```bash
   docker-compose logs -f
   ```

### 3. Cloud Deployment

#### AWS Deployment

1. **EC2 Setup**
   - Instance type: t3.large or better
   - Storage: 50GB gp3 SSD
   - Security group: Allow ports 80, 443, 3000

2. **Installation**
   ```bash
   # Install system dependencies
   sudo yum update -y
   sudo yum install -y python3-pip nodejs git
   
   # Clone and setup
   git clone https://github.com/yourusername/CryptoBot.git
   cd CryptoBot
   
   # Install dependencies
   pip3 install -r requirements.txt
   npm install
   
   # Configure
   cp .env.example .env
   # Edit .env with production settings
   ```

3. **Setup Process Manager**
   ```bash
   # Install PM2
   npm install -g pm2
   
   # Start services
   pm2 start ecosystem.config.js
   
   # Save PM2 configuration
   pm2 save
   
   # Setup startup script
   pm2 startup
   ```

#### Digital Ocean Deployment

1. **Droplet Setup**
   - Size: 4GB/2CPU minimum
   - OS: Ubuntu 20.04
   - Region: Choose based on target market

2. **Installation**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install dependencies
   sudo apt install -y python3-pip nodejs npm git
   
   # Clone and setup
   git clone https://github.com/yourusername/CryptoBot.git
   cd CryptoBot
   
   # Install app dependencies
   pip3 install -r requirements.txt
   npm install
   ```

3. **Configure Nginx**
   ```bash
   # Install Nginx
   sudo apt install -y nginx
   
   # Configure Nginx
   sudo nano /etc/nginx/sites-available/cryptobot
   ```

   ```nginx
   server {
       listen 80;
       server_name your_domain.com;
   
       location / {
           proxy_pass http://localhost:3000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

   ```bash
   # Enable site
   sudo ln -s /etc/nginx/sites-available/cryptobot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## Security Configuration

### 1. Firewall Setup

```bash
# Ubuntu/Debian
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. SSL Configuration

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx  # Ubuntu
sudo yum install -y certbot python3-certbot-nginx  # CentOS

# Get certificate
sudo certbot --nginx -d your_domain.com
```

### 3. Security Hardening

```bash
# Set file permissions
sudo chown -R $USER:$USER /path/to/CryptoBot
chmod -R 750 /path/to/CryptoBot

# Secure environment file
chmod 600 .env
```

## Monitoring Setup

### 1. System Monitoring

```bash
# Install monitoring tools
sudo apt install -y prometheus node-exporter grafana

# Configure Prometheus
sudo nano /etc/prometheus/prometheus.yml
```

```yaml
scrape_configs:
  - job_name: 'cryptobot'
    static_configs:
      - targets: ['localhost:3000']
```

### 2. Application Monitoring

```bash
# Install monitoring dependencies
pip install prometheus_client
npm install prom-client
```

### 3. Log Management

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/cryptobot
```

```
/path/to/CryptoBot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 640 $USER $USER
}
```

## Backup Configuration

### 1. Database Backup

```bash
# Create backup script
nano backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
pg_dump cryptobot > $BACKUP_DIR/db_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_$DATE.sql

# Remove old backups (keep last 7 days)
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
```

### 2. Configuration Backup

```bash
# Create config backup script
nano backup_config.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup configuration files
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
    .env \
    config/* \
    ecosystem.config.js
```

## Maintenance Procedures

### 1. Updates

```bash
# Update application
git pull
pip install -r requirements.txt
npm install

# Restart services
pm2 restart all
```

### 2. Monitoring

```bash
# Check system status
pm2 status
pm2 logs

# Check system resources
htop
df -h
```

### 3. Backup Verification

```bash
# Test database restore
gunzip -c latest_backup.sql.gz | psql cryptobot

# Test configuration restore
tar -xzf latest_config.tar.gz -C /tmp/test
```

## Troubleshooting

### 1. Common Issues

#### Connection Issues
```bash
# Check network connectivity
ping api.solana.com

# Check RPC status
curl -X POST -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}' \
     https://api.mainnet-beta.solana.com
```

#### Performance Issues
```bash
# Check system resources
top
free -h
df -h

# Check application logs
tail -f logs/error.log
pm2 logs
```

### 2. Recovery Procedures

```bash
# Restart services
pm2 restart all

# Clear cache
rm -rf .cache/*
redis-cli FLUSHALL

# Restore from backup
./restore.sh latest_backup
```

## Scaling Guidelines

### 1. Vertical Scaling

- Increase server resources
- Optimize database indexes
- Enable caching

### 2. Horizontal Scaling

- Set up load balancer
- Add read replicas
- Implement caching layer

### 3. Performance Optimization

- Enable compression
- Implement rate limiting
- Use connection pooling

## Deployment Checklist

- [ ] System requirements verified
- [ ] Dependencies installed
- [ ] Configuration files set up
- [ ] Environment variables configured
- [ ] Security measures implemented
- [ ] SSL certificates installed
- [ ] Monitoring tools configured
- [ ] Backup procedures tested
- [ ] Recovery procedures documented
- [ ] Performance baseline established
