# Cymbal Retail — Data Analytics & Agentic AI Platform Modernization

This repository contains the architecture designs, infrastructure code, data engineering pipelines, and agentic workflows for the **Google Cloud Data Analytics Advanced Training** initiative for **Cymbal Retail**.

---

## 🏗️ Architecture & Pilot Scope

Cymbal Retail is modernizing its enterprise data platform from an AWS / Databricks / S3 stack to a unified **Google Cloud Agentic Data Cloud** platform.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CYMBAL RETAIL PLATFORM MODERNIZATION                            │
├────────────────────────┬───────────────────────────────────────────────────────────────┤
│ Module 0 (Day 1)       │ Foundation: Terraform IaC, Environment Bootstrap & BRD       │
│ Module 1 (Day 1 & 2)   │ Solution Design Document (SDD), Lakehouse & Serverless Spark  │
│ Module 2 (Day 3)       │ Real-Time Streaming Intelligence & Low-Latency Bigtable Cache │
│ Module 3 (Day 4)       │ Conversational Multi-Agent System (ADK + BigQuery AI)         │
└────────────────────────┴───────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
.
├── README.md                                  # Repository overview and guide
├── Japan_delivery/                            # Meeting notes, recordings, and Japanese delivery summaries
│   ├── DA_Elevate_Day1_Meeting_Summary.md
│   └── transcript_raw.txt
│
├── module_0/                                  # Day 1: Foundation & Bootstrap
│   └── elevate-da-adv-day1/
│       ├── brd.md                             # Official Business Requirements Document (BRD v3.0)
│       ├── sdd-template.md                    # Software Design Document template
│       └── deploy/                            # Terraform IaC for core GCP infrastructure
│
├── module_1/                                  # Day 1 & 2: Lakehouse Data Engineering
│   ├── sdd.md                                 # Full Solution Design Document (SDD)
│   └── lab_spark/                             # Dataproc Serverless Migration & Multimodal Labs
│       ├── migrated_inventory_reconciliation_pipeline.py  # Refactored modular PySpark script
│       ├── cymbal_nightly_inventory_reconciliation.py     # Cloud Composer (Airflow) DAG
│       ├── BENCHMARK_REPORT.md                # Standard vs Lightning Engine benchmark analysis
│       ├── 01-databricks-dataproc-migration.md# Lab 1 guide: Databricks to Dataproc migration
│       ├── 02a-pos-manual-generic-rag.md      # Lab 2a guide: POS Hardware Multimodal RAG
│       ├── 02b-warranty-multimodal-rag.md     # Lab 2b guide: Warranty Document RAG
│       ├── 03-bigquery-graph-analytics.md     # Lab 3 guide: ISO GQL Graph Traceability
│       └── 04-data-governance-policy-tags-masking.md # Lab 4 guide: IAM Tags, Masking & RLS
│
├── module_2/                                  # Day 3: Streaming Analytics (Kafka / Bigtable)
└── module_3/                                  # Day 4: Agentic AI Platform (Multi-Agent System)
```

---

## ⚡ Highlights: Module 1 Lab 1 Dataproc Multi-Engine Benchmark

In **Module 1 / Lab 1**, Cymbal Retail's daily inventory reconciliation workload was migrated from an AWS Databricks notebook to a standalone PySpark application and benchmarked across Dataproc Serverless engines:

| Metric | Dataproc Standard Engine (JVM) | Dataproc Lightning Engine (Vectorized C++) | Advantage / Winner |
| :--- | :--- | :--- | :--- |
| **Execution Architecture** | Standard JVM Spark 3.5 | Native SIMD Vectorized C++ | ⚡ **Lightning Engine** |
| **Running Duration** | 129 seconds | **94 seconds** | ⚡ **27.1% faster runtime** |
| **Core Compute Duration** | 112.49 seconds | **78.26 seconds** | ⚡ **1.44x speedup** |
| **Compute Units Consumed** | 1,528.65 DCU-seconds | **1,098.10 DCU-seconds** | ⚡ **28.2% less compute** |
| **Shuffle Storage I/O** | 154,800 GB-seconds | **111,200 GB-seconds** | ⚡ **28.2% less shuffle I/O** |
| **Reconciled Records** | 8,400 rows | 8,400 rows | **Exact Parity (100% Match)** |
| **Decision** | Baseline Standard | **🏆 WINNER** | Orchestrated via Cloud Composer |

*Detailed benchmark report and metrics are available in [BENCHMARK_REPORT.md](module_1/lab_spark/BENCHMARK_REPORT.md).*
