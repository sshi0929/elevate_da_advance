# Solution Design Document — Index

**Program**: Project Elevate — Data Analytics Advanced Track
**Customer**: Cymbal Retail — Modern Lakehouse & Agentic AI Platform
**Repository**: <https://github.com/sshi0929/elevate_da_advance>

> [!NOTE]
> This is a **monorepo** spanning four delivery modules, so the design record is
> split across module directories. This file is the entry point and index. The
> full, authoritative Solution Design Document is
> [`module_1/sdd.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/sdd.md) (1,247 lines).

---

## 1. Primary design documents

| Document | Scope |
| :--- | :--- |
| [`module_0/elevate-da-adv-day1/brd.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_0/elevate-da-adv-day1/brd.md) | Business Requirements Document (v3.0) — customer context, use cases UC-1.1 … UC-2.4 |
| [`module_1/sdd.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/sdd.md) | **Solution Design Document** — problem statement, target architecture, sequence flows, data platform, security & governance |

### SDD section map

| § | Section | Notes |
| :--- | :--- | :--- |
| 1 | Problem Statement & Scope Boundaries | Current-state AWS/Databricks/S3 estate, bottleneck analysis, target architecture, alternatives considered |
| 2 | Production-Ready Future State Design | Scalability & elasticity, HA / multi-zone resilience, monitoring & observability |
| 3 | System Flows, Sequence Diagrams & Agent Design | UC-1.1 … UC-2.4 sequence flows; ADK multi-agent orchestration; sub-6s fast-path fallback |
| 4 | Data Platform Architecture, Security & Governance | Entity definitions, partitioning strategy, Bigtable salted row-key anti-hotspot design, BigQuery DDL, RLS, dynamic masking, OKF v0.1 / Dataplex Knowledge Catalog |

---

## 2. Module implementation reports

| Module | Report | Delivered |
| :--- | :--- | :--- |
| 1 | [`module_1/lab_spark/BENCHMARK_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/BENCHMARK_REPORT.md) | PySpark migration; Lightning vs Standard engine benchmark |
| 1 | [`module_1/lab_spark/LAB2_MULTIMODAL_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/LAB2_MULTIMODAL_REPORT.md) | Multimodal POS manual & warranty RAG pipelines |
| 1 | [`module_1/lab_spark/LAB4_DATA_GOVERNANCE_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_1/lab_spark/LAB4_DATA_GOVERNANCE_REPORT.md) | IAM governance tags, dynamic masking, row-level security |
| 3 | [`module_3/02_BQCA_DATA_AGENT_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/02_BQCA_DATA_AGENT_REPORT.md) | BigQuery Conversational Analytics Data Agent |
| 3 | [`module_3/03_ADK_MULTI_AGENT_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/03_ADK_MULTI_AGENT_REPORT.md) | Decoupled 3-toolset ADK coordinator agent |
| 3 | [`module_3/EVAL_MECHANISM_EXPLAINED.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/EVAL_MECHANISM_EXPLAINED.md) | How the ADK evaluation harness and LLM-as-judge work |

---

## 3. Evaluation & data contracts

All evaluation fixtures and data contract schemas live under
[`tests/eval/`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/):

| Artifact | Purpose |
| :--- | :--- |
| [`tests/eval/evaluation_report.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/evaluation_report.md) | Evaluation approach, methodology, and results |
| [`tests/eval/eval_config.yaml`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/eval_config.yaml) | Metrics, thresholds, judge model, tier split — single source of truth |
| [`tests/eval/datasets/golden-data.json`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/datasets/golden-data.json) | Golden benchmark dataset (ADK evalset, 7 cases) |
| [`tests/eval/contracts/`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/tests/eval/contracts/) | Data contract definitions for all 7 data sources the agent reads |

---

## 4. Deployed environment

| Resource | Value |
| :--- | :--- |
| GCP Project | `pj-elevate-da` |
| Region | `us-central1` |
| Service Account | `cymbal-sa-data@pj-elevate-da.iam.gserviceaccount.com` |
| Federated catalog | `pj-elevate-da.cymbal-lakehouse.elevate_data` (AWS Iceberg via BigLake REST Catalog) |
| Gold dataset | `pj-elevate-da.cymbal_gold` |
| Orchestration | Cloud Composer 3 — `cymbal-airflow-env` (Airflow 2.10.5) |
| Real-time serving | Cloud Bigtable — `operations-db:cashier_realtime_alerts` |
| Agent runtime | ADK 2.8.0 / Python 3.11 — `module_3/app`, root agent `cymbal_operations_agent` |
