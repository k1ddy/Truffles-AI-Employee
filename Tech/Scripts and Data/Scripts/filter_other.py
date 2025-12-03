import json
import os
import shutil

WORKFLOWS_DIR = r"C:\Users\user\Downloads\TrufflesDocs\n8n_workflows"
TARGET_DIR = r"C:\Users\user\Downloads\TrufflesDocs\n8n-other-workflows"

copied = []
for filename in os.listdir(WORKFLOWS_DIR):
    if not filename.endswith('.json'):
        continue
    
    filepath = os.path.join(WORKFLOWS_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    name = data.get('name', '')
    tags = data.get('tags', [])
    tag_names = [t.get('name', '') for t in tags]
    
    # Exclude truffles-chatbot and 5_ClassifyIntent
    if 'truffles-chatbot' not in tag_names and name != '5_ClassifyIntent':
        shutil.copy(filepath, TARGET_DIR)
        copied.append(filename)
        print(f"OK: {filename}")

print(f"\nTotal: {len(copied)} workflows")
