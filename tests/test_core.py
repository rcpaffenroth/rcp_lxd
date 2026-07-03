"""Test core utilities."""

import json
from unittest.mock import patch

from rcplxd.core import run, print_cmd, get_container_ip


def test_run_command_success():
    """Test run function with successful command."""
    rc, stdout, stderr = run(["echo", "hello"])
    assert rc == 0
    assert stdout == "hello"
    assert stderr == ""


def test_run_command_failure():
    """Test run function with failing command."""
    rc, stdout, _ = run(["false"])
    assert rc == 1
    assert stdout == ""


def test_print_cmd(capsys):
    """Test print_cmd function."""
    print_cmd(["echo", "hello world"])
    captured = capsys.readouterr()
    assert "$ echo 'hello world'" in captured.out


@patch('rcplxd.core.run')
def test_get_container_ip_success(mock_run):
    """Test get_container_ip with successful result."""
    info = [{"state": {"network": {"eth0": {"addresses": [{"address": "192.168.1.100"}]}}}}]
    mock_run.return_value = (0, json.dumps(info), "")

    ip = get_container_ip("test-vm")

    assert ip == "192.168.1.100"
    mock_run.assert_called_once_with(["lxc", "list", "test-vm", "-f", "json"])


@patch('rcplxd.core.run')
def test_get_container_ip_no_output(mock_run):
    """Test get_container_ip with no network address."""
    info = [{"state": {"network": {}}}]
    mock_run.return_value = (0, json.dumps(info), "")

    ip = get_container_ip("test-vm")

    assert ip == ""