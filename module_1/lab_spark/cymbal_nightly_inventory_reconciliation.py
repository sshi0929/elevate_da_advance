"""
Cloud Composer / Apache Airflow DAG: Cymbal Nightly Inventory Reconciliation
=============================================================================
Orchestrates the Dataproc Serverless 2.3 Lightning Engine batch workload nightly
at 10:00 PM UTC (0 22 * * *) and asserts data quality and parity in the BigQuery
Managed Iceberg Gold ledger (COUNT(*) = 8,400).
"""

from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.providers.google.cloud.operators.dataproc import DataprocCreateBatchOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCheckOperator

# Environment Configuration
PROJECT_ID = os.environ.get("PROJECT_ID", "pj-elevate-da")
REGION = os.environ.get("REGION", "us-central1")
SUBNET_URI = f"projects/{PROJECT_ID}/regions/{REGION}/subnetworks/cymbal-retail-subnet-{REGION}"
SERVICE_ACCOUNT = f"cymbal-sa-data@{PROJECT_ID}.iam.gserviceaccount.com"
STAGING_BUCKET = f"{PROJECT_ID}-module1-bucket"
CATALOG = f"{PROJECT_ID}.cymbal-lakehouse.elevate_data"
TARGET_TABLE = f"{PROJECT_ID}.cymbal_gold.gold_inventory_reconciliation_ledger"

# Default DAG Arguments
DEFAULT_ARGS = {
    "owner": "cymbal-data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Dataproc Serverless 2.3 Lightning Engine Batch Payload
LIGHTNING_BATCH_CONFIG = {
    "pyspark_batch": {
        "main_python_file_uri": f"gs://{STAGING_BUCKET}/code/migrated_inventory_reconciliation_pipeline.py",
        "args": [
            f"--catalog={CATALOG}",
            f"--target-table={TARGET_TABLE}",
            f"--gcs-staging-bucket={STAGING_BUCKET}",
            "--start-date=2025-01-01",
            "--until-date=2026-09-10",
        ],
    },
    "runtime_config": {
        "version": "2.3",
        "properties": {
            "dataproc.tier": "premium",
            "spark.dataproc.engine": "lightningEngine",
            "spark.dataproc.lineage.enabled": "true",
        },
    },
    "environment_config": {
        "execution_config": {
            "service_account": SERVICE_ACCOUNT,
            "subnetwork_uri": SUBNET_URI,
        },
    },
}

with DAG(
    dag_id="cymbal_nightly_inventory_reconciliation",
    default_args=DEFAULT_ARGS,
    description="Nightly Dataproc Serverless Lightning Engine reconciliation pipeline with BigQuery parity gate",
    schedule_interval="0 22 * * *",  # Nightly at 10:00 PM UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["cymbal", "retail", "dataproc", "lightning-engine", "inventory-reconciliation", "lakehouse"],
) as dag:

    # Task 1: Execute Dataproc Serverless PySpark batch using Lightning Engine
    run_inventory_reconciliation_lightning = DataprocCreateBatchOperator(
        task_id="run_inventory_reconciliation_lightning",
        project_id=PROJECT_ID,
        region=REGION,
        batch=LIGHTNING_BATCH_CONFIG,
        batch_id="recon-nightly-{{ ds_nodash }}-{{ ts_nodash.lower() }}-{{ ti.try_number }}",
    )

    # Task 2: Data Quality & Parity Gate in BigQuery (Must contain exactly 8,400 rows)
    validate_gold_table_parity = BigQueryCheckOperator(
        task_id="validate_gold_table_parity",
        sql=f"""
        SELECT COUNT(*) = 8400 
        FROM `{TARGET_TABLE}`
        """,
        use_legacy_sql=False,
        location=REGION,
    )

    # Dependency Pipeline: Lightning Batch -> Quality Parity Check
    run_inventory_reconciliation_lightning >> validate_gold_table_parity
