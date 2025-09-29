"""Container management utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .core import run, print_cmd, container_exists, get_container_status


def create_ssh_helper(name: str, ip: str) -> Optional[Path]:
    """Create a convenience SSH helper script."""
    if not ip:
        return None
    
    ssh_helper = Path.cwd() / f"ssh_{name}.sh"
    ssh_helper.write_text(
        f"""#!/usr/bin/env bash
exec ssh -o StrictHostKeyChecking=no rcpaffenroth@{ip} "$@"
""",
        encoding="utf-8"
    )
    try:
        ssh_helper.chmod(0o755)
    except OSError:
        pass
    return ssh_helper


def handle_existing_container(name: str, force: bool = False) -> bool:
    """Handle existing container - either delete it or abort.
    
    Returns True if we should continue (container deleted or didn't exist),
    False if we should abort.
    """
    if not container_exists(name):
        return True
    
    if force:
        print(f"Deleting existing container '{name}'...")
        print_cmd(["lxc", "delete", name, "--force"])
        run(["lxc", "delete", name, "--force"])
        return True
    
    reply = input(f"Container '{name}' already exists. Delete it? [y/N]: ").strip().lower()
    if reply.startswith("y"):
        print(f"Deleting existing container '{name}'...")
        print_cmd(["lxc", "delete", name, "--force"])
        run(["lxc", "delete", name, "--force"])
        return True
    else:
        print("Aborting.")
        return False


def stop_and_remove_container(name: str) -> None:
    """Stop and remove a container/VM."""
    if not container_exists(name):
        print(f"Warning: '{name}' does not exist (or lxc not available). Nothing to do.")
        return
    
    status = get_container_status(name)
    
    print(f"Cleaning up container: {name}")
    
    # Stop if running
    if status == "RUNNING":
        print("Stopping...")
        print_cmd(["lxc", "stop", name])
        run(["lxc", "stop", name])
    
    # Delete
    print("Removing...")
    print_cmd(["lxc", "delete", name])
    run(["lxc", "delete", name])
    
    print(f"Container '{name}' removed")