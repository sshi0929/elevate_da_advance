# Cymbal Retail — Data Analytics & Agentic AI Platform Modernization

This repository contains the architecture designs, infrastructure code, and implementation assets for the Google Cloud Data Analytics Advanced Training initiative.

## Repository Structure

```
├── module_0/                  # Foundation: Terraform IaC and Environment Bootstrap
│   └── elevate-da-adv-day1/   # Core infra: Kafka, Bigtable, Composer 3, BigQuery
├── module_1/                  # Solution Design & Architecture
│   └── sdd.md                 # Full Solution Design Document (SDD)
├── module_2/                  # Lakehouse & Data Pipelines (Coming Soon)
└── module_3/                  # Streaming Analytics & Agentic Operations (Coming Soon)
```

## Highlights: Solution Design Document (Module 1)
The primary deliverable for Module 1 is the comprehensive [Solution Design Document (sdd.md)](module_1/sdd.md), which establishes:
- **Cross-Cloud Lakehouse Federation:** Zero-copy BigLake Iceberg REST Catalog queries against remote AWS S3 datasets.
- **Serverless Data Engineering:** Dataproc Serverless for Apache Spark eliminating 24/7 idle cluster tax.
- **Real-Time Streaming & Operational Caching:** Managed Service for Apache Kafka paired with Cloud Bigtable (`operations-db`) for sub-10ms operational lookups.
- **Governed Unstructured Knowledge Mining:** Open Knowledge Format (OKF v0.1) and Dataplex Knowledge Catalog (`certified = true`) served via the Knowledge Catalog MCP Server.
- **Conversational Analytics & Agentic Operations:** BigQuery Conversational Analytics API (`geminidataanalytics.googleapis.com`) integrated into the Agent Development Kit (ADK) multi-agent runtime, paired with a custom web application featuring an inspectable SQL drawer.
