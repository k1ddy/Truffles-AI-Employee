#!/usr/bin/env python3
"""Get current chunking logic from Knowledge Sync"""
import requests
import json

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"
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
