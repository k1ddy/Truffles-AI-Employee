#!/usr/bin/env python3
"""Get raw execution data"""
import json
import urllib.request
import sys

API_KEY = "REDACTED_JWT"
EXEC_ID = sys.argv[1] if len(sys.argv) > 1 else "763373"

url = f"https://n8n.truffles.kz/api/v1/executions/{EXEC_ID}"
headers = {"X-N8N-API-KEY": API_KEY}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
