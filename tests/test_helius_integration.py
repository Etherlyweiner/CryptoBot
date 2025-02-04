"""
Test suite for Helius RPC integration
"""

import pytest
import os
from pathlib import Path
import json
import requests
from dotenv import load_dotenv
from unittest.mock import patch

# Load environment variables
load_dotenv()

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables"""
    with patch.dict(os.environ, {
        'HELIUS_API_KEY': 'test_api_key',
        'SOLANA_NETWORK': 'mainnet-beta'
    }):
        yield

def test_env_variables():
    """Test that required environment variables are set."""
    assert os.getenv("HELIUS_API_KEY") is not None, "HELIUS_API_KEY not set"
    assert os.getenv("HELIUS_API_KEY") == "test_api_key"
    assert os.getenv("SOLANA_NETWORK") is not None, "SOLANA_NETWORK not set"
    assert os.getenv("SOLANA_NETWORK") == "mainnet-beta"

def test_rpc_config():
    """Test RPC configuration file structure."""
    config_path = Path(__file__).parent.parent / "config" / "rpc.json"
    assert config_path.exists(), "RPC config file not found"
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Check required fields
    assert "primary" in config, "Missing primary RPC config"
    assert "fallback" in config, "Missing fallback RPC config"
    assert "settings" in config, "Missing RPC settings"
    
    # Check primary endpoint structure
    assert "url" in config["primary"], "Missing primary URL"
    assert "ws_url" in config["primary"], "Missing primary WebSocket URL"
    
    # Check settings structure
    settings = config["settings"]
    assert "max_retries" in settings, "Missing max_retries setting"
    assert "retry_delay" in settings, "Missing retry_delay setting"
    assert "timeout" in settings, "Missing timeout setting"

    # Test network configuration
    network = os.getenv("SOLANA_NETWORK")
    assert network in ["mainnet-beta", "devnet", "testnet"], "Invalid network"
    
    # Test API key configuration
    api_key = os.getenv("HELIUS_API_KEY")
    assert api_key is not None and len(api_key) > 0, "Invalid API key"

@pytest.mark.skip(reason="Requires real API key")
def test_helius_connection():
    """Test connection to Helius RPC endpoint."""
    api_key = os.getenv("HELIUS_API_KEY")
    endpoint = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getVersion",
        "params": []
    }
    
    response = requests.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 200, "Failed to connect to Helius RPC"
    
    data = response.json()
    assert 'result' in data, "Invalid response format"
    assert 'solana-core' in data['result'], "Invalid version info"

def test_websocket_config():
    """Test WebSocket configuration."""
    config_path = Path(__file__).parent.parent / "config" / "rpc.json"
    with open(config_path) as f:
        config = json.load(f)
    
    ws_settings = config["settings"]["websocket"]
    assert "ping_interval" in ws_settings, "Missing WebSocket ping_interval"
    assert "reconnect_delay" in ws_settings, "Missing WebSocket reconnect_delay"
    assert "max_reconnect_attempts" in ws_settings, "Missing WebSocket max_reconnect_attempts"

def test_rate_limiting():
    """Test rate limiting configuration."""
    config_path = Path(__file__).parent.parent / "config" / "rpc.json"
    with open(config_path) as f:
        config = json.load(f)
    
    rate_limit = config["settings"]["rate_limit"]
    assert "requests_per_second" in rate_limit, "Missing requests_per_second"
    assert "burst_limit" in rate_limit, "Missing burst_limit"
    assert "cooldown_period" in rate_limit, "Missing cooldown_period"
    
    # Check reasonable values
    assert 0 < rate_limit["requests_per_second"] <= 100, "Invalid requests_per_second"
    assert rate_limit["burst_limit"] >= rate_limit["requests_per_second"], "Burst limit too low"
    assert rate_limit["cooldown_period"] > 0, "Invalid cooldown_period"
