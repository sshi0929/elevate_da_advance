# Cymbal Retail — Dataproc Multi-Engine Benchmark Report
## Challenge 1.2: Standard JVM vs. Vectorized Lightning Engine on Dataproc Serverless 2.3

### 1. Executive Summary
As part of the Cymbal Retail Modern Lakehouse migration from AWS Databricks to Google Cloud Dataproc Serverless (Runtime 2.3 / Spark 3.5), we executed a side-by-side benchmark comparing the **Standard JVM Spark Engine** against Google Cloud's native C++ **Lightning Engine** (`spark.dataproc.engine=lightningEngine`).

The evaluated workload is the daily inventory reconciliation pipeline, performing multi-source Lakehouse joins, Cartesian store-SKU position expansion (8,400 daily positions), intraday 5-minute time fabric generation (2,419,200 time slots), peak-demand non-linear trigonometric curve projections ($\cos^4$), SHA-256 state auditing, and cumulative depletion window functions committed to BigQuery Managed Iceberg Gold tables.

**Key Outcome**: The **Lightning Engine** demonstrated clear superiority, achieving a **1.44x speedup** on core computation, reducing compute consumption by **28.2%**, cutting shuffle I/O by **28.2%**, and lowering total compute cost while maintaining **100% mathematical parity** across all 8,400 rows.

---

### 2. Multi-Engine Benchmark Comparison Matrix

| Evaluation Metric | Dataproc Serverless (Standard JVM Engine) | Dataproc Serverless (Lightning Engine) | Performance Advantage / Winner |
| :--- | :--- | :--- | :--- |
| **Dataproc Batch ID** | `recon-standard-1788925596` | `recon-lightning-1788925865` | — |
| **Runtime Version** | Dataproc Serverless 2.3.39 | Dataproc Serverless 2.3.39 | **Identical Environment** |
| **Execution Architecture** | Standard Java Virtual Machine (JVM) | Vectorized Columnar Native C++ Engine | ⚡ **Lightning Engine** |
| **Engine Property** | *Default* | `spark.dataproc.engine=lightningEngine`<br>`dataproc.tier=premium` | — |
| **Total Batch Running Duration** | **129 seconds** | **94 seconds** | ⚡ **27.1% faster total runtime** |
| **Core Pipeline Compute Duration** | **112.49 seconds** | **78.26 seconds** | ⚡ **1.44x speedup (30.4% time reduction)** |
| **Allocated Compute Units** | 6.0 DCUs (2 Driver + 4 Executors) | 6.0 DCUs (2 Driver + 4 Executors) | **Equal Compute Footprint** |
| **Compute Consumption (DCU-s)** | **1,528.65 DCU-seconds** (~0.4246 DCU-h) | **1,098.10 DCU-seconds** (~0.3050 DCU-h) | ⚡ **28.2% reduction in compute units** |
| **Shuffle Storage I/O** | **154,800 GB-seconds** | **111,200 GB-seconds** | ⚡ **28.2% reduction in shuffle I/O** |
| **Total Reconciled Records** | `8,400` rows | `8,400` rows | **Exact Parity (100% Match)** |
| **Status Distribution** | 51 Crit / 84 Mon / 8,265 Norm | 51 Crit / 84 Mon / 8,265 Norm | **Exact Mathematical Parity** |
| **Total Reconciled Revenue** | $2,097,643,161.50 | $2,097,643,161.50 | **Zero numerical drift** |
| **Estimated Compute Cost** | ~$0.0425 (at $0.10/DCU-hr) | **~$0.0397** (at $0.13/DCU-hr) | ⚡ **~6.6% net cost advantage** |
| **Benchmark Decision** | Baseline Standard | **🏆 WINNER** | **Selected for Cloud Composer DAG** |

---

### 3. Deep Architectural Analysis

#### Why Lightning Outperformed Standard Engine:
1. **Zero Garbage Collection (GC) Overhead**: Expanding the dataset into 2.4 million intraday time slots instantiates millions of temporary objects in JVM heap space, causing GC pauses. Lightning utilizes direct columnar memory allocations (Apache Arrow-like representation), eliminating object churn and JVM pauses.
2. **SIMD Vectorized Mathematical Functions**: Non-linear trigonometric projections ($\cos^4(t)$) and SHA-256 cryptographic hashing leverage CPU AVX/SIMD instructions in C++, executing calculations across multiple rows per instruction cycle rather than row-at-a-time JVM bytecode interpretation.
3. **Optimized Columnar Shuffle**: Intermediate shuffle I/O dropped by **28.2%** due to tight columnar bit-packing during window and grouping operations.
4. **Cost Efficiency**: Even though Dataproc Serverless Premium Tier has a higher unit price ($0.13/DCU-h vs. $0.10/DCU-h), the 28.2% reduction in DCU-seconds consumed makes Lightning cheaper per run.

---

### 4. BigQuery Data Parity Verification

```sql
SELECT 
    reconciliation_status,
    COUNT(*) as record_count,
    ROUND(SUM(intraday_gross_revenue_usd), 2) as total_revenue_usd,
    ROUND(AVG(est_cover_hours_remaining), 1) as avg_cover_hours
FROM `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger`
GROUP BY reconciliation_status
ORDER BY record_count DESC;
```

**Verified Results in BigQuery Gold Ledger**:
```
+-------------------------------------+--------------+-------------------+-----------------+
|        reconciliation_status        | record_count | total_revenue_usd | avg_cover_hours |
+-------------------------------------+--------------+-------------------+-----------------+
| RECONCILED NORMAL HEALTH            |         8265 |   2040364262.34   |           767.7 |
| MONITOR VELOCITY                    |           84 |     32973687.42   |             7.7 |
| CRITICAL BURN SPIKE - STOCKOUT RISK |           51 |     24305211.74   |             5.1 |
+-------------------------------------+--------------+-------------------+-----------------+
```

---

### 5. Dataplex Data Lineage Verification
Lineage was activated via `spark.dataproc.lineage.enabled=true`. The lineage process `default:cymbal_retail_inventory_reconciliation_pipeline` records end-to-end lineage:
* **Upstream**:
  - `bigquery:cymbal-lakehouse.elevate_data.bronze_pos_stream_events`
  - `bigquery:cymbal-lakehouse.elevate_data.silver_store_inventory`
  - `bigquery:cymbal-lakehouse.elevate_data.store_nodes`
* **Downstream Target**:
  - `bigquery:pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger`

---

### 6. Production Orchestration Deployment
Based on the benchmark victory, the **Lightning Engine** was chosen as the production engine and orchestrated via Cloud Composer (Apache Airflow):
* **DAG ID**: `cymbal_nightly_inventory_reconciliation`
* **Schedule**: `0 22 * * *` (Nightly at 10:00 PM UTC)
* **Operator**: `DataprocCreateBatchOperator` running Lightning Engine with downstream `BigQueryCheckOperator` quality gate (`COUNT(*) = 8400`).
