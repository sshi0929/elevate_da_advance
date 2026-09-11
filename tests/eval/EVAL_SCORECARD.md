# Cymbal Operations Agent — ADK Evaluation Scorecard

- **Generated**: 2026-09-11T02:43:19+00:00
- **Eval set**: `cymbal_ops_benchmark`
- **Runner**: `tests/eval/run_eval_suite.py` (parallelism=1, in-memory sessions)
- **Config**: `tests/eval/eval_config.yaml` (single source of truth)
- **Result**: **6/7 passed (85.7%)** in 1053.0s

## Scorecard

| Case | Tier | hallucinations_v1 | rubric_based_tool_use_quality_v1 | final_response_match_v2 | Result |
| :--- | :--- | ---: | ---: | ---: | :--- |
| `UC_1.3_real-time_cashier_metrics` | livedata | 1.0000 | 1.0000 | — | ✅ PASS |
| `UC_2.2_dual_cashier_baseline_parallel_dispatch` | livedata | 1.0000 | 0.7500 | — | ✅ PASS |
| `UC_1.1a_hardware_error` | reference | 0.4194 | — | 1.0000 | ❌ FAILED |
| `UC_1.1c_out-of-scope_hardware` | reference | 1.0000 | — | 1.0000 | ✅ PASS |
| `UC_1.2a_stockout_risk_lt_20h` | reference | 0.8182 | — | 1.0000 | ✅ PASS |
| `UC_2.1a_warranty_transaction` | reference | 1.0000 | — | 1.0000 | ✅ PASS |
| `UC_2.3_cross-cloud_offender_audit_sequential_dispatch` | reference | 0.9167 | — | 1.0000 | ✅ PASS |

## Grading policy

| Tier | Cases | Metrics | Rationale |
| :--- | ---: | :--- | :--- |
| `reference` | 5 | `final_response_match_v2` >= 0.7, `hallucinations_v1` >= 0.6 | Deterministic cases. The backing BigQuery tables and RAG corpora are static, so the golden final_response stays a valid reference answer and can be graded by a reference-based judge. |
| `livedata` | 2 | `hallucinations_v1` >= 0.6, `rubric_based_tool_use_quality_v1` >= 0.7 | Cases that read the 1-hour rolling Cloud Bigtable window (operations-db:cashier_realtime_alerts). Any frozen golden answer expires within the hour, so these are graded reference-free: faithfulness to the tool output actually returned, plus rubric-scored tool selection and argument correctness. |

> [!NOTE]
> All metrics are ADK-native (`PrebuiltMetrics`). The judge model is pinned to `gemini-3.8-flash` in both generated config files, overriding ADK's obsolete `gemini-2.5-flash` default (`eval_metrics.py:85`).
