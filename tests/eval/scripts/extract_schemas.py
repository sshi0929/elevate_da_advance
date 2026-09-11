#!/usr/bin/env python3
"""Extract live BigQuery + Bigtable schemas backing the evaluation data contracts.

The data contracts in ``tests/eval/contracts/`` must describe the *actual*
deployed tables, not an idealised model. This script pulls the ground truth
straight from the platform so the contracts can be regenerated and diffed
whenever the lakehouse changes.

Usage:
    uv run python tests/eval/scripts/extract_schemas.py
    uv run python tests/eval/scripts/extract_schemas.py --out /tmp/schemas.json
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

PROJECT_ID = "pj-elevate-da"

# ADC on a corp workstation is frequently minted against an unrelated quota
# project, which makes the Bigtable Admin API reject the call with
# "Cloud Bigtable Admin API has not been used in project <other> before".
# Pin the quota project unless the caller has already chosen one.
os.environ.setdefault("GOOGLE_CLOUD_QUOTA_PROJECT", PROJECT_ID)


# The six BigQuery / BigLake tables scoped into the Cymbal Retail Analytics
# Data Agent (see module_3/configure_data_agent.py).
BQ_TABLES = [
    "pj-elevate-da.cymbal_gold.pos_transactions_gold",
    "pj-elevate-da.cymbal_gold.pos_anomaly_alerts",
    "pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger",
    "pj-elevate-da.cymbal_gold.historical_transactional_data",
    "pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted",
    "pj-elevate-da.cymbal-lakehouse.elevate_data.silver_pos_transactions",
]


def _field_to_dict(field) -> dict:
    out = {
        "name": field.name,
        "type": field.field_type,
        "mode": field.mode,
        "description": field.description,
    }
    if field.fields:
        out["fields"] = [_field_to_dict(f) for f in field.fields]
    return out


def extract_bigquery() -> dict:
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    results = {}
    for fqn in BQ_TABLES:
        try:
            table = client.get_table(fqn)
        except Exception as e:  # noqa: BLE001 - report and continue
            results[fqn] = {"error": f"{type(e).__name__}: {e}"}
            print(f"  !! {fqn}: {type(e).__name__}: {e}", file=sys.stderr)
            continue

        entry = {
            "table_type": table.table_type,
            "num_rows": table.num_rows,
            "num_bytes": table.num_bytes,
            "created": table.created.isoformat() if table.created else None,
            "modified": table.modified.isoformat() if table.modified else None,
            "description": table.description,
            "labels": dict(table.labels or {}),
            "schema": [_field_to_dict(f) for f in table.schema],
        }
        if table.time_partitioning:
            entry["time_partitioning"] = {
                "type": table.time_partitioning.type_,
                "field": table.time_partitioning.field,
            }
        if table.clustering_fields:
            entry["clustering_fields"] = list(table.clustering_fields)
        if getattr(table, "external_data_configuration", None):
            edc = table.external_data_configuration
            entry["external"] = {
                "source_format": edc.source_format,
                "source_uris": list(edc.source_uris or []),
                "connection_id": getattr(edc, "connection_id", None),
            }
        results[fqn] = entry
        print(f"  ok {fqn}  ({len(entry['schema'])} cols, {table.num_rows} rows)")
    return results


def extract_bigtable() -> dict:
    """Bigtable is schemaless per-row; we capture column families + a sample row."""
    from google.cloud import bigtable

    instance_id, table_id = "operations-db", "cashier_realtime_alerts"
    try:
        client = bigtable.Client(project=PROJECT_ID, admin=True)
        instance = client.instance(instance_id)
        table = instance.table(table_id)
        families = {
            name: {"gc_rule": str(cf.gc_rule) if cf.gc_rule else None}
            for name, cf in table.list_column_families().items()
        }
        sample_qualifiers: dict[str, list[str]] = {}
        sample_row_key = None
        for row in table.read_rows(limit=1):
            sample_row_key = row.row_key.decode("utf-8", "replace")
            for fam, cols in row.cells.items():
                sample_qualifiers[fam] = sorted(
                    q.decode("utf-8", "replace") for q in cols
                )
            break
        print(f"  ok {instance_id}:{table_id}  (families: {', '.join(families)})")
        return {
            f"{instance_id}:{table_id}": {
                "instance_id": instance_id,
                "table_id": table_id,
                "column_families": families,
                "sample_row_key": sample_row_key,
                "sample_qualifiers": sample_qualifiers,
            }
        }
    except Exception as e:  # noqa: BLE001
        print(f"  !! bigtable: {type(e).__name__}: {e}", file=sys.stderr)
        return {f"{instance_id}:{table_id}": {"error": f"{type(e).__name__}: {e}"}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(pathlib.Path(__file__).parent / "_schema_snapshot.json"),
        help="Where to write the combined schema snapshot.",
    )
    args = parser.parse_args()

    print("Extracting BigQuery schemas...")
    payload = {"bigquery": extract_bigquery()}
    print("Extracting Bigtable schema...")
    payload["bigtable"] = extract_bigtable()

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
