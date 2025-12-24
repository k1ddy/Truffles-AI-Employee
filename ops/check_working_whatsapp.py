#!/usr/bin/env python3
"""Check working Send to WhatsApp node"""
import json
import urllib.request

API_KEY = "REDACTED_JWT"

# Multi-Agent workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

for node in workflow['nodes']:
    if node['name'] == 'Send to WhatsApp':
        print("=== WORKING SEND TO WHATSAPP ===")
        print(json.dumps(node['parameters'], indent=2, ensure_ascii=False))

# Callback workflow
url = f"https://n8n.truffles.kz/api/v1/workflows/HQOWuMDIBPphC86v"
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

for node in workflow['nodes']:
    if node['name'] == 'Send Manager Reply to WhatsApp':
        print("\n=== MY SEND TO WHATSAPP ===")
        print(json.dumps(node['parameters'], indent=2, ensure_ascii=False))
