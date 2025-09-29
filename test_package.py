#!/usr/bin/env python3
"""Simple test to verify the rcp_lxd package works correctly."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def test_cli_import():
    """Test that the CLI can be imported and basic commands work."""
    print("Testing CLI import and help commands...")
    
    # Test main help
    success, stdout, stderr = run_command("rcp_lxd --help")
    if not success:
        print(f"❌ Main help failed: {stderr}")
        return False
    if "LXD container/VM management utilities" not in stdout:
        print("❌ Main help output doesn't contain expected text")
        return False
    print("✅ Main help works")
    
    # Test subcommand help
    for cmd in ["clean", "create", "run-ansible"]:
        success, stdout, stderr = run_command(f"rcp_lxd {cmd} --help")
        if not success:
            print(f"❌ {cmd} help failed: {stderr}")
            return False
        print(f"✅ {cmd} help works")
    
    return True


def test_package_structure():
    """Test that the package structure is correct."""
    print("Testing package structure...")
    
    expected_files = [
        "rcplxd/__init__.py",
        "rcplxd/cli.py",
        "rcplxd/core.py",
        "rcplxd/container.py",
        "rcplxd/ansible_utils.py",
    ]
    
    for file_path in expected_files:
        if not Path(file_path).exists():
            print(f"❌ Missing file: {file_path}")
            return False
        print(f"✅ Found: {file_path}")
    
    return True


def main():
    """Run all tests."""
    print("Running rcp_lxd package tests...\n")
    
    # Test package structure
    if not test_package_structure():
        print("\n❌ Package structure tests failed")
        sys.exit(1)
    
    # Test CLI
    if not test_cli_import():
        print("\n❌ CLI tests failed")
        sys.exit(1)
    
    print("\n✅ All tests passed! The rcp_lxd package is working correctly.")


if __name__ == "__main__":
    main()