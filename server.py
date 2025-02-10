from flask import Flask, jsonify, request, abort
from functools import wraps
from config.security import SecurityManager
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
security_manager = SecurityManager()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr
        
        # Check IP whitelist
        if not security_manager.is_ip_whitelisted(ip):
            app.logger.warning(f"Unauthorized IP attempt: {ip}")
            abort(403)
            
        # Check rate limit
        if not security_manager.check_rate_limit(ip):
            app.logger.warning(f"Rate limit exceeded for IP: {ip}")
            abort(429)
            
        return f(*args, **kwargs)
    return decorated

@app.before_first_request
def initialize():
    """Initialize security manager and load configuration"""
    if not security_manager.load_config():
        app.logger.error("Failed to load security configuration")
        os._exit(1)

@app.route('/api/config')
@require_auth
def get_config():
    """Get configuration with secure API keys"""
    try:
        return jsonify({
            'rpc_endpoints': [
                {
                    'url': os.getenv('HELIUS_RPC'),
                    'key': security_manager.get_api_key('helius')
                },
                {
                    'url': os.getenv('QUICKNODE_RPC'),
                    'key': security_manager.get_api_key('quicknode')
                }
            ],
            'services': {
                'jupiter': os.getenv('JUPITER_API'),
                'birdeye': os.getenv('BIRDEYE_API')
            }
        })
    except Exception as e:
        app.logger.error(f"Error getting config: {e}")
        abort(500)

@app.route('/api/health')
@require_auth
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/rotate-keys', methods=['POST'])
@require_auth
def rotate_keys():
    """Rotate API keys"""
    try:
        services = request.json.get('services', [])
        results = {}
        for service in services:
            success = security_manager.rotate_key(service)
            results[service] = 'rotated' if success else 'failed'
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error rotating keys: {e}")
        abort(500)

# Error handlers
@app.errorhandler(403)
def forbidden(e):
    return jsonify(error='Forbidden'), 403

@app.errorhandler(429)
def ratelimit(e):
    return jsonify(error='Rate limit exceeded'), 429

@app.errorhandler(500)
def server_error(e):
    return jsonify(error='Internal server error'), 500

if __name__ == '__main__':
    # Use secure configuration for production
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 3001)),
        ssl_context='adhoc' if os.getenv('ENVIRONMENT') == 'production' else None
    )
