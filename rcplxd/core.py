"""Core utilities for LXD operations."""

import shlex
import subprocess
import json

def run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a shell command and return (code, stdout, stderr)."""
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def print_cmd(cmd: list[str]) -> None:
    """Print a command in shell-quoted format."""
    print("$", " ".join(shlex.quote(c) for c in cmd))


def get_container_ip(name: str) -> str:
    """Get the IP address of an LXD container/VM."""
    _, out, _ = run(["lxc", "list", name, "-f", "json"])
    info = json.loads(out)
    address = info[0]["state"]["network"].get("eth0", {}).get("addresses", [])
    return address[0]["address"] if address else ""