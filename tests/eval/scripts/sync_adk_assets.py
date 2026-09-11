#!/usr/bin/env python3
"""Generate the ADK-native evaluation assets from ``tests/eval/eval_config.yaml``.

``eval_config.yaml`` is the single source of truth for the evaluation. ADK,
however, only reads JSON criterion files and only discovers eval sets that live
inside ``<agents_dir>/<app_name>/``. This script bridges the two so a reviewer
edits exactly one file and nothing can silently drift.

Generated artifacts:

======================================================  ==========================
Artifact                                                Consumed by
======================================================  ==========================
module_3/app/eval_config_reference.json                 reference tier grading
module_3/app/eval_config_livedata.json                  livedata tier grading
module_3/app/test_config.json                           bare ``adk eval`` fallback
module_3/app/cymbal_ops_benchmark.evalset.json          ADK Dev UI discovery
======================================================  ==========================

Usage:
    uv run python tests/eval/scripts/sync_adk_assets.py            # write
    uv run python tests/eval/scripts/sync_adk_assets.py --check    # verify only
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EVAL_CONFIG = REPO_ROOT / "tests" / "eval" / "eval_config.yaml"


def _load_config() -> dict:
    try:
        import yaml
    except ImportError:
        sys.exit(
            "PyYAML is required.\n"
            "  uv pip install --python ./module_3/.venv/bin/python \\\n"
            "    --default-index http://airlock-proxy.uplink.goog:999/python/"
            "artifact-foundry-prod/ah-3p-staging-python/simple/ pyyaml"
        )
    return yaml.safe_load(EVAL_CONFIG.read_text(encoding="utf-8"))


def _judge_options(cfg: dict) -> dict:
    return {"judgeModel": cfg["judge"]["model"]}


def _criterion(metric_name: str, spec: dict, cfg: dict) -> dict:
    """Translate one YAML metric spec into an ADK criterion object.

    A bare float would be accepted by ADK, but then the judge model falls back
    to ADK's hardcoded (obsolete) default. Always emit the full object.
    """
    criterion: dict = {
        "threshold": spec["threshold"],
        "judgeModelOptions": _judge_options(cfg),
    }
    if metric_name == "rubric_based_tool_use_quality_v1":
        criterion["rubrics"] = [
            {
                "rubricId": r["id"],
                "type": r.get("type", "TOOL_USE_QUALITY"),
                "rubricContent": {"textProperty": " ".join(r["property"].split())},
                "description": " ".join(r["description"].split()),
            }
            for r in spec["rubrics"]
        ]
    return criterion


def build_artifacts(cfg: dict) -> dict[pathlib.Path, str]:
    """Returns {absolute path: exact file content} for every generated artifact."""
    artifacts: dict[pathlib.Path, str] = {}

    for tier_name, tier in cfg["tiers"].items():
        payload = {
            "_generated": (
                "DO NOT EDIT. Generated from tests/eval/eval_config.yaml by "
                "tests/eval/scripts/sync_adk_assets.py"
            ),
            "_tier": tier_name,
            "criteria": {
                name: _criterion(name, spec, cfg)
                for name, spec in tier["metrics"].items()
            },
        }
        artifacts[REPO_ROOT / tier["emits"]] = json.dumps(payload, indent=2) + "\n"

    # `adk eval` auto-discovers <eval_set_dir>/test_config.json whenever
    # --config_file_path is omitted. Mirror the reference tier there so an
    # accidental bare invocation cannot fall back to ADK's obsolete default
    # judge model.
    reference_path = REPO_ROOT / cfg["tiers"]["reference"]["emits"]
    fallback = json.loads(artifacts[reference_path])
    fallback["_generated"] = (
        "DO NOT EDIT. Generated from tests/eval/eval_config.yaml. Auto-discovered "
        "fallback for a bare `adk eval`; mirrors the reference tier. Prefer "
        "tests/eval/run_eval_suite.py, which applies the correct per-tier configs."
    )
    artifacts[REPO_ROOT / "module_3" / "app" / "test_config.json"] = (
        json.dumps(fallback, indent=2) + "\n"
    )

    # ADK's LocalEvalSetsManager and the Dev UI only look inside
    # <agents_dir>/<app_name>/, so the canonical golden dataset is mirrored
    # there byte-for-byte.
    golden = REPO_ROOT / cfg["datasets"]["golden"]
    artifacts[REPO_ROOT / cfg["datasets"]["adk_mirror"]] = golden.read_text(
        encoding="utf-8"
    )

    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any artifact is missing or stale. Writes nothing.",
    )
    args = parser.parse_args()

    cfg = _load_config()
    artifacts = build_artifacts(cfg)

    stale: list[str] = []
    for path, content in artifacts.items():
        rel = path.relative_to(REPO_ROOT)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            print(f"  ok      {rel}")
            continue
        if args.check:
            stale.append(str(rel))
            print(f"  STALE   {rel}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  written {rel}")

    if stale:
        print(
            f"\n{len(stale)} artifact(s) out of sync with {EVAL_CONFIG.name}.\n"
            "Run: uv run python tests/eval/scripts/sync_adk_assets.py",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
