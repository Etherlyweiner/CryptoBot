"""
Test Helius Connection using direct HTTP request
"""

import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

def test_connection():
    print("Testing Helius RPC Connection...")
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("HELIUS_API_KEY")
    
    if not api_key:
        print("Error: HELIUS_API_KEY not found in environment variables")
        return False
    
    # Create endpoint URL with API key
    endpoint = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    print(f"\nTesting connection to Helius RPC...")
    
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
