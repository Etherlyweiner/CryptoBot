const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = 8443;

const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
};

// Self-signed certificate options
const options = {
    key: `-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDEJ5MRQ4KO3F4k
bCO9JwyCjhCXTHVulg5gFJxV0XRTzRH6DnqcHR8pK4D0BYV0I2GBm7jYIHLVxzA5
B0P1HvVj8tL0tG8Zr5D+5TN1UpQd4jx4NHUkGF8WZT3sQ7oFPy7pGz9LQFj8vpqE
8XZO5RvGyhJB2LrXq9E5Qfh5Gg5YZw5CZxH5Ux5q3RnvOK5dhkKU8jJZxDzO4x5t
0ZyBxLqV8FvFp5ZoYKsXzO5fG5PKx5Q2v8RZkjJu5ZbRwbhWR7/G5Ep2aEzOXH8o
XJBcjHAqrX1Oj5JGdwKbKbS0QI0LyS0eqXJ2Z8pEXXgQ+yK/H3F1ohGHEjLVFHFl
AgMBAAECggEAD6HmzUhqlOB4xnv5RHhA0yh9uIxPCXGjFGXuO+/inCqVWX6qLuYg
KxGRBQZCvvLY1yBAZZZPKYr0y1QGFHhOFjG1njV/vlvXKPGEqHfXwxzj7w0J8Qd4
oqY0VEzGqFVHxoVrXgTh8jzqMhHI4yCUNzgOvF/BT0XZZhJ6qwOzpY0y8U+TuEJ6
kK7MUV2nGU6h6nHvwqLWI6z3oQOEQXJ3uA6K5uBB1LR0Rv8gC4qhRn5LZXZC+Aqg
7dQ5UQIDAQABAoIBAQCJKJoG1iWAkXB2NZiV3pmxHjZoqD0cy7j8QFyCHHvfxFXz
1gXQJ4Zh4qh5HQUXzxlqxPPtXjOHYxmm5YXxwqZA9bTCrW0XZJ5d4lxFxjWvQA0E
7sl2tECg9gylixFH0HRqk7y8FElX0XpWvjwQn0UAQ7o8gPQJ4QIBAAKBgQDEJ5MR
Q4KO3F4kbCO9JwyCjhCXTHVulg5gFJxV0XRTzRH6DnqcHR8pK4D0BYV0I2GBm7jY
IHLVxzA5B0P1HvVj8tL0tG8Zr5D+5TN1UpQd4jx4NHUkGF8WZT3sQ7oFPy7pGz9L
QFj8vpqE8XZO5RvGyhJB2LrXq9E5Qfh5Gg5YZw5CZxH5Ux5q3RnvOK5dhkKU8jJZ
xDzO4x5t0ZyBxLqV8FvFp5ZoYKsXzO5fG5PKx5Q2v8RZkjJu5ZbRwbhWR7/G5Ep2
aEzOXH8oXJBcjHAqrX1Oj5JGdwKbKbS0QI0LyS0eqXJ2Z8pEXXgQ+yK/H3F1ohGH
EjLVFHFlAgMBAAECggEAD6HmzUhqlOB4xnv5RHhA0yh9uIxPCXGjFGXuO+/inCqV
WX6qLuYgKxGRBQZCvvLY1yBAZZZPKYr0y1QGFHhOFjG1njV/vlvXKPGEqHfXwxzj
7w0J8Qd4oqY0VEzGqFVHxoVrXgTh8jzqMhHI4yCUNzgOvF/BT0XZZhJ6qwOzpY0y
8U+TuEJ6kK7MUV2nGU6h6nHvwqLWI6z3oQOEQXJ3uA6K5uBB1LR0Rv8gC4qhRn5L
ZXZC+Aqg7dQ5UQIDAQABAoIBAQCJKJoG1iWAkXB2NZiV3pmxHjZoqD0cy7j8QFyC
HHvfxFXz1gXQJ4Zh4qh5HQUXzxlqxPPtXjOHYxmm5YXxwqZA9bTCrW0XZJ5d4lxF
xjWvQA0E7sl2tECg9gylixFH0HRqk7y8FElX0XpWvjwQn0UAQ7o8gPQJ4Q==
-----END PRIVATE KEY-----`,
    cert: `-----BEGIN CERTIFICATE-----
MIIDazCCAlOgAwIBAgIUBj+Jh6hM4k8QULQh/L5AqIdrFEwwDQYJKoZIhvcNAQEL
BQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM
GEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yNDAyMDIwMjQ2MzhaFw0yNTAy
MDEwMjQ2MzhaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw
HwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQDEJ5MRQ4KO3F4kbCO9JwyCjhCXTHVulg5gFJxV0XRT
zRH6DnqcHR8pK4D0BYV0I2GBm7jYIHLVxzA5B0P1HvVj8tL0tG8Zr5D+5TN1UpQd
4jx4NHUkGF8WZT3sQ7oFPy7pGz9LQFj8vpqE8XZO5RvGyhJB2LrXq9E5Qfh5Gg5Y
Zw5CZxH5Ux5q3RnvOK5dhkKU8jJZxDzO4x5t0ZyBxLqV8FvFp5ZoYKsXzO5fG5PK
x5Q2v8RZkjJu5ZbRwbhWR7/G5Ep2aEzOXH8oXJBcjHAqrX1Oj5JGdwKbKbS0QI0L
yS0eqXJ2Z8pEXXgQ+yK/H3F1ohGHEjLVFHFlAgMBAAGjUzBRMB0GA1UdDgQWBBQG
P4mHqEziTxBQtCH8vkCoh2sUTDAfBgNVHSMEGDAWgBQGP4mHqEziTxBQtCH8vkCo
h2sUTDAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQCJKJoG1iWA
kXB2NZiV3pmxHjZoqD0cy7j8QFyCHHvfxFXz1gXQJ4Zh4qh5HQUXzxlqxPPtXjOH
Yxmm5YXxwqZA9bTCrW0XZJ5d4lxFxjWvQA0E7sl2tECg9gylixFH0HRqk7y8FElX
0XpWvjwQn0UAQ7o8gPQJ4Q==
-----END CERTIFICATE-----`
};

const server = https.createServer(options, (req, res) => {
    // Handle favicon.ico requests
    if (req.url === '/favicon.ico') {
        res.writeHead(204);
        res.end();
        return;
    }

    // Normalize file path
    let filePath = '.' + req.url;
    if (filePath === './') {
        filePath = './static/trading.html';
    } else if (!filePath.startsWith('./static/')) {
        filePath = './static' + req.url;
    }

    // Get file extension
    const extname = path.extname(filePath);
    let contentType = MIME_TYPES[extname] || 'application/octet-stream';

    // Add CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    // Read and serve the file
    fs.readFile(filePath, (error, content) => {
        if (error) {
            if (error.code === 'ENOENT') {
                res.writeHead(404);
                res.end('File not found');
            } else {
                res.writeHead(500);
                res.end('Server error: ' + error.code);
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

server.listen(PORT, () => {
    console.log(`Server running at https://localhost:${PORT}/`);
    console.log('NOTE: You may see a security warning in your browser.');
    console.log('This is normal for development. Click "Advanced" and "Proceed" to continue.');
});
