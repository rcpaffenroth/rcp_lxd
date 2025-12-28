"""Test configuration and fixtures."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def expected_package_files():
    """Return list of expected package files."""
    return [
        "rcplxd/__init__.py",
        "rcplxd/cli.py", 
        "rcplxd/core.py",
        "rcplxd/container.py",
        "rcplxd/ansible_utils.py",
    ]


def run_command(cmd: str) -> tuple[bool, str, str]:
    """Run a command and return success status."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
    return result.returncode == 0, result.stdout, result.stderr