#!/usr/bin/env python3
"""Update all modified workflows via n8n API"""
import json
import requests

API_KEY = "REDACTED_JWT"
N8N_URL = "https://n8n.truffles.kz"

workflows = [
    ("656fmXR6GPZrJbxm", "1_Webhook_656fmXR6GPZrJbxm.json"),
    ("C38zCf2jfc2Zqfzf", "2_ChannelAdapter_C38zCf2jfc2Zqfzf.json"),
    ("3QqFRxapNa29jODD", "4_MessageBuffer_3QqFRxapNa29jODD.json"),
    ("4vaEvzlaMrgovhNz", "6_Multi-Agent_4vaEvzlaMrgovhNz.json"),
]

allowed = ["name", "nodes", "connections", "settings", "staticData"]

for workflow_id, filename in workflows:
    print(f"\nUpdating {filename}...")
    try:
        with open(f"/home/zhan/truffles/ops/{filename}") as f:
            workflow = json.load(f)
        
        clean = {k: v for k, v in workflow.items() if k in allowed}
        
        resp = requests.put(
            f"{N8N_URL}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
            json=clean
        )
        
        print(f"  Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"  Error: {resp.text[:200]}")
    except Exception as e:
        print(f"  Failed: {e}")

print("\nDone!")
