"""
Tests for the server module.
"""

import pytest
from pathlib import Path
from bot.server import get_static_dir

def test_static_dir_exists():
    """Test that the static directory exists."""
    static_dir = get_static_dir()
    assert static_dir.exists(), f"Static directory not found at {static_dir}"
    assert static_dir.is_dir(), f"{static_dir} is not a directory"

def test_static_dir_has_required_files():
    """Test that the static directory contains required files."""
    static_dir = get_static_dir()
    required_files = ['trading.html', 'wallet.js', 'jupiter.js', 'dexscreener.js']
    
    for file in required_files:
        assert (static_dir / file).exists(), f"Required file {file} not found"
        assert (static_dir / file).is_file(), f"{file} is not a file"
