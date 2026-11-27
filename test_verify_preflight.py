"""Regression coverage for source-bound credentialed preflight evidence."""

import json
import os
from pathlib import Path
import tempfile
import unittest

from apps.livekit_agent.verify_preflight import verify_latest_preflight

REVISION = "1" * 40


def report(revision=REVISION, *, mode="connectivity", status="passed"):
    return {
        "schema_version": 1,
        "source_revision": revision,
        "mode": mode,
        "status": status,
        "checks": [
            {"name": name, "status": "passed"}
            for name in (
                "components", "storage", "configuration",
                "livekit_connectivity", "openai_connectivity",
            )
        ],
    }


class VerifyPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def write(self, payload, run_id="a" * 32):
        path = self.directory / f"preflight_{run_id}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_accepts_passed_connectivity_for_exact_revision(self):
        self.write(report())
        result = verify_latest_preflight(self.directory, REVISION)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["source_revision"], REVISION)

    def test_rejects_offline_failed_or_wrong_revision(self):
        for payload in (
            report(mode="offline"),
            report(status="failed"),
            report(revision="2" * 40),
        ):
            with self.subTest(payload=payload):
                self.write(payload)
                self.assertEqual(
                    verify_latest_preflight(self.directory, REVISION)["status"],
                    "failed",
                )

    def test_newest_regular_report_controls_the_gate(self):
        older = self.write(report(), "a" * 32)
        newer = self.write(report(status="failed"), "b" * 32)
        os.utime(older, ns=(1, 1))
        os.utime(newer, ns=(2, 2))
        self.assertEqual(
            verify_latest_preflight(self.directory, REVISION)["status"], "failed"
        )

    def test_ignores_symlink_and_rejects_oversized_latest_report(self):
        external = self.directory / "external.json"
        external.write_text(json.dumps(report()), encoding="utf-8")
        (self.directory / f"preflight_{'a' * 32}.json").symlink_to(external)
        self.assertEqual(
            verify_latest_preflight(self.directory, REVISION)["status"], "failed"
        )

        oversized = self.directory / f"preflight_{'b' * 32}.json"
        oversized.write_bytes(b"{}" + b" " * (64 * 1024 + 1))
        self.assertEqual(
            verify_latest_preflight(self.directory, REVISION)["status"], "failed"
        )


if __name__ == "__main__":
    unittest.main()
