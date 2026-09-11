"""Cymbal Retail Unified Operations & Risk Coordinator Agent.

Decoupled 3-toolset ADK Coordinator Agent binding:
1. cymbal_analytics_tool (NL2SQL Data Agent Tool)
2. pos_troubleshooting_rag_tool (BigQuery VECTOR_SEARCH + Stitched Runbooks)
3. bigtable_mcp_toolset (Cloud Bigtable MCP Microservice on Cloud Run)
"""

import os
from google.adk.agents import Agent
from app.prompt import SYSTEM_INSTRUCTION
from app.tools.analytics_tool import cymbal_analytics_tool
from app.tools.rag_tool import pos_troubleshooting_rag_tool
from app.tools.bigtable_tool import get_bigtable_mcp_toolset, read_cashier_realtime_metrics

# Model selection: gemini-3.6-flash as required by Challenge 3.1
MODEL_NAME = os.getenv("COORDINATOR_MODEL", "gemini-3.8-flash")

# Instantiate Cloud Run MCP toolset
bigtable_mcp_toolset = get_bigtable_mcp_toolset()

# Define root coordinator agent
cymbal_operations_agent = Agent(
    name="cymbal_operations_agent",
    description="Cymbal Retail Unified Operations & Risk Coordinator Agent orchestrating relational analytics, POS runbooks, and real-time cashier risk intelligence.",
    model=MODEL_NAME,
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        cymbal_analytics_tool,
        pos_troubleshooting_rag_tool,
        bigtable_mcp_toolset,
        read_cashier_realtime_metrics,
    ],
)

root_agent = cymbal_operations_agent
