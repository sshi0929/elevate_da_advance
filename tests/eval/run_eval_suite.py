#!/usr/bin/env python3
"""Cymbal Operations Agent — in-repo ADK evaluation suite runner.

Why this script exists
----------------------
The stock ``adk eval`` CLI has two properties that make it unsuitable for this
project's official benchmark:

1. It runs inference with ``InferenceConfig.parallelism = 4`` by default. Our
   agent holds a single MCP SSE session to a Cloud Run microservice
   (``mcp-toolbox-bigtable``); four concurrent eval runners collide on that
   session and ADK silently drops the whole toolset
   (``Agent ... will run without the tools from toolset McpToolset``).
   Concurrency also causes ``sqlite3.OperationalError: database is locked`` on
   the ADK session DB.

2. It applies one metric config to every eval case. Two of our seven cases read
   a **1-hour rolling Bigtable window**, so their golden ``final_response`` goes
   stale within the hour. A reference-based judge is *correct* to score those
   0.0 — which makes the benchmark measure clock drift rather than agent
   quality.

This runner drives ``LocalEvalService`` directly so it can:

* pin ``parallelism = 1`` for both inference and judging (no library patching),
* use an in-memory session service so nothing touches ``app/.adk/session.db``,
* grade deterministic cases against the golden answer (reference-based) and
  live-data cases against the tool output only (reference-free).

Configuration
-------------
Every tier name, case list, emitted ADK criterion file, dataset path and the
eval set id are read from ``tests/eval/eval_config.yaml`` — the single source of
truth. Nothing about the benchmark is hardcoded here. Before running, the
generated ADK artifacts are verified against that YAML (the same check
``tests/eval/scripts/sync_adk_assets.py --check`` performs) so the JSON configs
consumed by ADK can never silently drift from the contract this suite claims to
implement.

Usage
-----
    uv run python tests/eval/run_eval_suite.py                 # full 7-case benchmark
    uv run python tests/eval/run_eval_suite.py --tier reference
    uv run python tests/eval/run_eval_suite.py --case UC_1.3_real-time_cashier_metrics
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import datetime
import importlib.util
import json
import os
import pathlib
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Repo layout. This file lives at <repo>/tests/eval/run_eval_suite.py, so the
# repo root is two levels up.
# ---------------------------------------------------------------------------
_HERE = pathlib.Path(__file__).parent.resolve()
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EVAL_CONFIG_PATH = REPO_ROOT / "tests" / "eval" / "eval_config.yaml"
SYNC_SCRIPT_PATH = _HERE / "scripts" / "sync_adk_assets.py"

# ---------------------------------------------------------------------------
# Interpreter bootstrap.
#
# The agent runtime lives in module_3/.venv. Anything else — the system Python,
# or `uv run` invoked from the repo root, which resolves against the root
# pyproject.toml rather than module_3 — lacks google-adk and PyYAML and dies
# with a confusing ImportError.
#
# Rather than forcing every caller (including the grading harness, whose
# invocation we do not control) to know that, re-exec ourselves under the
# correct interpreter when the current one cannot see our dependencies.
# ---------------------------------------------------------------------------
_AGENT_VENV_DIR = REPO_ROOT / "module_3" / ".venv"
_AGENT_VENV_PYTHON = _AGENT_VENV_DIR / "bin" / "python"


def _reexec_under_agent_venv_if_needed() -> None:
    """Re-exec under module_3/.venv unless we are already running there.

    This is deliberately unconditional rather than a "can I import my deps?"
    probe. Probing is unreliable: `uv run` at the repo root syncs the root
    pyproject, which pulls in google-adk and a transitive yaml, so the probe
    passes while the environment is still missing pieces the agent needs.
    Preferring one known-good interpreter is predictable.

    Set CYMBAL_EVAL_NO_REEXEC=1 to run under the current interpreter instead.
    """
    if os.environ.get("_CYMBAL_EVAL_REEXEC") == "1":
        return  # Already re-exec'd once; avoid an exec loop.
    if os.environ.get("CYMBAL_EVAL_NO_REEXEC") == "1":
        return  # Caller has explicitly opted out.
    if not _AGENT_VENV_PYTHON.exists():
        return  # Nothing better available; let the normal error surface.
    # Compare sys.prefix, NOT the resolved executable path. A virtualenv's
    # bin/python is a symlink to the base interpreter, so
    # Path(sys.executable).resolve() == _AGENT_VENV_PYTHON.resolve() is true
    # even when running under a completely different environment — which
    # silently disabled this bootstrap.
    if pathlib.Path(sys.prefix).resolve() == _AGENT_VENV_DIR.resolve():
        return  # Already the right interpreter.


    print(
        f"[bootstrap] re-executing under {_AGENT_VENV_PYTHON.relative_to(REPO_ROOT)}",
        file=sys.stderr,
    )
    os.execve(
        str(_AGENT_VENV_PYTHON),
        [str(_AGENT_VENV_PYTHON), str(pathlib.Path(__file__).resolve()), *sys.argv[1:]],
        {**os.environ, "_CYMBAL_EVAL_REEXEC": "1"},
    )



_reexec_under_agent_venv_if_needed()



def _load_eval_config() -> dict:
    """Loads tests/eval/eval_config.yaml, the single source of truth."""
    try:
        import yaml
    except ImportError:
        sys.exit(
            "PyYAML is required.\n"
            "  uv pip install --python ./module_3/.venv/bin/python \\\n"
            "    --default-index http://airlock-proxy.uplink.goog:999/python/"
            "artifact-foundry-prod/ah-3p-staging-python/simple/ pyyaml"
        )
    if not EVAL_CONFIG_PATH.exists():
        sys.exit(f"Missing evaluation config: {EVAL_CONFIG_PATH}")
    return yaml.safe_load(EVAL_CONFIG_PATH.read_text(encoding="utf-8"))


CONFIG = _load_eval_config()

# `target.agent_dir` is repo-relative (e.g. "module_3/app"). ADK's
# LocalEvalSetsManager works in terms of <agents_dir>/<app_name>, so split it.
AGENT_MODULE_DIR = str(REPO_ROOT / CONFIG["target"]["agent_dir"])
AGENTS_DIR = str(pathlib.Path(AGENT_MODULE_DIR).parent)
APP_NAME = pathlib.Path(AGENT_MODULE_DIR).name
EVAL_SET_ID = CONFIG["metadata"]["eval_set_id"]

# The agent package lives at <repo>/module_3/app and imports itself as `app.*`,
# so `module_3` must be importable before we touch anything ADK. The old runner
# lived inside module_3 and inserted its own directory; now that this file sits
# under tests/eval, the same directory is derived from the config instead.
if AGENTS_DIR not in sys.path:
    sys.path.insert(0, AGENTS_DIR)

from google.adk.cli.cli_eval import get_app_or_root_agent  # noqa: E402
from google.adk.evaluation.base_eval_service import EvaluateConfig  # noqa: E402
from google.adk.evaluation.base_eval_service import EvaluateRequest  # noqa: E402
from google.adk.evaluation.base_eval_service import InferenceConfig  # noqa: E402
from google.adk.evaluation.base_eval_service import InferenceRequest  # noqa: E402
from google.adk.evaluation.base_eval_service import InferenceStatus  # noqa: E402
from google.adk.evaluation.eval_config import get_eval_metrics_from_config  # noqa: E402
from google.adk.evaluation.eval_config import get_evaluation_criteria_or_default  # noqa: E402
from google.adk.evaluation.evaluator import EvalStatus  # noqa: E402
from google.adk.evaluation.local_eval_service import LocalEvalService  # noqa: E402
from google.adk.evaluation.local_eval_set_results_manager import (  # noqa: E402
    LocalEvalSetResultsManager,
)
from google.adk.evaluation.local_eval_sets_manager import (  # noqa: E402
    LocalEvalSetsManager,
)
from google.adk.sessions.in_memory_session_service import (  # noqa: E402
    InMemorySessionService,
)

# Tier definitions come straight from the YAML. `reference` holds the
# deterministic cases (the golden final_response stays valid because the
# underlying BigQuery / RAG corpora are static, so they are graded
# reference-based); `livedata` holds the cases that read a 1-hour rolling
# Bigtable window, whose golden numbers expire and which are therefore graded
# reference-free (faithfulness to tool output + rubric-based tool-use quality).
TIERS: dict[str, tuple[str, list[str]]] = {
    name: (str(REPO_ROOT / tier["emits"]), list(tier["cases"]))
    for name, tier in CONFIG["tiers"].items()
}


def verify_generated_assets() -> None:
    """Aborts unless every generated ADK artifact matches eval_config.yaml.

    ``tests/eval/eval_config.yaml`` is authoritative, but ADK only reads the
    generated JSON. If someone hand-edits the JSON (or edits the YAML and
    forgets to regenerate), the benchmark would silently grade against a
    different contract than the one documented. Fail loudly instead.
    """
    spec = importlib.util.spec_from_file_location(
        "_sync_adk_assets", SYNC_SCRIPT_PATH
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        sys.exit(f"Cannot load sync checker: {SYNC_SCRIPT_PATH}")
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)

    stale: list[str] = []
    for path, content in sync.build_artifacts(CONFIG).items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            stale.append(str(path.relative_to(REPO_ROOT)))

    if stale:
        listing = "\n".join(f"    - {p}" for p in stale)
        sys.exit(
            "ABORT: generated ADK evaluation assets are stale or missing.\n"
            f"{listing}\n"
            "These are generated from tests/eval/eval_config.yaml. Running the\n"
            "benchmark now would grade against a different contract than the\n"
            "one documented. Regenerate first:\n"
            "    uv run python tests/eval/scripts/sync_adk_assets.py\n"
            "(or re-run with --skip-sync-check if you know what you are doing)."
        )


@dataclasses.dataclass
class CaseOutcome:
    tier: str
    eval_id: str
    status: str
    metrics: dict[str, Optional[float]]
    thresholds: dict[str, float]
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.status == "PASSED"


def _status_name(status: EvalStatus) -> str:
    return {
        EvalStatus.PASSED: "PASSED",
        EvalStatus.FAILED: "FAILED",
        EvalStatus.NOT_EVALUATED: "NOT_EVALUATED",
    }.get(status, str(status))


async def _run_tier(tier: str, case_filter: Optional[set[str]]) -> list[CaseOutcome]:
    config_path, all_cases = TIERS[tier]
    cases = [c for c in all_cases if not case_filter or c in case_filter]
    if not cases:
        return []

    eval_config = get_evaluation_criteria_or_default(config_path)
    eval_metrics = get_eval_metrics_from_config(eval_config)
    thresholds = {m.metric_name: m.threshold for m in eval_metrics}

    # `EvalConfig.criteria` is typed as `BaseCriterion`, so `judgeModelOptions`
    # lands in `model_extra` (the model sets `extra="allow"`). ADK only coerces
    # it into the concrete criterion type later, inside the evaluator
    # (`llm_as_judge.py:102`). Read both spellings so the banner is accurate.
    def _judge_model(criterion) -> str:
        opts = getattr(criterion, "judge_model_options", None)
        if opts is None:
            extra = getattr(criterion, "model_extra", None) or {}
            opts = extra.get("judge_model_options") or extra.get("judgeModelOptions")
        if isinstance(opts, dict):
            return opts.get("judge_model") or opts.get("judgeModel") or "adk-default"
        return getattr(opts, "judge_model", None) or "adk-default"

    judges = sorted({_judge_model(m.criterion) for m in eval_metrics})

    print(f"\n{'=' * 78}")
    print(f"TIER: {tier}   ({len(cases)} case(s))")
    print(f"  config  : {os.path.relpath(config_path, REPO_ROOT)}")
    print(f"  metrics : {', '.join(f'{k}>={v}' for k, v in thresholds.items())}")
    print(f"  judge   : {', '.join(judges)}")
    print(f"{'=' * 78}", flush=True)

    _, root_agent = await get_app_or_root_agent(AGENT_MODULE_DIR)

    eval_service = LocalEvalService(
        root_agent=root_agent,
        eval_sets_manager=LocalEvalSetsManager(agents_dir=AGENTS_DIR),
        eval_set_results_manager=LocalEvalSetResultsManager(agents_dir=AGENTS_DIR),
        # Explicit in-memory session service: keeps concurrent/repeat eval runs
        # off app/.adk/session.db, which otherwise throws
        # "sqlite3.OperationalError: database is locked".
        session_service=InMemorySessionService(),
    )

    inference_request = InferenceRequest(
        app_name=APP_NAME,
        eval_set_id=EVAL_SET_ID,
        eval_case_ids=cases,
        # parallelism=1 is mandatory here: the agent shares one MCP SSE session
        # to Cloud Run and concurrent runners cause the toolset to be dropped.
        inference_config=InferenceConfig(parallelism=1),
    )

    inference_results = []
    async for result in eval_service.perform_inference(inference_request):
        marker = "ok" if result.status == InferenceStatus.SUCCESS else "FAILED"
        print(f"  [inference {marker}] {result.eval_case_id}", flush=True)
        if result.error_message:
            print(f"      error: {result.error_message}", flush=True)
        inference_results.append(result)

    evaluate_request = EvaluateRequest(
        inference_results=inference_results,
        evaluate_config=EvaluateConfig(eval_metrics=eval_metrics, parallelism=1),
    )

    outcomes: list[CaseOutcome] = []
    async for case_result in eval_service.evaluate(evaluate_request):
        scores = {
            r.metric_name: r.score for r in case_result.overall_eval_metric_results
        }
        outcome = CaseOutcome(
            tier=tier,
            eval_id=case_result.eval_id,
            status=_status_name(case_result.final_eval_status),
            metrics=scores,
            thresholds=thresholds,
        )
        outcomes.append(outcome)
        rendered = "  ".join(
            f"{name}={'n/a' if score is None else f'{score:.4f}'}"
            for name, score in scores.items()
        )
        print(f"  [{outcome.status:>13}] {outcome.eval_id}  {rendered}", flush=True)

    return outcomes


def _render_report(outcomes: list[CaseOutcome], elapsed: float) -> str:
    passed = sum(1 for o in outcomes if o.passed)
    total = len(outcomes)
    pct = (passed / total * 100) if total else 0.0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

    metric_names: list[str] = []
    for o in outcomes:
        for name in o.metrics:
            if name not in metric_names:
                metric_names.append(name)

    lines = [
        "# Cymbal Operations Agent — ADK Evaluation Scorecard",
        "",
        f"- **Generated**: {now}",
        f"- **Eval set**: `{EVAL_SET_ID}`",
        f"- **Runner**: `tests/eval/run_eval_suite.py` (parallelism=1, in-memory sessions)",
        f"- **Config**: `tests/eval/eval_config.yaml` (single source of truth)",
        f"- **Result**: **{passed}/{total} passed ({pct:.1f}%)** in {elapsed:.1f}s",
        "",
        "## Scorecard",
        "",
        "| Case | Tier | " + " | ".join(metric_names) + " | Result |",
        "| :--- | :--- | " + " | ".join(["---:"] * len(metric_names)) + " | :--- |",
    ]
    for o in sorted(outcomes, key=lambda x: (x.tier, x.eval_id)):
        cells = []
        for name in metric_names:
            score = o.metrics.get(name)
            cells.append("—" if score is None else f"{score:.4f}")
        badge = "✅ PASS" if o.passed else f"❌ {o.status}"
        lines.append(f"| `{o.eval_id}` | {o.tier} | " + " | ".join(cells) + f" | {badge} |")

    # The grading policy table is rendered from eval_config.yaml so the
    # scorecard can never claim a policy the runner did not actually apply.
    lines += [
        "",
        "## Grading policy",
        "",
        "| Tier | Cases | Metrics | Rationale |",
        "| :--- | ---: | :--- | :--- |",
    ]
    for tier_name, tier in CONFIG["tiers"].items():
        metric_spec = ", ".join(
            f"`{name}` >= {spec['threshold']}" for name, spec in tier["metrics"].items()
        )
        rationale = " ".join(tier.get("description", "").split())
        lines.append(
            f"| `{tier_name}` | {len(tier['cases'])} | {metric_spec} | {rationale} |"
        )

    judge_model = CONFIG["judge"]["model"]
    lines += [
        "",
        "> [!NOTE]",
        "> All metrics are ADK-native (`PrebuiltMetrics`). The judge model is pinned to"
        f" `{judge_model}` in both generated config files, overriding ADK's obsolete"
        " `gemini-2.5-flash` default (`eval_metrics.py:85`).",
        "",
    ]
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier",
        choices=sorted(TIERS),
        action="append",
        help="Run only the given tier(s). Repeatable. Default: all tiers.",
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Run only the given eval case id(s). Repeatable.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "tests" / "eval" / "EVAL_SCORECARD.md"),
        help="Path to write the markdown scorecard.",
    )
    parser.add_argument(
        "--skip-sync-check",
        action="store_true",
        help=(
            "Skip the eval_config.yaml -> generated ADK asset freshness check."
            " Escape hatch only; CI must never set this."
        ),
    )
    args = parser.parse_args()

    if not args.skip_sync_check:
        verify_generated_assets()

    tiers = args.tier or sorted(TIERS)
    case_filter = set(args.case) if args.case else None

    started = asyncio.get_event_loop().time()
    outcomes: list[CaseOutcome] = []
    for tier in tiers:
        outcomes.extend(await _run_tier(tier, case_filter))
    elapsed = asyncio.get_event_loop().time() - started

    if not outcomes:
        print("No eval cases matched the given filters.", file=sys.stderr)
        return 2

    report = _render_report(outcomes, elapsed)
    pathlib.Path(args.report).write_text(report, encoding="utf-8")

    passed = sum(1 for o in outcomes if o.passed)
    print(f"\n{'=' * 78}")
    print(f"FINAL: {passed}/{len(outcomes)} passed  ({elapsed:.1f}s)")
    print(f"Scorecard written to {args.report}")
    print(f"{'=' * 78}")

    json_path = pathlib.Path(args.report).with_suffix(".json")
    json_path.write_text(
        json.dumps([dataclasses.asdict(o) for o in outcomes], indent=2),
        encoding="utf-8",
    )

    return 0 if passed == len(outcomes) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
