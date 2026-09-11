# Module 3 Lab 3: Building & Orchestrating the Multi-Tool ADK Agent — Technical Delivery & Validation Report

---

## Executive Summary

This report documents the end-to-end design, implementation, and automated benchmark validation of the **Cymbal Retail Unified Operations & Risk Coordinator Agent (`cymbal_operations_agent`)** for **Project Elevate — Google Cloud Japan Customer Engineering Enablement (Module 3 Lab 3)**.

The solution establishes a decoupled, production-grade Multi-Tool Agent built on the **Google Agent Development Kit (ADK 2.8.0)** and powered by **`gemini-3.6-flash`**. The agent bridges three distinct operational systems across Google Cloud and federated AWS lakehouses:
1. **Relational & Federated Lakehouse Analytics (`cymbal_analytics_tool`)**: Leverages the BigQuery Conversational Data Agent API (`global` endpoint) for real-time natural language to GoogleSQL generation across store inventory, burn rates, warranty terms, fraud alerts, and federated AWS S3 transactions.
2. **POS Hardware Diagnostic Runbooks (`pos_troubleshooting_rag_tool`)**: Advanced BigQuery vector similarity search (`text-embedding-005`) over fine-grained sliding-window chunks (500 chars / 100 char overlap) with adjacent context window stitching ($N-1$ to $N+1$), certified similarity guardrail ($\ge 0.70$), full-text `SEARCH` fallback, and clickable HTTPS manual links.
3. **Real-Time Cashier Risk Intelligence (`bigtable_mcp_toolset`)**: Cloud Run MCP Toolbox microservice (`mcp-toolbox-bigtable`) querying Cloud Bigtable instance `operations-db` (`cashier_realtime_alerts`) over SSE with OIDC ID Token authentication, providing sub-second 1-hour rolling metrics and operational audit status flags.

### Benchmark Validation Highlights
* **Test Suite**: Automated harness (`test_agent_scenarios.py`) executing all 7 required operational scenarios.
* **Overall Pass Rate**: **7 / 7 (100.0%) Passed**.
* **Parallel Dispatch (UC 2.2)**: Verified concurrent dual-tool dispatch in Turn 1 (Cloud Bigtable MCP + BigQuery Data Agent).
* **Sequential Dispatch (UC 2.3)**: Verified multi-turn sequential discovery (GCP anomaly ranking $\rightarrow$ AWS S3 checkout logs).

---

## Architecture Topology

```mermaid
flowchart TD
    User["Store Lead / Auditor<br><i>(ADK Web UI / Python SDK)</i>"] --> Coordinator["ADK Coordinator Agent<br><code><b>cymbal_operations_agent</b></code><br><i>(Model: gemini-3.6-flash)</i>"]

    subgraph ToolsetGateways ["Decoupled 3-Toolset Gateways"]
        Coordinator -->|1. Relational & Lakehouse Analytics| Tool1["NL2SQL Data Agent Tool<br><code><b>cymbal_analytics_tool</b></code><br><i>(Verbatim NL2SQL API)</i>"]
        Coordinator -->|2. Hardware Diagnostics & SOPs| Tool2["POS Manual RAG Tool<br><code><b>pos_troubleshooting_rag_tool</b></code><br><i>(Stitched Vector Search)</i>"]
        Coordinator -->|3. Live Cashier Telemetry| Tool3["Cloud Bigtable MCP Toolset<br><code><b>bigtable_mcp_toolset</b></code><br><i>(ADK McpToolset via SSE)</i>"]
    end

    subgraph GCP_Backend ["Google Cloud & Federated Lakehouse Infrastructure"]
        Tool1 --> BQCA["BigQuery Conversational Data Agent<br><code>projects/pj-elevate-da/locations/global/...</code>"]
        BQCA --> BQ_Gold[("cymbal_gold & module1_unstructureddata<br>• pos_transactions_gold<br>• pos_anomaly_alerts<br>• gold_inventory_reconciliation_ledger<br>• warranty_generic_sections_extracted")]
        BQCA --> AWS_S3[("AWS S3 via BigLake REST Catalog<br>• silver_pos_transactions")]

        Tool2 --> BQ_Chunks[("BigQuery Vector Store<br><code>pos_manual_chunk_embeddings</code><br><i>(500-char sliding windows)</i>")]

        Tool3 --> CloudRun["Cloud Run Microservice<br><code>mcp-toolbox-bigtable</code><br><i>(us-central1, Secret Manager mounted)</i>"]
        CloudRun --> Bigtable[("Cloud Bigtable<br><code>operations-db:cashier_realtime_alerts</code>")]
    end
```

---

## Configuration & Environment Matrix

| Parameter | Assigned Resource Value | Purpose |
| :--- | :--- | :--- |
| **GCP Project ID** | `pj-elevate-da` | Host project for all data, ML, and compute resources |
| **GCP Region** | `us-central1` | Primary region for BigQuery, Cloud Run, Bigtable, and Composer |
| **Data Agent Location** | `global` | Prevents mTLS and regional endpoint routing errors |
| **Data Agent ID** | `cymbal-retail-analytics-data-agent` | Published BigQuery Conversational Data Agent |
| **Data Agent Resource** | `projects/pj-elevate-da/locations/global/dataAgents/cymbal-retail-analytics-data-agent` | Target NL2SQL endpoint |
| **Cloud Run MCP Service** | `https://mcp-toolbox-bigtable-15183141503.us-central1.run.app` | Database Toolbox MCP SSE server |
| **Secret Manager Secret** | `bigtable-mcp-tools-secret` (v2) | Mounts `tools.yaml` configuration into Cloud Run |
| **Bigtable Instance / Table** | `operations-db` / `cashier_realtime_alerts` | Live 1-hour cashier rolling stats & audit flags |
| **Service Account** | `cymbal-sa-data@pj-elevate-da.iam.gserviceaccount.com` | Granted `roles/run.invoker` and `roles/bigtable.user` |
| **Vector Chunks Table** | `pj-elevate-da.cymbal_gold.pos_manual_chunk_embeddings` | 500-char sliding-window chunks with text-embedding-005 |
| **Coordinator Model** | `gemini-3.6-flash` | Gemini 3.x Flash series for fast routing & tool orchestration |

---

## Challenge Implementations

### Challenge 1.1: Project Scaffolding & Virtual Environment
* **Location**: `/usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/`
* **Virtual Environment**: `.venv` using Python 3.11 with pinned versions:
  - `google-adk==2.8.0`
  - `mcp==1.30.0` (pinned to `mcp<2` to resolve ADK `ProgressFnT` compatibility)
  - `google-genai==2.22.0`
  - `google-cloud-bigquery==3.45.0`
  - `google-cloud-bigtable==2.44.0`
* **Configuration Files**: Created `.env` and `app/.env` parameterizing all service URLs and dataset IDs.

### Challenge 2.1: NL2SQL Data Agent Tool (`cymbal_analytics_tool`)
* **File**: [`app/tools/analytics_tool.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/tools/analytics_tool.py)
* **Architecture**: Direct client calling Gemini Data Analytics Chat API endpoint (`https://geminidataanalytics.googleapis.com/v1/projects/pj-elevate-da/locations/global:chat`).
* **Verbatim Prompt Passing**: Guarantees that standardized enterprise business glossary terms (e.g. *Total On-Hand Inventory*, *Estimated Cover Hours*, *Net Transaction Revenue*, *Cashier Manual Override Rate*) are preserved without keyword stripping.
* **Transient Fault Tolerance**: Implements 3 exponential backoff retries with graceful fallbacks.

### Challenge 2.2: Fine-Grained POS Manual Chunking & Stitched RAG Tool (`pos_troubleshooting_rag_tool`)
* **File**: [`app/tools/rag_tool.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/tools/rag_tool.py)
* **Re-Chunking**: Redid coarse Module 1 sections into 500-character blocks with 100-character overlap (400 step size) stored in `pj-elevate-da.cymbal_gold.pos_manual_chunk_embeddings`.
* **Dense Embeddings**: Materialized 768-dimensional embeddings using BigQuery ML model `pos_text_embedding_model` (`text-embedding-005`) with `task_type => 'RETRIEVAL_DOCUMENT'`.
* **Adjacent Context Stitching**: At query time, self-joins matched chunk $N$ to chunks $N-1$ and $N+1$ using `STRING_AGG(chunk_content, '\n' ORDER BY chunk_index ASC)` to deliver complete procedural runbooks.
* **Safety Guardrail & Full-Text Fallback**:
  - Enforces strict similarity threshold $\ge 0.70$.
  - Triggers full-text `SEARCH()` fallback on error codes if vector search drops below threshold.
  - Returns certified warning string when queries fall completely out-of-scope (e.g. Ford F-150 automotive repairs).
* **Clickable Links**: Automatically converts `gs://` URIs to HTTPS links (`https://storage.cloud.google.com/...`).

### Challenge 2.3: Cloud Bigtable MCP Microservice & Toolset (`bigtable_mcp_toolset`)
* **Configuration**: Authored [`tools.yaml`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/tools.yaml) targeting `operations-db`. Stored in Secret Manager as `bigtable-mcp-tools-secret` (v2).
* **Bigtable GoogleSQL Fix**: Addressed Bigtable `_key` typing (`BYTES` vs `STRING`) via `CAST(_key AS STRING) LIKE @prefix || '%'` and reversed timestamp ordering (`ORDER BY _key ASC`).
* **Cloud Run Deployment**: Deployed `mcp-toolbox-bigtable` in `us-central1` using image `us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest`.
* **Python Toolset Implementation**: [`app/tools/bigtable_tool.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/tools/bigtable_tool.py) implements `get_bigtable_mcp_toolset()` using ADK's `McpToolset` connecting via SSE with OIDC ID Token headers.

### Challenge 3.1: Coordinator Binding & System Prompts
* **Prompt Instructions**: [`app/prompt.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/prompt.py) details explicit intent routing rules:
  - Pattern 1: Single-tool dispatch for isolated inquiries.
  - Pattern 2: Parallel tool dispatch for intra-day risk comparison (UC 2.2).
  - Pattern 3: Sequential multi-turn dispatch for cross-cloud offender audits (UC 2.3).
* **Root Agent**: [`app/agent.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/agent.py) binds `cymbal_operations_agent` with model `gemini-3.6-flash` and exposes `root_agent`.

---

## Benchmark Validation Results (Part 4)

The test suite executed all 7 operational scenarios using `InMemoryRunner`. Results were captured in [`test_benchmark_results.json`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/test_benchmark_results.json).

### Scenario Test Matrix

| Scenario ID | Category | Operational Verification Criteria | Tool(s) Invoked | Elapsed | Result |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **UC 1.1a** | Hardware Error | Returns certified PDF link for Toshiba TCx 810 with ERR-PAY-4001 SOP | `pos_troubleshooting_rag_tool` (x2) | 31.46s | **PASS** |
| **UC 1.1c** | Out-of-Scope Hardware | Triggers similarity score fallback returning certified warning string | `pos_troubleshooting_rag_tool` | 13.26s | **PASS** |
| **UC 1.2a** | Stockout Risk (<20h) | Queries `gold_inventory_reconciliation_ledger` filtering `< 20.0` cover hours | `cymbal_analytics_tool` (x4) | 70.76s | **PASS** |
| **UC 1.3** | Real-Time Cashier Metrics | Queries Bigtable row key prefix `STORE_048#CASH_1190` for live flags | `get_cashier_realtime_metrics` | 10.91s | **PASS** |
| **UC 2.1a** | Warranty Transaction | Unnests line items and joins extracted warranty terms in BigQuery | `cymbal_analytics_tool` (x8) | 148.70s | **PASS** |
| **UC 2.2** | Dual Cashier Baseline | **Parallel Dispatch**: Calls Bigtable MCP and BigQuery concurrently in Turn 1 | `get_cashier_realtime_metrics` + `cymbal_analytics_tool` | 92.89s | **PASS** |
| **UC 2.3** | Cross-Cloud Offender Audit | **Sequential Dispatch**: GCP anomaly ranking $\rightarrow$ AWS S3 checkout logs | `cymbal_analytics_tool` (x5) + `get_cashier_realtime_metrics` | 107.01s | **PASS** |

**Final Score**: **7 / 7 (100.0%) Scenarios Verified and Passing**.

---

## Detailed Execution Traces & Verification Evidence

### 1. UC 1.1a: Hardware Error (ERR-PAY-4001 Recovery SOP)
* **Prompt**: *"What is the immediate field recovery protocol when a cashier encounters an ERR-PAY-4001 EMV contactless payment freeze, and how do we ensure the customer is not double-charged?"*
* **Tool Invocation**: `pos_troubleshooting_rag_tool({"query": "ERR-PAY-4001 EMV contactless payment freeze field recovery protocol double charge prevention"})`
* **Stitched Document Match**: `Toshiba_TCx_810_Guide.pdf` (Relevance: 0.8124 $\ge 0.70$).
* **Verified Documentation Link**: [Toshiba TCx 810 Guide](https://storage.cloud.google.com/pj-elevate-da-module1-bucket/store_pos_manual_generic/Toshiba_TCx_810_Guide.pdf)
* **Outcome**: Verified step-by-step unfreeze procedure, terminal reboot sequence, and pre-auth reversal protocol to prevent double charging.

### 2. UC 1.1c: Out-of-Scope Hardware (Safety Guardrail)
* **Prompt**: *"How do I replace the engine oil on a Ford F-150 truck?"*
* **Tool Invocation**: `pos_troubleshooting_rag_tool({"query": "How do I replace the engine oil on a Ford F-150 truck?"})`
* **Relevance Score**: Top match similarity score $< 0.42$ (below 0.70 threshold); full-text search fallback returned 0 rows.
* **Agent Response**:
  > *"Warning: No certified POS hardware troubleshooting runbook found matching query (similarity score below safety threshold of 0.7). This hardware component or issue is out-of-scope for certified store POS manuals. Please consult external maintenance or facilities support."*

### 3. UC 1.2a: Stockout Risk (<20h Cover Hours)
* **Prompt**: *"What is the estimated cover hours remaining for store inventory positions experiencing stockout risk of less than 20 hours, and what is their total on-hand inventory?"*
* **Tool Invocation**: `cymbal_analytics_tool` with verbatim prompt passing.
* **Generated GoogleSQL**:
  ```sql
  SELECT
    store_id,
    store_name,
    item_id,
    item_name,
    est_cover_hours_remaining,
    (shelf_qty + backroom_qty) AS total_on_hand_inventory
  FROM `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger`
  WHERE est_cover_hours_remaining < 20.0
  ORDER BY est_cover_hours_remaining ASC;
  ```
* **Outcome**: Verified exact filter `< 20.0`, accurate computation of total on-hand inventory ($\text{shelf} + \text{backroom}$), and prioritized risk ranking.

### 4. UC 1.3: Real-Time Cashier Metrics (Cloud Bigtable)
* **Prompt**: *"Read live 1-hour rolling metrics and audit status flags for Cashier CASH_1190 at Store 48."*
* **Tool Invocation**: `get_cashier_realtime_metrics({"prefix": "STORE_048#CASH_1190"})`
* **Retrieved Real-Time Telemetry**:
  - **Audit Status Flag**: `REVIEW` (Critical Alert)
  - **ML Fraud Risk Score**: `0.999987`
  - **1-Hour Transaction Count**: `32` transactions
  - **1-Hour Manual Overrides**: `19` overrides
  - **1-Hour Promo Discount Rate**: `65.63%`
  - **Last Checkout Recorded**: `2026-09-10 08:31:26 UTC`

### 5. UC 2.1a: Warranty Transaction & Policy Extraction
* **Prompt**: *"Check transaction details for TXN-20260312-0015811 and show the warranty coverage policy for the purchased item."*
* **Tool Invocation**: `cymbal_analytics_tool`
* **Relational Execution**: Joined `pos_transactions_gold` line items against `warranty_generic_sections_extracted` in BigQuery, extracting duration, replacement terms, accidental damage conditions, and claim procedures.

### 6. UC 2.2: Dual Cashier Baseline (Parallel Dispatch)
* **Prompt**: *"What is Cashier CASH_1190's live 1-hour override rate right now, compared to their 7-day historical override baseline?"*
* **ADK Trace Verification**:
  ```
  🔧 [TOOL CALL 1] get_cashier_realtime_metrics({"prefix": "STORE_048#CASH_1190"})
  🔧 [TOOL CALL 2] cymbal_analytics_tool({"query": "What is Cashier CASH_1190's 7-day historical manual override baseline rate?"})
  ```
* **Outcome**: Concurrently retrieved live telemetry (65.52% override rate, 19 overrides in 1 hour) and 7-day historical baseline, synthesizing an intra-day risk comparison table for Loss Prevention.

### 7. UC 2.3: Cross-Cloud Offender Audit (Sequential Multi-Turn Dispatch)
* **Prompt**: *"Show cashiers with active cashier promo abuse alerts in the last 7 days and retrieve checkout logs for the top offender."*
* **ADK Trace Verification**:
  - **Turn 1 (Discovery & Anomaly Ranking)**: `cymbal_analytics_tool` queried `pos_anomaly_alerts` and identified `CASH_1190` at `STORE_048` as the top offender.
  - **Turn 2 (Deep Checkout Audit)**: `cymbal_analytics_tool` retrieved itemized checkout records and discount amounts from federated AWS S3 (`silver_pos_transactions`) and `pos_transactions_gold`.
  - **Turn 3 (Telemetry Correlation)**: Invoked `get_cashier_realtime_metrics` to correlate historical promo abuse with active 1-hour risk score (`0.999987`) and `REVIEW` flag.

---

## Production Hardening & Advanced Security (Part 5)

1. **End-User OAuth Authentication (Delegated Access)**:
   - Implemented dynamic user/SA OAuth2 token resolution (`_get_access_token()`) in `app/tools/analytics_tool.py`, ensuring BigQuery queries execute under the caller's verified Google Cloud credentials.
2. **Query Cost & Resource Guardrails (`maximum_bytes_billed`)**:
   - Integrated `maximum_bytes_billed = 10 * 1024 * 1024 * 1024` (10 GB) query limits into BigQuery client job configurations in `app/tools/rag_tool.py` to eliminate unexpected full-table scan charges.
3. **Semantic Store Entity Resolution**:
   - Store resolution supports both informal strings ("Store 48", "store 48") and formal identifiers (`STORE_048`), normalizing them into standard Bigtable row key prefixes.
4. **Multi-Tenant Data Isolation (RLS / CLS)**:
   - Complements the Row-Level Security (RLS) policies implemented in Module 1 Lab 4 (`rls_analyst_stores`), ensuring store-level data access is enforced at the database layer.

---

## Code Assets & Artifacts Index

| Asset Path | Description |
| :--- | :--- |
| [`app/agent.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/agent.py) | Root coordinator agent definition (`cymbal_operations_agent`) |
| [`app/prompt.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/prompt.py) | System prompt, domain scopes, and intent routing protocols |
| [`app/tools/analytics_tool.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/tools/analytics_tool.py) | NL2SQL Data Agent Tool targeting global published endpoint |
| [`app/tools/rag_tool.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/tools/rag_tool.py) | Fine-grained vector search with adjacent context stitching ($N-1$ to $N+1$) |
| [`app/tools/bigtable_tool.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/app/tools/bigtable_tool.py) | Cloud Run MCP Toolbox client (`McpToolset`) via SSE with OIDC auth |
| [`tools.yaml`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/tools.yaml) | Database Toolbox configuration payload for Bigtable |
| [`test_agent_scenarios.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/test_agent_scenarios.py) | Automated test suite validating all 7 operational scenarios |
| [`test_benchmark_results.json`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/test_benchmark_results.json) | Complete JSON execution traces, latency, and status per test case |
| [`requirements.txt`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/requirements.txt) | Pinned production dependencies |
| [`.env`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/.env) | Environment variable definitions for local and container runtime |

---

## Conclusion & Next Steps

Module 3 Lab 3 is **100% complete**. All 3 toolsets have been successfully engineered, deployed, bound to the root coordinator agent, and verified against all functional requirements and business criteria.

With Module 3 Labs 1, 2, and 3 fully delivered, the **Cymbal Retail Modern Lakehouse & Agentic AI Platform** across **Module 0, Module 1, Module 2, and Module 3** is complete and operational.
