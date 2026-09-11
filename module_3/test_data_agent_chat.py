import urllib.request
import json
import subprocess
import time
import urllib.error

PROJECT_ID = "pj-elevate-da"
LOCATION = "global"
AGENT_ID = "cymbal-retail-analytics-data-agent"

token = subprocess.check_output([
    '/usr/local/google/home/watanabesei/google-cloud-sdk/bin/gcloud',
    'auth', 'application-default', 'print-access-token'
]).decode().strip()

chat_url = f"https://geminidataanalytics.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}:chat"

prompts = [
    ("UC 1.2 Inventory Stockout Analysis", "What is the estimated cover hours remaining for store inventory positions experiencing stockout risk of less than 20 hours, and what is their total on-hand inventory?"),
    ("UC 2.1 Warranty Lookup by Txn ID", "Check transaction details for TXN-20260312-0015811 and show the warranty coverage policy for the purchased item."),
    ("UC 2.3 Step 1 Top Offending Cashiers", "Show cashiers with active cashier promo abuse alerts in the last 7 days and rank the top offending cashiers."),
    ("UC 2.3 Step 2 Cross-Cloud AWS S3 Checkout", "Retrieve historical checkout transaction logs for top promo abuse offender Cashier CASH_1164.")
]

for title, prompt in prompts:
    print(f"\n=======================================================")
    print(f"Testing: {title}")
    print(f"Prompt: {prompt}")
    print(f"=======================================================")

    payload = {
        'parent': f'projects/{PROJECT_ID}/locations/{LOCATION}',
        'dataAgentContext': {
            'dataAgent': f'projects/{PROJECT_ID}/locations/{LOCATION}/dataAgents/{AGENT_ID}',
            'contextVersion': 'PUBLISHED'
        },
        'messages': [
            {
                'userMessage': {
                    'text': prompt
                }
            }
        ]
    }

    req = urllib.request.Request(
        chat_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(f"Status: {resp.status}")
            generated_queries = []
            agent_responses = []
            for item in data:
                sys_msg = item.get('systemMessage', {})
                parts = sys_msg.get('text', {}).get('parts', [])
                if len(parts) >= 2 and parts[0] == "Running a query":
                    generated_queries.append(parts[1])
                user_msg = item.get('modelMessage', {}) or item.get('userMessage', {})
                # check for model generated text
                if 'modelMessage' in item:
                    model_parts = item['modelMessage'].get('text', {}).get('parts', [])
                    agent_responses.extend(model_parts)
                if 'generatedQuery' in item:
                    generated_queries.append(item['generatedQuery'].get('query', ''))

            if generated_queries:
                for q in generated_queries:
                    print(f"Generated SQL:\n{q.strip()}\n")
            else:
                print("No explicit SQL query extracted. Raw items count:", len(data))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(2)
