"""
Tests for the dashboard components.
"""

import pytest
from pathlib import Path
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from cryptobot.ui.components import render_header
from cryptobot.ui.dashboard import Dashboard

def test_assets_dir_exists():
    """Test that the assets directory exists."""
    assets_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "assets"
    assert assets_dir.exists(), f"Assets directory not found at {assets_dir}"
    assert assets_dir.is_dir(), f"{assets_dir} is not a directory"

def test_assets_dir_has_required_files():
    """Test that the assets directory has the required files."""
    assets_dir = Path(os.path.dirname(os.path.dirname(__file__))) / "assets"
    required_files = ["logo.png"]
    for file in required_files:
        assert (assets_dir / file).exists(), f"Required file {file} not found in assets directory"
