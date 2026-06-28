from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def collect_disk_metrics(path: str = "/") -> dict[str, Any]:
    target = Path(path)
    if psutil:
        usage = psutil.disk_usage(str(target))
        return {
            "path": str(target),
            "total_bytes": int(usage.total),
            "used_bytes": int(usage.used),
            "free_bytes": int(usage.free),
            "percent": round(float(usage.percent), 2),
        }

    usage = shutil.disk_usage(str(target))
    return {
        "path": str(target),
        "total_bytes": int(usage.total),
        "used_bytes": int(usage.used),
        "free_bytes": int(usage.free),
        "percent": round(float((usage.used / usage.total) * 100 if usage.total else 0.0), 2),
    }
