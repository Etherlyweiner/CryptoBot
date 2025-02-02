"""
Master initialization script for CryptoBot.
"""
import os
import sys
import asyncio
from pathlib import Path
import subprocess
import json

def run_script(script_name):
    """Run a Python script and return its output."""
    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

async def initialize_all():
    """Run all initialization steps."""
    try:
        print("Starting CryptoBot initialization...\n")
        
        # 1. Set up environment
        print("1. Setting up environment...")
        output = run_script("scripts/setup_env.py")
        print(output)
        
        # 2. Generate SSL certificate
        print("\n2. Generating SSL certificate...")
        output = run_script("scripts/generate_cert.py")
        print(output)
        
        # 3. Generate JWT secret
        print("\n3. Generating JWT secret...")
        output = run_script("scripts/generate_jwt_secret.py")
        print(output)
        
        # 4. Generate API key
        print("\n4. Generating API key...")
        output = run_script("scripts/generate_api_key.py")
        print(output)
        
        # 5. Initialize Redis
        print("\n5. Initializing Redis...")
        output = run_script("scripts/init_redis.py")
        print(output)
        
        print("\nInitialization completed successfully!")
        print("\nNext steps:")
        print("1. Update sensitive values in .env file")
        print("2. Start the Redis server if not already running")
        print("3. Start the bot with: python run.py")
        
    except Exception as e:
        print(f"\nError during initialization: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(initialize_all())
