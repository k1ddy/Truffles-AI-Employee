#!/usr/bin/env python3
"""Patch system prompt in workflow and update via API"""
import json
import requests
import sys

WORKFLOW_ID = "4vaEvzlaMrgovhNz"
API_KEY = "REDACTED_JWT"
N8N_URL = "https://n8n.truffles.kz"

# 1. Download current workflow
print("Downloading current workflow...")
resp = requests.get(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY}
)
if resp.status_code != 200:
    print(f"Failed to download: {resp.status_code}")
    sys.exit(1)

workflow = resp.json()
print(f"Downloaded: {workflow.get('name')}")

# 2. Find Generate Response node and patch prompt
NEW_SECTION = """## ПЕРВОЕ СООБЩЕНИЕ (ОБЯЗАТЕЛЬНО)
Если в истории написано '(новый диалог)' — это первое сообщение клиента.
В этом случае ОБЯЗАТЕЛЬНО начни ответ с: 'Здравствуйте! Я виртуальный помощник Truffles.'
Затем сразу ответь на запрос клиента. НЕ игнорируй его вопрос.

## ДАННЫЕ"""

patched = False
for node in workflow.get('nodes', []):
    if node.get('name') == 'Generate Response':
        opts = node.get('parameters', {}).get('options', {})
        prompt = opts.get('systemMessage', '')
        
        if 'ПЕРВОЕ СООБЩЕНИЕ' in prompt:
            print("Already patched!")
            sys.exit(0)
        
        # Replace "## ДАННЫЕ" with new section
        if '## ДАННЫЕ' in prompt:
            new_prompt = prompt.replace('## ДАННЫЕ', NEW_SECTION)
            node['parameters']['options']['systemMessage'] = new_prompt
            patched = True
            print("Prompt patched!")
        break

if not patched:
    print("Could not find place to patch")
    sys.exit(1)

# 3. Upload - keep only allowed fields
allowed = ["name", "nodes", "connections", "settings", "staticData"]
clean = {k: v for k, v in workflow.items() if k in allowed}

print("Uploading patched workflow...")
resp = requests.put(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json=clean
)

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("SUCCESS!")
else:
    print(resp.text[:500])
