const http = require('http');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');
const express = require('express');
const rateLimit = require('express-rate-limit');

const app = express();
const PORT = process.env.PORT || 8000;

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
});

app.use(limiter);
app.use(express.json());
app.use(express.static('static'));

// MIME types for static files
const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
};

// Create HTTP server
const server = http.createServer(app);

// Create WebSocket server
const wss = new WebSocket.Server({ server });

// WebSocket connection handling
wss.on('connection', (ws) => {
    console.log('New WebSocket client connected');
    
    // Send initial connection success message
    ws.send(JSON.stringify({
        type: 'connection',
        status: 'connected'
    }));
    
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            
            // Handle different message types
            switch (data.type) {
                case 'ping':
                    ws.send(JSON.stringify({
                        type: 'pong',
                        timestamp: data.timestamp
                    }));
                    break;
                    
                case 'subscribe':
                    // Handle subscription requests
                    console.log('Client subscribed to:', data.topics);
                    break;
                    
                default:
                    console.log('Unknown message type:', data.type);
            }
        } catch (error) {
            console.error('Error handling WebSocket message:', error);
        }
    });
    
    ws.on('close', () => {
        console.log('Client disconnected');
    });
});

// API Routes
app.get('/api/status', (req, res) => {
    res.json({
        status: 'running',
        timestamp: new Date().toISOString()
    });
});

app.get('/api/trade-history', (req, res) => {
    // TODO: Implement trade history endpoint
    res.json({
        trades: []
    });
});

app.get('/api/token-prices', (req, res) => {
    // TODO: Implement token prices endpoint
    res.json({
        prices: {}
    });
});

app.get('/api/performance', (req, res) => {
    // TODO: Implement performance metrics endpoint
    res.json({
        metrics: {}
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({
        error: 'Internal Server Error',
        message: err.message
    });
});

// Start server
server.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});
