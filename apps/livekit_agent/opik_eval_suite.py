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
    return Path(__file__).resolve().parents[2]


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


def _get_opik_config() -> Dict[str, Any]:
    return {
        "api_key": os.getenv("OPIK_API_KEY"),
        "url_override": os.getenv("OPIK_URL_OVERRIDE"),
        "project_name": os.getenv("OPIK_PROJECT", "difficultai"),
        "workspace": os.getenv("OPIK_WORKSPACE", "default"),
        "disabled": os.getenv("OPIK_DISABLED", "").lower() in ("1", "true", "yes"),
    }


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

    config = _get_opik_config()
    if config["disabled"]:
        print("Opik is disabled via OPIK_DISABLED; nothing to do.")
        return 0

    if not config["api_key"] and not config["url_override"]:
        print("Missing Opik credentials: set OPIK_API_KEY or OPIK_URL_OVERRIDE.")
        return 2

    import opik
    from opik.evaluation.metrics.score_result import ScoreResult

    from agents.evaluator import EvaluatorAgent

    _print_header("DifficultAI Opik Evaluation Suite")
    print(f"Project: {config['project_name']}")
    print(f"Workspace: {config['workspace']}")
    if config["url_override"]:
        print(f"URL Override: {config['url_override']}")

    configure_kwargs: Dict[str, Any] = {}
    if config["api_key"]:
        configure_kwargs["api_key"] = config["api_key"]
    if config["workspace"]:
        configure_kwargs["workspace"] = config["workspace"]
    if config["url_override"]:
        configure_kwargs["url"] = config["url_override"]
    if configure_kwargs:
        opik.configure(**configure_kwargs)

    client = opik.Opik(project_name=config["project_name"], workspace=config["workspace"])
    dataset_name = os.getenv("OPIK_EVAL_DATASET", "difficultai-scorecard-regression")
    dataset = client.get_or_create_dataset(
        name=dataset_name,
        description="Deterministic scorecard regression dataset for DifficultAI",
    )

    seed_items = _seed_dataset_items()
    for item in seed_items:
        _validate_seed_item(item)

    evaluator = EvaluatorAgent()

    # Ensure evaluator stays deterministic for the same input.
    sample = seed_items[0]
    first = evaluator.evaluate_conversation(
        metrics=sample["metrics"],
        scenario=sample["scenario"],
    )
    second = evaluator.evaluate_conversation(
        metrics=sample["metrics"],
        scenario=sample["scenario"],
    )
    if (first.get("scores") or {}) != (second.get("scores") or {}):
        raise RuntimeError(
            "EvaluatorAgent is non-deterministic for the same (metrics, scenario) input; "
            "not suitable for regression eval suite"
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
        return {
            "scorecard": scorecard,
            "case_id": dataset_item.get("case_id"),
        }

    def _scorecard_dimension(name: str, key: str):
        def scorer(dataset_item: Dict[str, Any], task_outputs: Dict[str, Any]):
            scores = (task_outputs.get("scorecard") or {}).get("scores") or {}
            if key not in scores:
                raise KeyError(
                    f"Missing scorecard dimension '{key}' for case_id={dataset_item.get('case_id')!r} "
                    f"in scores: {scores!r}"
                )

            try:
                value = float(scores[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Non-numeric value for scorecard dimension '{key}': {scores[key]!r}"
                ) from exc
            return ScoreResult(name=name, value=value)

        return scorer

    scorers = [
        _scorecard_dimension("scorecard.clarity", "clarity"),
        _scorecard_dimension("scorecard.confidence", "confidence"),
        _scorecard_dimension("scorecard.commitment", "commitment"),
        _scorecard_dimension("scorecard.adaptability", "adaptability"),
        _scorecard_dimension("scorecard.composure", "composure"),
        _scorecard_dimension("scorecard.effectiveness", "effectiveness"),
    ]

    sha = _git_sha()
    environment = os.getenv("OPIK_EVAL_ENV", os.getenv("APP_ENV", "local"))
    dataset_version = os.getenv("OPIK_EVAL_DATASET_VERSION", "v1")
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
