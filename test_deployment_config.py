"""Regression checks for the owner-pilot worker deployment contract."""

from pathlib import Path
import stat
import unittest

import yaml


ROOT = Path(__file__).parent


class DeploymentConfigTests(unittest.TestCase):
    def test_container_runs_production_worker_as_non_root(self):
        path = ROOT / "Dockerfile"
        self.assertTrue(path.is_file(), f"Missing deployment artifact: {path}")
        normalized = " ".join(path.read_text(encoding="utf-8").split())
        self.assertIn("FROM python:3.11-slim", normalized)
        self.assertIn("USER difficultai", normalized)
        self.assertIn('CMD ["python", "-m", "apps.livekit_agent", "start"]', normalized)
        self.assertIn("SCORECARD_DIR=/data/scorecards", normalized)

    def test_owner_pilot_mount_matches_scorecard_directory(self):
        path = ROOT / "compose.owner-pilot.yml"
        self.assertTrue(path.is_file(), f"Missing deployment artifact: {path}")
        compose = " ".join(path.read_text(encoding="utf-8").split())
        self.assertIn("SCORECARD_DIR: /data/scorecards", compose)
        self.assertIn("difficultai-scorecards:/data/scorecards", compose)
        self.assertIn("image: ${DIFFICULTAI_IMAGE:-difficultai-owner-pilot:latest}", compose)
        self.assertIn("- .env", compose)
        self.assertIn("restart: unless-stopped", compose)

    def test_build_context_excludes_credentials_and_runtime_evidence(self):
        path = ROOT / ".dockerignore"
        self.assertTrue(path.is_file(), f"Missing deployment artifact: {path}")
        exclusions = set(path.read_text(encoding="utf-8").splitlines())
        for required in (".env", ".env.*", "scorecards", ".git", ".venv", "node_modules"):
            self.assertIn(required, exclusions)

    def test_ci_executes_worker_image_and_replacement_volume_check(self):
        script = ROOT / "scripts" / "verify-worker-image.sh"
        workflow = ROOT / ".github" / "workflows" / "python-tests.yml"
        self.assertTrue(script.is_file(), f"Missing image verification: {script}")
        self.assertTrue(script.stat().st_mode & stat.S_IXUSR, "Verification script must be executable")
        contents = " ".join(script.read_text(encoding="utf-8").split())
        self.assertIn('docker compose --project-name "$project"', contents)
        self.assertIn("$compose config --quiet", contents)
        self.assertIn("$compose build", contents)
        self.assertGreaterEqual(contents.count("$compose run --rm --no-deps worker"), 5)
        self.assertIn("python -m apps.livekit_agent.smoke_test --offline", contents)
        self.assertIn("down --volumes --remove-orphans", contents)
        self.assertIn("scripts/verify-worker-image.sh", workflow.read_text(encoding="utf-8"))

    def test_vite_waits_for_legacy_pages_publication(self):
        workflow = ROOT / ".github" / "workflows" / "deploy-pages.yml"
        raw = workflow.read_text(encoding="utf-8")
        config = yaml.safe_load(raw)
        # PyYAML's YAML 1.1 loader treats the plain key `on` as boolean true.
        triggers = config.get("on", config.get(True))
        self.assertIsInstance(triggers, dict)
        self.assertNotIn("workflow_run", triggers)
        self.assertEqual(config.get("permissions", {}).get("actions"), "read")
        deploy = config["jobs"]["deploy"]
        self.assertEqual(deploy.get("permissions", {}).get("actions"), "read")
        contents = " ".join(raw.split())
        self.assertIn("node scripts/wait-for-legacy-pages.mjs", contents)
        self.assertIn("if: github.event_name == 'push'", contents)
        for variable in ("GH_TOKEN", "REPOSITORY", "COMMIT_SHA"):
            self.assertIn(variable, contents)
        self.assertTrue(
            (ROOT / "apps" / "web" / "demo" / "scripts" /
             "wait-for-legacy-pages.mjs").is_file()
        )


if __name__ == "__main__":
    unittest.main()
