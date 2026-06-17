"""Main CLI interface for rcp_lxd."""

import time
from pathlib import Path

import click

from .ansible_utils import create_inventory_file, run_ansible_playbook, wait_for_ssh
from .container import container_exists, create_ssh_helper, get_container_status
from .core import get_container_ip, print_cmd, run

# The cloud-init file ships at the repo root, one level above this package.
# Anchoring to __file__ makes the default work regardless of the cwd.
DEFAULT_CLOUD_INIT = Path(__file__).resolve().parent.parent / "cloud-init"

# Default Ubuntu release; bump manually on each new LTS.
DEFAULT_DISTRO = "resolute"


@click.group()
@click.version_option(package_name="rcp-lxd")
def cli():
    """LXD container/VM management utilities."""


@cli.command()
@click.option("--name", "-n", help="Container/VM name to remove")
@click.option("--force", "-f", is_flag=True, help="Remove without confirmation")
@click.option("--tailscale-logout", "-t", is_flag=True, help="Logout from Tailscale on removal")
@click.option("--interactive", "-I", is_flag=True, help="Fill in options via a TUI form")
def clean(name: str | None, force: bool, tailscale_logout: bool, interactive: bool) -> None:
    """Stop and remove an LXD container/VM."""
    if interactive:
        from .tui import Field, run_form
        vals = run_form("rcp_lxd clean", [
            Field("name", "Container/VM name", "text", name or ""),
            Field("force", "Remove without confirmation", "bool", force),
            Field("tailscale_logout", "Logout from Tailscale", "bool", tailscale_logout),
        ])
        if vals is None:
            print("Cancelled.")
            return
        name, force, tailscale_logout = vals["name"], vals["force"], vals["tailscale_logout"]

    if not name:
        raise click.UsageError("Missing option '--name' (or use --interactive).")

    if not container_exists(name):
        print(f"Warning: '{name}' does not exist. Nothing to do.")
        return
    
    status = get_container_status(name)
    
    if not force:
        click.confirm(f"About to remove '{name}' (Status: {status}). Continue?", abort=True)
    
    print(f"Cleaning up container: {name}")
    
    if status == "RUNNING":
        print("Stopping...")
        if tailscale_logout:
            print("Logging out from Tailscale...")
            print_cmd(["lxc", "exec", name, "--", "tailscale", "logout"])
            run(["lxc", "exec", name, "--", "tailscale", "logout"])
        print_cmd(["lxc", "stop", name])
        run(["lxc", "stop", name])
    
    print("Removing...")
    print_cmd(["lxc", "delete", name])
    run(["lxc", "delete", name])
    print(f"Container '{name}' removed")


@cli.command()
@click.option("--name", "-n", default="vm1", help="Container/VM name")
@click.option("--distro", "-d", default=DEFAULT_DISTRO, help="Ubuntu release, or 'mint' for Linux Mint zena (container-only)")
@click.option("--cpu", "-c", default=2, type=int, help="Number of CPUs")
@click.option("--memory", "-m", default="4GiB", help="Memory size")
@click.option("--cloud-init", "-i", default=str(DEFAULT_CLOUD_INIT), type=click.Path(exists=True), help="Cloud-init file")
@click.option("--vm", is_flag=True, help="Create VM instead of container")
@click.option("--interactive", "-I", is_flag=True, help="Fill in options via a TUI form")
def create(name: str, distro: str, cpu: int, memory: str, cloud_init: str, vm: bool, interactive: bool):
    """Create and configure an LXD container/VM with Ubuntu or Mint."""

    if interactive:
        from .tui import Field, run_form
        vals = run_form("rcp_lxd create", [
            Field("name", "Container/VM name", "text", name),
            Field("distro", "Ubuntu release, or 'mint' for Linux Mint zena", "text", distro),
            Field("cpu", "Number of CPUs", "int", cpu),
            Field("memory", "Memory size (e.g. 4GiB)", "text", memory),
            Field("cloud_init", "Cloud-init file", "text", cloud_init),
            Field("vm", "Create as VM (Ubuntu only)", "bool", vm),
        ])
        if vals is None:
            print("Cancelled.")
            return
        name, distro, cpu, memory, cloud_init, vm = (
            vals["name"], vals["distro"], vals["cpu"],
            vals["memory"], vals["cloud_init"], vals["vm"],
        )
        if not Path(cloud_init).exists():
            raise click.UsageError(f"Cloud-init file not found: {cloud_init}")

    # Resolve the image. "mint" is a shortcut for the Linux Mint zena image on
    # the images: remote; we force the /cloud variant because the default Mint
    # image has no cloud-init, which the rcpaffenroth/SSH bootstrap relies on.
    if distro.lower() == "mint":
        if vm:
            raise click.UsageError("Mint is container-only; --vm is not supported.")
        image = "images:mint/zena/cloud"
    else:
        image = f"ubuntu:{distro}"

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
    cmd = ["lxc", "launch", image, name]
    if vm:
        cmd.append("--vm")
    cmd += [
        "--config", f"user.user-data={cloud_data}",
        "-c", f"limits.memory={memory}",
        "-c", f"limits.cpu={cpu}",
    ]

    print(f"Creating {'VM' if vm else 'container'} '{name}' from {image}...")
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
@click.option("--name", "-n", help="Container/VM name")
@click.option("--wait-ssh/--no-wait-ssh", default=True, help="Wait for SSH")
@click.option("--all", "run_all", is_flag=True, help="Run all playbooks")
@click.option("--system-setup", is_flag=True, help="Run system_setup.yml")
@click.option("--rcpaffenroth-setup", is_flag=True, help="Run rcpaffenroth_setup.yml")
@click.option("--tailscale-setup", is_flag=True, help="Run tailscale_setup.yml")
@click.option("--playbook", "-p", help="Run arbitrary playbook (e.g., xfce_setup.yml)")
@click.option("--extra-args", "-e", multiple=True, help="Additional ansible arguments")
@click.option("--interactive", "-I", is_flag=True, help="Fill in options via a TUI form")
def run_ansible(name: str | None, wait_ssh: bool, run_all: bool, system_setup: bool,
                rcpaffenroth_setup: bool, tailscale_setup: bool, playbook: str | None,
                extra_args: tuple[str, ...], interactive: bool):
    """Run Ansible playbooks against an LXD container/VM."""

    if interactive:
        from .tui import Field, run_form
        vals = run_form("rcp_lxd run-ansible", [
            Field("name", "Container/VM name", "text", name or ""),
            Field("wait_ssh", "Wait for SSH", "bool", wait_ssh),
            Field("run_all", "Run all playbooks", "bool", run_all),
            Field("system_setup", "Run system_setup.yml", "bool", system_setup),
            Field("rcpaffenroth_setup", "Run rcpaffenroth_setup.yml", "bool", rcpaffenroth_setup),
            Field("tailscale_setup", "Run tailscale_setup.yml", "bool", tailscale_setup),
            Field("playbook", "Arbitrary playbook (e.g. xfce_setup.yml)", "text", playbook or ""),
            Field("extra_args", "Extra ansible args (space-separated)", "text", " ".join(extra_args)),
        ])
        if vals is None:
            print("Cancelled.")
            return
        name = vals["name"]
        wait_ssh, run_all = vals["wait_ssh"], vals["run_all"]
        system_setup, rcpaffenroth_setup = vals["system_setup"], vals["rcpaffenroth_setup"]
        tailscale_setup = vals["tailscale_setup"]
        playbook = vals["playbook"] or None
        extra_args = tuple(vals["extra_args"].split())

    if not name:
        raise click.UsageError("Missing option '--name' (or use --interactive).")

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
