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
- [x] **Japan Delivery Enablement & Lecture Transcriptions**:
  - Transcribed Day 1 sync and all 3 Day 2 technical training recordings using `gemini-3.8-flash` on Vertex AI via GCS staging (`gs://pj-elevate-da-module1-bucket/day2_audio/`).
  - Generated complete, verbatim Markdown files with timestamps, speaker identification, and executive summaries in [`Japan_delivery/Day2_audio/`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/Day2_audio/):
    1. [`Day2_Iceberg_lecture1_transcript.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/Day2_audio/Day2_Iceberg_lecture1_transcript.md) (44.3 min / 45K chars)
    2. [`Day2_Iceberg_lecture2_transcript.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/Day2_audio/Day2_Iceberg_lecture2_transcript.md) (16.7 min / 18K chars)
    3. [`Day2_Spark_lecture1_transcript.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/Day2_audio/Day2_Spark_lecture1_transcript.md) (50.1 min / 53K chars)
    4. [`Day2_PropertyGraph_transcript.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/Day2_audio/Day2_PropertyGraph_transcript.md) (24.1 min / 23K chars)
    5. [`Day2_Security_transcript.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/Day2_audio/Day2_Security_transcript.md) (25.5 min / 26K chars)
  - All transcripts synced as Google Docs to shared Drive folder: [`DA Elevate Japan Delivery — Transcripts`](https://drive.google.com/drive/folders/1wLXrXEzXt3WQXzogCzDSp4JW0l0MTG4r) (Editor access shared with `takumik@google.com`).
- [x] **Autonomous Audio Watcher & Drive Synchronization Pipeline**:
  - Script: [`Japan_delivery/auto_transcribe_and_sync.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/auto_transcribe_and_sync.py).
  - Standing Rule: Any newly arriving audio clip in `Japan_delivery/` is automatically staged to GCS (`gs://pj-elevate-da-module1-bucket/japan_delivery_audio/`), transcribed via `gemini-3.8-flash` on Vertex AI (verbatim timestamps + executive summary), converted and uploaded to Google Drive folder `1wLXrXEzXt3WQXzogCzDSp4JW0l0MTG4r` as a Google Doc + raw `.md`, and indexed in `00_README`. Local tracking maintained at [`Japan_delivery/sync_manifest.json`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/sync_manifest.json).

- [x] **Module 1 / Lab 3 — BigQuery Property Graph Analytics & Supply Chain Recall (BRD 2.4)**:
  - Installed and verified latest [`bigquery-graph`](file:///usr/local/google/home/watanabesei/.gemini/config/skills/bigquery-graph/SKILL.md) skill from `google/adk-python`.
  - Verified 4 node tables (`customer_nodes` 32,264 rows, `store_nodes` 50 rows, `supplier_nodes` 5 rows, `batch_lot_nodes` 41 rows) and 3 edge tables (`produced_batch_edges` 41 rows, `shipped_to_edges` 180 rows, `sold_lot_to_customer_edges` 100 rows) in federated AWS Iceberg dataset `pj-elevate-da.cymbal-lakehouse.elevate_data`.
  - Registered property graph `pj-elevate-da.cymbal_gold.supply_chain_traceability_graph` via native DDL.
  - Variable-length path traversal (`-[s:SHIPPED_TO]->{1,3}`) verified 180 paths with `PATH_LENGTH(p)` and `TO_JSON(p)`.
  - VIP Recall Triage pattern match (`MATCH (sup)->(lot)->(cust)`) isolated exactly 38 high-priority PLATINUM/GOLD customers.
  - Diamond blast-radius matching discovered 99 secondary co-exposure events across common high-risk supplier `SUP_001`.
  - Emergency contact ledger extracted 44 hardware serials and phone numbers via `GRAPH_TABLE()`.
  - Supplier defect scorecard revealed `SUP_001` (Apex Battery) with 100% defect rate vs. 0.0% across all other suppliers.
  - Materialized gold 360° recall view `pj-elevate-da.cymbal_gold.supply_chain_recall_traceability_360` bridging graph traversals into relational SQL and text-to-SQL agents.
- [x] **Module 1 / Lab 4 — IAM Data Governance Tags, Dynamic Masking & Row-Level Security (BRD 2.2)**:
  - Created Cloud Resource Manager Tag Key `pii_classification` (`tagKeys/281480941817283`) with `purpose = DATA_GOVERNANCE` under `projects/pj-elevate-da`.
  - Created 4 hierarchical Tag Values (`customer_name` High, `customer_id` Med, `financial_amount` Med, `store_metadata` Low).
  - Attached column tags via native BigQuery SQL DDL (`ALTER TABLE ... ALTER COLUMN ... SET OPTIONS(data_governance_tags=[...])`) to 5 columns in dedicated working table `aws_pos_transactions_gold2` (90,816 rows). Verified via `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`.
  - Provisioned 4 `RAW_DATA_ACCESS_POLICY` and 4 `DATA_MASKING_POLICY` data policies via BigQuery Data Policy API v2.
  - Implemented Row Access Policies on `gold_inventory_reconciliation_ledger2` (8,400 rows) with `rls_unrestricted_lead` (`FILTER USING (TRUE)`) and `rls_analyst_stores` (`store_id IN ('STORE_048', 'STORE_009')`).
  - Multi-persona live query verification executed via SA token impersonation:
    - 👑 **Data Lead (`sa-data-lead`)**: 100% unmasked plaintext names/amounts + nationwide store visibility.
    - 🎭 **Business Analyst (`sa-analyst`)**: Irreversible 64-character `SHA256` names, masked `XXXXX<last4>` customer IDs, `$0.00` amounts, and strictly scoped to authorized store (`STORE_009`).
    - 🚫 **Restricted User (`sa-restricted`)**: Immediate `403 Forbidden` on protected CLS columns, and `0 rows` returned on RLS ledger (Default Deny).
  - Full scripts saved in [`04_data_governance_pipelines.sql`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/04_data_governance_pipelines.sql) and report in [`LAB4_DATA_GOVERNANCE_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/LAB4_DATA_GOVERNANCE_REPORT.md).

### 4. Immediate Next Action (DA Track)
* **Module 1 All Labs (1, 2a, 2b, 3, 4) Complete!**: Proceed to Module 2 (Advanced Lakehouse Transformations & Feature Store) / Day 3 enablement as soon as assets are published.

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
