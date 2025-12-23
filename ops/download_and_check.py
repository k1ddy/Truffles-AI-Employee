#!/usr/bin/env python3
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "zTbaCLWLJN6vPMk4"

url = f'https://n8n.truffles.kz/api/v1/workflows/{WORKFLOW_ID}'
headers = {'X-N8N-API-KEY': API_KEY}
response = requests.get(url, headers=headers)
data = response.json()

print("Status:", response.status_code)

# Find Get Active Clients node and show query
for node in data.get('nodes', []):
    name = node.get('name', '')
    if 'Active Clients' in name or 'query' in str(node.get('parameters', {})):
        params = node.get('parameters', {})
        if 'query' in params:
            print(f"\nNode: {name}")
            print(f"Query: {params['query'][:400]}")
