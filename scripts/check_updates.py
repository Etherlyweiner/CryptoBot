#!/usr/bin/env python3
"""
Script to check for package updates and compatibility.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pkg_resources
import requests
from packaging import version


def get_installed_packages() -> Dict[str, str]:
    """Get currently installed packages and their versions."""
    return {pkg.key: pkg.version for pkg in pkg_resources.working_set}


def get_latest_versions(packages: List[str]) -> Dict[str, str]:
    """Get latest versions from PyPI."""
    latest_versions = {}
    for package in packages:
        try:
            response = requests.get(f"https://pypi.org/pypi/{package}/json")
            if response.status_code == 200:
                latest_versions[package] = response.json()["info"]["version"]
        except Exception as e:
            print(f"Error fetching version for {package}: {e}")
    return latest_versions


def parse_requirements(filename: str) -> List[Tuple[str, str, str]]:
    """Parse requirements file to get package constraints."""
    requirements = []
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Handle different requirement formats
                if ">=" in line and "<" in line:
                    name = line.split(">=")[0].strip()
                    min_ver = line.split(">=")[1].split("<")[0].strip()
                    max_ver = line.split("<")[1].strip()
                    requirements.append((name, min_ver, max_ver))
                elif "==" in line:
                    name = line.split("==")[0].strip()
                    ver = line.split("==")[1].strip()
                    requirements.append((name, ver, ver))
    return requirements


def check_compatibility(package: str, current_version: str, latest_version: str) -> bool:
    """Check if the latest version is compatible with our constraints."""
    try:
        setup_path = Path(__file__).parent.parent / "setup.py"
        if not setup_path.exists():
            return False

        with open(setup_path) as f:
            setup_content = f.read()
            
        # Look for version constraints in setup.py
        if f'"{package}>=' in setup_content:
            constraints = setup_content.split(f'"{package}>=')[1].split('"')[0]
            min_ver = constraints.split(",")[0]
            max_ver = constraints.split("<")[1] if "<" in constraints else None
            
            latest = version.parse(latest_version)
            if max_ver and latest >= version.parse(max_ver):
                return False
            return latest >= version.parse(min_ver)
    except Exception as e:
        print(f"Error checking compatibility for {package}: {e}")
        return False


def main():
    """Main function to check for updates."""
    print("Checking for package updates...")
    
    # Get installed packages
    installed = get_installed_packages()
    
    # Get packages from setup.py
    setup_path = Path(__file__).parent.parent / "setup.py"
    if not setup_path.exists():
        print("setup.py not found!")
        return

    requirements = parse_requirements(setup_path)
    packages = [req[0] for req in requirements]
    
    # Get latest versions
    latest = get_latest_versions(packages)
    
    updates_available = False
    for package, current_version in installed.items():
        if package in latest:
            latest_version = latest[package]
            if version.parse(latest_version) > version.parse(current_version):
                if check_compatibility(package, current_version, latest_version):
                    print(f"Update available for {package}: {current_version} -> {latest_version}")
                    updates_available = True
                else:
                    print(f"Update available for {package} but may not be compatible: {current_version} -> {latest_version}")

    if not updates_available:
        print("All packages are up to date!")
    else:
        print("\nTo update packages, run: pip install --upgrade -r requirements.txt")
        print("Note: Make sure to test thoroughly after updating packages!")


if __name__ == "__main__":
    main()
