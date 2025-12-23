#!/usr/bin/env python3
"""Find WhatsApp send nodes in workflows"""
import json
import urllib.request

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

# Check Multi-Agent for WhatsApp send
for wf_id, name in [("4vaEvzlaMrgovhNz", "Multi-Agent"), ("7jGZrdbaAAvtTnQX", "Escalation")]:
    url = f"https://n8n.truffles.kz/api/v1/workflows/{wf_id}"
    headers = {"X-N8N-API-KEY": API_KEY}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        workflow = json.loads(response.read().decode())
    
    print(f"\n=== {name} ===")
    for node in workflow['nodes']:
        node_name = node['name'].lower()
        if 'whatsapp' in node_name or 'send' in node_name or 'response' in node_name:
            print(f"\nNode: {node['name']} ({node['type']})")
            params = node.get('parameters', {})
            # Show relevant params
            if 'url' in params:
                print(f"  URL: {params['url'][:100]}...")
            if 'query' in params:
                print(f"  SQL: {params['query'][:100]}...")

# Check client_settings structure
print("\n=== CLIENT_SETTINGS COLUMNS ===")
import subprocess
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-c',
     "SELECT column_name FROM information_schema.columns WHERE table_name='client_settings' ORDER BY ordinal_position;"],
    capture_output=True, text=True
)
print(result.stdout)
