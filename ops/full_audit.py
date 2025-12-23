#!/usr/bin/env python3
"""Full system audit - complete picture"""

import json
import requests
import subprocess
import re

API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4'

print("=" * 70)
print("ПОЛНЫЙ АУДИТ СИСТЕМЫ TRUFFLES")
print("=" * 70)

# ============================================================
# 1. ALL WORKFLOWS
# ============================================================
print("\n" + "=" * 70)
print("1. ВСЕ WORKFLOWS")
print("=" * 70)

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
workflows = resp.json()['data']

active_workflows = []
for w in sorted(workflows, key=lambda x: x['name']):
    status = "ACTIVE" if w['active'] else "inactive"
    print(f"  {w['name']}: {status} ({w['id']})")
    if w['active']:
        active_workflows.append(w)

# ============================================================
# 2. MAIN MESSAGE FLOW
# ============================================================
print("\n" + "=" * 70)
print("2. ОСНОВНОЙ FLOW СООБЩЕНИЙ")
print("=" * 70)

flow_order = [
    '1_Webhook',
    '2_ChannelAdapter', 
    '3_Normalize',
    '4_MessageBuffer',
    '5_TurnDetector',
    '6_Multi-Agent'
]

print("\nПуть сообщения клиента:")
print("  WhatsApp → 1_Webhook → 2_ChannelAdapter → 3_Normalize")
print("  → 4_MessageBuffer → 5_TurnDetector → 6_Multi-Agent → WhatsApp")
print("\nЭскалация:")
print("  6_Multi-Agent → 7_Escalation_Handler → 8_Telegram_Adapter → Telegram")
print("\nОтвет менеджера:")
print("  Telegram → 9_Telegram_Callback → WhatsApp")
print("\nМониторинг:")
print("  10_Handover_Monitor (каждые 5 мин) → напоминания")

# ============================================================
# 3. DATABASE TABLES
# ============================================================
print("\n" + "=" * 70)
print("3. БАЗА ДАННЫХ")
print("=" * 70)

tables_sql = """
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
"""

result = subprocess.run([
    'docker', 'exec', '-i', 'truffles_postgres_1',
    'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-c', tables_sql
], capture_output=True, text=True)

tables = [t.strip() for t in result.stdout.strip().split('\n') if t.strip()]
print(f"\nТаблицы ({len(tables)}):")
for t in tables:
    print(f"  - {t}")

# Get columns for key tables
key_tables = ['conversations', 'handovers', 'messages', 'users', 'client_settings']
for table in key_tables:
    if table in tables:
        cols_sql = f"""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        ORDER BY ordinal_position;
        """
        result = subprocess.run([
            'docker', 'exec', '-i', 'truffles_postgres_1',
            'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-c', cols_sql
        ], capture_output=True, text=True)
        print(f"\n  {table}:")
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    print(f"    {parts[0]}: {parts[1]}")

# ============================================================
# 4. STATE CHECKS - где проверяется состояние
# ============================================================
print("\n" + "=" * 70)
print("4. ПРОВЕРКИ СОСТОЯНИЙ")
print("=" * 70)

state_patterns = [
    'bot_status',
    'bot_muted',
    'no_count',
    'status',
    'is_muted',
    'handover',
    'active',
    'pending',
    'resolved'
]

print("\nГде проверяется состояние:")

for w in workflows:
    resp = requests.get(
        f"https://n8n.truffles.kz/api/v1/workflows/{w['id']}",
        headers={'X-N8N-API-KEY': API_KEY}
    )
    data = resp.json()
    if 'nodes' not in data:
        continue
    
    workflow_checks = []
    for node in data['nodes']:
        params_str = json.dumps(node.get('parameters', {}))
        for pattern in state_patterns:
            if pattern in params_str.lower():
                workflow_checks.append(f"{node['name']}: {pattern}")
                break
    
    if workflow_checks:
        print(f"\n  {w['name']}:")
        for check in workflow_checks[:5]:  # limit to 5
            print(f"    - {check}")

# ============================================================
# 5. EXTERNAL DEPENDENCIES
# ============================================================
print("\n" + "=" * 70)
print("5. ВНЕШНИЕ ЗАВИСИМОСТИ")
print("=" * 70)

print("""
  - WhatsApp (Evolution API): отправка/получение сообщений
  - Telegram Bot API: эскалации, callbacks
  - Qdrant: vector search для knowledge base
  - PostgreSQL: хранение данных
  - OpenRouter/Anthropic: LLM для ответов
""")

# ============================================================
# 6. CURRENT DATA STATE
# ============================================================
print("\n" + "=" * 70)
print("6. ТЕКУЩЕЕ СОСТОЯНИЕ ДАННЫХ")
print("=" * 70)

stats_sql = """
SELECT 
  (SELECT COUNT(*) FROM conversations) as conversations,
  (SELECT COUNT(*) FROM handovers) as handovers,
  (SELECT COUNT(*) FROM handovers WHERE status = 'pending') as pending_handovers,
  (SELECT COUNT(*) FROM handovers WHERE status = 'active') as active_handovers,
  (SELECT COUNT(*) FROM messages) as messages,
  (SELECT COUNT(*) FROM conversations WHERE bot_status = 'muted') as muted_conversations;
"""

result = subprocess.run([
    'docker', 'exec', '-i', 'truffles_postgres_1',
    'psql', '-U', 'n8n', '-d', 'chatbot', '-t', '-c', stats_sql
], capture_output=True, text=True)

print(f"\nСтатистика:")
print(result.stdout)

# ============================================================
# 7. KNOWN ISSUES
# ============================================================
print("\n" + "=" * 70)
print("7. ИЗВЕСТНЫЕ ПРОБЛЕМЫ")
print("=" * 70)

print("""
  1. Дублирование сообщений в БД
  2. Закрепление не уходит после [Решено]
  3. Mute на время вместо явного состояния
  4. no_count вместо проверки активной заявки
  5. Бот может ответить после эскалации (race condition)
""")

# ============================================================
# 8. BROKEN REFERENCES
# ============================================================
print("\n" + "=" * 70)
print("8. СЛОМАННЫЕ ССЫЛКИ В WORKFLOWS")
print("=" * 70)

pattern = r"\$\(['\"]([^'\"]+)['\"]\)"
all_broken = []

for w in workflows:
    resp = requests.get(
        f"https://n8n.truffles.kz/api/v1/workflows/{w['id']}",
        headers={'X-N8N-API-KEY': API_KEY}
    )
    data = resp.json()
    if 'nodes' not in data:
        continue
    
    node_names = set(n['name'] for n in data['nodes'])
    
    for node in data['nodes']:
        params_str = json.dumps(node.get('parameters', {}))
        refs = re.findall(pattern, params_str)
        for ref in set(refs):
            if ref not in node_names:
                all_broken.append(f"{w['name']}: {node['name']} -> {ref}")

if all_broken:
    for b in all_broken:
        print(f"  BROKEN: {b}")
else:
    print("  Нет сломанных ссылок")

print("\n" + "=" * 70)
print("АУДИТ ЗАВЕРШЁН")
print("=" * 70)
