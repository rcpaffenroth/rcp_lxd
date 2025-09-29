#!/usr/bin/env python3

"""
Simple Python version of clean.sh using Click for CLI parsing.

Stops and removes an LXD container/VM.
Intentionally minimal error handling for simplicity.
"""

from __future__ import annotations

import shlex
import subprocess
from typing import List, Tuple

import click


def run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(cmd, text=True, capture_output=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def print_cmd(cmd: List[str]) -> None:
    print("$", " ".join(shlex.quote(c) for c in cmd))


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--name", "name", "-n", required=True, help="Container/VM name to remove")
@click.option("--force", "force", "-f", is_flag=True, help="Remove without confirmation")
def main(name: str, force: bool) -> None:
    # Check existence
    rc, _, _ = run(["lxc", "info", name])
    if rc != 0:
        print(f"Warning: '{name}' does not exist (or lxc not available). Nothing to do.")
        return

    # Status
    _rc, status, _ = run(["lxc", "list", name, "-c", "s", "--format", "csv"])  # RUNNING/STOPPED

    # Confirm
    if not force:
        click.confirm(f"About to remove '{name}' (Status: {status}). Continue?", default=False, abort=True)

    print(f"Cleaning up container: {name}")

    # Stop if running
    if status.strip().upper() == "RUNNING":
        print("Stopping...")
        print_cmd(["lxc", "stop", name])
        run(["lxc", "stop", name])

    # Delete
    print("Removing...")
    print_cmd(["lxc", "delete", name])
    run(["lxc", "delete", name])

    print(f"Container '{name}' removed")


if __name__ == "__main__":
    main()
