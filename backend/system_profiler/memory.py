from __future__ import annotations

import platform
import subprocess
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def _run_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def _read_vm_stat() -> dict[str, int]:
    if platform.system() != "Darwin":
        return {}
    output = _run_command(["vm_stat"])
    stats: dict[str, int] = {}
    page_size = 4096
    for line in output.splitlines():
        if "page size of" in line:
            for token in line.split():
                if token.isdigit():
                    page_size = int(token)
                    break
            stats["page_size"] = page_size
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", maxsplit=1)
        cleaned = value.strip().rstrip(".").replace(".", "")
        try:
            stats[key.strip()] = int(cleaned)
        except ValueError:
            continue
    return stats


def collect_memory_metrics() -> dict[str, Any]:
    virtual = psutil.virtual_memory() if psutil else None
    swap = psutil.swap_memory() if psutil else None
    vm_stats = _read_vm_stat()
    page_size = vm_stats.get("page_size", 4096)
    wired_bytes = vm_stats.get("Pages wired down", 0) * page_size
    compressed_bytes = vm_stats.get("Pages occupied by compressor", 0) * page_size
    active_bytes = vm_stats.get("Pages active", 0) * page_size
    inactive_bytes = vm_stats.get("Pages inactive", 0) * page_size

    return {
        "total_bytes": int(getattr(virtual, "total", 0)),
        "used_bytes": int(getattr(virtual, "used", 0)),
        "available_bytes": int(getattr(virtual, "available", 0)),
        "free_bytes": int(getattr(virtual, "free", 0)),
        "percent": round(float(getattr(virtual, "percent", 0.0)), 2),
        "swap_total_bytes": int(getattr(swap, "total", 0)),
        "swap_used_bytes": int(getattr(swap, "used", 0)),
        "swap_percent": round(float(getattr(swap, "percent", 0.0)), 2),
        "active_bytes": active_bytes,
        "inactive_bytes": inactive_bytes,
        "wired_bytes": wired_bytes,
        "compressed_bytes": compressed_bytes,
    }
