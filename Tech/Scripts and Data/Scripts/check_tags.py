import json
import os

WORKFLOWS_DIR = r"C:\Users\user\Downloads\TrufflesDocs\n8n_workflows"

for filename in os.listdir(WORKFLOWS_DIR):
    if filename.endswith('.json'):
        filepath = os.path.join(WORKFLOWS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        name = data.get('name', 'N/A')
        tags = data.get('tags', [])
        tag_names = [t.get('name', '') for t in tags] if tags else ['(no tags)']
        
        print(f"{name}: {', '.join(tag_names)}")
