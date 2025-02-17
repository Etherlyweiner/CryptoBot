import os
import yaml
import getpass

def setup_telegram_credentials():
    print("Telegram API Credential Setup")
    print("-" * 30)
    print("\n1. Go to https://my.telegram.org")
    print("2. Log in with your phone number: +1 870 866 5073")
    print("3. Click on 'API development tools'")
    print("4. Create a new application if you haven't already")
    print("\nEnter your credentials below:\n")
    
    api_id = input("API ID: ").strip()
    api_hash = getpass.getpass("API Hash: ").strip()
    
    # Load existing config
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'telegram_config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update credentials
    config['telegram']['api_id'] = api_id
    config['telegram']['api_hash'] = api_hash
    
    # Save updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("\nCredentials saved successfully!")
    print("You can now run the Telegram monitor.")

if __name__ == "__main__":
    setup_telegram_credentials()
