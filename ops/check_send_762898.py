#!/usr/bin/env python3
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762898?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

data = d.get("data", {})
result_data = data.get("resultData", {})
run_data = result_data.get("runData", {})

# Find all Send nodes
send_nodes = [name for name in run_data.keys() if "Send" in name]
print(f"Send nodes: {send_nodes}")

for node_name in send_nodes:
    print(f"\n=== {node_name} ===")
    node = run_data[node_name][0]
    
    # Get the HTTP request that was made
    # Check if there's inputOverride or execution data
    exec_data = node.get("executionData", {})
    if exec_data:
        print(f"Execution data: {json.dumps(exec_data, indent=2)[:500]}")

# Check what data flows into Send Response
if "Send Response" in run_data:
    node = run_data["Send Response"][0]
    source = node.get("source", [])
    print(f"\nSend Response source: {source}")

# Check Save Trace - it has phone and response
if "Save Trace" in run_data:
    items = run_data["Save Trace"][0]["data"]["main"][0]
    if items:
        # Usually Save Trace comes after Send, check source data
        pass

# Check Prepare Response
if "Prepare Response" in run_data:
    items = run_data["Prepare Response"][0]["data"]["main"][0]
    if items:
        j = items[0]["json"]
        print(f"\n=== Prepare Response output ===")
        print(f"remoteJid: {j.get('remoteJid')}")
        print(f"phone: {j.get('phone')}")
        print(f"response: {j.get('response', '')[:50]}...")

# Check Parse Input
if "Parse Input" in run_data:
    items = run_data["Parse Input"][0]["data"]["main"][0]
    if items:
        j = items[0]["json"]
        print(f"\n=== Parse Input ===")
        print(f"remoteJid: {j.get('remoteJid')}")
        print(f"phone: {j.get('phone')}")
        print(f"client_slug: {j.get('client_slug')}")
