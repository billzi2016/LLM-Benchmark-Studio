from __future__ import annotations

import os
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def collect_process_metrics() -> dict[str, Any]:
    pid = os.getpid()
    if not psutil:
        return {"pid": pid, "cpu_percent": 0.0, "memory_percent": 0.0, "threads": 0}
    process = psutil.Process(pid)
    memory_info = process.memory_info()
    try:
        open_files = len(process.open_files())
    except (OSError, psutil.Error):
        open_files = 0
    return {
        "pid": pid,
        "cpu_percent": round(float(process.cpu_percent(interval=0.0)), 2),
        "memory_percent": round(float(process.memory_percent()), 2),
        "rss_bytes": int(memory_info.rss),
        "vms_bytes": int(memory_info.vms),
        "threads": process.num_threads(),
        "open_files": open_files,
    }
