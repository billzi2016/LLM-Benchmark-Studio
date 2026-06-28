from __future__ import annotations

import json
import plistlib
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


def _run_plist_command(command: list[str]) -> Any | None:
    try:
        result = subprocess.run(command, check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    if not result.stdout:
        return None
    try:
        return plistlib.loads(result.stdout)
    except Exception:  # noqa: BLE001
        return None


def _collect_nested_objects(node: Any, results: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        results.append(node)
        for value in node.values():
            _collect_nested_objects(value, results)
    elif isinstance(node, list):
        for item in node:
            _collect_nested_objects(item, results)


def _normalize_metric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    if isinstance(value, str):
        stripped = value.strip().rstrip("%")
        if not stripped:
            return None
        try:
            return round(float(stripped), 2)
        except ValueError:
            return None
    return None


def _collect_gpu_metrics_from_ioreg() -> dict[str, float | None]:
    plist_data = _run_plist_command(["ioreg", "-r", "-d", "2", "-a", "-w", "0", "-c", "IOAccelerator"])
    if plist_data is None:
        return {
            "utilization_percent": None,
            "renderer_utilization_percent": None,
            "tiler_utilization_percent": None,
            "ane_utilization_percent": None,
        }
    all_nodes: list[dict[str, Any]] = []
    _collect_nested_objects(plist_data, all_nodes)
    key_map = {
        "utilization_percent": ("Device Utilization %", "GPU Utilization %", "Utilization %"),
        "renderer_utilization_percent": ("Renderer Utilization %", "Renderer Utilization"),
        "tiler_utilization_percent": ("Tiler Utilization %", "Tiler Utilization"),
        "ane_utilization_percent": (
            "ANE Utilization %",
            "ANE Utilization",
            "Neural Engine Utilization %",
        ),
    }
    metrics = {key: None for key in key_map}
    for node in all_nodes:
        for metric_name, candidate_keys in key_map.items():
            if metrics[metric_name] is not None:
                continue
            for key in candidate_keys:
                if key in node:
                    metrics[metric_name] = _normalize_metric(node[key])
                    break
    return metrics


def collect_gpu_metrics() -> dict[str, Any]:
    if platform.system() != "Darwin":
        return {
            "available": False,
            "vendor": "",
            "name": "",
            "utilization_percent": None,
            "renderer_utilization_percent": None,
            "tiler_utilization_percent": None,
            "ane_utilization_percent": None,
        }

    display_info = _run_json_command(["system_profiler", "SPDisplaysDataType", "-json"]) or {}
    display_items = display_info.get("SPDisplaysDataType", []) if isinstance(display_info, dict) else []
    primary = display_items[0] if display_items else {}
    metrics = _collect_gpu_metrics_from_ioreg()
    return {
        "available": bool(display_items),
        "vendor": primary.get("spdisplays_vendor", "") if isinstance(primary, dict) else "",
        "name": (
            primary.get("_name") or primary.get("sppci_model") or primary.get("spdisplays_vendor") or ""
            if isinstance(primary, dict)
            else ""
        ),
        **metrics,
    }
