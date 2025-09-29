"""Ansible integration utilities."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List

from .core import run, print_cmd


def wait_for_ssh(host: str, user: str = "rcpaffenroth", tries: int = 60, delay: float = 5.0) -> None:
    """Wait for SSH to become available on a host."""
    for _ in range(tries):
        rc, _, _ = run([
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=no",
            f"{user}@{host}",
            "exit",
        ])
        if rc == 0:
            return
        time.sleep(delay)


def create_inventory_file(name: str, ip: str, inventory_path: Path | None = None) -> Path:
    """Create an Ansible inventory file for a container/VM."""
    if inventory_path is None:
        inv_dir = Path.cwd() / "inventory"
        inv_dir.mkdir(parents=True, exist_ok=True)
        inventory_path = inv_dir / f"{name}_temp.ini"
    else:
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
    
    inventory_content = f"""
{name} ansible_host={ip} ansible_user=rcpaffenroth ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[have_root]
{name}

[have_rcpaffenroth]
{name}
""".strip()
    
    inventory_path.write_text(inventory_content, encoding="utf-8")
    return inventory_path


def run_ansible_playbook(inventory_file: Path, target: str, playbook: Path, extra_args: List[str] | None = None) -> None:
    """Run an Ansible playbook against a target."""
    if not playbook.exists():
        print(f"Warning: Playbook {playbook} does not exist, skipping.")
        return
    
    cmd = ["ansible-playbook", "-i", str(inventory_file), "-l", target]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(str(playbook))
    
    print_cmd(cmd)
    run(cmd)


def get_playbook_path(playbook_name: str) -> Path:
    """Get the path to a playbook in the standard location."""
    playdir = Path(os.path.expanduser("~/projects/ansible/playdir"))
    return playdir / playbook_name