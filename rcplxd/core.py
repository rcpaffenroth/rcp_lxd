"""Core utilities for LXD operations."""

from __future__ import annotations

import shlex
import subprocess
from typing import List, Tuple


def run(cmd: List[str], check: bool = False) -> Tuple[int, str, str]:
    """Run a shell command and return (code, stdout, stderr)."""
    p = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def print_cmd(cmd: List[str]) -> None:
    """Print a command in shell-quoted format."""
    print("$", " ".join(shlex.quote(c) for c in cmd))


def get_container_ip(name: str) -> str:
    """Get the IP address of an LXD container/VM."""
    _rc, out, _ = run(["lxc", "list", name, "-f", "csv", "-c", "4"])  # IPv4 column
    # First token before any space
    return out.splitlines()[0].split(" ")[0] if out else ""


def container_exists(name: str) -> bool:
    """Check if a container/VM exists."""
    rc, _, _ = run(["lxc", "info", name])
    return rc == 0


def get_container_status(name: str) -> str:
    """Get the status of a container/VM."""
    _rc, status, _ = run(["lxc", "list", name, "-c", "s", "--format", "csv"])  # RUNNING/STOPPED
    return status.strip().upper()