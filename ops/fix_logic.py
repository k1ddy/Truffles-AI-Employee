#!/usr/bin/env python3
"""
1. Remove auto-close from monitor (only reminders)
2. Fix timeout history - only show if no resolved after timeout
3. Set timeouts to 1/2 min for testing
"""

import json
import requests

API_KEY = 'REDACTED_JWT'

# ==================== 1. Fix Monitor - remove auto-close ====================
print("=== 1. Removing auto-close from 10_Handover_Monitor ===")

resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY}
)
data = resp.json()
nodes = data['nodes']
connections = data['connections']

# Update Decide Action to only return reminder_1 and reminder_2, no auto_close
for node in nodes:
    if node['name'] == 'Decide Action':
        node['parameters']['jsCode'] = """const handovers = $input.all();
const results = [];

for (const item of handovers) {
  const h = item.json;
  const minutes = Math.floor(h.minutes_waiting || 0);
  const timeout1 = h.reminder_timeout_1 || 30;
  const timeout2 = h.reminder_timeout_2 || 60;
  
  let action = 'none';
  
  // Второе напоминание (СРОЧНО)
  if (minutes >= timeout2 && !h.reminder_2_sent_at) {
    action = 'reminder_2';
  }
  // Первое напоминание
  else if (minutes >= timeout1 && !h.reminder_1_sent_at) {
    action = 'reminder_1';
  }
  // Нет автозакрытия - заявка висит пока менеджер не ответит
  
  if (action !== 'none') {
    results.push({
      json: {
        ...h,
        action,
        minutes_waiting: minutes
      }
    });
  }
}

return results;"""
        print("  Updated Decide Action - removed auto_close")
        break

# Update Action Switch - remove auto_close output
for node in nodes:
    if node['name'] == 'Action Switch':
        rules = node['parameters']['rules']['values']
        # Keep only reminder_1 and reminder_2
        new_rules = [r for r in rules if any(
            c.get('rightValue') in ['reminder_1', 'reminder_2'] 
            for c in r.get('conditions', {}).get('conditions', [])
        )]
        node['parameters']['rules']['values'] = new_rules
        print("  Updated Action Switch - removed auto_close rule")
        break

# Update connections - remove auto_close path
if 'Action Switch' in connections:
    main = connections['Action Switch']['main']
    # Keep only first 2 outputs (reminder_1, reminder_2)
    connections['Action Switch']['main'] = main[:2] if len(main) > 2 else main
    print("  Updated Action Switch connections")

resp = requests.put(
    'https://n8n.truffles.kz/api/v1/workflows/ZRcuYYCv1o9B0MyY',
    headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
    json={'name': data['name'], 'nodes': nodes, 'connections': connections, 'settings': data.get('settings', {})}
)
print(f"  Status: {resp.status_code}")

# ==================== 2. Fix History Logic ====================
print("\n=== 2. Fixing timeout history logic in 8_Telegram_Adapter ===")

# Find workflow
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
workflows = resp.json()['data']
adapter_id = None
for w in workflows:
    if '8_Telegram_Adapter' in w['name']:
        adapter_id = w['id']
        break

if adapter_id:
    resp = requests.get(
        f'https://n8n.truffles.kz/api/v1/workflows/{adapter_id}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    data = resp.json()
    nodes = data['nodes']
    
    # Update Check Previous Timeout query - only show if no resolved AFTER timeout
    for node in nodes:
        if node['name'] == 'Check Previous Timeout':
            node['parameters']['query'] = """SELECT 
  t.user_message as prev_message,
  t.resolved_at as timeout_at,
  EXTRACT(EPOCH FROM (NOW() - t.resolved_at)) / 3600 as hours_ago
FROM handovers t
JOIN conversations c ON c.id = t.conversation_id
WHERE c.id = '{{ $json.conversation_id }}'
  AND t.status = 'timeout'
  AND t.resolved_at > NOW() - INTERVAL '24 hours'
  -- Проверяем что ПОСЛЕ этого timeout не было resolved заявки
  AND NOT EXISTS (
    SELECT 1 FROM handovers r 
    WHERE r.conversation_id = t.conversation_id 
      AND r.status = 'resolved'
      AND r.resolved_at > t.resolved_at
  )
ORDER BY t.resolved_at DESC
LIMIT 1;"""
            print("  Updated Check Previous Timeout - only unresolved timeouts")
            break
    
    resp = requests.put(
        f'https://n8n.truffles.kz/api/v1/workflows/{adapter_id}',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json={'name': data['name'], 'nodes': nodes, 'connections': data['connections'], 'settings': data.get('settings', {})}
    )
    print(f"  Status: {resp.status_code}")

print("\n=== Done ===")
print("- Auto-close removed")
print("- History only shows if timeout was NOT followed by resolved")
