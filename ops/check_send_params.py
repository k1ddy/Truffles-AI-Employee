#!/usr/bin/env python3
import requests
import json

API_KEY = "REDACTED_JWT"

# Get latest Multi-Agent execution
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions?workflowId=4vaEvzlaMrgovhNz&limit=1",
    headers={"X-N8N-API-KEY": API_KEY}
)
exec_list = resp.json()
exec_id = exec_list["data"][0]["id"]
print(f"Checking execution {exec_id}")

resp = requests.get(
    f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Find all Send nodes
send_nodes = [name for name in run_data.keys() if "Send" in name]
print(f"\nSend nodes executed: {send_nodes}")

# Check each Send node
for node_name in send_nodes:
    print(f"\n=== {node_name} ===")
    node = run_data[node_name][0]
    
    # Check input
    try:
        # Look at the HTTP request parameters
        params = node.get("data", {}).get("main", [[]])[0]
        if params:
            j = params[0].get("json", {})
            print(f"Output keys: {list(j.keys())[:10]}")
    except:
        pass
    
    # Check source (what node it came from)
    source = node.get("source", [])
    if source:
        print(f"Source: {source[0].get('previousNode')}")

# Also check Parse Input for remoteJid
if "Parse Input" in run_data:
    items = run_data["Parse Input"][0]["data"]["main"][0]
    if items:
        j = items[0]["json"]
        print(f"\n=== Parse Input ===")
        print(f"remoteJid: {j.get('remoteJid')}")
        print(f"phone: {j.get('phone')}")

# Check Prepare Response
if "Prepare Response" in run_data:
    items = run_data["Prepare Response"][0]["data"]["main"][0]
    if items:
        j = items[0]["json"]
        print(f"\n=== Prepare Response ===")
        print(f"remoteJid: {j.get('remoteJid')}")
        print(f"phone: {j.get('phone')}")
