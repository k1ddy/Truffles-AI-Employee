#!/usr/bin/env python3
"""List recent n8n executions"""
import json
import urllib.request

url = "https://n8n.truffles.kz/api/v1/executions?limit=30"
headers = {
    "X-N8N-API-KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
}

# Workflow name mapping
WORKFLOWS = {
    "656fmXR6GPZrJbxm": "1_Webhook",
    "C38zCf2jfc2Zqfzf": "2_ChannelAdapter", 
    "DCs6AoJDIOPB4ZtF": "3_Normalize",
    "3QqFRxapNa29jODD": "4_MessageBuffer",
    "kEXEMbThwUsCJ2Cz": "5_TurnDetector",
    "4vaEvzlaMrgovhNz": "6_Multi-Agent"
}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

print(f"{'ID':<10} | {'Status':<8} | {'Workflow':<18} | {'Started':<20}")
print("-" * 70)

for e in data["data"][:25]:
    wf_id = e.get("workflowId", "")
    wf_name = WORKFLOWS.get(wf_id, wf_id[:8] if wf_id else "unknown")
    started = e.get("startedAt", "")[:19]
    print(f"{e['id']:<10} | {e['status']:<8} | {wf_name:<18} | {started}")
