"""Test container utilities."""

from unittest.mock import patch

import pytest

from rcplxd.container import (
    container_exists,
    create_ssh_helper,
    get_container_status,
    list_host_gpus,
    resolve_gpus,
)

# Two GPUs as `nvidia-smi --query-gpu=index,name,pci.bus_id --format=csv,noheader`
# reports them, with the 8-digit PCI domain LXD does not use.
NVIDIA_SMI_CSV = (
    "0, NVIDIA GeForce RTX 4090, 00000000:41:00.0\n"
    "1, NVIDIA GeForce RTX 4090, 00000000:61:00.0"
)


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


@patch('rcplxd.container.shutil.which', return_value="/usr/bin/nvidia-smi")
@patch('rcplxd.container.run')
def test_list_host_gpus_trims_pci_domain(mock_run, _mock_which):
    """nvidia-smi's 8-digit domain is trimmed to the 4-digit form LXD expects."""
    mock_run.return_value = (0, NVIDIA_SMI_CSV, "")

    gpus = list_host_gpus()

    assert [g["index"] for g in gpus] == ["0", "1"]
    assert [g["pci"] for g in gpus] == ["0000:41:00.0", "0000:61:00.0"]
    assert gpus[0]["name"] == "NVIDIA GeForce RTX 4090"


@patch('rcplxd.container.shutil.which', return_value=None)
def test_list_host_gpus_without_nvidia_smi(_mock_which):
    """Missing nvidia-smi is a clear error, not a traceback from subprocess."""
    with pytest.raises(ValueError, match="nvidia-smi not found"):
        list_host_gpus()


@patch('rcplxd.container.shutil.which', return_value="/usr/bin/nvidia-smi")
@patch('rcplxd.container.run')
def test_resolve_gpus_all_on_gpuless_host(mock_run, _mock_which):
    """'--gpu all' on a driver-but-no-card host errors instead of silently doing nothing."""
    mock_run.return_value = (0, "", "")

    with pytest.raises(ValueError, match="reported no GPUs"):
        resolve_gpus(("all",))


@pytest.mark.parametrize("specs,expected", [
    (("0",), ["0000:41:00.0"]),
    (("1",), ["0000:61:00.0"]),
    (("0", "1"), ["0000:41:00.0", "0000:61:00.0"]),
    (("0,1",), ["0000:41:00.0", "0000:61:00.0"]),
    (("all",), ["0000:41:00.0", "0000:61:00.0"]),
    (("1", "1"), ["0000:61:00.0"]),          # duplicates collapse
    (("1", "0"), ["0000:61:00.0", "0000:41:00.0"]),  # selection order preserved
])
@patch('rcplxd.container.shutil.which', return_value="/usr/bin/nvidia-smi")
@patch('rcplxd.container.run')
def test_resolve_gpus(mock_run, _mock_which, specs, expected):
    """Indices, comma lists, and 'all' all map to the right PCI addresses."""
    mock_run.return_value = (0, NVIDIA_SMI_CSV, "")

    assert [g["pci"] for g in resolve_gpus(specs)] == expected


@patch('rcplxd.container.shutil.which', return_value="/usr/bin/nvidia-smi")
@patch('rcplxd.container.run')
def test_resolve_gpus_unknown_index(mock_run, _mock_which):
    """Asking for a GPU the host doesn't have fails before anything is created."""
    mock_run.return_value = (0, NVIDIA_SMI_CSV, "")

    with pytest.raises(ValueError, match="No GPU with index '7'"):
        resolve_gpus(("7",))


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