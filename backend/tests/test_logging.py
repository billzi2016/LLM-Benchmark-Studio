from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from apps.core.logging import log_llm_walltime


class LoggingTests(SimpleTestCase):
    def test_logging_paths_point_to_logs_directory(self) -> None:
        self.assertIn("/logs/", settings.SERVICE_LOG_PATH.replace("\\", "/"))
        self.assertIn("/logs/", settings.LLM_WALLTIME_LOG_PATH.replace("\\", "/"))

    @patch("apps.core.logging.llm_walltime_logger.info")
    def test_llm_walltime_payload_contains_elapsed_and_walltime(self, logger_info) -> None:  # type: ignore[no-untyped-def]
        started_at = datetime(2026, 6, 27, 7, 0, 0, tzinfo=timezone.utc)
        finished_at = started_at + timedelta(seconds=3.25)

        log_llm_walltime(
            provider="ollama",
            model="gpt-oss:20b",
            task_kind="benchmark",
            prompt_length=128,
            started_at=started_at,
            finished_at=finished_at,
            dataset_name="mmlu",
            language_code="en",
        )

        payload = json.loads(logger_info.call_args.args[0])
        self.assertEqual(payload["provider"], "ollama")
        self.assertEqual(payload["model"], "gpt-oss:20b")
        self.assertEqual(payload["dataset_name"], "mmlu")
        self.assertEqual(payload["language_code"], "en")
        self.assertEqual(payload["elapsed_seconds"], 3.25)
        self.assertEqual(payload["walltime_seconds"], 3.25)
