#!/usr/bin/env python3
"""Get current chunking logic from Knowledge Sync"""
import requests
import json

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "zTbaCLWLJN6vPMk4"

r = requests.get(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY}
)

workflow = r.json()
nodes = {n["name"]: n for n in workflow["nodes"]}

print("=== Parse Sections node ===")
parse_sections = nodes.get("Parse Sections", {})
code = parse_sections.get("parameters", {}).get("jsCode", "not found")
print(code)
