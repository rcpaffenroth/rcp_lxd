"""Container management utilities."""

from pathlib import Path

from .core import run


def container_exists(name: str) -> bool:
    """Check if a container/VM exists."""
    rc, _, _ = run(["lxc", "info", name])
    return rc == 0


def get_container_status(name: str) -> str:
    """Get the status of a container/VM."""
    _, status, _ = run(["lxc", "list", name, "-c", "s", "--format", "csv"])
    return status.strip().upper()


def create_ssh_helper(name: str, ip: str) -> Path | None:
    """Create a convenience SSH helper script."""
    if not ip:
        return None
    
    ssh_helper = Path.cwd() / f"ssh_{name}.sh"
    ssh_helper.write_text(
        f"#!/usr/bin/env bash\nexec ssh -o StrictHostKeyChecking=no rcpaffenroth@{ip} \"$@\"\n",
        encoding="utf-8"
    )
    ssh_helper.chmod(0o755)
    return ssh_helper