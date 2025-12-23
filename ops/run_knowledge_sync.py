#!/usr/bin/env python3
"""Trigger Knowledge Sync workflow execution"""
import requests

WORKFLOW_ID = "zTbaCLWLJN6vPMk4"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
N8N_URL = "https://n8n.truffles.kz"

# Execute workflow via executions endpoint
resp = requests.post(
    f"{N8N_URL}/api/v1/executions",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json={"workflowId": WORKFLOW_ID}
)

print(f"Status: {resp.status_code}")
print(resp.text[:1000] if resp.text else "No response")
