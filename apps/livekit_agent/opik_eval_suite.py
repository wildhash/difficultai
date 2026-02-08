"""\
Opik Evaluation Suite for DifficultAI

This script demonstrates systematic evaluation + experiment tracking using Opik:

- A fixed regression dataset (representative scenario/metrics pairs)
- A deterministic task (our `EvaluatorAgent` scorecard)
- Per-item scoring functions that convert scorecard dimensions into Opik metrics

Run:
  make opik-eval-suite

Notes:
- Requires `OPIK_API_KEY` (Opik Cloud) or `OPIK_URL_OVERRIDE` (self-hosted).
- Uses `OPIK_PROJECT` and `OPIK_WORKSPACE` to route data.
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


def _repo_root() -> Path:
    env_root = os.getenv("REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()

    path = Path(__file__).resolve()
    allow_guess = os.getenv("OPIK_EVAL_ALLOW_ROOT_GUESS", "").lower() in ("1", "true", "yes")
    for parent in [path] + list(path.parents):
        if (parent / ".git").is_dir():
            return parent

    if allow_guess:
        print(
            f"Warning: could not confidently locate repository root from {path}; "
            "defaulting to current working directory. Set REPO_ROOT to override."
        )
        return Path.cwd()

    raise RuntimeError(
        f"Could not locate repository root from {path}; set REPO_ROOT (or set OPIK_EVAL_ALLOW_ROOT_GUESS=1)."
    )


def _git_sha() -> Optional[str]:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return sha
    except Exception:
        return None


def _print_header(title: str) -> None:
    print("=" * 78)
    print(title)
    print("=" * 78)


def _ensure_repo_on_path() -> None:
    root = _repo_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_REQUIRED_METRICS_KEYS = {
    "vague_response_count",
    "deflection_count",
    "commitments_made",
    "total_exchanges",
    "current_difficulty",
    "scenario_difficulty",
}

_REQUIRED_SCENARIO_KEYS = {"persona_type", "company", "role", "difficulty"}


def _validate_seed_item(item: Dict[str, Any]) -> None:
    metrics = item.get("metrics") or {}
    scenario = item.get("scenario") or {}

    missing_metrics = _REQUIRED_METRICS_KEYS - set(metrics.keys())
    missing_scenario = _REQUIRED_SCENARIO_KEYS - set(scenario.keys())
    if missing_metrics or missing_scenario:
        raise ValueError(
            f"Invalid dataset item {item.get('case_id')!r}: missing metrics {sorted(missing_metrics)} "
            f"or scenario {sorted(missing_scenario)}"
        )

    for key in _REQUIRED_METRICS_KEYS:
        try:
            float(metrics[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Metric {key!r} for case_id={item.get('case_id')!r} must be numeric, got {metrics[key]!r}"
            ) from exc

    if metrics.get("total_exchanges", 0) <= 0:
        raise ValueError(
            f"total_exchanges must be positive for case_id={item.get('case_id')!r}, got {metrics.get('total_exchanges')!r}"
        )


def _seed_dataset_items() -> List[Dict[str, Any]]:
    """A small, deterministic dataset for scorecard regression.

    Each item is shaped to be directly consumable by our task function and
    easy to extend.
    """

    return [
        {
            "case_id": "baseline-strong",
            "scenario": {
                "persona_type": "ELITE_INTERVIEWER",
                "company": "TechCorp",
                "role": "Software Engineer",
                "difficulty": 0.3,
            },
            "metrics": {
                "vague_response_count": 0,
                "deflection_count": 0,
                "commitments_made": 2,
                "total_exchanges": 6,
                "current_difficulty": 0.3,
                "scenario_difficulty": 0.3,
            },
        },
        {
            "case_id": "vague-answers",
            "scenario": {
                "persona_type": "ELITE_INTERVIEWER",
                "company": "TechCorp",
                "role": "Software Engineer",
                "difficulty": 0.5,
            },
            "metrics": {
                "vague_response_count": 3,
                "deflection_count": 0,
                "commitments_made": 1,
                "total_exchanges": 6,
                "current_difficulty": 0.6,
                "scenario_difficulty": 0.5,
            },
        },
        {
            "case_id": "deflection-heavy",
            "scenario": {
                "persona_type": "SKEPTICAL_INVESTOR",
                "company": "FinCo",
                "role": "Founder",
                "difficulty": 0.7,
            },
            "metrics": {
                "vague_response_count": 1,
                "deflection_count": 3,
                "commitments_made": 0,
                "total_exchanges": 6,
                "current_difficulty": 0.9,
                "scenario_difficulty": 0.7,
            },
        },
        {
            "case_id": "commitment-strong",
            "scenario": {
                "persona_type": "ANGRY_CUSTOMER",
                "company": "RetailCo",
                "role": "Account Manager",
                "difficulty": 0.6,
            },
            "metrics": {
                "vague_response_count": 0,
                "deflection_count": 0,
                "commitments_made": 3,
                "total_exchanges": 6,
                "current_difficulty": 0.6,
                "scenario_difficulty": 0.6,
            },
        },
        {
            "case_id": "under-pressure",
            "scenario": {
                "persona_type": "HOSTILE_REPORTER",
                "company": "MediaCo",
                "role": "Spokesperson",
                "difficulty": 0.9,
            },
            "metrics": {
                "vague_response_count": 2,
                "deflection_count": 2,
                "commitments_made": 1,
                "total_exchanges": 7,
                "current_difficulty": 1.0,
                "scenario_difficulty": 0.9,
            },
        },
    ]


def main() -> int:
    _ensure_repo_on_path()
    load_dotenv()

    from difficultai.observability.opik_tracing import (
        configure_opik,
        get_opik_config,
        is_opik_enabled,
    )

    if not is_opik_enabled():
        print("Opik is disabled via OPIK_DISABLED; nothing to do.")
        return 0

    config = get_opik_config()
    if not config.get("api_key") and not config.get("url_override"):
        print("Missing Opik credentials: set OPIK_API_KEY or OPIK_URL_OVERRIDE.")
        return 2

    dataset_version = os.getenv("OPIK_EVAL_DATASET_VERSION", "v1")
    strict_eval = os.getenv("OPIK_EVAL_STRICT", "1").lower() not in ("0", "false", "no")

    import opik
    from opik.evaluation.metrics.score_result import ScoreResult

    from agents.evaluator import EvaluatorAgent

    _print_header("DifficultAI Opik Evaluation Suite")
    print(f"Project: {config['project_name']}")
    print(f"Workspace: {config['workspace']}")
    if config["url_override"]:
        print(f"URL Override: {config['url_override']}")

    configure_opik(config)

    client = opik.Opik(project_name=config["project_name"], workspace=config["workspace"])
    dataset_name = os.getenv(
        "OPIK_EVAL_DATASET",
        f"difficultai-scorecard-regression-{dataset_version}",
    )
    dataset = client.get_or_create_dataset(
        name=dataset_name,
        description="Deterministic scorecard regression dataset for DifficultAI",
    )

    seed_items = _seed_dataset_items()
    for item in seed_items:
        _validate_seed_item(item)

    from difficultai.scorecard import SCORECARD_DIMENSIONS

    evaluator = EvaluatorAgent()
    expected_dimensions = set(SCORECARD_DIMENSIONS)

    check_determinism = os.getenv("OPIK_EVAL_CHECK_DETERMINISM", "1").lower() not in (
        "0",
        "false",
        "no",
    )
    if check_determinism:
        import math

        for sample in seed_items:
            first = evaluator.evaluate_conversation(
                metrics=sample["metrics"],
                scenario=sample["scenario"],
            )
            second = evaluator.evaluate_conversation(
                metrics=sample["metrics"],
                scenario=sample["scenario"],
            )
            first_scores = first.get("scores") or {}
            second_scores = second.get("scores") or {}

            if set(first_scores.keys()) != set(second_scores.keys()):
                raise RuntimeError(
                    f"EvaluatorAgent returned different score keys for case_id={sample.get('case_id')!r}: "
                    f"{sorted(first_scores.keys())} vs {sorted(second_scores.keys())}"
                )

            for key in first_scores.keys():
                a = first_scores[key]
                b = second_scores[key]

                try:
                    fa = float(a)
                    fb = float(b)
                except (TypeError, ValueError):
                    if a != b:
                        raise RuntimeError(
                            f"Non-deterministic non-numeric score for '{key}' in case_id={sample.get('case_id')!r}: "
                            f"{a!r} vs {b!r}"
                        )
                    continue

                if not math.isclose(fa, fb, rel_tol=0.0, abs_tol=1e-6):
                    raise RuntimeError(
                        f"Non-deterministic score for '{key}' in case_id={sample.get('case_id')!r}: {fa!r} vs {fb!r}"
                    )

    # Insert seed cases if the dataset is empty (or count is unavailable).
    if (dataset.dataset_items_count or 0) == 0:
        dataset.insert(seed_items)
        print(f"Seeded dataset '{dataset_name}' with {len(seed_items)} items")
    else:
        print(f"Using existing dataset '{dataset_name}' (items: {dataset.dataset_items_count})")

    def task(dataset_item: Dict[str, Any]) -> Dict[str, Any]:
        metrics = dataset_item.get("metrics") or {}
        scenario = dataset_item.get("scenario") or {}
        scorecard = evaluator.evaluate_conversation(metrics=metrics, scenario=scenario)

        if not isinstance(scorecard, dict):
            reason = (
                f"EvaluatorAgent returned invalid scorecard for case_id={dataset_item.get('case_id')!r}: {scorecard!r}"
            )
            if strict_eval:
                raise RuntimeError(reason)
            return {
                "scorecard": None,
                "case_id": dataset_item.get("case_id"),
                "error": reason,
            }

        scores = scorecard.get("scores")
        if not isinstance(scores, dict):
            reason = (
                f"EvaluatorAgent returned invalid scorecard for case_id={dataset_item.get('case_id')!r}: {scorecard!r}"
            )
            if strict_eval:
                raise RuntimeError(reason)
            return {
                "scorecard": None,
                "case_id": dataset_item.get("case_id"),
                "error": reason,
            }

        if strict_eval:
            missing_dimensions = expected_dimensions - set(scores.keys())
            if missing_dimensions:
                raise RuntimeError(
                    f"EvaluatorAgent missing expected dimensions {sorted(missing_dimensions)} for case_id={dataset_item.get('case_id')!r}"
                )
        return {
            "scorecard": scorecard,
            "case_id": dataset_item.get("case_id"),
        }

    def _scorecard_dimension(name: str, key: str):
        def scorer(dataset_item: Dict[str, Any], task_outputs: Dict[str, Any]):
            if task_outputs.get("scorecard") is None:
                reason = task_outputs.get("error") or "Task returned no scorecard"
                return ScoreResult(name=name, value=0.0, reason=reason, scoring_failed=True)

            scores = (task_outputs.get("scorecard") or {}).get("scores") or {}
            if key not in scores:
                reason = (
                    f"Missing scorecard dimension '{key}' for case_id={dataset_item.get('case_id')!r} "
                    f"in scores: {scores!r}"
                )
                if strict_eval:
                    raise KeyError(reason)
                return ScoreResult(name=name, value=0.0, reason=reason, scoring_failed=True)

            try:
                value = float(scores[key])
            except (TypeError, ValueError) as exc:
                reason = (
                    f"Non-numeric value for scorecard dimension '{key}' for case_id={dataset_item.get('case_id')!r}: "
                    f"{scores[key]!r}"
                )
                if strict_eval:
                    raise ValueError(reason) from exc
                return ScoreResult(name=name, value=0.0, reason=reason, scoring_failed=True)
            return ScoreResult(name=name, value=value)

        return scorer

    scorers = [
        _scorecard_dimension(f"scorecard.{dimension}", dimension)
        for dimension in SCORECARD_DIMENSIONS
    ]

    sha = _git_sha()
    environment = os.getenv("OPIK_EVAL_ENV", os.getenv("APP_ENV", "local"))
    experiment_config: Dict[str, Any] = {
        "git_sha": sha,
        "eval_suite": "scorecard_regression",
        "environment": environment,
        "dataset_name": dataset_name,
        "dataset_version": dataset_version,
    }

    result = opik.evaluate(
        dataset=dataset,
        task=task,
        scoring_functions=scorers,
        project_name=config["project_name"],
        experiment_name_prefix=os.getenv("OPIK_EVAL_EXPERIMENT_PREFIX", "difficultai-scorecard"),
        experiment_config=experiment_config,
        experiment_tags=["difficultai", "scorecard", "regression"],
        verbose=1,
        task_threads=1,
    )

    print()
    print("Evaluation run complete")
    if result.experiment_url:
        print(f"Experiment URL: {result.experiment_url}")
    else:
        print(f"Experiment ID: {result.experiment_id}")

    project_url = client.get_project_url()
    if project_url:
        print(f"Project URL: {project_url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
