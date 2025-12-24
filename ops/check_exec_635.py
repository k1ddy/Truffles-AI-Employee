#!/usr/bin/env python3
import json
import urllib.request

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/executions/763635?includeData=true"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

run_data = data.get('data', {}).get('resultData', {}).get('runData', {})

print("=== FIND HANDOVER DATA OUTPUT ===")
if 'Find Handover Data' in run_data:
    out = run_data['Find Handover Data'][-1].get('data', {}).get('main', [[]])
    if out and out[0]:
        print(json.dumps(out[0][0].get('json', {}), indent=2))

print("\n=== SEND WHATSAPP ERROR ===")
if 'Send Manager Reply to WhatsApp' in run_data:
    error = run_data['Send Manager Reply to WhatsApp'][-1].get('error', {})
    print(json.dumps(error, indent=2, ensure_ascii=False, default=str)[:1000])
