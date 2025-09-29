"""Test container utilities."""

from unittest.mock import patch

from rcplxd.container import container_exists, get_container_status, create_ssh_helper


@patch('rcplxd.container.run')
def test_container_exists_true(mock_run):
    """Test container_exists when container exists."""
    mock_run.return_value = (0, "", "")
    
    assert container_exists("test-vm") is True
    mock_run.assert_called_once_with(["lxc", "info", "test-vm"])


@patch('rcplxd.container.run')
def test_container_exists_false(mock_run):
    """Test container_exists when container doesn't exist."""
    mock_run.return_value = (1, "", "Container not found")
    
    assert container_exists("test-vm") is False


@patch('rcplxd.container.run')
def test_get_container_status(mock_run):
    """Test get_container_status function."""
    mock_run.return_value = (0, "running", "")
    
    status = get_container_status("test-vm")
    
    assert status == "RUNNING"
    mock_run.assert_called_once_with(["lxc", "list", "test-vm", "-c", "s", "--format", "csv"])


def test_create_ssh_helper_no_ip():
    """Test create_ssh_helper with no IP."""
    result = create_ssh_helper("test-vm", "")
    assert result is None


@patch('pathlib.Path.write_text')
@patch('pathlib.Path.chmod')
def test_create_ssh_helper_with_ip(mock_chmod, mock_write_text):
    """Test create_ssh_helper with valid IP."""
    ip = "192.168.1.100"
    name = "test-vm"
    
    result = create_ssh_helper(name, ip)
    
    assert result is not None
    assert result.name == f"ssh_{name}.sh"
    
    expected_content = f"#!/usr/bin/env bash\nexec ssh -o StrictHostKeyChecking=no rcpaffenroth@{ip} \"$@\"\n"
    mock_write_text.assert_called_once_with(expected_content, encoding="utf-8")
    mock_chmod.assert_called_once_with(0o755)