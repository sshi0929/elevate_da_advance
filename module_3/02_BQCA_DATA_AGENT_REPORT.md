# Module 3 Lab 2: BigQuery Conversational Data Agent (BQCA) Verification Report

**Project**: `pj-elevate-da` (`15183141503`)  
**Data Agent ID**: `cymbal-retail-analytics-data-agent`  
**Display Name**: `Cymbal Retail Analytics Data Agent`  
**Resource Name**: `projects/pj-elevate-da/locations/global/dataAgents/cymbal-retail-analytics-data-agent`  
**Location**: `global` (Explicitly configured to eliminate mTLS / regional endpoint routing errors)  
**Publication Status**: **Published** (`publishedContext` active and live in production)  
**BigQuery Studio Console URL**: [Data Agents Dashboard](https://console.cloud.google.com/bigquery/data-agents?project=pj-elevate-da)

---

## 🏛️ Executive Summary

In Module 3 Lab 2, we provisioned, configured, and verified the **BigQuery Conversational Data Agent (BQCA)** for Cymbal Retail. The agent enables natural language analytical querying (NL2SQL) across conformed gold retail datasets, AI-extracted unstructured warranty policies, and federated AWS S3 Iceberg tables via BigLake.

All 5 core lab challenges were completed, automated, and validated with **100% exact SQL match** against the lab reference benchmarks:
1. **Challenge 1.1 (Provisioning & Scoping)**: Agent created with `global` location scoped across 6 tables in 3 datasets.
2. **Challenge 2.1 (System Instructions)**: 5-section governance instruction implemented covering table routing, warranty triage (UC 2.1), cross-cloud audit (UC 2.3), and safety guardrails.
3. **Challenge 3.1 (Golden Queries)**: 5 verified GoogleSQL golden query pairs registered for few-shot prompt grounding.
4. **Challenge 4.1 & 4.2 (Glossary Terms)**: 6 enterprise business metrics defined and linked (including custom metric `Shelf Stock Ratio`).
5. **Challenge 5.1 (Interactive Validation)**: Live execution via Gemini Data Analytics Chat API (`:chat`) tested across all benchmark prompts, achieving 100% parity with expected reference SQL.

---

## 📊 Data Asset Scope (6 Tables Verified)

| Table Full Identifier | Storage Layer | Role / Intent | Verified Rows |
| :--- | :--- | :--- | :--- |
| `pj-elevate-da.cymbal_gold.pos_transactions_gold` | BigQuery Managed Table | Real-time intraday POS sales transactions | **15,046** |
| `pj-elevate-da.cymbal_gold.pos_anomaly_alerts` | BigQuery Managed Table | Real-time ML anomaly and promo abuse alerts | **1,296** |
| `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger` | BigQuery Managed Iceberg Table | Daily store inventory reconciliation & cover hours | **8,400** |
| `pj-elevate-da.cymbal_gold.historical_transactional_data` | BigQuery Managed Table | Past customer transaction records with nested items array | **22,390** |
| `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted` | BigQuery Managed Table | Gemini-extracted unstructured warranty terms & policies | **26** |
| `pj-elevate-da.cymbal-lakehouse.elevate_data.silver_pos_transactions` | AWS S3 via BigLake REST Catalog | Cross-cloud Iceberg POS checkout ledger | **90,816** |

---

## 🎯 Verification Benchmark Results (100% Parity)

### 1. UC 1.2 Store Inventory Stockout Analysis
* **User Prompt**:  
  `"What is the estimated cover hours remaining for store inventory positions experiencing stockout risk of less than 20 hours, and what is their total on-hand inventory?"`
* **Agent Generated SQL**:
```sql
SELECT store_id,
       store_name,
       city,
       item_id,
       shelf_qty,
       backroom_qty,
       (shelf_qty + backroom_qty) AS total_on_hand_inventory,
       intraday_gross_revenue_usd,
       est_cover_hours_remaining,
       reconciliation_status
FROM `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger`
WHERE est_cover_hours_remaining < 20.0
ORDER BY intraday_gross_revenue_usd DESC,
         est_cover_hours_remaining ASC
LIMIT 20;
```
* **Evaluation**: **PASS (100% exact match)**. Correct table selection, calculated column `(shelf_qty + backroom_qty)`, filtering `< 20.0`, and revenue/cover hours ranking.

---

### 2. UC 2.1 Past Warranty Lookup by Transaction ID
* **User Prompt**:  
  `"Check transaction details for TXN-20260312-0015811 and show the warranty coverage policy for the purchased item."`
* **Agent Generated SQL**:
```sql
SELECT tx.transaction_id,
       tx.business_date,
       tx.customer_loyalty_tier,
       tx.store_id,
       tx.payment_method,
       item.item_id AS product_id,
       item.item_name AS product_name,
       item.unit_price,
       warr.warranty_duration_months,
       warr.service_level,
       warr.coverage_scope_details,
       warr.exclusions_and_limitations,
       warr.official_retailer_guarantee_and_sla,
       warr.support_url
FROM `pj-elevate-da.cymbal_gold.historical_transactional_data` tx,
     UNNEST(tx.items) AS item
JOIN `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted` warr 
  ON item.item_id = warr.product_id
WHERE tx.transaction_id = 'TXN-20260312-0015811'
LIMIT 1;
```
* **Evaluation**: **PASS (100% exact match)**. Unnests repeated `tx.items` record array, joins on `product_id`, projects all warranty SLA and policy attributes.

---

### 3. UC 2.3 Step 1 Top Offending Cashiers Ranking (GCP BigQuery)
* **User Prompt**:  
  `"Show cashiers with active cashier promo abuse alerts in the last 7 days and rank the top offending cashiers."`
* **Agent Generated SQL**:
```sql
SELECT store_id,
       cashier_id,
       COUNT(alert_id) AS alert_count,
       ROUND(AVG(risk_score), 4) AS avg_risk_score,
       MAX(risk_score) AS max_risk_score,
       MAX(alert_ts) AS latest_alert_ts
FROM `pj-elevate-da.cymbal_gold.pos_anomaly_alerts`
WHERE alert_type = 'cashier_promo_abuse'
  AND alert_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY store_id,
         cashier_id
ORDER BY alert_count DESC,
         avg_risk_score DESC
LIMIT 20;
```
* **Evaluation**: **PASS (100% exact match)**. Aggregates alerts, dynamically bounds to 7-day interval, groups by cashier and store, ranks by alert count and risk score.

---

### 4. UC 2.3 Step 2 Cross-Cloud AWS S3 Checkout Audit
* **User Prompt**:  
  `"Retrieve historical checkout transaction logs for top promo abuse offender Cashier CASH_1164."`
* **Agent Generated SQL**:
```sql
SELECT transaction_id,
       event_timestamp,
       store_id,
       pos_terminal_id,
       cashier_id,
       payment_method,
       total_amount_usd
FROM `pj-elevate-da.cymbal-lakehouse.elevate_data`.silver_pos_transactions
WHERE cashier_id = 'CASH_1164'
ORDER BY event_timestamp ASC
LIMIT 10;
```
* **Evaluation**: **PASS (100% exact match)**. Directly queries the federated AWS S3 Iceberg table via BigLake REST Catalog for cashier `CASH_1164`.

---

## 🗂️ Delivered Code & Configuration Artifacts

- [`module_3/configure_data_agent.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/configure_data_agent.py): Automation script provisioning, configuring, and publishing the Data Agent via `geminidataanalytics.googleapis.com/v1`.
- [`module_3/test_data_agent_chat.py`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/test_data_agent_chat.py): End-to-end chat test runner executing natural language prompts against the live Data Agent.
- [`module_3/02_BQCA_DATA_AGENT_REPORT.md`](file:///usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/02_BQCA_DATA_AGENT_REPORT.md): This verification report.
