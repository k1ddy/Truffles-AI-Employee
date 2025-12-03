import json
import subprocess
import os

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY0MTkzNjI5fQ.I06M9VWLgBkZKCk14CqahwM3ntuvUn_VcA9XzEHQV0Q"
BASE_URL = "https://n8n.truffles.kz/api/v1/workflows"
OUTPUT_DIR = r"C:\Users\user\Downloads\TrufflesDocs\n8n_workflows"

os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(r'C:\Users\user\Downloads\TrufflesDocs\workflows_list.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

workflows = data.get('data', [])

for w in workflows:
    wid = w['id']
    name = w['name'].replace('/', '_').replace('\\', '_').replace(' ', '_')
    filename = f"{name}_{wid}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    url = f"{BASE_URL}/{wid}"
    cmd = ['curl.exe', '-s', '-H', f'X-N8N-API-KEY: {API_KEY}', url, '-o', filepath]
    
    result = subprocess.run(cmd, capture_output=True)
    
    if result.returncode == 0 and os.path.exists(filepath):
        print(f"OK: {filename}")
    else:
        print(f"FAIL: {name}")

print(f"\nВсего скачано: {len(os.listdir(OUTPUT_DIR))}")
