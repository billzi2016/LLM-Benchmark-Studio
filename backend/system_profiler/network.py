from __future__ import annotations

from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def collect_network_metrics() -> dict[str, Any]:
    counters = psutil.net_io_counters() if psutil else None
    return {
        "bytes_sent": int(getattr(counters, "bytes_sent", 0)),
        "bytes_recv": int(getattr(counters, "bytes_recv", 0)),
        "packets_sent": int(getattr(counters, "packets_sent", 0)),
        "packets_recv": int(getattr(counters, "packets_recv", 0)),
        "errin": int(getattr(counters, "errin", 0)),
        "errout": int(getattr(counters, "errout", 0)),
        "dropin": int(getattr(counters, "dropin", 0)),
        "dropout": int(getattr(counters, "dropout", 0)),
    }
