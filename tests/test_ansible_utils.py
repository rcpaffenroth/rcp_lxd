"""Test Ansible utilities."""

from pathlib import Path
from unittest.mock import patch

from rcplxd.ansible_utils import create_inventory_file, run_ansible_playbook


@patch('pathlib.Path.mkdir')
@patch('pathlib.Path.write_text')
def test_create_inventory_file(mock_write_text, mock_mkdir):
    """Test create_inventory_file function."""
    name = "test-vm"
    ip = "192.168.1.100"
    
    result = create_inventory_file(name, ip)
    
    assert result.name == f"{name}_temp.ini"
    assert "inventory" in str(result)
    
    expected_content = f"""{name} ansible_host={ip} ansible_user=rcpaffenroth ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[have_root]
{name}

[have_rcpaffenroth]
{name}"""
    
    mock_write_text.assert_called_once_with(expected_content, encoding="utf-8")
    mock_mkdir.assert_called_once_with(exist_ok=True)


@patch('rcplxd.ansible_utils.run')
@patch('rcplxd.ansible_utils.print_cmd')
@patch('pathlib.Path.exists')
def test_run_ansible_playbook_exists(mock_exists, mock_print_cmd, mock_run):
    """Test run_ansible_playbook when playbook exists."""
    mock_exists.return_value = True
    
    inventory_file = Path("test_inventory.ini")
    target = "test-vm"
    playbook_name = "test_playbook.yml"
    extra_args = ["--check"]
    
    run_ansible_playbook(inventory_file, target, playbook_name, extra_args)
    
    mock_print_cmd.assert_called_once()
    mock_run.assert_called_once()
    
    # Check the command that would be run
    call_args = mock_run.call_args[0][0]
    assert "ansible-playbook" in call_args
    assert str(inventory_file) in call_args
    assert target in call_args
    assert "--check" in call_args


@patch('rcplxd.ansible_utils.run')
@patch('rcplxd.ansible_utils.print_cmd')
@patch('pathlib.Path.exists')
@patch('builtins.print')
def test_run_ansible_playbook_not_exists(mock_print, mock_exists, mock_print_cmd, mock_run):
    """Test run_ansible_playbook when playbook doesn't exist."""
    mock_exists.return_value = False
    
    inventory_file = Path("test_inventory.ini")
    target = "test-vm"
    playbook_name = "missing_playbook.yml"
    extra_args = []
    
    run_ansible_playbook(inventory_file, target, playbook_name, extra_args)
    
    mock_print.assert_called_once()
    mock_print_cmd.assert_not_called()
    mock_run.assert_not_called()