#!/usr/bin/env python3

"""
Simple Python version of create.sh using Click for CLI parsing.

Notes:
- Keeps the core behavior: create LXD container/VM with cloud-init, optional privileged mode,
  port forwards, and optional Ansible playbooks.
- Intentionally light on error handling for simplicity.
- Requires: lxc, cloud-init inside the image, ansible/ssh if playbooks are used.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import click


def run(cmd: List[str], check: bool = False) -> Tuple[int, str, str]:
    """Run a shell command and return (code, stdout, stderr)."""
    p = subprocess.run(cmd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def print_cmd(cmd: List[str]) -> None:
    print("$", " ".join(shlex.quote(c) for c in cmd))


def get_container_ip(name: str) -> str:
    _rc, out, _ = run(["lxc", "list", name, "-f", "csv", "-c", "4"])  # IPv4 column
    # First token before any space
    return out.splitlines()[0].split(" ")[0] if out else ""


# (SSH wait helper removed to keep script minimal)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--name", "name", "-n", default="vm1", show_default=True, help="Container/VM name")
@click.option("--distro", "distro", "-d", default="noble", show_default=True, help="Ubuntu release (e.g. focal, jammy, noble)")
@click.option("--cpu", "cpu", "-c", default=2, show_default=True, type=int, help="Number of CPUs")
@click.option("--memory", "memory", "-m", default="4GiB", show_default=True, help="Memory size, e.g., 4GiB")
@click.option("--cloud-init", "cloud_init", "-i", default="./cloud-init", show_default=True, type=click.Path(exists=True, dir_okay=False), help="Cloud-init file")
@click.option("--vm", is_flag=True, help="Create VM instead of container")
def main(
    name: str,
    distro: str,
    cpu: int,
    memory: str,
    cloud_init: str,
    vm: bool,
):
    """Create and configure an LXD container/VM with Ubuntu."""

    # (Ansible execution removed; inventory will still be generated for convenience.)

    # Exists? Prompt to delete like the bash version
    rc, _, _ = run(["lxc", "info", name])
    if rc == 0:
        reply = input(f"Container '{name}' already exists. Delete it? [y/N]: ").strip().lower()
        if reply.startswith("y"):
            print(f"Deleting existing container '{name}'...")
            print_cmd(["lxc", "delete", name, "--force"])
            run(["lxc", "delete", name, "--force"])  # ignore errors
        else:
            print("Aborting.")
            sys.exit(1)

    # Launch
    cloud_data = Path(cloud_init).read_text()
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

    # (privileged mode removed for simplicity)

    # Wait for cloud-init
    print("Waiting for container to start and cloud-init to complete...")
    time.sleep(15)

    # (port forwarding removed for simplicity)

    # Always create an Ansible inventory file for convenience
    ip = get_container_ip(name)
    inv_file: Optional[Path] = None
    if ip:
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
        print(f"Created temporary inventory at: {inv_file}")
    else:
        print("Warning: Could not determine container IP; inventory not written.")

    # Create a tiny SSH helper script for convenience
    ip = ip or get_container_ip(name)
    ssh_helper = None
    if ip:
        ssh_helper = Path(__file__).resolve().parent / f"ssh_{name}.sh"
        ssh_helper.write_text(
            """#!/usr/bin/env bash
exec ssh -o StrictHostKeyChecking=no rcpaffenroth@{ip} "$@"
""".format(ip=ip)
        )
        try:
            ssh_helper.chmod(0o755)
        except Exception:
            pass
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
        print(f"  ansible-playbook -i {inv_file} -l {name} --skip-tags=slow ~/projects/ansible/playdir/system_setup.yml")
        print(f"  ansible-playbook -i {inv_file} -l {name} --skip-tags=slow,nonlocal ~/projects/ansible/playdir/rcpaffenroth_setup.yml")
        print(f"  ansible-playbook -i {inv_file} -l {name} -e TAILSCALE_HOSTNAME=ts{name} --skip-tags=slow,nonlocal ~/projects/ansible/playdir/tailscale_setup.yml")
        print(f"  ansible-playbook -i {inv_file} -l {name} --skip-tags=slow,nonlocal ~/projects/ansible/playdir/xfce_setup.yml")
    if ssh_helper and ip:
        print()
        print("SSH helper created:")
        print(f"  {ssh_helper}")
        print("Usage:")
        print(f"  {ssh_helper}")
    print(f"Direct exec: lxc exec {name} -- bash")
    print()
    print(f"To delete: lxc delete {name} --force")


if __name__ == "__main__":
    main()
