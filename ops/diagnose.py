#!/usr/bin/env python3
"""
БЫСТРАЯ ДИАГНОСТИКА
Запуск: python3 ~/truffles/ops/diagnose.py

Показывает:
- Последние executions всех ключевых workflows
- Состояние conversations
- Состояние handovers
"""
import json
import urllib.request
import subprocess

API_KEY = "REDACTED_JWT"

WORKFLOWS = {
    "Multi-Agent": "4vaEvzlaMrgovhNz",
    "Escalation Handler": "7jGZrdbaAAvtTnQX",
    "Telegram Adapter": "fFPEbTNlkBSjo66A",
    "Telegram Callback": "HQOWuMDIBPphC86v"
}

def get_executions(workflow_id, limit=2):
    url = f"https://n8n.truffles.kz/api/v1/executions?workflowId={workflow_id}&limit={limit}"
    headers = {"X-N8N-API-KEY": API_KEY}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode()).get('data', [])

def get_execution_error(exec_id):
    url = f"https://n8n.truffles.kz/api/v1/executions/{exec_id}?includeData=true"
    headers = {"X-N8N-API-KEY": API_KEY}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        error = data.get('data', {}).get('resultData', {}).get('error', {})
        if error:
            return f"{error.get('message', '')} @ {error.get('node', {}).get('name', 'unknown') if isinstance(error.get('node'), dict) else error.get('node', 'unknown')}"
    return None

print("=" * 60)
print("ДИАГНОСТИКА TRUFFLES")
print("=" * 60)

# 1. Executions
print("\n📊 ПОСЛЕДНИЕ EXECUTIONS:")
print("-" * 40)
for name, wf_id in WORKFLOWS.items():
    execs = get_executions(wf_id)
    if execs:
        latest = execs[0]
        status_icon = "✅" if latest['status'] == 'success' else "❌"
        print(f"{status_icon} {name}: {latest['status']}")
        if latest['status'] == 'error':
            error = get_execution_error(latest['id'])
            if error:
                print(f"   └── {error[:60]}")

# 2. Database state
print("\n📁 БАЗА ДАННЫХ:")
print("-" * 40)

# Conversations
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN bot_status='muted' THEN 1 END) as muted, COUNT(telegram_topic_id) as with_topic FROM conversations;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Conversations: {parts[0].strip()} total, {parts[1].strip()} muted, {parts[2].strip()} with topic")

# Handovers
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN status='pending' THEN 1 END) as pending, COUNT(CASE WHEN status='active' THEN 1 END) as active FROM handovers;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Handovers: {parts[0].strip()} total, {parts[1].strip()} pending, {parts[2].strip()} active")

print("\n" + "=" * 60)
print("Для деталей execution: python3 ~/truffles/ops/get_exec_detail.py EXEC_ID")
print("=" * 60)
