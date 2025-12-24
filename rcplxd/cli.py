"""Main CLI interface for rcp_lxd."""

import time
from pathlib import Path

import click

from .ansible_utils import create_inventory_file, run_ansible_playbook, wait_for_ssh
from .container import container_exists, create_ssh_helper, get_container_status
from .core import get_container_ip, print_cmd, run


@click.group()
@click.version_option(package_name="rcp-lxd")
def cli():
    """LXD container/VM management utilities."""


@cli.command()
@click.option("--name", "-n", required=True, help="Container/VM name to remove")
@click.option("--force", "-f", is_flag=True, help="Remove without confirmation")
def clean(name: str, force: bool) -> None:
    """Stop and remove an LXD container/VM."""
    if not container_exists(name):
        print(f"Warning: '{name}' does not exist. Nothing to do.")
        return
    
    status = get_container_status(name)
    
    if not force:
        click.confirm(f"About to remove '{name}' (Status: {status}). Continue?", abort=True)
    
    print(f"Cleaning up container: {name}")
    
    if status == "RUNNING":
        print("Stopping...")
        print_cmd(["lxc", "stop", name])
        run(["lxc", "stop", name])
    
    print("Removing...")
    print_cmd(["lxc", "delete", name])
    run(["lxc", "delete", name])
    print(f"Container '{name}' removed")


@cli.command()
@click.option("--name", "-n", default="vm1", help="Container/VM name")
@click.option("--distro", "-d", default="noble", help="Ubuntu release")
@click.option("--cpu", "-c", default=2, type=int, help="Number of CPUs")
@click.option("--memory", "-m", default="4GiB", help="Memory size")
@click.option("--cloud-init", "-i", default="./cloud-init", type=click.Path(exists=True), help="Cloud-init file")
@click.option("--vm", is_flag=True, help="Create VM instead of container")
def create(name: str, distro: str, cpu: int, memory: str, cloud_init: str, vm: bool):
    """Create and configure an LXD container/VM with Ubuntu."""
    
    # Handle existing container
    if container_exists(name):
        reply = input(f"Container '{name}' already exists. Delete it? [y/N]: ").strip().lower()
        if reply.startswith("y"):
            print(f"Deleting existing container '{name}'...")
            print_cmd(["lxc", "delete", name, "--force"])
            run(["lxc", "delete", name, "--force"])
        else:
            print("Aborting.")
            return
    
    # Launch container/VM
    cloud_data = Path(cloud_init).read_text(encoding="utf-8")
    cmd = ["lxc", "launch", f"ubuntu:{distro}", name]
    if vm:
        cmd.append("--vm")
    cmd += [
        "--config", f"user.user-data={cloud_data}",
        "-c", f"limits.memory={memory}",
        "-c", f"limits.cpu={cpu}",
    ]
    
    print(f"Creating {'VM' if vm else 'container'} '{name}' with Ubuntu {distro}...")
    print(f"Resources: {cpu} CPUs, {memory} memory")
    run(cmd)
    
    # Wait for cloud-init
    print("Waiting for container to start and cloud-init to complete...")
    time.sleep(15)
    
    # Get IP and create inventory
    ip = get_container_ip(name)
    if ip:
        inv_file = create_inventory_file(name, ip)
        print(f"Created inventory: {inv_file}")
        
        # Create SSH helper
        ssh_helper = create_ssh_helper(name, ip)
        if ssh_helper:
            print(f"Created SSH helper: {ssh_helper}")
    else:
        print("Warning: Could not determine container IP")
    
    print(f"\\n=== Container '{name}' created successfully ===")
    print(f"IP: {ip or '(not available)'}")
    print(f"To delete: rcp_lxd clean --name {name}")


@cli.command("run-ansible")
@click.option("--name", "-n", required=True, help="Container/VM name")
@click.option("--wait-ssh/--no-wait-ssh", default=True, help="Wait for SSH")
@click.option("--all", "run_all", is_flag=True, help="Run all playbooks")
@click.option("--system-setup", is_flag=True, help="Run system_setup.yml")
@click.option("--rcpaffenroth-setup", is_flag=True, help="Run rcpaffenroth_setup.yml")
@click.option("--tailscale-setup", is_flag=True, help="Run tailscale_setup.yml")
@click.option("--playbook", "-p", help="Run arbitrary playbook (e.g., xfce_setup.yml)")
@click.option("--extra-args", "-e", multiple=True, help="Additional ansible arguments")
def run_ansible(name: str, wait_ssh: bool, run_all: bool, system_setup: bool, 
                rcpaffenroth_setup: bool, tailscale_setup: bool, playbook: str | None,
                extra_args: tuple[str, ...]):
    """Run Ansible playbooks against an LXD container/VM."""
    
    ip = get_container_ip(name)
    if not ip:
        print(f"Could not determine IP for '{name}'. Is it running?")
        return
    
    print(f"Target: {name} ({ip})")
    
    # Create inventory
    inv_file = create_inventory_file(name, ip)
    print(f"Using inventory: {inv_file}")
    
    # Wait for SSH
    if wait_ssh:
        print("Waiting for SSH...")
        wait_for_ssh(ip)
    
    # Handle custom playbook
    if playbook:
        args = list(extra_args) if extra_args else []
        run_ansible_playbook(inv_file, name, playbook, args)
        return
    
    # Select playbooks
    if run_all or not any([system_setup, rcpaffenroth_setup, tailscale_setup]):
        system_setup = rcpaffenroth_setup = tailscale_setup = True
    
    # Run playbooks
    if system_setup:
        run_ansible_playbook(inv_file, name, "system_setup.yml", [])
    
    if rcpaffenroth_setup:
        run_ansible_playbook(inv_file, name, "rcpaffenroth_setup.yml", ["--skip-tags=nonlocal"])
    
    if tailscale_setup:
        run_ansible_playbook(inv_file, name, "tailscale_setup.yml", 
                           ["-e", f"TAILSCALE_HOSTNAME=ts{name}", "--skip-tags=nonlocal"])


if __name__ == "__main__":
    cli()
