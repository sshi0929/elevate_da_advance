#!/usr/bin/env python3
"""Builds ADK Golden EvalSet from verified benchmark test scenarios."""

import json
import os
import time
from google.adk.evaluation.eval_case import (
    EvalCase,
    SessionInput,
    Invocation,
    IntermediateData,
)
from google.adk.evaluation.eval_set import EvalSet
from google.genai import types as genai_types

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "test_benchmark_results.json")
APP_DIR = os.path.join(os.path.dirname(__file__), "app")

with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
    benchmark_data = json.load(f)

eval_cases = []

for item in benchmark_data:
    case_id = f"{item['id']}_{item['category'].lower().replace(' ', '_').replace('(', '').replace(')', '').replace('<', 'lt_')}"
    prompt_text = item["prompt"]
    final_text = item.get("final_text", "")
    tool_calls = item.get("tool_calls", [])

    # Map tool calls to FunctionCall objects
    expected_tool_calls = []
    for tc in tool_calls:
        tool_name = tc.get("name", "")
        tool_args = tc.get("args", {})
        expected_tool_calls.append(
            genai_types.FunctionCall(
                name=tool_name,
                args=tool_args,
            )
        )

    # Build typed Invocation
    invocation = Invocation(
        invocation_id=f"turn_1_{item['id'].lower()}",
        user_content=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=prompt_text)],
        ),
        final_response=genai_types.Content(
            role="model",
            parts=[genai_types.Part.from_text(text=final_text)],
        ),
        intermediate_data=IntermediateData(
            tool_uses=expected_tool_calls,
            intermediate_responses=[],
        ),
        creation_timestamp=time.time(),
    )

    eval_case = EvalCase(
        eval_id=case_id,
        session_input=SessionInput(
            app_name="app",
            user_id="store_manager",
            state={},
        ),
        conversation=[invocation],
        creation_timestamp=time.time(),
    )
    eval_cases.append(eval_case)

# Create EvalSet
eval_set = EvalSet(
    eval_set_id="cymbal_ops_benchmark",
    name="Cymbal Retail Unified Operations & Risk Benchmark",
    description="7-scenario operational evaluation suite covering POS hardware diagnostics, out-of-scope guardrails, stockout risk analytics, real-time Bigtable cashier metrics, warranty joins, parallel dispatch baselines, and sequential cross-cloud audits.",
    eval_cases=eval_cases,
    creation_timestamp=time.time(),
)

# Output paths
evalset_path_named = os.path.join(APP_DIR, "cymbal_ops_benchmark.evalset.json")
evalset_path_default = os.path.join(APP_DIR, "eval_set_1.evalset.json")

# Write named evalset
with open(evalset_path_named, "w", encoding="utf-8") as f:
    f.write(eval_set.model_dump_json(indent=2))

# Also update eval_set_1 so both are populated
eval_set_1 = EvalSet(
    eval_set_id="eval_set_1",
    name="eval_set_1",
    description="Cymbal Retail Unified Operations & Risk Benchmark",
    eval_cases=eval_cases,
    creation_timestamp=time.time(),
)
with open(evalset_path_default, "w", encoding="utf-8") as f:
    f.write(eval_set_1.model_dump_json(indent=2))

print(f"Successfully generated {len(eval_cases)} eval cases into:")
print(f"1. {evalset_path_named}")
print(f"2. {evalset_path_default}")
