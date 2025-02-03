"""
Test Helius Connection using direct HTTP request
"""

import requests
import json
from pathlib import Path

def test_connection():
    print("Testing Helius RPC Connection...")
    
    # Load RPC config
    config_path = Path(__file__).parent.parent / "config" / "rpc.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Get primary endpoint
    endpoint = config["primary"]["url"]
    print(f"\nUsing endpoint: {endpoint}")
    
    # Prepare JSON-RPC request
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getVersion",
        "params": []
    }
    
    try:
        print("\nTesting RPC connection...")
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        print(f"\nResponse: {json.dumps(result, indent=2)}")
        print("\nConnection test successful!")
        return True
        
    except Exception as e:
        print(f"\nError testing connection: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return False

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
