"""Cloud Bigtable MCP Toolset for Cymbal Retail Cashier Risk Intelligence.

Connects to the deployed Cloud Run MCP Toolbox microservice:
https://mcp-toolbox-bigtable-15183141503.us-central1.run.app/mcp/sse
querying live 1-hour rolling metrics and audit flags in operations-db:cashier_realtime_alerts.
"""

import json
import os
import re
import struct
from typing import Any, Dict
import google.auth
from google.auth import impersonated_credentials
import google.auth.transport.requests
from google.cloud import bigtable
from google.cloud.bigtable.row_set import RowSet
from google.adk.tools.mcp_tool import McpToolset, SseConnectionParams

BIGTABLE_MCP_URL = os.getenv(
    "BIGTABLE_MCP_URL",
    "https://mcp-toolbox-bigtable-15183141503.us-central1.run.app"
)
PROJECT_ID = os.getenv("PROJECT_ID", "pj-elevate-da")
BIGTABLE_INSTANCE = os.getenv("BIGTABLE_INSTANCE", "operations-db")
BIGTABLE_TABLE = os.getenv("BIGTABLE_TABLE", "cashier_realtime_alerts")
TARGET_SA = f"cymbal-sa-data@{PROJECT_ID}.iam.gserviceaccount.com"


def _get_mcp_auth_token() -> str:
    """Generates a Google Cloud OIDC ID token for the Cloud Run MCP service."""
    try:
        base_creds, _ = google.auth.default()
        sa_creds = impersonated_credentials.Credentials(
            source_credentials=base_creds,
            target_principal=TARGET_SA,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        id_creds = impersonated_credentials.IDTokenCredentials(
            target_credentials=sa_creds,
            target_audience=BIGTABLE_MCP_URL,
        )
        auth_req = google.auth.transport.requests.Request()
        id_creds.refresh(auth_req)
        return id_creds.token
    except Exception as e:
        print(f"Warning: Failed to acquire OIDC ID token for Cloud Run MCP service: {e}")
        return ""


def get_bigtable_mcp_toolset() -> McpToolset:
    """Instantiates the ADK McpToolset bound to the Cloud Run Database Toolbox microservice."""
    token = _get_mcp_auth_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    connection_params = SseConnectionParams(
        url=f"{BIGTABLE_MCP_URL}/mcp/sse",
        headers=headers,
        timeout=30.0,
    )
    return McpToolset(connection_params=connection_params)


def read_cashier_realtime_metrics(store_id: str, cashier_id: str) -> str:
    """Reads live 1-hour rolling cashier fraud metrics and audit status flags from Cloud Bigtable.

    Use this tool to inspect real-time cashier behavior at a specific store:
    - 1-hour rolling manual override count
    - 1-hour rolling promo discount rate
    - Total 1-hour transaction volume
    - Real-time ML fraud risk score (0.0 to 1.0)
    - Operational audit status flag ('clear' vs 'review')
    - Timestamp of the most recent checkout event

    Args:
        store_id: Store number or ID (e.g. 'STORE_048', '48', 'Store 48').
        cashier_id: Cashier identifier (e.g. 'CASH_1190', '1190').

    Returns:
        Formatted summary of live 1-hour operational metrics and audit status.
    """
    # Normalize store_id and cashier_id into row key prefix STORE_XXX#CASH_YYYY
    store_num = re.sub(r"[^0-9]", "", str(store_id))
    cashier_num = re.sub(r"[^0-9]", "", str(cashier_id))
    norm_store = f"STORE_{int(store_num):03d}" if store_num else str(store_id)
    norm_cashier = f"CASH_{cashier_num}" if cashier_num else str(cashier_id)
    prefix = f"{norm_store}#{norm_cashier}"

    # Try direct Bigtable SDK read for maximum speed & resilience, fallback to structured output
    try:
        client = bigtable.Client(project=PROJECT_ID, admin=False)
        instance = client.instance(BIGTABLE_INSTANCE)
        table = instance.table(BIGTABLE_TABLE)

        row_set = RowSet()
        row_set.add_row_range_with_prefix(prefix)
        rows = list(table.read_rows(row_set=row_set, limit=5))

        if not rows:
            return (
                f"No active real-time events found in Cloud Bigtable for {norm_cashier} at {norm_store} "
                f"(prefix: `{prefix}`). Cashier may be currently offline or has no checkouts in the last hour."
            )

        # First row is the most recent (reversed timestamp)
        r = rows[0]
        audit_status_cell = r.cells.get("flags", {}).get(b"audit_status", [None])[0]
        audit_status = audit_status_cell.value.decode("utf-8") if audit_status_cell else "unknown"

        stats = r.cells.get("stats", {})

        def get_f64(col: str) -> float:
            c = stats.get(col.encode("utf-8"))
            return struct.unpack(">d", c[0].value)[0] if c else 0.0

        def get_i64(col: str) -> int:
            c = stats.get(col.encode("utf-8"))
            return struct.unpack(">q", c[0].value)[0] if c else 0

        def get_str(col: str) -> str:
            c = stats.get(col.encode("utf-8"))
            return c[0].value.decode("utf-8") if c else ""

        risk_score = get_f64("risk_score")
        overrides = get_i64("cashier_1h_manual_override_count")
        promo_rate = get_f64("cashier_1h_promo_rate")
        txn_count = get_i64("cashier_1h_txn_count")
        last_event_ts = get_str("last_event_ts")

        status_badge = "🚨 CRITICAL REVIEW REQUIRED" if audit_status == "review" else "✅ CLEAR / NORMAL"

        return (
            f"### Live 1-Hour Rolling Cashier Metrics (Cloud Bigtable)\n"
            f"- **Target Cashier:** `{norm_cashier}` at `{norm_store}`\n"
            f"- **Audit Status Flag:** `{audit_status.upper()}` ({status_badge})\n"
            f"- **Real-Time Fraud Risk Score:** `{risk_score:.6f}`\n"
            f"- **1-Hour Manual Overrides:** `{overrides}` overrides\n"
            f"- **1-Hour Promo Discount Rate:** `{promo_rate * 100:.2f}%`\n"
            f"- **1-Hour Total Transactions:** `{txn_count}` checkouts\n"
            f"- **Last Checkout Event Recorded:** `{last_event_ts}`\n"
            f"- **Bigtable Instance / Table:** `{BIGTABLE_INSTANCE}` / `{BIGTABLE_TABLE}`\n"
        )
    except Exception as e:
        return f"Error reading live cashier metrics from Bigtable for {prefix}: {e}"
