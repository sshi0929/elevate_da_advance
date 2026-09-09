# Project Elevate — Unified Project Memory & Agent Guide (GEMINI.md / AGENT.md)

## 📌 Executive Summary & Project Identity
* **Program**: Project Elevate — Google Cloud Japan Customer Engineering Advanced Enablement.
* **User Profile**: Pre-sales Customer Engineer, Data Analytics Team, Google Cloud Japan.
* **Workspace Root**: `/usr/local/google/home/watanabesei/account_work/Admin/pj_elevate`
* **Core Tracks**:
  1. **Data Analytics Advanced Track** (`DA_advanced/`): Cymbal Retail Modern Lakehouse & Agentic AI Platform.
  2. **AI / Agent School Track** (`AI/`): Enterprise HR/IT Multi-Agent System & Two-Pillar Evaluation.

---

## 🏛️ Track 1: Data Analytics Advanced (Cymbal Retail Modernization)

### 1. Context & Architecture
* **Customer**: Cymbal Retail (500+ storefronts, global e-commerce portal) migrating from AWS/Databricks/S3 to Google Cloud Modern Lakehouse & Agentic AI.
* **Official Evaluation Git Monorepo**: `https://github.com/sshi0929/elevate_da_advance.git` (local root: `DA_advanced/`).
* **BRD Location**: [`DA_advanced/module_0/elevate-da-adv-day1/brd.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_0/elevate-da-adv-day1/brd.md) (v3.0).
* **SDD Location**: [`DA_advanced/module_1/sdd.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/sdd.md).

### 2. Active Environment Configuration
* **GCP Project ID**: `pj-elevate-da` | **Region**: `us-central1`
* **Service Account**: `cymbal-sa-data@pj-elevate-da.iam.gserviceaccount.com`
* **Subnet**: `projects/pj-elevate-da/regions/us-central1/subnetworks/cymbal-retail-subnet-us-central1`
* **GCS Staging**: `gs://pj-elevate-da-module1-bucket`
* **Federated Catalog**: `pj-elevate-da.cymbal-lakehouse.elevate_data` (AWS Iceberg via BigLake REST Catalog)
* **Gold Sink Table**: `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger` (Managed Iceberg)
* **Cloud Composer**: `cymbal-airflow-env` (Composer 3 / Airflow 2.10.5 in `us-central1`)
* **Airflow URL**: `https://1348a0a0dd624452858576ff65fd281c-dot-us-central1.composer.googleusercontent.com`

### 3. Completed Milestones (DA Track)
- [x] **Module 0 / Day 1 (100%)**: BRD review, Terraform infrastructure bootstrap (`deploy/`), full SDD authored (`module_1/sdd.md`).
- [x] **Module 1 / Lab 1 — PySpark Migration**: Refactored Databricks notebook to modular PySpark script [`migrated_inventory_reconciliation_pipeline.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/migrated_inventory_reconciliation_pipeline.py) using `writeMethod=direct`.
- [x] **Module 1 / Lab 1 — Multi-Engine Benchmark**:
  - **Standard Engine** (`recon-standard-1788925596`): 129s runtime, 112.49s compute, 1,528.65 DCU-s.
  - **Lightning Engine** (`recon-lightning-1788925865`): 94s runtime, 78.26s compute, 1,098.10 DCU-s.
  - **Outcome**: **Lightning Engine won with 1.44x speedup, 28.2% compute reduction, 28.2% shuffle reduction**, lower cost (~$0.0397 vs ~$0.0425), and 100% exact parity (8,400 rows: 51 Crit / 84 Mon / 8,265 Norm).
  - Full report documented in [`BENCHMARK_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/BENCHMARK_REPORT.md).
- [x] **Module 1 / Lab 1 — Dataplex Lineage**: OpenLineage verified connecting 3 lakehouse sources to the gold ledger.
- [x] **Module 1 / Lab 1 — Cloud Composer Orchestration**: Deployed [`cymbal_nightly_inventory_reconciliation.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/cymbal_nightly_inventory_reconciliation.py) with `DataprocCreateBatchOperator` (Lightning) and `BigQueryCheckOperator` (`COUNT(*) = 8400`). Ad-hoc run triggered.
- [x] **Module 1 / Lab 2a — Multimodal POS Hardware Intelligence & RAG**:
  - Object table `pos_manual_generic_pdfs_objects` over 5 OEM manuals with automated metadata caching.
  - Remote model `gemini_pos_manual_extractor` registered.
  - Batch extraction `pos_manual_generic_sections_extracted` materialized via `AI.GENERATE_TABLE` with 12 typed columns.
  - 768-dim dense embeddings materialized into `pos_manual_embeddings` via `text-embedding-005`.
  - Native `VECTOR_SEARCH` verified with Cosine distance (0.2495 top match for Toshiba NVMe SSD replacement).
  - Grounded RAG directives generated for store operations and emergency SOPs.
- [x] **Module 1 / Lab 2b — Warranty Dark Data Intelligence & Native Semantic Search**:
  - Object table `warranty_generic_pdfs_objects` exposing 26 warranty PDF certificates with `ObjectRef` verification.
  - Direct zero-shot boolean evaluation (`AI.IF`) on raw PDF binaries for accidental damage and unit replacement options.
  - Zero-shot retail taxonomy classification (`AI.CLASSIFY`) accurately categorizing audio, wearables, and computing devices.
  - Batch extraction `warranty_generic_sections_extracted` materialized with 17 typed fields and verbatim content.
  - Quality Gate passed: 26/26 rows, 0 missing names/prices/durations, avg content length 5,838 chars (min 2,764 >= 800).
  - Autonomous stored embeddings materialized into `warranty_generic_pdf_chunk_embeddings` with `GENERATED ALWAYS AS (AI.EMBED(...)) STORED OPTIONS(asynchronous = TRUE)`.
  - Native semantic search (`AI.SEARCH`) executed with top match `prod_155` (OnePlus Nord Buds CE, distance 0.2089).
  - Full scripts saved in [`02_multimodal_rag_pipelines.sql`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/02_multimodal_rag_pipelines.sql) and report in [`LAB2_MULTIMODAL_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/LAB2_MULTIMODAL_REPORT.md).

### 4. Immediate Next Action (DA Track)
* **Module 1 / Lab 3**: BigQuery Graph Analytics ([`03-bigquery-graph-analytics.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/03-bigquery-graph-analytics.md)) evaluating property graphs, GQL, and graph-based retail intelligence.

---

## 🤖 Track 2: AI / Agent School (HR Agent & Two-Pillar Evaluation)

### 1. Context & Architecture
* **Repository**: `https://github.com/tayzar-tznw/elevate` (Fork: `https://github.com/sshi0929/elevate`) under `AI/agent_school/lecture/module3/elevate/`.
* **Core Reference**: `AI/agent_school/lecture/module3/reference/HR Agentic Solution BRD.md`.
* **Two-Pillar Evaluation Strategy**:
  * **Pillar 1 (Production Benchmark)**: Deep evaluation across 70+ test cases via LLM-as-Judge (`gemini-3.7-flash`) achieving **97.0% accuracy** (68/70).
  * **Pillar 2 (CI/CD Quality Gate)**: Fast deterministic local test runner (`tests/eval/run_local_brd_eval.py`) running in **0.9s** with **$0.00 cost** (100% pass rate, 21/21) enforced in `.github/workflows/eval-ci.yaml` (minimum 95% pass rate required).

### 2. Delivered Assets & Merged PRs
* **PR #7 (Merged)**: `ci(eval): add GitHub Actions BRD evaluation quality gate & test runner`.
* **PR #9 (Merged)**: `docs(eval): add two-pillar evaluation strategy & NotebookLM source documents`.
* **Evaluation Assets**: `tests/eval/datasets/brd-eval-data.json`, `brd-eval-multi-turn.json`, `response_quality.py`, `notebooklm_eval_source.md`.

---

## ⚙️ Coding Agent & ADK Operational Guidelines (from AGENTS.md)

### 1. CLI Tooling & Commands
* CLI: `google-agents-cli` (`uv tool install google-agents-cli`).
* Primary Command Suite:
  | Command | Purpose |
  | :--- | :--- |
  | `agents-cli playground` | Interactive local testing |
  | `uv run pytest tests/unit tests/integration` | Run unit and integration tests |
  | `agents-cli eval generate` | Run agent on eval dataset, produce traces |
  | `agents-cli eval grade` | Run agent evaluations on the traces |
  | `agents-cli eval compare` | Compare two grade-results files (regression check) |
  | `agents-cli eval optimize` | Auto-tune agent prompts using eval data |
  | `agents-cli deploy` | Deploy agent to development environment |

### 2. Operational Rules for Coding Agents
* **Code Preservation**: Modify ONLY code directly targeted by the request. Never wipe surrounding context, configurations, or comments.
* **Model Integrity**: Never alter the model name unless explicitly requested. On 404 errors, check `GOOGLE_CLOUD_LOCATION` (e.g., `global` vs `us-central1`), not the model identifier.
* **Execution with uv**: Always invoke python via `uv run python script.py`.
* **Circuit Breaker**: If an identical error recurs 3+ times, diagnose root cause rather than retrying blindly.
* **Terraform Conflict (409)**: Use `terraform import` rather than recreating conflicting resources.

---

## ⚠️ Critical Cross-Project Constraints & Gotchas
1. **BigLake Iceberg Writes**: Do NOT use BigQuery indirect load jobs (`temporaryGcsBucket`), which trigger `WRITE_TRUNCATE` unsupported error on Iceberg. Always specify `writeMethod=direct`.
2. **Lightning Engine Requirements**: Requires `dataproc.tier=premium` and `spark.dataproc.engine=lightningEngine`.
3. **Single GitHub Monorepo Rule**: All code across all modules must reside inside `https://github.com/sshi0929/elevate_da_advance.git` without unconfigured nested `.git` sub-repos.
4. **Shell Navigation**: Never execute raw `cd` in tool commands; use absolute paths or `-C` flags.
