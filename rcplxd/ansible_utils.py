"""Ansible integration utilities."""

import os
import time
from pathlib import Path

from .core import run, print_cmd


def ansible_repo() -> Path:
    """Path to the ansible repo, overridable via the ANSIBLE_REPO env var.

    Defaults to ~/projects/ansible. Setting ANSIBLE_REPO lets you point at a
    specific checkout/worktree rather than the hardcoded main checkout.
    """
    return Path(os.environ.get("ANSIBLE_REPO", os.path.expanduser("~/projects/ansible")))


def wait_for_ssh(host: str, tries: int = 60) -> None:
    """Wait for SSH to become available on a host."""
    for _ in range(tries):
        rc, _, _ = run([
            "ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
            f"rcpaffenroth@{host}", "exit"
        ])
        if rc == 0:
            return
        time.sleep(5)


def create_inventory_file(name: str, ip: str) -> Path:
    """Create an Ansible inventory file for a container/VM."""
    inv_dir = Path.cwd() / "inventory"
    inv_dir.mkdir(exist_ok=True)
    inventory_path = inv_dir / f"{name}_temp.ini"
    
    inventory_content = f"""{name} ansible_host={ip} ansible_user=rcpaffenroth ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[have_root]
{name}

[have_rcpaffenroth]
{name}"""
    
    inventory_path.write_text(inventory_content, encoding="utf-8")
    return inventory_path


def run_ansible_playbook(inventory_file: Path, target: str, playbook_name: str, extra_args: list[str]) -> None:
    """Run an Ansible playbook against a target."""
    repo = ansible_repo()
    playbook = repo / "playdir" / playbook_name
    if not playbook.exists():
        print(f"Warning: Playbook {playbook} does not exist, skipping.")
        return

    # Pin the config to the same repo so it no longer depends on the cwd
    # (the ansible.cfg symlink) or which checkout that symlink points at.
    os.environ["ANSIBLE_CONFIG"] = str(repo / "ansible.cfg")
    cmd = ["ansible-playbook", "-i", str(inventory_file), "-l", target] + extra_args + [str(playbook)]
    print_cmd(cmd)
    run(cmd)