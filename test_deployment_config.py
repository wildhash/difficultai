"""Regression checks for the owner-pilot worker deployment contract."""

from pathlib import Path
import unittest


ROOT = Path(__file__).parent


class DeploymentConfigTests(unittest.TestCase):
    def test_container_runs_production_worker_as_non_root(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM python:3.11-slim", dockerfile)
        self.assertIn("USER difficultai", dockerfile)
        self.assertIn('CMD ["python", "-m", "apps.livekit_agent", "start"]', dockerfile)
        self.assertIn("SCORECARD_DIR=/data/scorecards", dockerfile)

    def test_owner_pilot_mount_matches_scorecard_directory(self):
        compose = (ROOT / "compose.owner-pilot.yml").read_text(encoding="utf-8")
        self.assertIn("SCORECARD_DIR: /data/scorecards", compose)
        self.assertIn("difficultai-scorecards:/data/scorecards", compose)
        self.assertIn("- .env", compose)
        self.assertIn("restart: unless-stopped", compose)

    def test_build_context_excludes_credentials_and_runtime_evidence(self):
        exclusions = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())
        for required in (".env", ".env.*", "scorecards", ".git", ".venv", "node_modules"):
            self.assertIn(required, exclusions)


if __name__ == "__main__":
    unittest.main()
