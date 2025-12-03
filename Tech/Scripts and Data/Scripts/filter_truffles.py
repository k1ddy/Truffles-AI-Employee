import json
import os
import shutil

WORKFLOWS_DIR = r"C:\Users\user\Downloads\TrufflesDocs\n8n_workflows"
TARGET_DIR = r"C:\Users\user\Downloads\TrufflesDocs\Truffles-Chat-Bot\truffles-chatbot-v1"

# Clear target directory
for f in os.listdir(TARGET_DIR):
    os.remove(os.path.join(TARGET_DIR, f))

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
    
    # Include if has truffles-chatbot tag OR is 5_ClassifyIntent
    if 'truffles-chatbot' in tag_names or name == '5_ClassifyIntent':
        shutil.copy(filepath, TARGET_DIR)
        copied.append(filename)
        print(f"OK: {filename}")

print(f"\nTotal: {len(copied)} workflows")
