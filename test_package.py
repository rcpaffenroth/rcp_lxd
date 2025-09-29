#!/usr/bin/env python3
"""Simple test to verify the rcp_lxd package works correctly."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str) -> tuple[bool, str, str]:
    """Run a command and return success status."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    return result.returncode == 0, result.stdout, result.stderr


def main():
    """Run basic tests."""
    print("Testing rcp_lxd package...")
    
    # Test package structure
    expected_files = [
        "rcplxd/__init__.py",
        "rcplxd/cli.py", 
        "rcplxd/core.py",
        "rcplxd/container.py",
        "rcplxd/ansible_utils.py",
    ]
    
    for file_path in expected_files:
        if not Path(file_path).exists():
            print(f"❌ Missing: {file_path}")
            sys.exit(1)
        print(f"✅ Found: {file_path}")
    
    # Test CLI
    success, stdout, stderr = run_command("rcp_lxd --help")
    if not success:
        print(f"❌ CLI failed: {stderr}")
        sys.exit(1)
    
    if "LXD container/VM management utilities" not in stdout:
        print("❌ Unexpected CLI output")
        sys.exit(1)
    
    print("✅ CLI works")
    print("✅ All tests passed!")


if __name__ == "__main__":
    main()