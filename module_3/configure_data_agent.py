import urllib.request
import json
import subprocess
import time
import urllib.error

PROJECT_ID = "pj-elevate-da"
LOCATION = "global"
AGENT_ID = "cymbal-retail-analytics-data-agent"

# Obtain ADC token
token = subprocess.check_output([
    '/usr/local/google/home/watanabesei/google-cloud-sdk/bin/gcloud',
    'auth', 'application-default', 'print-access-token'
]).decode().strip()

agent_url = f"https://geminidataanalytics.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/dataAgents/{AGENT_ID}?updateMask=display_name,description,data_analytics_agent.staging_context,data_analytics_agent.published_context"

system_instruction = """You are the Cymbal Retail Analytics Data Agent, an expert conversational AI data analyst specializing in retail analytics, inventory optimization, cashier audit, and customer warranty triage. You operate strictly over Google Cloud BigQuery and federated AWS S3 datasets: `pj-elevate-da.cymbal_gold`, `pj-elevate-da.module1_unstructureddata`, and `pj-elevate-da.cymbal-lakehouse.elevate_data`.

### Table Selection Matrix
- **Intraday Sales Checkouts**: Query `pj-elevate-da.cymbal_gold.pos_transactions_gold`. Filter for today's transactions (`business_date = CURRENT_DATE()`) unless a specific date range is requested.
- **Past Purchase Lookup & Warranty Claims**: Query `pj-elevate-da.cymbal_gold.historical_transactional_data`. The items are stored in repeated record array `tx.items`, requiring `UNNEST(tx.items) AS item`.
- **Cashier Promo Abuse Audits**: Query `pj-elevate-da.cymbal_gold.pos_anomaly_alerts`. Filter by `alert_type = 'cashier_promo_abuse'` within a dynamic 7-day timestamp window (`alert_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)`) unless specified otherwise.
- **Cross-Cloud Offender Checkout Logs**: Query federated AWS S3 Iceberg table `pj-elevate-da.cymbal-lakehouse.elevate_data.silver_pos_transactions` via BigLake connector.
- **Store Inventory & Cover Hours**: Query `pj-elevate-da.cymbal_gold.gold_inventory_reconciliation_ledger`. Total on-hand inventory is calculated as `(shelf_qty + backroom_qty)`. Filter for `est_cover_hours_remaining < 20.0` ONLY when stockout risk or critical cover hours are explicitly requested.
- **Warranty Policy Terms**: Query `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted` for warranty durations, service levels, coverage scopes, and exclusions.

### Warranty Triage Methodology (UC 2.1)
When triaging customer warranty claims:
1. Locate purchase facts in `pj-elevate-da.cymbal_gold.historical_transactional_data` by transaction ID (`tx.transaction_id = ...`) or customer ID (`tx.customer_id = ...`).
2. Flatten the item array using `UNNEST(tx.items) AS item` and join with policy terms in `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted warr` on `item.item_id = warr.product_id`.
3. Assess active coverage by comparing elapsed time `DATE_DIFF(CURRENT_DATE(), tx.business_date, MONTH)` against `warr.warranty_duration_months`.

### Cross-Cloud Audit Methodology (UC 2.3)
When conducting cashier fraud and promo abuse audits across clouds:
1. **Step 1 (GCP BigQuery Offender Ranking)**: Query `pj-elevate-da.cymbal_gold.pos_anomaly_alerts` where `alert_type = 'cashier_promo_abuse'` over the last 7 days, group by `store_id` and `cashier_id`, count alerts, average risk scores, and rank descending to identify the top offender.
2. **Step 2 (AWS S3 Federated Audit)**: Query `pj-elevate-da.cymbal-lakehouse.elevate_data.silver_pos_transactions` filtering directly by the identified offending `cashier_id` (e.g. `CASH_1164`) to inspect the raw transaction logs stored in AWS S3.

### Governance & Output Standards
- **Read-Only**: Generate strictly SELECT statements. Never produce DDL, DML, DROP, or INSERT statements.
- **Limiting & Ranking**: Append `LIMIT 20` (or `LIMIT 10` for single offender transactions) to multi-row list queries. Order by gross revenue (`intraday_gross_revenue_usd DESC`), risk score (`risk_score DESC`), or cover hours (`est_cover_hours_remaining ASC`)."""

tables = [
    {"projectId": PROJECT_ID, "datasetId": "cymbal_gold", "tableId": "pos_transactions_gold"},
    {"projectId": PROJECT_ID, "datasetId": "cymbal_gold", "tableId": "pos_anomaly_alerts"},
    {"projectId": PROJECT_ID, "datasetId": "cymbal_gold", "tableId": "gold_inventory_reconciliation_ledger"},
    {"projectId": PROJECT_ID, "datasetId": "cymbal_gold", "tableId": "historical_transactional_data"},
    {"projectId": PROJECT_ID, "datasetId": "module1_unstructureddata", "tableId": "warranty_generic_sections_extracted"},
    {"projectId": PROJECT_ID, "datasetId": "cymbal-lakehouse.elevate_data", "tableId": "silver_pos_transactions"}
]

example_queries = [
    {
        "naturalLanguageQuestion": "What is the estimated cover hours remaining for store inventory positions experiencing stockout risk of less than 20 hours, and what is their total on-hand inventory?",
        "sqlQuery": """SELECT
  store_id,
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
ORDER BY intraday_gross_revenue_usd DESC, est_cover_hours_remaining ASC
LIMIT 20;"""
    },
    {
        "naturalLanguageQuestion": "Check transaction details for TXN-20260312-0015811 and show the warranty coverage policy for the purchased item.",
        "sqlQuery": """SELECT
  tx.transaction_id,
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
LIMIT 1;"""
    },
    {
        "naturalLanguageQuestion": "Customer CUST_00386 purchased an item at Store 9 using a Gift Card.. Is their item covered under warranty?",
        "sqlQuery": """SELECT
  tx.transaction_id,
  tx.business_date,
  tx.customer_id,
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
  warr.support_url,
  CASE
    WHEN DATE_DIFF(CURRENT_DATE(), tx.business_date, MONTH) <= warr.warranty_duration_months THEN 'COVERED'
    ELSE 'EXPIRED'
  END AS warranty_status
FROM `pj-elevate-da.cymbal_gold.historical_transactional_data` tx,
UNNEST(tx.items) AS item
JOIN `pj-elevate-da.module1_unstructureddata.warranty_generic_sections_extracted` warr
  ON item.item_id = warr.product_id
WHERE tx.customer_id = 'CUST_00386'
ORDER BY tx.business_date DESC
LIMIT 1;"""
    },
    {
        "naturalLanguageQuestion": "Show cashiers with active cashier promo abuse alerts in the last 7 days and rank the top offending cashiers.",
        "sqlQuery": """SELECT
  store_id,
  cashier_id,
  COUNT(alert_id) AS alert_count,
  ROUND(AVG(risk_score), 4) AS avg_risk_score,
  MAX(risk_score) AS max_risk_score,
  MAX(alert_ts) AS latest_alert_ts
FROM `pj-elevate-da.cymbal_gold.pos_anomaly_alerts`
WHERE alert_type = 'cashier_promo_abuse'
  AND alert_ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY store_id, cashier_id
ORDER BY alert_count DESC, avg_risk_score DESC
LIMIT 20;"""
    },
    {
        "naturalLanguageQuestion": "Retrieve historical checkout transaction logs for top promo abuse offender Cashier CASH_1164.",
        "sqlQuery": """SELECT
  transaction_id,
  event_timestamp,
  store_id,
  pos_terminal_id,
  cashier_id,
  payment_method,
  total_amount_usd
FROM `pj-elevate-da.cymbal-lakehouse.elevate_data`.silver_pos_transactions
WHERE cashier_id = 'CASH_1164'
ORDER BY event_timestamp ASC
LIMIT 10;"""
    }
]

glossary_terms = [
    {
        "displayName": "Net Transaction Revenue",
        "description": "Net sales transaction revenue after subtracting discounts and refunds."
    },
    {
        "displayName": "Estimated Inventory Cover Hours",
        "description": "Number of operational hours remaining until stockout given the current sales velocity and on-hand inventory."
    },
    {
        "displayName": "Cashier Promo Override Rate",
        "description": "Percentage of transactions where cashier manual promotional overrides were triggered."
    },
    {
        "displayName": "Total On-Hand Inventory",
        "description": "Sum of shelf inventory units and backroom storage units: shelf_qty + backroom_qty."
    },
    {
        "displayName": "Warranty Policy Duration",
        "description": "Duration of active OEM manufacturer warranty coverage in months: warranty_duration_months."
    },
    {
        "displayName": "Shelf Stock Ratio",
        "description": "[Definition]: Percentage of total on-hand store inventory units placed on retail sales floor shelves. - Target Table: gold_inventory_reconciliation_ledger - Calculation Formula: SAFE_DIVIDE(shelf_qty, (shelf_qty + backroom_qty)) * 100"
    }
]

context = {
    "systemInstruction": system_instruction,
    "datasourceReferences": {
        "bq": {
            "tableReferences": tables
        }
    },
    "exampleQueries": example_queries,
    "glossaryTerms": glossary_terms
}

update_payload = {
    "name": f"projects/{PROJECT_ID}/locations/{LOCATION}/dataAgents/{AGENT_ID}",
    "displayName": "Cymbal Retail Analytics Data Agent",
    "description": "Conversational data agent for Cymbal Retail modern lakehouse analytics, inventory cover hours, warranty triage, and cross-cloud audits.",
    "dataAnalyticsAgent": {
        "stagingContext": context,
        "publishedContext": context
    }
}

print(f"Sending PATCH request to {agent_url}...")
req = urllib.request.Request(
    agent_url,
    data=json.dumps(update_payload).encode('utf-8'),
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    method='PATCH'
)

try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print("Update LRO initiated:", res.get("name"))
        op_name = res.get("name")
        if op_name:
            op_url = f"https://geminidataanalytics.googleapis.com/v1/{op_name}"
            op_req = urllib.request.Request(op_url, headers={'Authorization': f'Bearer {token}'})
            for i in range(15):
                time.sleep(2)
                with urllib.request.urlopen(op_req) as op_resp:
                    op_data = json.loads(op_resp.read().decode())
                    print(f"Polling LRO {i}: done={op_data.get('done', False)}")
                    if op_data.get('done'):
                        print("Successfully updated and published Data Agent!")
                        break
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code, e.read().decode())
except Exception as e:
    print("ERROR:", e)
