"""
Generate an API key for testing.
"""
import secrets
import json
import hashlib
from datetime import datetime
from pathlib import Path

def generate_api_key():
    """Generate an API key and secret, update security.json."""
    # Generate API key and secret
    api_key = f"cb_{secrets.token_hex(16)}"
    api_secret = secrets.token_hex(32)
    
    # Hash the secret
    secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()
    
    # Update security.json
    security_file = Path("config/security.json")
    if security_file.exists():
        with open(security_file) as f:
            config = json.load(f)
        
        config["api_keys"][api_key] = {
            "user_id": "test_user",
            "secret_hash": secret_hash,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "enabled": True
        }
        
        with open(security_file, "w") as f:
            json.dump(config, f, indent=4)
        
        print("\nGenerated API credentials for testing:")
        print(f"API Key: {api_key}")
        print(f"API Secret: {api_secret}")
        print("\nStore these credentials securely!")
    else:
        print("Error: security.json not found")

if __name__ == "__main__":
    generate_api_key()
