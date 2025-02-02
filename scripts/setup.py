"""
Main setup script for CryptoBot.
"""
import os
import sys
from pathlib import Path

def run_setup():
    """Run all setup steps."""
    print("Starting CryptoBot setup...")
    
    # Add scripts directory to path
    scripts_dir = Path(__file__).parent
    sys.path.append(str(scripts_dir))
    
    # Import setup modules
    from setup_env import setup_env
    from setup_security import setup_security
    from setup_monitoring import setup_monitoring
    
    try:
        # Run setup steps
        print("\n1. Setting up environment variables...")
        setup_env()
        
        print("\n2. Setting up security configuration...")
        setup_security()
        
        print("\n3. Setting up monitoring configuration...")
        setup_monitoring()
        
        print("\nSetup completed successfully!")
        print("\nNext steps:")
        print("1. Update sensitive values in .env file")
        print("2. Review and customize config/security.json")
        print("3. Review and customize config/monitoring.json")
        print("4. Start the bot with: python run.py")
        
    except Exception as e:
        print(f"\nError during setup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_setup()
