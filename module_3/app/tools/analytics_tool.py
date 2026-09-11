"""NL2SQL Data Agent Tool for Cymbal Retail Analytics.

Connects to the published BigQuery Conversational Data Agent:
projects/pj-elevate-da/locations/global/dataAgents/cymbal-retail-analytics-data-agent
"""

import json
import os
import time
import urllib.error
import urllib.request
import google.auth
import google.auth.transport.requests

PROJECT_ID = os.getenv("PROJECT_ID", "pj-elevate-da")
LOCATION = os.getenv("DATA_AGENT_LOCATION", "global")
DATA_AGENT_ID = os.getenv("DATA_AGENT_ID", "cymbal-retail-analytics-data-agent")
DATA_AGENT_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/dataAgents/{DATA_AGENT_ID}"
CHAT_ENDPOINT = f"https://geminidataanalytics.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}:chat"


def _get_access_token() -> str:
    """Retrieves a valid OAuth2 access token with Cloud Platform scope."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def cymbal_analytics_tool(query: str) -> str:
    """Executes conversational NL2SQL analytics against Cymbal Retail's BigQuery data warehouse and federated AWS lakehouse.

    Use this tool for:
    - Store inventory levels, stockout risks, cover hours (< 20h), on-hand inventory, and burn rates (`gold_inventory_reconciliation_ledger`).
    - Intraday transaction lookups, line items, prices, and quantities (`pos_transactions_gold`).
    - Warranty coverage duration, terms, accidental damage, and replacement policies (`warranty_generic_sections_extracted`).
    - Cashier promo abuse detection, order-level anomaly ranking (`pos_anomaly_alerts`).
    - Historical cross-cloud cashier checkout logs and transaction histories (`historical_transactional_data` / federated `silver_pos_transactions`).

    Args:
        query: Verbatim natural language analytical question. Standard enterprise terms
               (e.g., 'Total On-Hand Inventory', 'Estimated Cover Hours', 'Cashier Manual Override Rate')
               MUST be preserved without modification.

    Returns:
        Formatted analytical response from the BigQuery Data Agent.
    """
    payload = {
        "parent": f"projects/{PROJECT_ID}/locations/{LOCATION}",
        "dataAgentContext": {
            "dataAgent": DATA_AGENT_NAME,
            "contextVersion": "PUBLISHED",
        },
        "messages": [
            {
                "userMessage": {
                    "text": query
                }
            }
        ]
    }

    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            token = _get_access_token()
            req = urllib.request.Request(
                CHAT_ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))

                # Extract generated SQL queries and model messages
                generated_queries = []
                model_responses = []

                for item in data:
                    if "systemMessage" in item:
                        parts = item["systemMessage"].get("text", {}).get("parts", [])
                        if len(parts) >= 2 and parts[0] == "Running a query":
                            generated_queries.append(parts[1])
                    if "modelMessage" in item:
                        parts = item["modelMessage"].get("text", {}).get("parts", [])
                        model_responses.extend(parts)
                    if "generatedQuery" in item:
                        generated_queries.append(item["generatedQuery"].get("query", ""))

                output_parts = []
                if generated_queries:
                    output_parts.append(f"**Executed GoogleSQL:**\n```sql\n{generated_queries[0].strip()}\n```\n")
                if model_responses:
                    output_parts.append("\n".join(model_responses))
                elif not output_parts:
                    output_parts.append(f"Query completed successfully. Raw response received ({len(data)} events).")

                return "\n\n".join(output_parts)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            last_error = f"HTTP {e.code}: {err_body}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            else:
                break
        except Exception as e:
            last_error = str(e)
            time.sleep(2 ** attempt)

    return f"Error: Cymbal store and enterprise lakehouse data is currently unreachable ({last_error}). Please try again later."
