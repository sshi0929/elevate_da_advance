# Project Context Memory: Elevate Data Analytics Advanced (Cymbal Retail)

## 📌 Executive Summary & Project Identity
* **Initiative**: Google Cloud Data Analytics Advanced Training — Cymbal Retail Agentic AI & Data Platform Modernization.
* **Customer**: Cymbal Retail (500+ storefronts, global e-commerce portal) migrating from AWS/Databricks/S3 to Google Cloud Modern Lakehouse & Agentic AI Platform.
* **User Profile**: Pre-sales Customer Engineer, Data Analytics Team, Google Cloud Japan.
* **Official Evaluation Git Monorepo**: `https://github.com/sshi0929/elevate_da_advance.git` (local root: `/usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced`).
* **BRD Location**: `DA_advanced/module_0/elevate-da-adv-day1/brd.md` (v3.0).
* **SDD Location**: `DA_advanced/module_1/sdd.md`.

---

## ⚙️ Active Environment Configuration
* **GCP Project ID**: `pj-elevate-da`
* **Region**: `us-central1`
* **Data Service Account**: `cymbal-sa-data@pj-elevate-da.iam.gserviceaccount.com`
* **Dedicated Subnet**: `projects/pj-elevate-da/regions/us-central1/subnetworks/cymbal-retail-subnet-us-central1`
* **GCS Staging Bucket**: `gs://pj-elevate-da-module1-bucket`
* **Federated Catalog Dataset**: `pj-elevate-da.cymbal-lakehouse.elevate_data` (AWS Iceberg via BigLake REST Catalog)
* **BigQuery Gold Destination Table**: `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger` (Managed Iceberg)
* **Cloud Composer Environment**: `cymbal-airflow-env` (Composer 3 / Airflow 2.10.5 in `us-central1`)
* **Composer DAGs GCS Path**: `gs://us-central1-cymbal-airflow--239c1410-bucket/dags`
* **Airflow Webserver URL**: `https://1348a0a0dd624452858576ff65fd281c-dot-us-central1.composer.googleusercontent.com`

---

## 🏆 Current Progress & Completed Milestones

### 1. Module 0 / Day 1: Foundation & Architecture (100% COMPLETE)
- Reviewed official BRD ([`brd.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_0/elevate-da-adv-day1/brd.md)) covering pilot scope, multi-system orchestration, and evaluation rubric.
- Deployed baseline Terraform infrastructure under `module_0/elevate-da-adv-day1/deploy/`.
- Authored and verified the full Solution Design Document ([`sdd.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/sdd.md)).

### 2. Module 1 / Day 2 — Lab 1: Databricks to Dataproc Migration (100% COMPLETE)
- **Challenge 1.1 (PySpark Refactor)**: Modernized Databricks notebook into standalone modular PySpark script [`migrated_inventory_reconciliation_pipeline.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/migrated_inventory_reconciliation_pipeline.py). Replaced proprietary widgets with `argparse`, implemented `writeMethod=direct` for BigLake Iceberg writes, and preserved full 7-stage vectorized logic (8,400 positions, 2.42M intraday time slots, $\cos^4$ demand curve, SHA-256 audit hash, cumulative depletion window).
- **Challenge 1.2 (Multi-Engine Benchmark)**: Evaluated Standard JVM vs. Vectorized Lightning Engine on Dataproc Serverless 2.3:
  - **Standard Engine** (`recon-standard-1788925596`): Running time 129s, Core compute 112.49s, 1,528.65 DCU-s.
  - **Lightning Engine** (`recon-lightning-1788925865`): Running time 94s, Core compute 78.26s, 1,098.10 DCU-s.
  - **Winner**: **Lightning Engine** delivered **1.44x core speedup**, **28.2% compute reduction**, **28.2% shuffle I/O reduction**, and lower net cost (~$0.0397 vs ~$0.0425).
  - **Data Parity**: Exactly 8,400 rows matching target (51 Critical / 84 Monitor / 8,265 Normal Health).
  - **Data Lineage**: OpenLineage verified in Dataplex (`default:cymbal_retail_inventory_reconciliation_pipeline`) linking 3 lakehouse inputs to the Gold Iceberg ledger.
  - **Report**: Full documentation in [`BENCHMARK_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/BENCHMARK_REPORT.md).
- **Challenge 1.3 (Cloud Composer DAG)**: Authored and deployed [`cymbal_nightly_inventory_reconciliation.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/cymbal_nightly_inventory_reconciliation.py). Scheduled nightly at `0 22 * * *` with `DataprocCreateBatchOperator` (Lightning Engine) and `BigQueryCheckOperator` (`COUNT(*) = 8400`). Ad-hoc run triggered and active.
- **Git Consolidation**: Stripped nested `.git` repos, organized monorepo, updated root [`README.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/README.md), committed and pushed cleanly to `https://github.com/sshi0929/elevate_da_advance.git` (`main`).

---

## 🗺️ Project Roadmap & Next Actions

### Immediate Next Task: Module 1 / Lab 2a
* **Guide**: [`02a-pos-manual-generic-rag.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/02a-pos-manual-generic-rag.md)
* **Goal**: Multimodal POS Hardware Intelligence & Conversational RAG with BigQuery AI.
* **Steps**:
  1. Create BigQuery Object Table `pos_manual_generic_pdfs_objects` over `gs://${PROJECT_ID}-module1-bucket/store_pos_manual_generic/*` using `ObjectRef`.
  2. Run single-doc smoke test with `AI.GENERATE((prompt, ref))`.
  3. Structured extraction of technical specifications using `AI.GENERATE_TABLE` with `output_schema`.
  4. Generate 768d vector embeddings using `AI.EMBED` (`text-embedding-005`).
  5. In-database semantic retrieval with `VECTOR_SEARCH` and grounded troubleshooting RAG using `gemini-3.5-flash`.

### Subsequent Lab Pipeline
* **Lab 2b**: [`02b-warranty-multimodal-rag.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/02b-warranty-multimodal-rag.md) — Warranty PDF RAG (`AI.IF`, `AI.CLASSIFY`, stored embeddings, `AI.SEARCH`).
* **Lab 3**: [`03-bigquery-graph-analytics.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/03-bigquery-graph-analytics.md) — ISO GoogleSQL GQL Property Graph for supply chain defect & recall tracing.
* **Lab 4**: [`04-data-governance-policy-tags-masking.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/04-data-governance-policy-tags-masking.md) — IAM Data Governance Tags API v3, Dynamic Masking (`SHA256`, `$0.00`, `LAST_FOUR`), and Row-Level Security.
* **Module 2 (Day 3)**: Real-Time Streaming Intelligence (Kafka, sliding windows, Cloud Bigtable cache <10ms, in-flight inference <100ms).
* **Module 3 (Day 4)**: Agentic AI Platform (Multi-Agent System, Central Router, SQL/RAG/Cache agents, web chat UI, golden evaluation).

---

## ⚠️ Critical Constraints & Gotchas
1. **BigLake Iceberg Writes**: Do NOT use BigQuery indirect load jobs with `temporaryGcsBucket` (triggers `WRITE_TRUNCATE` unsupported error). Always use `writeMethod=direct`.
2. **Lightning Engine Requirements**: Requires `dataproc.tier=premium` and `spark.dataproc.engine=lightningEngine`.
3. **Single GitHub Repo for Evaluation**: All code across all modules must reside inside `https://github.com/sshi0929/elevate_da_advance.git`. Never nest unconfigured `.git` sub-repos.
4. **Shell Rules**: Never run `cd` in shell commands. Use absolute paths or `-C` flags.
