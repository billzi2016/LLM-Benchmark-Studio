from __future__ import annotations

import json
import platform
import subprocess
from typing import Any


def _run_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def _run_json_command(command: list[str]) -> dict[str, Any] | list[Any] | None:
    output = _run_command(command)
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def _bytes_to_gib(value: int | str | None) -> float:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(number / (1024**3), 2)


def collect_system_info() -> dict[str, Any]:
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    processor = platform.processor()
    hostname = platform.node()
    info: dict[str, Any] = {
        "platform": system,
        "release": release,
        "machine": machine,
        "processor": processor,
        "hostname": hostname,
    }
    if system != "Darwin":
        return info

    hardware_info = _run_json_command(["system_profiler", "SPHardwareDataType", "-json"]) or {}
    display_info = _run_json_command(["system_profiler", "SPDisplaysDataType", "-json"]) or {}
    hardware_items = hardware_info.get("SPHardwareDataType", []) if isinstance(hardware_info, dict) else []
    display_items = display_info.get("SPDisplaysDataType", []) if isinstance(display_info, dict) else []
    hardware = hardware_items[0] if hardware_items else {}

    physical_cores = _run_command(["sysctl", "-n", "hw.physicalcpu"])
    logical_cores = _run_command(["sysctl", "-n", "hw.logicalcpu"])
    total_memory = _run_command(["sysctl", "-n", "hw.memsize"])

    info.update(
        {
            "macos_version": platform.mac_ver()[0] or "unknown",
            "cpu_brand": _run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
            or str(hardware.get("chip_type") or hardware.get("machine_name") or processor or "unknown"),
            "physical_cores": int(physical_cores or 0),
            "logical_cores": int(logical_cores or 0),
            "total_memory_gib": _bytes_to_gib(total_memory),
            "model_name": hardware.get("machine_name", "unknown"),
            "model_identifier": hardware.get("machine_model", "unknown"),
            "chip": hardware.get("chip_type", "unknown"),
            "serial_number": hardware.get("serial_number", "unknown"),
            "gpu_count": len(display_items),
        }
    )
    return info
