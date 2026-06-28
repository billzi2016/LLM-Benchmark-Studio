from __future__ import annotations

from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


def collect_network_metrics() -> dict[str, Any]:
    counters = psutil.net_io_counters() if psutil else None
    if counters is None:
        counters = _read_linux_net_dev()
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


class _NetCounters:
    def __init__(self, **kwargs: int) -> None:
        self.bytes_sent = kwargs.get("bytes_sent", 0)
        self.bytes_recv = kwargs.get("bytes_recv", 0)
        self.packets_sent = kwargs.get("packets_sent", 0)
        self.packets_recv = kwargs.get("packets_recv", 0)
        self.errin = kwargs.get("errin", 0)
        self.errout = kwargs.get("errout", 0)
        self.dropin = kwargs.get("dropin", 0)
        self.dropout = kwargs.get("dropout", 0)


def _read_linux_net_dev() -> _NetCounters | None:
    try:
        with open("/proc/net/dev", "r", encoding="utf-8") as file:
            lines = file.readlines()[2:]
    except OSError:
        return None
    total = {
        "bytes_recv": 0,
        "packets_recv": 0,
        "errin": 0,
        "dropin": 0,
        "bytes_sent": 0,
        "packets_sent": 0,
        "errout": 0,
        "dropout": 0,
    }
    for line in lines:
        if ":" not in line:
            continue
        _, values = line.split(":", maxsplit=1)
        parts = values.split()
        if len(parts) < 16:
            continue
        total["bytes_recv"] += int(parts[0])
        total["packets_recv"] += int(parts[1])
        total["errin"] += int(parts[2])
        total["dropin"] += int(parts[3])
        total["bytes_sent"] += int(parts[8])
        total["packets_sent"] += int(parts[9])
        total["errout"] += int(parts[10])
        total["dropout"] += int(parts[11])
    return _NetCounters(**total)
