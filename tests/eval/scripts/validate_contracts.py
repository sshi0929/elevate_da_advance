#!/usr/bin/env python3
"""Validate that the Cymbal data contracts still describe reality.

The YAML contracts under ``tests/eval/contracts/`` are only worth anything if
they are checked against the deployed platform. This script is the runnable
test that does that, in three layers:

1. **Schema conformance** — every contracted column must exist on the live
   BigQuery / BigLake table with the same ``type`` and ``mode`` (recursing into
   ``RECORD`` sub-fields), and any live column the contract does not describe is
   reported as undocumented drift. For the Cloud Bigtable contract the declared
   column families must exist on the live table.

2. **Fixture linkage** — every contract rule marked ``enforced_by:
   eval-fixture`` must have a matching assertion id in
   ``tests/eval/datasets/golden-data-contract-fixtures.json``, and every fixture
   assertion id must map back to a real contract rule. Orphans are reported in
   both directions, so neither file can rot independently of the other.

3. **Data assertions** — each fixture SQL probe is executed and compared
   against its operator/threshold. Bigtable assertions are executed with the
   Cloud Bigtable SDK over a bounded row scan.

Usage:
    uv run python tests/eval/scripts/validate_contracts.py
    uv run python tests/eval/scripts/validate_contracts.py --skip-data
    uv run python tests/eval/scripts/validate_contracts.py --contract pos_anomaly_alerts

Exit code is non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import struct
import sys
from typing import Any, Optional

PROJECT_ID = "pj-elevate-da"

# ADC on a corp workstation is frequently minted against an unrelated quota
# project, which makes the Bigtable Admin API reject the call with
# "Cloud Bigtable Admin API has not been used in project <other> before".
# Pin the quota project unless the caller has already chosen one. See
# tests/eval/scripts/extract_schemas.py, which hit the same wall.
os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", PROJECT_ID)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CONTRACTS_DIR = REPO_ROOT / "tests" / "eval" / "contracts"
FIXTURES_PATH = (
    REPO_ROOT / "tests" / "eval" / "datasets" / "golden-data-contract-fixtures.json"
)

# BigQuery reports legacy SQL type names on TableSchema (STRING, INTEGER,
# FLOAT, BOOLEAN, RECORD). Contracts are written in the same dialect, but accept
# the GoogleSQL spellings as equivalent so a contract author cannot trip on it.
_TYPE_ALIASES = {
    "INT64": "INTEGER",
    "FLOAT64": "FLOAT",
    "BOOL": "BOOLEAN",
    "STRUCT": "RECORD",
    "BIGNUMERIC": "BIGNUMERIC",
}

_OPERATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _load_yaml(path: pathlib.Path) -> dict:
    try:
        import yaml
    except ImportError:
        sys.exit(
            "PyYAML is required.\n"
            "  uv pip install --python ./module_3/.venv/bin/python \\\n"
            "    --default-index http://airlock-proxy.uplink.goog:999/python/"
            "artifact-foundry-prod/ah-3p-staging-python/simple/ pyyaml"
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _contract_name(path: pathlib.Path) -> str:
    """`.../bigquery/pos_anomaly_alerts.contract.yaml` -> `pos_anomaly_alerts`."""
    return path.name.replace(".contract.yaml", "")


def load_contracts(selected: Optional[set[str]]) -> list[tuple[pathlib.Path, dict]]:
    paths = sorted(CONTRACTS_DIR.rglob("*.contract.yaml"))
    if not paths:
        sys.exit(f"No contracts found under {CONTRACTS_DIR}")
    out = []
    for p in paths:
        if selected and _contract_name(p) not in selected:
            continue
        out.append((p, _load_yaml(p)))
    if selected and not out:
        sys.exit(f"No contract matched --contract {sorted(selected)}")
    return out


def load_fixtures() -> dict[str, dict]:
    """Returns {repo-relative contract path: fixture}."""
    if not FIXTURES_PATH.exists():
        sys.exit(f"Missing fixture set: {FIXTURES_PATH}")
    payload = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return {f["contract"]: f for f in payload.get("fixtures", [])}


# ---------------------------------------------------------------------------
# Result accumulation
# ---------------------------------------------------------------------------
class Section:
    """One (contract, check-layer) result bucket."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.checks = 0
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.skipped = False

    def check(self, ok: bool, message: str) -> None:
        self.checks += 1
        if not ok:
            self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def badge(self) -> str:
        if self.skipped:
            return "SKIP"
        if not self.checks:
            return "n/a"
        return "PASS" if self.passed else f"FAIL({len(self.failures)})"


# ---------------------------------------------------------------------------
# 1. Schema conformance
# ---------------------------------------------------------------------------
def _norm_type(t: Optional[str]) -> str:
    t = (t or "").upper()
    return _TYPE_ALIASES.get(t, t)


def _norm_mode(m: Optional[str]) -> str:
    return (m or "NULLABLE").upper()


def _compare_fields(
    contracted: list[dict],
    live: list[Any],
    section: Section,
    prefix: str = "",
) -> None:
    live_by_name = {f.name: f for f in live}
    for col in contracted or []:
        name = col["name"]
        path = f"{prefix}{name}"
        field = live_by_name.get(name)
        if field is None:
            section.check(False, f"column `{path}` is contracted but missing live")
            continue
        section.check(
            _norm_type(col.get("type")) == _norm_type(field.field_type),
            f"column `{path}` type mismatch: contract={col.get('type')} "
            f"live={field.field_type}",
        )
        section.check(
            _norm_mode(col.get("mode")) == _norm_mode(field.mode),
            f"column `{path}` mode mismatch: contract={col.get('mode')} "
            f"live={field.mode}",
        )
        if col.get("fields") or field.fields:
            _compare_fields(
                col.get("fields") or [], list(field.fields or []), section, f"{path}."
            )

    contracted_names = {c["name"] for c in (contracted or [])}
    for name in live_by_name:
        if name not in contracted_names:
            section.check(
                False,
                f"column `{prefix}{name}` exists live but is missing from the contract",
            )


def check_bigquery_schema(contract: dict, section: Section) -> None:
    from google.cloud import bigquery

    fqn = contract["provider"]["fully_qualified_name"]
    client = bigquery.Client(project=PROJECT_ID)
    try:
        table = client.get_table(fqn)
    except Exception as e:  # noqa: BLE001 - surfaced as a contract failure
        section.check(False, f"cannot read live table `{fqn}`: {type(e).__name__}: {e}")
        return
    _compare_fields(contract.get("schema", []), list(table.schema), section)


def check_bigtable_schema(contract: dict, section: Section) -> None:
    from google.cloud import bigtable

    provider = contract["provider"]
    instance_id = provider["instance"]
    table_id = provider["table"]
    declared = [
        cf["name"] for cf in provider.get("physical", {}).get("column_families", [])
    ]
    # The contract also documents qualifiers under a top-level `column_families`
    # block; use it as the authoritative family list when present.
    declared += [cf["name"] for cf in contract.get("column_families", [])]
    declared = sorted(set(declared))

    try:
        client = bigtable.Client(project=PROJECT_ID, admin=True)
        table = client.instance(instance_id).table(table_id)
        live = set(table.list_column_families())
    except Exception as e:  # noqa: BLE001
        section.check(
            False,
            f"cannot read live Bigtable `{instance_id}:{table_id}`: "
            f"{type(e).__name__}: {e}",
        )
        return

    for name in declared:
        section.check(
            name in live,
            f"column family `{name}` is contracted but missing live "
            f"(live families: {sorted(live)})",
        )
    for name in sorted(live - set(declared)):
        section.check(
            False,
            f"column family `{name}` exists live but is missing from the contract",
        )


# ---------------------------------------------------------------------------
# 2. Fixture linkage
# ---------------------------------------------------------------------------
def check_linkage(contract: dict, fixture: Optional[dict], section: Section) -> None:
    rules = {r["id"]: r for r in contract.get("quality", {}).get("rules", [])}
    required = {rid for rid, r in rules.items() if r.get("enforced_by") == "eval-fixture"}

    if fixture is None:
        if required:
            section.check(
                False,
                f"contract declares {len(required)} `eval-fixture` rule(s) but no "
                f"fixture entry exists in {FIXTURES_PATH.name}",
            )
        else:
            section.warn("no fixture entry (contract declares no eval-fixture rules)")
        return

    asserted = [a["id"] for a in fixture.get("assertions", [])]
    dupes = {i for i in asserted if asserted.count(i) > 1}
    for dupe in sorted(dupes):
        section.check(False, f"duplicate fixture assertion id `{dupe}`")

    asserted_set = set(asserted)
    for rid in sorted(required - asserted_set):
        section.check(
            False, f"rule `{rid}` is enforced_by eval-fixture but has no fixture assertion"
        )
    for rid in sorted(required & asserted_set):
        section.check(True, "")
    for aid in sorted(asserted_set - set(rules)):
        section.check(
            False,
            f"fixture assertion `{aid}` does not map back to any rule in the contract",
        )
    # Dimension agreement is cheap to verify and catches copy/paste drift.
    for a in fixture.get("assertions", []):
        rule = rules.get(a["id"])
        if rule and a.get("dimension") and rule.get("dimension"):
            section.check(
                a["dimension"] == rule["dimension"],
                f"fixture assertion `{a['id']}` dimension={a['dimension']} but "
                f"contract rule dimension={rule['dimension']}",
            )


# ---------------------------------------------------------------------------
# 3a. BigQuery data assertions
# ---------------------------------------------------------------------------
def run_bigquery_assertions(fixture: dict, section: Section, verbose: bool) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    for a in fixture.get("assertions", []):
        aid = a["id"]
        op = a.get("operator", ">=")
        threshold = a.get("threshold")
        if op not in _OPERATORS:
            section.check(False, f"{aid}: unsupported operator `{op}`")
            continue
        try:
            rows = list(client.query(a["sql"]).result())
        except Exception as e:  # noqa: BLE001
            section.check(False, f"{aid}: query failed: {type(e).__name__}: {e}")
            continue
        if len(rows) != 1:
            section.check(False, f"{aid}: expected exactly 1 row, got {len(rows)}")
            continue
        if "value" not in rows[0].keys():
            section.check(False, f"{aid}: query has no column aliased `value`")
            continue
        value = rows[0]["value"]
        if value is None:
            section.check(False, f"{aid}: `value` is NULL")
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            section.check(False, f"{aid}: `value` is not numeric ({value!r})")
            continue
        ok = _OPERATORS[op](value, float(threshold))
        section.check(ok, f"{aid}: value={value:.6g} violates {op} {threshold}")
        if verbose:
            print(f"      {'ok  ' if ok else 'FAIL'} {aid}: {value:.6g} {op} {threshold}")


# ---------------------------------------------------------------------------
# 3b. Bigtable data assertions
# ---------------------------------------------------------------------------
def _decode(value: bytes, encoding: str):
    if encoding == "be_int64":
        return struct.unpack(">q", value)[0]
    if encoding == "be_float64":
        return struct.unpack(">d", value)[0]
    if encoding == "utf8":
        return value.decode("utf-8")
    raise ValueError(f"unsupported encoding `{encoding}`")


def _cell(row, family: str, qualifier: str) -> Optional[bytes]:
    cells = row.cells.get(family, {}).get(qualifier.encode("utf-8"))
    return cells[0].value if cells else None


def _scan(table, prefix: Optional[str], limit: int) -> list:
    from google.cloud.bigtable.row_set import RowSet

    if prefix:
        row_set = RowSet()
        row_set.add_row_range_with_prefix(prefix)
        return list(table.read_rows(row_set=row_set, limit=limit))
    return list(table.read_rows(limit=limit))


def _run_bigtable_check(spec: dict, table, default_limit: int) -> tuple[bool, str]:
    """Executes one declarative Bigtable check. Returns (ok, detail)."""
    check = spec.get("check")
    prefix = spec.get("row_key_prefix")
    limit = int(spec.get("limit", default_limit))
    rows = _scan(table, prefix, limit)
    scope = f"prefix `{prefix}`" if prefix else "table head"

    if not rows and check != "row_key_prefix_exists":
        return False, f"no rows returned for {scope} (limit {limit})"

    if check == "row_key_prefix_exists":
        want = int(spec.get("expect_min_rows", 1))
        return (
            len(rows) >= want,
            f"{len(rows)} row(s) under {scope}, expected >= {want}",
        )

    if check == "row_key_regex":
        pattern = re.compile(spec["pattern"])
        bad = [r.row_key.decode() for r in rows if not pattern.match(r.row_key.decode())]
        return (
            not bad,
            f"{len(rows) - len(bad)}/{len(rows)} row keys match {spec['pattern']}"
            + (f"; first offenders: {bad[:3]}" if bad else ""),
        )

    if check == "qualifiers_present":
        columns = spec.get("columns")
        if columns is None:
            columns = [f"{spec['column_family']}:{q}" for q in spec["qualifiers"]]
        missing: list[str] = []
        for row in rows:
            for col in columns:
                fam, qual = col.split(":", 1)
                if _cell(row, fam, qual) is None:
                    missing.append(f"{row.row_key.decode()}::{col}")
        return (
            not missing,
            f"{len(rows)} row(s) x {len(columns)} column(s) checked"
            + (f"; {len(missing)} missing, e.g. {missing[:3]}" if missing else ""),
        )

    if check in ("decoded_value_range", "decoded_value_in_set"):
        fam = spec["column_family"]
        encoding = spec["encoding"]
        checked = 0
        bad: list[str] = []
        for row in rows:
            for qual in spec["qualifiers"]:
                raw = _cell(row, fam, qual)
                if raw is None:
                    continue  # presence is core_qualifiers_present's job
                try:
                    value = _decode(raw, encoding)
                except Exception as e:  # noqa: BLE001
                    bad.append(f"{row.row_key.decode()}::{fam}:{qual} decode {e}")
                    continue
                checked += 1
                if check == "decoded_value_range":
                    lo, hi = spec.get("min"), spec.get("max")
                    if (lo is not None and value < lo) or (
                        hi is not None and value > hi
                    ):
                        bad.append(f"{row.row_key.decode()}::{fam}:{qual}={value}")
                else:
                    if value not in spec["allowed"]:
                        bad.append(f"{row.row_key.decode()}::{fam}:{qual}={value!r}")
        return (
            not bad,
            f"{checked} value(s) decoded over {len(rows)} row(s) in {scope}"
            + (f"; {len(bad)} violation(s), e.g. {bad[:3]}" if bad else ""),
        )

    if check == "row_key_prefix_newest_first":
        want = int(spec.get("expect_min_rows", 1))
        if len(rows) < want:
            return False, f"{len(rows)} row(s) under {scope}, expected >= {want}"
        suffixes = [r.row_key.decode().rsplit("#", 1)[-1] for r in rows]
        widths = {len(s) for s in suffixes}
        if len(widths) > 1:
            return (
                False,
                f"reversed-timestamp suffixes have mixed widths {sorted(widths)}, so "
                "lexicographic scan order does not equal recency order",
            )
        numeric = [int(s) for s in suffixes]
        # Bigtable scans ascending by row key; a reversed timestamp means the
        # smallest suffix is the most recent event, so ascending suffixes ==
        # newest row first.
        ordered = all(a <= b for a, b in zip(numeric, numeric[1:]))
        return (
            ordered,
            f"{len(rows)} row(s) under {scope}; newest-first="
            f"{ordered}; first key {rows[0].row_key.decode()}",
        )

    if check == "cross_qualifier_compare":
        fam = spec["column_family"]
        encoding = spec["encoding"]
        op = _OPERATORS[spec.get("operator", "<=")]
        checked = 0
        bad: list[str] = []
        for row in rows:
            lhs_raw = _cell(row, fam, spec["left"])
            rhs_raw = _cell(row, fam, spec["right"])
            if lhs_raw is None or rhs_raw is None:
                continue
            lhs, rhs = _decode(lhs_raw, encoding), _decode(rhs_raw, encoding)
            checked += 1
            if not op(lhs, rhs):
                bad.append(f"{row.row_key.decode()}: {lhs} vs {rhs}")
        return (
            not bad,
            f"{checked} row(s) compared"
            + (f"; {len(bad)} violation(s), e.g. {bad[:3]}" if bad else ""),
        )

    return False, f"unsupported bigtable check `{check}`"


def run_bigtable_assertions(fixture: dict, section: Section, verbose: bool) -> None:
    from google.cloud import bigtable

    scan_cfg = fixture.get("scan", {})
    default_limit = int(scan_cfg.get("limit", 1000))
    try:
        client = bigtable.Client(project=PROJECT_ID, admin=False)
        table = client.instance(fixture["instance"]).table(fixture["table"])
    except Exception as e:  # noqa: BLE001
        section.check(False, f"cannot open Bigtable client: {type(e).__name__}: {e}")
        return

    for pre in fixture.get("preconditions", []):
        try:
            ok, detail = _run_bigtable_check(pre, table, default_limit)
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {e}"
        label = f"precondition {pre['check']}"
        section.check(ok, f"{label}: {detail}")
        if verbose:
            print(f"      {'ok  ' if ok else 'FAIL'} {label}: {detail}")

    for a in fixture.get("assertions", []):
        try:
            ok, detail = _run_bigtable_check(a, table, default_limit)
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"{type(e).__name__}: {e}"
        section.check(ok, f"{a['id']}: {detail}")
        if verbose:
            print(f"      {'ok  ' if ok else 'FAIL'} {a['id']}: {detail}")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        action="append",
        help="Validate only the named contract(s), e.g. pos_anomaly_alerts. Repeatable.",
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Run schema + linkage checks only. Issues no billed BigQuery queries.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-assertion trace; print only the summary table.",
    )
    args = parser.parse_args()
    verbose = not args.quiet

    selected = set(args.contract) if args.contract else None
    contracts = load_contracts(selected)
    fixtures = load_fixtures()

    print(f"Contracts dir : {CONTRACTS_DIR.relative_to(REPO_ROOT)}")
    print(f"Fixture set   : {FIXTURES_PATH.relative_to(REPO_ROOT)}")
    print(f"Quota project : {os.environ['GOOGLE_CLOUD_QUOTA_PROJECT']}")
    print(f"Data assertions: {'SKIPPED (--skip-data)' if args.skip_data else 'ENABLED'}")

    results: list[tuple[str, Section, Section, Section]] = []

    for path, contract in contracts:
        name = _contract_name(path)
        rel = str(path.relative_to(REPO_ROOT))
        platform = contract["provider"]["platform"]
        print(f"\n--- {name}  [{platform}]  {contract['provider']['fully_qualified_name']}")

        schema = Section("schema")
        linkage = Section("linkage")
        data = Section("data")

        if platform == "bigtable":
            check_bigtable_schema(contract, schema)
        else:
            check_bigquery_schema(contract, schema)
        print(f"    schema  : {schema.badge} ({schema.checks} checks)")
        for f in schema.failures:
            print(f"      FAIL {f}")

        fixture = fixtures.get(rel)
        check_linkage(contract, fixture, linkage)
        print(f"    linkage : {linkage.badge} ({linkage.checks} checks)")
        for f in linkage.failures:
            print(f"      FAIL {f}")
        for w in linkage.warnings:
            print(f"      note {w}")

        if args.skip_data:
            data.skipped = True
        elif fixture is None:
            data.skipped = True
        elif fixture.get("platform") == "bigtable":
            run_bigtable_assertions(fixture, data, verbose)
        else:
            run_bigquery_assertions(fixture, data, verbose)
        print(f"    data    : {data.badge} ({data.checks} checks)")
        for f in data.failures:
            print(f"      FAIL {f}")

        results.append((name, schema, linkage, data))

    # Summary table -----------------------------------------------------------
    width = max(len(n) for n, *_ in results)
    print(f"\n{'=' * (width + 44)}")
    print(f"{'CONTRACT'.ljust(width)}  {'SCHEMA':>9}  {'LINKAGE':>9}  {'DATA':>9}  RESULT")
    print(f"{'-' * (width + 44)}")
    failed = 0
    for name, schema, linkage, data in results:
        overall_ok = schema.passed and linkage.passed and data.passed
        if not overall_ok:
            failed += 1
        print(
            f"{name.ljust(width)}  {schema.badge:>9}  {linkage.badge:>9}  "
            f"{data.badge:>9}  {'PASS' if overall_ok else 'FAIL'}"
        )
    print(f"{'=' * (width + 44)}")
    print(f"{len(results) - failed}/{len(results)} contracts PASS")

    if failed:
        print(
            "\nOne or more contracts no longer describe reality. Fix the platform or "
            "update the contract deliberately — do not weaken the assertion.",
            file=sys.stderr,
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
