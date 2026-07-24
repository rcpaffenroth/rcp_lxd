"""Container management utilities."""

import shutil
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


def list_host_gpus() -> list[dict[str, str]]:
    """List the host's NVIDIA GPUs, in nvidia-smi index order.

    Each entry has "index" (the nvidia-smi index the user selects with), "name",
    and "pci" (the PCI address LXD uses to identify the card). nvidia-smi reports
    the address with an 8-digit domain ("00000000:41:00.0"); LXD wants the
    conventional 4-digit form ("0000:41:00.0"), so we trim the domain.
    """
    if shutil.which("nvidia-smi") is None:
        raise ValueError("nvidia-smi not found; cannot enumerate GPUs for passthrough.")

    rc, out, err = run(["nvidia-smi", "--query-gpu=index,name,pci.bus_id",
                        "--format=csv,noheader"])
    if rc != 0:
        raise ValueError(f"nvidia-smi failed: {err or 'unknown error'}")

    gpus = []
    for line in out.splitlines():
        index, gpu_name, bus_id = (part.strip() for part in line.split(",", 2))
        domain, bus, devfn = bus_id.split(":")
        gpus.append({"index": index, "name": gpu_name,
                     "pci": f"{domain[-4:]}:{bus}:{devfn}".lower()})

    if not gpus:
        # The driver is installed but no card is present. Fail loudly rather than
        # let "--gpu all" quietly become "no GPUs" on a GPU-less host.
        raise ValueError("nvidia-smi reported no GPUs on this host.")
    return gpus


def resolve_gpus(specs: tuple[str, ...]) -> list[dict[str, str]]:
    """Resolve --gpu selectors into host GPU records.

    Selectors are nvidia-smi indices, optionally comma-separated, or "all".
    Duplicates are collapsed so passing the same GPU twice is harmless.
    """
    tokens = [tok.strip() for spec in specs for tok in spec.split(",") if tok.strip()]
    gpus = list_host_gpus()

    if any(tok.lower() == "all" for tok in tokens):
        return gpus

    by_index = {g["index"]: g for g in gpus}
    selected: list[dict[str, str]] = []
    for tok in tokens:
        if tok not in by_index:
            raise ValueError(
                f"No GPU with index {tok!r}; host GPUs are {sorted(by_index)} "
                "(see 'nvidia-smi -L')."
            )
        if by_index[tok] not in selected:
            selected.append(by_index[tok])
    return selected


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