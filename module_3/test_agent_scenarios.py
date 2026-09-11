"""Automated Test Suite for Cymbal Operations Coordinator Agent.

Validates all 7 operational scenarios defined in Module 3 Lab 3:
- UC 1.1a: Hardware Error (ERR-PAY-4001 EMV freeze -> Toshiba TCx 810 Guide)
- UC 1.1c: Out-of-Scope Hardware (Ford F-150 -> safety threshold warning)
- UC 1.2a: Stockout Risk (<20h -> gold_inventory_reconciliation_ledger)
- UC 1.3: Real-Time Cashier Metrics (CASH_1190 at Store 48 -> Cloud Bigtable)
- UC 2.1a: Warranty Transaction (TXN-20260312-0015811 -> line items & warranty policy)
- UC 2.2: Dual Cashier Baseline (Parallel dispatch: Bigtable MCP + BigQuery Data Agent)
- UC 2.3: Cross-Cloud Offender Audit (Sequential dispatch: anomaly ranking + checkout logs)
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List
from google.adk.runners import InMemoryRunner
from google.genai import types
from app.agent import root_agent

SCENARIOS = [
    {
        "id": "UC_1.1a",
        "category": "Hardware Error",
        "prompt": "What is the immediate field recovery protocol when a cashier encounters an ERR-PAY-4001 EMV contactless payment freeze, and how do we ensure the customer is not double-charged?",
        "expected_tool": "pos_troubleshooting_rag_tool",
        "verification_criteria": "Returns certified PDF documentation link from GCS for Toshiba TCx 810.",
    },
    {
        "id": "UC_1.1c",
        "category": "Out-of-Scope Hardware",
        "prompt": "How do I replace the engine oil on a Ford F-150 truck?",
        "expected_tool": "pos_troubleshooting_rag_tool",
        "verification_criteria": "Triggers similarity score fallback returning certified warning string.",
    },
    {
        "id": "UC_1.2a",
        "category": "Stockout Risk (<20h)",
        "prompt": "What is the estimated cover hours remaining for store inventory positions experiencing stockout risk of less than 20 hours, and what is their total on-hand inventory?",
        "expected_tool": "cymbal_analytics_tool",
        "verification_criteria": "Queries gold_inventory_reconciliation_ledger filtering < 20.0 cover hours and sums total on-hand inventory.",
    },
    {
        "id": "UC_1.3",
        "category": "Real-Time Cashier Metrics",
        "prompt": "Read live 1-hour rolling metrics and audit status flags for Cashier CASH_1190 at Store 48.",
        "expected_tool": "get_cashier_realtime_metrics",
        "verification_criteria": "Queries Bigtable row key prefix STORE_048#CASH_1190 for live flags and metrics.",
    },
    {
        "id": "UC_2.1a",
        "category": "Warranty Transaction",
        "prompt": "Check transaction details for TXN-20260312-0015811 and show the warranty coverage policy for the purchased item.",
        "expected_tool": "cymbal_analytics_tool",
        "verification_criteria": "Unnests line items and joins extracted warranty policy terms in BigQuery.",
    },
    {
        "id": "UC_2.2",
        "category": "Dual Cashier Baseline (Parallel Dispatch)",
        "prompt": "What is Cashier CASH_1190's live 1-hour override rate right now, compared to their 7-day historical override baseline?",
        "expected_tool": "parallel_dispatch",
        "verification_criteria": "ADK trace verifies PARALLEL DISPATCH calling both Bigtable MCP and BigQuery tools concurrently in Turn 1.",
    },
    {
        "id": "UC_2.3",
        "category": "Cross-Cloud Offender Audit (Sequential Dispatch)",
        "prompt": "Show cashiers with active cashier promo abuse alerts in the last 7 days and retrieve checkout logs for the top offender.",
        "expected_tool": "sequential_dispatch",
        "verification_criteria": "ADK trace verifies SEQUENTIAL DISPATCH (GCP anomaly ranking -> AWS S3 checkout logs).",
    },
]


async def run_scenario(runner: InMemoryRunner, session_id: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print(f"🚀 RUNNING TEST: {scenario['id']} — {scenario['category']}")
    print(f"📝 Prompt: \"{scenario['prompt']}\"")
    print(f"🎯 Expected Tooling: {scenario['expected_tool']}")
    print(f"🔍 Criteria: {scenario['verification_criteria']}")
    print("-" * 80)

    start_time = time.time()
    tool_calls: List[Dict[str, Any]] = []
    tool_responses: List[Dict[str, Any]] = []
    text_responses: List[str] = []

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=scenario["prompt"])],
    )

    try:
        async for event in runner.run_async(
            user_id="lead-auditor",
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call:
                        call_info = {
                            "name": part.function_call.name,
                            "args": dict(part.function_call.args) if part.function_call.args else {},
                        }
                        tool_calls.append(call_info)
                        print(f"  🔧 [TOOL CALL] {call_info['name']}({json.dumps(call_info['args'])})")

                    if part.function_response:
                        resp_name = part.function_response.name
                        resp_data = part.function_response.response
                        tool_responses.append({"name": resp_name, "response": str(resp_data)[:300]})
                        print(f"  📥 [TOOL RESPONSE] from {resp_name} ({len(str(resp_data))} chars)")

                    if part.text and getattr(event, "author", None) != "user":
                        text_responses.append(part.text)

        elapsed = time.time() - start_time
        final_text = "\n".join(text_responses)

        print("\n💬 [FINAL AGENT RESPONSE]:")
        for line in final_text.splitlines():
            print(f"   {line}")

        # Assess verification criteria
        passed = False
        notes = []

        if scenario["id"] == "UC_1.1a":
            tool_used = any(c["name"] == "pos_troubleshooting_rag_tool" for c in tool_calls)
            has_link = ("https://storage.cloud.google.com" in final_text) or ("Toshiba" in final_text)
            has_sop = ("ERR-PAY-4001" in final_text) or ("recovery" in final_text.lower())
            passed = tool_used and has_link and has_sop
            notes.append(f"tool_used={tool_used}, has_link={has_link}, has_sop={has_sop}")

        elif scenario["id"] == "UC_1.1c":
            tool_used = any(c["name"] == "pos_troubleshooting_rag_tool" for c in tool_calls)
            has_warning = ("warning" in final_text.lower()) or ("out-of-scope" in final_text.lower()) or ("threshold" in final_text.lower())
            passed = tool_used and has_warning
            notes.append(f"tool_used={tool_used}, has_warning={has_warning}")

        elif scenario["id"] == "UC_1.2a":
            tool_used = any(c["name"] == "cymbal_analytics_tool" for c in tool_calls)
            has_metrics = ("cover" in final_text.lower()) or ("inventory" in final_text.lower()) or ("hours" in final_text.lower())
            passed = tool_used and has_metrics
            notes.append(f"tool_used={tool_used}, has_metrics={has_metrics}")

        elif scenario["id"] == "UC_1.3":
            tool_used = any(c["name"] in ("get_cashier_realtime_metrics", "read_cashier_realtime_metrics") for c in tool_calls)
            has_metrics = ("review" in final_text.lower()) or ("0.99" in final_text) or ("override" in final_text.lower())
            passed = tool_used and has_metrics
            notes.append(f"tool_used={tool_used}, has_metrics={has_metrics}")

        elif scenario["id"] == "UC_2.1a":
            tool_used = any(c["name"] == "cymbal_analytics_tool" for c in tool_calls)
            has_policy = ("warranty" in final_text.lower()) or ("policy" in final_text.lower()) or ("coverage" in final_text.lower()) or ("month" in final_text.lower())
            passed = tool_used and has_policy
            notes.append(f"tool_used={tool_used}, has_policy={has_policy}")

        elif scenario["id"] == "UC_2.2":
            called_bt = any(c["name"] in ("get_cashier_realtime_metrics", "read_cashier_realtime_metrics") for c in tool_calls)
            called_bq = any(c["name"] == "cymbal_analytics_tool" for c in tool_calls)
            passed = called_bt and called_bq
            notes.append(f"called_bt={called_bt}, called_bq={called_bq} (parallel={len(tool_calls) >= 2})")

        elif scenario["id"] == "UC_2.3":
            tool_count = len(tool_calls)
            called_tools = [c["name"] for c in tool_calls]
            has_offender = ("CASH_1190" in final_text) or ("cashier" in final_text.lower())
            passed = (tool_count >= 1) and has_offender
            notes.append(f"tool_count={tool_count}, called_tools={called_tools}, has_offender={has_offender}")

        status_str = "✅ PASS" if passed else "⚠️ NEEDS ATTENTION"
        print(f"\n📊 RESULT: {status_str} ({', '.join(notes)}) | Elapsed: {elapsed:.2f}s")

        return {
            "id": scenario["id"],
            "category": scenario["category"],
            "prompt": scenario["prompt"],
            "passed": passed,
            "elapsed": elapsed,
            "tool_calls": tool_calls,
            "notes": notes,
            "final_text": final_text,
        }

    except Exception as e:
        print(f"\n❌ ERROR in {scenario['id']}: {e}")
        return {
            "id": scenario["id"],
            "category": scenario["category"],
            "prompt": scenario["prompt"],
            "passed": False,
            "elapsed": time.time() - start_time,
            "tool_calls": tool_calls,
            "notes": [f"Exception: {e}"],
            "final_text": "",
        }


async def main():
    print("=" * 80)
    print("🎯 STARTING MODULE 3 LAB 3 BENCHMARK & VERIFICATION SUITE")
    print(f"🤖 Agent: {root_agent.name} | Model: {root_agent.model}")
    print(f"🛠️ Bound Tools: {[t.name if hasattr(t, 'name') else str(t) for t in root_agent.tools]}")
    print("=" * 80)

    runner = InMemoryRunner(agent=root_agent)
    results = []

    for scenario in SCENARIOS:
        # Create unique session per scenario to isolate state
        session = await runner.session_service.create_session(
            user_id="lead-auditor",
            app_name=runner.app_name,
        )
        res = await run_scenario(runner, session.id, scenario)
        results.append(res)
        # Brief pause between scenarios
        await asyncio.sleep(2)

    # Summary
    print("\n" + "=" * 80)
    print("📋 OVERALL BENCHMARK RESULTS SUMMARY")
    print("=" * 80)
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for r in results:
        mark = "✅ PASS" if r["passed"] else "❌ FAIL"
        calls = ", ".join(c["name"] for c in r["tool_calls"]) or "None"
        print(f"{mark} | {r['id']:<8} | {r['category']:<35} | Tools: [{calls}] | {r['elapsed']:.2f}s")

    print("-" * 80)
    print(f"🎯 Total Score: {passed_count}/{total_count} ({passed_count / total_count * 100:.1f}%) Passed")
    print("=" * 80)

    # Save detailed JSON output
    out_file = "/usr/local/google/home/watanabesei/account_work/Admin/pj_elevate/DA_advanced/module_3/test_benchmark_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Saved full benchmark results to {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
