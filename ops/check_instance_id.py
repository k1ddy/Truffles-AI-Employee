#!/usr/bin/env python3
"""Find where instance_id comes from"""
import json
import urllib.request
import subprocess

API_KEY = "REDACTED_JWT"

url = f"https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz"
headers = {"X-N8N-API-KEY": API_KEY}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as response:
    workflow = json.loads(response.read().decode())

# Search for instance_id in all nodes
print("=== NODES WITH instance_id ===")
for node in workflow['nodes']:
    params = json.dumps(node.get('parameters', {}))
    if 'instance_id' in params.lower():
        print(f"\n{node['name']}:")
        if 'jsCode' in node.get('parameters', {}):
            code = node['parameters']['jsCode']
            for line in code.split('\n'):
                if 'instance_id' in line.lower():
                    print(f"  {line.strip()}")

# Check clients table
print("\n=== CLIENTS TABLE ===")
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-c',
     "SELECT column_name FROM information_schema.columns WHERE table_name='clients' ORDER BY ordinal_position;"],
    capture_output=True, text=True
)
print(result.stdout)

# Check client data
print("=== CLIENT DATA ===")
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', 'n8n', '-d', 'chatbot', '-c',
     "SELECT id, name, slug, instance_id FROM clients;"],
    capture_output=True, text=True
)
print(result.stdout)
