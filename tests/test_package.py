"""Test package structure and basic functionality."""

from tests.conftest import run_command


def test_package_structure(project_root, expected_package_files):
    """Test that all expected package files exist."""
    for file_path in expected_package_files:
        full_path = project_root / file_path
        assert full_path.exists(), f"Missing file: {file_path}"


def test_cli_help():
    """Test that the CLI help command works."""
    success, stdout, stderr = run_command("rcp_lxd --help")
    assert success, f"CLI help failed: {stderr}"
    assert "LXD container/VM management utilities" in stdout


def test_cli_version():
    """Test that the CLI version command works."""
    success, stdout, stderr = run_command("rcp_lxd --version")
    assert success, f"CLI version failed: {stderr}"
    assert "0.1.0" in stdout


def test_clean_command_help():
    """Test that the clean command help works."""
    success, stdout, stderr = run_command("rcp_lxd clean --help")
    assert success, f"Clean help failed: {stderr}"
    assert "Stop and remove an LXD container/VM" in stdout


def test_create_command_help():
    """Test that the create command help works."""
    success, stdout, stderr = run_command("rcp_lxd create --help")
    assert success, f"Create help failed: {stderr}"
    assert "Create and configure an LXD container/VM" in stdout


def test_run_ansible_command_help():
    """Test that the run-ansible command help works."""
    success, stdout, stderr = run_command("rcp_lxd run-ansible --help")
    assert success, f"Run-ansible help failed: {stderr}"
    assert "Run Ansible playbooks" in stdout