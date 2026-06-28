from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .cpu import collect_cpu_metrics
from .disk import collect_disk_metrics
from .gpu import collect_gpu_metrics
from .memory import collect_memory_metrics
from .network import collect_network_metrics
from .process import collect_process_metrics
from .system_info import collect_system_info


def collect_system_snapshot() -> dict[str, Any]:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "system": collect_system_info(),
        "cpu": collect_cpu_metrics(),
        "memory": collect_memory_metrics(),
        "gpu": collect_gpu_metrics(),
        "disk": collect_disk_metrics("/"),
        "network": collect_network_metrics(),
        "process": collect_process_metrics(),
    }
