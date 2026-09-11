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
    6. [`Day2_wrap-up_transcript.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/Day2_audio/Day2_wrap-up_transcript.md) (25.2 min / 18K chars)
  - All transcripts synced as Google Docs to shared Drive folder: [`DA Elevate Japan Delivery — Transcripts`](https://drive.google.com/drive/folders/1wLXrXEzXt3WQXzogCzDSp4JW0l0MTG4r) (Editor access shared with `takumik@google.com`).
- [x] **Autonomous Audio Watcher & Drive Synchronization Daemon**:
  - Script: [`Japan_delivery/auto_transcribe_and_sync.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/auto_transcribe_and_sync.py).
  - Background Daemon: Registered and actively running 24/7 as `systemd --user` service `da-audio-watcher.service` (`systemctl --user status da-audio-watcher.service`, polling every 15s). Logs to [`Japan_delivery/watcher.log`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/watcher.log).
  - Standing Rule: Any newly arriving audio clip in `Japan_delivery/` is automatically detected, verified for upload completion, staged to GCS (`gs://pj-elevate-da-module1-bucket/japan_delivery_audio/`), transcribed via `gemini-3.8-flash` on Vertex AI (verbatim timestamps + executive summary), converted and uploaded to Google Drive folder `1wLXrXEzXt3WQXzogCzDSp4JW0l0MTG4r` as a Google Doc + raw `.md`, and indexed in `00_README`. Local tracking maintained at [`Japan_delivery/sync_manifest.json`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/Japan_delivery/sync_manifest.json).

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

- [x] **Module 2 (Day 3) — Real-Time Stream Ingestion, ML Inference & Continuous Activation**:
  - **Challenge 1.1 (Kafka -> Pub/Sub)**: Managed Kafka cluster (`kafka-cluster`), Cloud Storage bucket for Dataflow staging, and Pub/Sub topic `pos-transactions-topic` with dead-letter topic `pos-transactions-dead-letter-topic`.
  - **Challenge 1.2 (Medallion Architecture)**: Single Message Transform (SMT) with JavaScript UDF (`transforms/add_business_date.js`) calculating `business_date` (cutoff 04:00 AM local). Direct Pub/Sub BigQuery subscriptions writing to Bronze (`pos_transactions_raw`), Silver (`pos_transactions_silver` CDC stream with change tracking enabled), and Gold (`pos_transactions_gold`). Verified 0 dead-letter drops and thousands of conformed transactions.
  - **Challenge 2.1 (Stateless ML Inference)**: Remote model `cymbal_models.order_anomaly_model` evaluating order-level fraud risk on raw payloads. Materialized alerts stream into `cymbal_gold.pos_anomaly_alerts`.
  - **Challenge 2.2 (Windowed ML Inference)**: Apache Beam streaming pipeline on Cloud Dataflow (`cashier_abuse_pipeline.py`) reading Silver CDC stream, computing 1-hour sliding windows with 10-second updates, calling remote ML endpoint (`cashier_abuse_model`), and directly writing real-time cashier risk stats to Cloud Bigtable (`operations-db:cashier_realtime_alerts`). Verified 92+ `review` audit alerts caught with risk score > 0.9999.
  - **Challenge 2.3 (Operational Activation & Continuous Queries Reverse ETL)**:
    - Provisioned Cloud Bigtable table `pos_transactions_enriched` with CF `tx` and CF `alerts`.
    - Created dedicated Bigtable App Profile `bq-export` with `priority = PRIORITY_LOW`.
    - Created BigQuery Enterprise Edition reservation `continuous-queries-reservation` (`slot_capacity = 0`, `autoscale.max_slots = 100`) and assigned to project `pj-elevate-da` for `CONTINUOUS` job types.
- [x] **Module 3 / Lab 1 — Semantic Layer & Metadata as Code (kcmd / kc-mac)**:
  - Data Quality scan `pos-transactions-quality-scan` executed on `pos_transactions_gold` (10,284 rows, 100% pass score).
  - Built `mdcode` CLI and installed `~/.local/bin/kcmd`.
  - Exported and synchronized Dataplex Knowledge Catalog snapshot in `module_3/catalog/` across 10 tables.
  - Registered `kc-mac` MCP server in `~/.gemini/settings.json` and validated toolset.
  - Standard table descriptions applied to all 5 core tables via DDL.
- [x] **Module 3 / Lab 2 — BigQuery Conversational Data Agent (BQCA)**:
  - Created and published `Cymbal Retail Analytics Data Agent` (`cymbal-retail-analytics-data-agent`) in location **`global`** to eliminate mTLS routing issues.
  - Scoped to 6 conformed & federated tables across BigQuery and AWS S3 via BigLake catalog: `pos_transactions_gold` (15,046 rows), `pos_anomaly_alerts` (1,296 rows), `gold_inventory_reconciliation_ledger` (8,400 rows), `historical_transactional_data` (22,390 rows), `warranty_generic_sections_extracted` (26 rows), and federated `silver_pos_transactions` (90,816 rows).
  - Implemented 5-section governance system instruction for table selection, UC 2.1 warranty claim triage, and UC 2.3 cross-cloud cashier audit.
  - Registered 5 verified GoogleSQL golden queries and 6 enterprise business glossary terms (including custom metric `Shelf Stock Ratio`).
  - Interactive validation benchmark passed with 100% exact SQL match on all test prompts (UC 1.2, UC 2.1, UC 2.3 Step 1 & Step 2).
  - Automation scripts and full report delivered in [`configure_data_agent.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/configure_data_agent.py), [`test_data_agent_chat.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/test_data_agent_chat.py), and [`02_BQCA_DATA_AGENT_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/02_BQCA_DATA_AGENT_REPORT.md).

- [x] **Module 3 / Lab 3 — Decoupled 3-Toolset ADK Coordinator Agent (`cymbal_operations_agent`)**:
  - Engineered production-grade Multi-Tool ADK Agent using **ADK 2.8.0** and **`gemini-3.6-flash`** orchestrating three decoupled toolsets:
    1. **`cymbal_analytics_tool`**: NL2SQL Data Agent Tool connecting to published BigQuery Conversational Data Agent (`global` endpoint) with verbatim business glossary preservation and exponential backoff.
    2. **`pos_troubleshooting_rag_tool`**: High-precision vector similarity search (`text-embedding-005`) over 500-char sliding-window chunks (`pos_manual_chunk_embeddings`) with adjacent context stitching ($N-1$ to $N+1$), $\ge 0.70$ relevance guardrail, full-text `SEARCH` fallback, and clickable HTTPS manual links.
    3. **`bigtable_mcp_toolset`**: Cloud Run MCP Toolbox microservice (`mcp-toolbox-bigtable` in `us-central1`) querying live 1-hour cashier rolling stats and audit status flags in `operations-db:cashier_realtime_alerts` via SSE and OIDC ID Token authentication.
  - Deployed microservice on Cloud Run mounting Secret Manager configuration (`bigtable-mcp-tools-secret` v2) with Bigtable GoogleSQL typing fixes (`CAST(_key AS STRING)`).
  - Authored comprehensive intent routing instructions in [`app/prompt.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/prompt.py) for Single-Tool, Parallel (UC 2.2), and Sequential Multi-Turn (UC 2.3) dispatches.
  - Automated benchmark test suite ([`test_agent_scenarios.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/test_agent_scenarios.py)) passed with **100% score (7/7)** across all operational scenarios:
    - UC 1.1a (ERR-PAY-4001 SOP & Toshiba TCx 810 Guide) -> PASS (31.46s)
    - UC 1.1c (Ford F-150 out-of-scope fallback warning) -> PASS (13.26s)
    - UC 1.2a (Stockout risk < 20h & total on-hand inventory) -> PASS (70.76s)
    - UC 1.3 (Real-time CASH_1190 at Store 48 Bigtable telemetry) -> PASS (10.91s)
    - UC 2.1a (TXN-20260312-0015811 warranty join in BigQuery) -> PASS (148.70s)
    - UC 2.2 (Dual cashier baseline: **Parallel Dispatch** Turn 1) -> PASS (92.89s)
    - UC 2.3 (Cross-cloud offender audit: **Sequential Dispatch**) -> PASS (107.01s)
  - Full delivery report authored in [`03_ADK_MULTI_AGENT_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/03_ADK_MULTI_AGENT_REPORT.md).

- [x] **Module 3 / Lab 3.2 — Agent Evaluation Benchmark, Data Contracts & Trainer Submission Package**:
  - **Submission layout** built at the repo root to the trainer's spec: [`tests/eval/`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/) plus root-level [`pyproject.toml`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/pyproject.toml), [`agents-cli-manifest.yaml`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/agents-cli-manifest.yaml) and [`SDD.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/SDD.md) (index pointing at `module_1/sdd.md`).
  - **Report** [`tests/eval/evaluation_report.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/evaluation_report.md) authored to the canonical structure mandated by the `agent-eval-guide` skill's `report_template.md` (header block → Executive Summary → Assumptions & Scope → Section 1 use-case matrix / cost architecture / scoring formulation → Section 2 execution output & diagnostics → Limitations). Approach self-score **S_overall = 4.325 / 5.0**.
  - **Benchmark result: 6/7 PASSED (85.7%) in 1,053 s**, quality index Q = 0.9217, agent on `gemini-3.8-flash`, judge pinned to `gemini-3.8-flash`.
  - **Metric design** — ADK defaults scored **0/7 against a working agent** and were rejected with reproduced counter-examples: `tool_trajectory_avg_score` requires exact dict equality on free-text tool args; `response_match_score` is ROUGE-1 and punished a correct live-data answer at 0.5405. Replaced with three ADK-native LLM-judge metrics.
  - **Two-tier grading (the central design decision)**: `reference` tier (5 static cases) = `final_response_match_v2` ≥ 0.7 + `hallucinations_v1` ≥ 0.6; `livedata` tier (2 cases reading the 1-hour rolling Bigtable window) = `hallucinations_v1` ≥ 0.6 + `rubric_based_tool_use_quality_v1` ≥ 0.7 with 4 authored rubrics. A frozen golden expires within the hour, so those cases are graded reference-free.
  - **BRD coverage**: 6/6 in-scope BRD use cases (UC-1.1, 1.2, 1.3, 2.1, 2.2, 2.3); UC-2.4 excluded per the BRD's own statement that the Module 3 agent does not connect to the graph dataset.
  - **Outstanding failure `UC_1.1a_hardware_error`** (`hallucinations_v1` = 0.4194, 13/31 sentences grounded) — root-caused with evidence to a **retrieval-corpus gap**: `pos_manual_chunk_embeddings` contains only the `ERR-PAY-4001` code→name→severity line and no recovery procedure. The agent made 5 RAG calls, was correctly refused twice by the 0.70 similarity gate, then fabricated a 31-sentence runbook. Fix = anti-fabrication clause in the RAG tool instruction + re-chunk the manual.
  - ⚠️ **Golden-dataset defect discovered**: `final_response_match_v2` scored **1.0000** on that fabricated answer because the golden was captured from a prior live run of the same agent and shares the fabrication. Reference-based metrics are structurally blind to hallucinations their reference shares — this is why every case is also graded by a reference-free metric.
  - **Config as code**: [`eval_config.yaml`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/eval_config.yaml) is the single source of truth; `sync_adk_assets.py` generates the 4 ADK JSON artifacts with a `--check` drift gate the runner enforces at startup.
  - **7 data contracts** (`tests/eval/contracts/`) covering the 6 BigQuery/BigLake tables plus Bigtable `cashier_realtime_alerts`, diffed against a live schema snapshot. `validate_contracts.py`: **schema 7/7 PASS** (256 column checks, 0 drift), **linkage 7/7 PASS** (66 checks, 0 orphans), **data assertions 5/7** — two GENUINE upstream defects, not weakened: (1) `est_cover_hours_remaining` NULL on 561/8,400 ledger rows (6.68%), so UC 1.2a's `< 20.0` predicate can never surface them; (2) `silver_pos_transactions` has 1,733 surplus `transaction_id` values (byte-identical Kafka at-least-once duplicates), over-counting UC 2.3 by ~1.9%.
  - **Cost model** via `estimate_eval_cost.py`: **≈ $1.09 per full run** — agent 178,542 in / 18,114 out = $0.202 (exact, from persisted `usage_metadata`), judge ≈ $0.884 (estimated; ADK does not persist auto-rater usage). Judge is 81% of spend.
  - **Execution controls** (do NOT re-introduce the defaults): `InferenceConfig(parallelism=1)` — 4 parallel runners collide on the single Cloud Run MCP SSE session and ADK *silently drops the whole toolset*; explicit `InMemorySessionService()` — avoids `database is locked` on `app/.adk/session.db`. Both `.venv` patches were reverted and the settings are passed from the runner instead.
  - ⚠️ The ADK **Dev UI ignores every `*_config.json`** (`dev_server.py:1341` uses the Run-modal checkboxes and has no judge-model field), so UI runs use the obsolete `gemini-2.5-flash` default and the wrong metric set. Always use the CLI runner for an official scorecard.
  - `tests/eval/run_eval_suite.py` re-execs itself under `module_3/.venv`, so plain `python3 tests/eval/run_eval_suite.py` works from any directory. (Detect the active venv with `sys.prefix`, never `sys.executable` — a venv's `bin/python` is a symlink to the base interpreter, so that comparison is always true.)

### 4. Project Elevate Data Analytics Advanced Track Status
* **All Modules Complete (100%)**:
  - Module 0 / Day 1: Infrastructure Bootstrap & SDD.
  - Module 1: PySpark Migration (Lightning vs Standard), Dataplex Lineage, Composer Orchestration, Multimodal POS/Warranty RAG, BigQuery Property Graphs, IAM Governance & Dynamic Masking.
  - Module 2: Real-Time Medallion Streaming (Kafka $\rightarrow$ Pub/Sub SMT $\rightarrow$ BigQuery CDC), Stateless/Windowed ML Inference (Dataflow $\rightarrow$ Bigtable alerts), Continuous Queries Reverse ETL.
  - Module 3: Semantic Layer & Metadata as Code (kcmd/kc-mac), Conversational Analytics Data Agent (BQCA), and Decoupled Multi-Tool ADK Coordinator Agent.

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
