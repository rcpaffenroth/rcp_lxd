"""Main CLI interface for rcp_lxd."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import click

from .ansible_utils import (
    create_inventory_file,
    get_playbook_path,
    run_ansible_playbook,
    wait_for_ssh,
)
from .container import handle_existing_container, stop_and_remove_container, create_ssh_helper
from .core import get_container_ip, get_container_status, run


@click.group()
@click.version_option(package_name="rcp-lxd")
def cli():
    """LXD container/VM management utilities."""


@cli.command()
@click.option("--name", "-n", required=True, help="Container/VM name to remove")
@click.option("--force", "-f", is_flag=True, help="Remove without confirmation")
def clean(name: str, force: bool) -> None:
    """Stop and remove an LXD container/VM."""
    from .core import container_exists
    
    if not container_exists(name):
        print(f"Warning: '{name}' does not exist (or lxc not available). Nothing to do.")
        return
    
    status = get_container_status(name)
    
    # Confirm
    if not force:
        click.confirm(f"About to remove '{name}' (Status: {status}). Continue?", default=False, abort=True)
    
    stop_and_remove_container(name)


@cli.command()
@click.option("--name", "-n", default="vm1", show_default=True, help="Container/VM name")
@click.option("--distro", "-d", default="noble", show_default=True, help="Ubuntu release (e.g. focal, jammy, noble)")
@click.option("--cpu", "-c", default=2, show_default=True, type=int, help="Number of CPUs")
@click.option("--memory", "-m", default="4GiB", show_default=True, help="Memory size, e.g., 4GiB")
@click.option("--cloud-init", "-i", default="./cloud-init", show_default=True, type=click.Path(exists=True, dir_okay=False), help="Cloud-init file")
@click.option("--vm", is_flag=True, help="Create VM instead of container")
def create(
    name: str,
    distro: str,
    cpu: int,
    memory: str,
    cloud_init: str,
    vm: bool,
):
    """Create and configure an LXD container/VM with Ubuntu."""
    
    # Handle existing container
    if not handle_existing_container(name):
        return
    
    # Launch
    cloud_data = Path(cloud_init).read_text(encoding="utf-8")
    cmd = ["lxc", "launch", f"ubuntu:{distro}", name]
    if vm:
        cmd.append("--vm")
    cmd += [
        "--config",
        f"user.user-data={cloud_data}",
        "-c",
        f"limits.memory={memory}",
        "-c",
        f"limits.cpu={cpu}",
    ]
    print(f"Creating container '{name}' with Ubuntu {distro}...")
    print(f"Resources: {cpu} CPUs, {memory} memory")
    run(cmd, check=True)
    
    # Wait for cloud-init
    print("Waiting for container to start and cloud-init to complete...")
    time.sleep(15)
    
    # Get IP and create inventory
    ip = get_container_ip(name)
    inv_file: Optional[Path] = None
    if ip:
        inv_file = create_inventory_file(name, ip)
        print(f"Created temporary inventory at: {inv_file}")
    else:
        print("Warning: Could not determine container IP; inventory not written.")
    
    # Create SSH helper script
    ssh_helper = create_ssh_helper(name, ip) if ip else None
    
    # Print summary
    print()
    print(f"=== Container '{name}' created successfully ===")
    print(f"Ubuntu version: {distro}")
    print(f"Resources: {cpu} CPUs, {memory} memory")
    print(f"Container IP: {ip or '(not available yet)'}")
    
    # Print example Ansible usage
    if inv_file and ip:
        print()
        print("Example: run Ansible playbooks against this VM")
        print(f"  ansible-inventory -i {inv_file} --graph all")
        print(f"  rcp_lxd run-ansible --name {name} --system-setup")
        print(f"  rcp_lxd run-ansible --name {name} --all")
    
    if ssh_helper and ip:
        print()
        print("SSH helper created:")
        print(f"  {ssh_helper}")
        print("Usage:")
        print(f"  {ssh_helper}")
    
    print(f"Direct exec: lxc exec {name} -- bash")
    print()
    print(f"To delete: rcp_lxd clean --name {name}")


@cli.command("run-ansible")
@click.option("--name", "-n", required=True, help="Container/VM name")
@click.option("--inventory", "-i", type=click.Path(dir_okay=False), help="Path to inventory file; will be created if omitted")
@click.option("--wait-ssh/--no-wait-ssh", default=True, show_default=True, help="Wait for SSH before running playbooks")
@click.option("--all/--no-all", "run_all", default=False, show_default=True, help="Run all playbooks")
@click.option("--system-setup", is_flag=True, help="Run system_setup.yml")
@click.option("--rcpaffenroth-setup", is_flag=True, help="Run rcpaffenroth_setup.yml")
@click.option("--tailscale-setup", is_flag=True, help="Run tailscale_setup.yml")
@click.option("--xfce-setup", is_flag=True, help="Run xfce_setup.yml")
def run_ansible(
    name: str,
    inventory: Optional[str],
    wait_ssh: bool,
    run_all: bool,
    system_setup: bool,
    rcpaffenroth_setup: bool,
    tailscale_setup: bool,
    xfce_setup: bool,
):
    """Run Ansible playbooks against an LXD container/VM."""
    
    # Determine IP
    ip = get_container_ip(name)
    if not ip:
        print(f"Could not determine IP for '{name}'. Is it running?")
        return
    print(f"Target: {name} ({ip})")
    
    # Create or use inventory
    if inventory:
        inv_file = Path(inventory)
        if not inv_file.exists():
            inv_file = create_inventory_file(name, ip, inv_file)
            print(f"Created inventory: {inv_file}")
    else:
        inv_file = create_inventory_file(name, ip)
        print(f"Using inventory: {inv_file}")
    
    # Optional SSH wait
    if wait_ssh:
        print("Waiting for SSH to become available...")
        wait_for_ssh(ip)
    
    # Select playbooks
    if run_all or not any([system_setup, rcpaffenroth_setup, tailscale_setup, xfce_setup]):
        system_setup = rcpaffenroth_setup = tailscale_setup = xfce_setup = True
    
    # Run selected playbooks
    if system_setup:
        playbook = get_playbook_path("system_setup.yml")
        run_ansible_playbook(inv_file, name, playbook, ["--skip-tags=slow"])
    
    if rcpaffenroth_setup:
        playbook = get_playbook_path("rcpaffenroth_setup.yml")
        run_ansible_playbook(inv_file, name, playbook, ["--skip-tags=slow,nonlocal"])
    
    if tailscale_setup:
        playbook = get_playbook_path("tailscale_setup.yml")
        run_ansible_playbook(inv_file, name, playbook, [
            "-e", f"TAILSCALE_HOSTNAME=ts{name}",
            "--skip-tags=slow,nonlocal"
        ])
    
    if xfce_setup:
        playbook = get_playbook_path("xfce_setup.yml")
        run_ansible_playbook(inv_file, name, playbook, ["--skip-tags=slow,nonlocal"])


if __name__ == "__main__":
    cli()