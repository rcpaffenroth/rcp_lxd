#!/usr/bin/env python3

"""
Run Ansible playbooks against an LXD container/VM.

Simplified helper that:
- Determines the target's IP via `lxc list`.
- Creates a minimal inventory file if not provided.
- Waits for SSH (optional) and runs selected playbooks.

Defaults mirror the previous behavior from create.sh/create.py with light error handling.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

import click


def run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def print_cmd(cmd: List[str]) -> None:
    print("$", " ".join(shlex.quote(c) for c in cmd))


def get_container_ip(name: str) -> str:
    _rc, out, _ = run(["lxc", "list", name, "-f", "csv", "-c", "4"])  # IPv4 column
    return out.splitlines()[0].split(" ")[0] if out else ""


def wait_for_ssh(host: str, user: str = "rcpaffenroth", tries: int = 60, delay: float = 5.0) -> None:
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


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--name", "name", "-n", required=True, help="Container/VM name")
@click.option("--inventory", "inventory", "-i", type=click.Path(dir_okay=False), help="Path to inventory file; will be created if omitted")
@click.option("--wait-ssh/--no-wait-ssh", default=True, show_default=True, help="Wait for SSH before running playbooks")
@click.option("--all/--no-all", "run_all", default=False, show_default=True, help="Run all playbooks")
@click.option("--system-setup", is_flag=True, help="Run system_setup.yml")
@click.option("--rcpaffenroth-setup", is_flag=True, help="Run rcpaffenroth_setup.yml")
@click.option("--tailscale-setup", is_flag=True, help="Run tailscale_setup.yml")
@click.option("--xfce-setup", is_flag=True, help="Run xfce_setup.yml")
def main(
    name: str,
    inventory: Optional[str],
    wait_ssh: bool,
    run_all: bool,
    system_setup: bool,
    rcpaffenroth_setup: bool,
    tailscale_setup: bool,
    xfce_setup: bool,
):
    # Determine IP
    ip = get_container_ip(name)
    if not ip:
        print(f"Could not determine IP for '{name}'. Is it running?")
        return
    print(f"Target: {name} ({ip})")

    # Inventory
    inv_file: Path
    if inventory:
        inv_file = Path(inventory)
        if not inv_file.exists():
            inv_file.parent.mkdir(parents=True, exist_ok=True)
            inv_file.write_text(
                f"""
{name} ansible_host={ip} ansible_user=rcpaffenroth ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[have_root]
{name}

[have_rcpaffenroth]
{name}
""".strip()
            )
            print(f"Created inventory: {inv_file}")
    else:
        inv_dir = Path(__file__).resolve().parent / "inventory"
        inv_dir.mkdir(parents=True, exist_ok=True)
        inv_file = inv_dir / f"{name}_temp.ini"
        inv_file.write_text(
            f"""
{name} ansible_host={ip} ansible_user=rcpaffenroth ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[have_root]
{name}

[have_rcpaffenroth]
{name}
""".strip()
        )
        print(f"Using inventory: {inv_file}")

    # Optional SSH wait
    if wait_ssh:
        print("Waiting for SSH to become available...")
        wait_for_ssh(ip)

    # Select playbooks
    if run_all or not any([system_setup, rcpaffenroth_setup, tailscale_setup, xfce_setup]):
        system_setup = rcpaffenroth_setup = tailscale_setup = xfce_setup = True

    playdir = Path(os.path.expanduser("~/projects/ansible/playdir"))

    def ap(args: List[str]) -> None:
        print_cmd(args)
        run(args)

    if system_setup:
        yml = playdir / "system_setup.yml"
        if yml.exists():
            ap(["ansible-playbook", "-i", str(inv_file), "-l", name, "--skip-tags=slow", str(yml)])

    if rcpaffenroth_setup:
        yml = playdir / "rcpaffenroth_setup.yml"
        if yml.exists():
            ap(["ansible-playbook", "-i", str(inv_file), "-l", name, "--skip-tags=slow,nonlocal", str(yml)])

    if tailscale_setup:
        yml = playdir / "tailscale_setup.yml"
        if yml.exists():
            ap(["ansible-playbook", "-i", str(inv_file), "-l", name, "-e", f"TAILSCALE_HOSTNAME=ts{name}", "--skip-tags=slow,nonlocal", str(yml)])

    if xfce_setup:
        yml = playdir / "xfce_setup.yml"
        if yml.exists():
            ap(["ansible-playbook", "-i", str(inv_file), "-l", name, "--skip-tags=slow,nonlocal", str(yml)])


if __name__ == "__main__":
    main()
