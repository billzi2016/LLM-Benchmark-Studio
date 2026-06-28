from __future__ import annotations

import os
import platform
import subprocess
import time
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


def _read_top_cpu_summary() -> dict[str, float]:
    output = _run_command(["top", "-l", "2", "-n", "0"]) if platform.system() == "Darwin" else ""
    result: dict[str, float] = {}
    for line in output.splitlines():
        if "CPU usage:" not in line:
            continue
        _, values = line.split(":", maxsplit=1)
        for part in values.split(","):
            tokens = part.strip().split()
            if len(tokens) < 2:
                continue
            key = tokens[1].lower()
            if key == "sys":
                key = "system"
            try:
                result[key] = float(tokens[0].rstrip("%"))
            except ValueError:
                continue
    return result


def collect_cpu_metrics() -> dict[str, Any]:
    physical_cores = psutil.cpu_count(logical=False) if psutil else None
    logical_cores = psutil.cpu_count(logical=True) if psutil else os.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=0.2) if psutil else None
    per_cpu_percent = psutil.cpu_percent(interval=None, percpu=True) if psutil else []
    times_percent = psutil.cpu_times_percent(interval=None)._asdict() if psutil else {}
    load_avg = list(os.getloadavg()) if hasattr(os, "getloadavg") else [None, None, None]

    if cpu_percent is None and platform.system() == "Linux":
        cpu_percent = _read_linux_cpu_percent()
    if not per_cpu_percent and platform.system() == "Linux":
        per_cpu_percent = _read_linux_per_cpu_percent()

    if platform.system() == "Darwin":
        top_summary = _read_top_cpu_summary()
        if cpu_percent is None and top_summary:
            cpu_percent = max(0.0, 100.0 - top_summary.get("idle", 0.0))
        times_percent = {
            "user": top_summary.get("user", times_percent.get("user", 0.0)),
            "system": top_summary.get("system", times_percent.get("system", 0.0)),
            "idle": top_summary.get("idle", times_percent.get("idle", 0.0)),
            "nice": top_summary.get("nice", times_percent.get("nice", 0.0)),
        }

    return {
        "percent": round(float(cpu_percent), 2) if cpu_percent is not None else None,
        "per_cpu_percent": [round(float(value), 2) for value in per_cpu_percent],
        "physical_cores": physical_cores or 0,
        "logical_cores": logical_cores or 0,
        "load_average": {
            "1m": round(float(load_avg[0] or 0.0), 2),
            "5m": round(float(load_avg[1] or 0.0), 2),
            "15m": round(float(load_avg[2] or 0.0), 2),
        },
        "times_percent": {
            "user": round(float(times_percent.get("user", 0.0)), 2),
            "system": round(float(times_percent.get("system", 0.0)), 2),
            "idle": round(float(times_percent.get("idle", 0.0)), 2),
            "nice": round(float(times_percent.get("nice", 0.0)), 2),
        },
    }


def _linux_cpu_snapshot() -> tuple[int, int] | None:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as file:
            first = file.readline().strip().split()
    except OSError:
        return None
    if not first or first[0] != "cpu":
        return None
    values = [int(item) for item in first[1:]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return total, idle


def _read_linux_cpu_percent() -> float | None:
    first = _linux_cpu_snapshot()
    if not first:
        return None
    time.sleep(0.2)
    second = _linux_cpu_snapshot()
    if not second:
        return None
    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    return (1 - (idle_delta / total_delta)) * 100


def _read_linux_per_cpu_percent() -> list[float]:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as file:
            rows = [line.strip().split() for line in file if line.startswith("cpu") and line[3].isdigit()]
    except OSError:
        return []
    results: list[float] = []
    for row in rows:
        values = [int(item) for item in row[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        results.append(0.0 if total <= 0 else (1 - (idle / total)) * 100)
    return results
