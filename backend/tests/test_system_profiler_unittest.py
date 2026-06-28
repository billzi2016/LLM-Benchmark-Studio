from __future__ import annotations

import unittest

from system_profiler.snapshot import collect_system_snapshot


class SystemProfilerSnapshotUnitTest(unittest.TestCase):
    def test_collect_system_snapshot_returns_expected_sections(self) -> None:
        snapshot = collect_system_snapshot()

        self.assertIn("timestamp", snapshot)
        self.assertIn("system", snapshot)
        self.assertIn("cpu", snapshot)
        self.assertIn("memory", snapshot)
        self.assertIn("gpu", snapshot)
        self.assertIn("disk", snapshot)
        self.assertIn("network", snapshot)
        self.assertIn("process", snapshot)

    def test_collect_system_snapshot_exposes_numeric_metrics(self) -> None:
        snapshot = collect_system_snapshot()

        self.assertGreaterEqual(snapshot["cpu"]["percent"], 0.0)
        self.assertLessEqual(snapshot["cpu"]["percent"], 100.0)

        self.assertGreaterEqual(snapshot["memory"]["percent"], 0.0)
        self.assertLessEqual(snapshot["memory"]["percent"], 100.0)
        self.assertGreater(snapshot["memory"]["total_bytes"], 0)

        self.assertGreaterEqual(snapshot["disk"]["percent"], 0.0)
        self.assertLessEqual(snapshot["disk"]["percent"], 100.0)
        self.assertGreater(snapshot["disk"]["total_bytes"], 0)

        self.assertGreaterEqual(snapshot["network"]["bytes_sent"], 0)
        self.assertGreaterEqual(snapshot["network"]["bytes_recv"], 0)

        self.assertGreater(snapshot["process"]["pid"], 0)
        self.assertGreaterEqual(snapshot["process"]["threads"], 0)


if __name__ == "__main__":
    unittest.main()
