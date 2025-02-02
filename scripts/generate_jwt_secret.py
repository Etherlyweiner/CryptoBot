"""
Generate a secure JWT secret and update configuration.
"""
import secrets
import json
from pathlib import Path

def generate_jwt_secret():
    """Generate a secure JWT secret and update security.json."""
    # Generate secret
    jwt_secret = secrets.token_hex(32)
    
    # Update security.json
    security_file = Path("config/security.json")
    if security_file.exists():
        with open(security_file) as f:
            config = json.load(f)
        
        config["jwt_secret"] = jwt_secret
        
        with open(security_file, "w") as f:
            json.dump(config, f, indent=4)
        
        print("Updated JWT secret in security.json")
    else:
        print("Error: security.json not found")

if __name__ == "__main__":
    generate_jwt_secret()
