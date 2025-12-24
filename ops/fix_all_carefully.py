#!/usr/bin/env python3
"""
Careful fix with verification:
1. Decide Action - check reminder_1 BEFORE reminder_2
2. Send Escalation - add [Решено] button
3. Action Switch[answered] -> Resolve Handover
"""

import json
import requests

API_KEY = 'REDACTED_JWT'

def backup_and_update(workflow_id, name, modifier_func):
    """Get workflow, backup, modify, update"""
    resp = requests.get(
        f'https://n8n.truffles.kz/api/v1/workflows/{workflow_id}',
        headers={'X-N8N-API-KEY': API_KEY}
    )
    if resp.status_code != 200:
        print(f"  ERROR getting {name}: {resp.status_code}")
        return False
    
    data = resp.json()
    
    # Backup
    with open(f'/home/zhan/truffles/ops/backup_{name}.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  Backup saved: backup_{name}.json")
    
    # Modify
    if not modifier_func(data):
        print(f"  No changes needed for {name}")
        return True
    
    # Update
    resp = requests.put(
        f'https://n8n.truffles.kz/api/v1/workflows/{workflow_id}',
        headers={'X-N8N-API-KEY': API_KEY, 'Content-Type': 'application/json'},
        json={
            'name': data['name'],
            'nodes': data['nodes'],
            'connections': data['connections'],
            'settings': data.get('settings', {})
        }
    )
    if resp.status_code == 200:
        print(f"  SUCCESS: {name} updated")
        return True
    else:
        print(f"  ERROR: {resp.status_code} - {resp.text[:200]}")
        return False

# ==================== 1. Fix Monitor ====================
print("=== 1. Fixing 10_Handover_Monitor (reminder order) ===")

def fix_monitor(data):
    for node in data['nodes']:
        if node['name'] == 'Decide Action':
            # Check reminder_1 FIRST, then reminder_2
            node['parameters']['jsCode'] = """const handovers = $input.all();
const results = [];

for (const item of handovers) {
  const h = item.json;
  const minutes = Math.floor(h.minutes_waiting || 0);
  const timeout1 = h.reminder_timeout_1 || 30;
  const timeout2 = h.reminder_timeout_2 || 60;
  
  let action = 'none';
  
  // СНАЧАЛА проверяем reminder_1
  if (minutes >= timeout1 && !h.reminder_1_sent_at) {
    action = 'reminder_1';
  }
  // ПОТОМ проверяем reminder_2 (только если reminder_1 уже отправлен)
  else if (minutes >= timeout2 && h.reminder_1_sent_at && !h.reminder_2_sent_at) {
    action = 'reminder_2';
  }
  
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
            print("  Fixed: Decide Action (reminder_1 before reminder_2)")
            return True
    return False

backup_and_update('ZRcuYYCv1o9B0MyY', '10_Monitor', fix_monitor)

# ==================== 2. Fix Telegram Adapter ====================
print("\n=== 2. Fixing 8_Telegram_Adapter (add [Решено] button) ===")

# Find adapter workflow
resp = requests.get(
    'https://n8n.truffles.kz/api/v1/workflows',
    headers={'X-N8N-API-KEY': API_KEY}
)
adapter_id = None
for w in resp.json()['data']:
    if '8_Telegram_Adapter' in w['name']:
        adapter_id = w['id']
        break

def fix_adapter(data):
    for node in data['nodes']:
        if node['name'] == 'Send Escalation':
            params = node['parameters']['bodyParameters']['parameters']
            for p in params:
                if p['name'] == 'reply_markup':
                    old_value = p['value']
                    # Add [Решено] button between [Беру] and [Не могу]
                    new_value = '={"inline_keyboard":[[{"text":"Беру ✋","callback_data":"take_{{ $json.handover_id }}"},{"text":"Решено ✅","callback_data":"resolve_{{ $json.handover_id }}"},{"text":"Не могу ❌","callback_data":"skip_{{ $json.handover_id }}"}]]}'
                    p['value'] = new_value
                    print(f"  Fixed: Send Escalation buttons")
                    print(f"    Old: [Беру][Не могу]")
                    print(f"    New: [Беру][Решено][Не могу]")
                    return True
    return False

if adapter_id:
    backup_and_update(adapter_id, '8_Adapter', fix_adapter)
else:
    print("  ERROR: 8_Telegram_Adapter not found")

# ==================== 3. Fix Callback ====================
print("\n=== 3. Fixing 9_Telegram_Callback (answered -> resolve) ===")

def fix_callback(data):
    connections = data['connections']
    
    # Find current answered output index in Action Switch
    # Action Switch outputs: [0]=take, [1]=resolve, [2]=skip, [3]=return, [4]=answered, [5]=snooze
    
    if 'Action Switch' not in connections:
        print("  ERROR: Action Switch not found in connections")
        return False
    
    main = connections['Action Switch']['main']
    
    # Output [4] should go to Resolve Handover instead of Answered Response
    if len(main) > 4:
        old_target = main[4][0]['node'] if main[4] else '(none)'
        main[4] = [{"node": "Resolve Handover", "type": "main", "index": 0}]
        print(f"  Fixed: Action Switch[4] (answered)")
        print(f"    Old: -> {old_target}")
        print(f"    New: -> Resolve Handover")
        return True
    
    return False

backup_and_update('HQOWuMDIBPphC86v', '9_Callback', fix_callback)

# ==================== 4. Reset test data ====================
print("\n=== 4. Resetting test data ===")
import subprocess
result = subprocess.run([
    'docker', 'exec', '-i', 'truffles_postgres_1', 
    'psql', '-U', 'n8n', '-d', 'chatbot', '-c',
    """UPDATE handovers SET status = 'resolved', resolved_at = NOW() WHERE status NOT IN ('resolved', 'timeout');
    UPDATE client_settings SET reminder_timeout_1 = 1, reminder_timeout_2 = 2;
    SELECT 'Test ready: 1min/2min reminders' as status;"""
], capture_output=True, text=True)
print(result.stdout)

print("\n=== DONE ===")
print("Changes:")
print("1. Reminder order fixed: reminder_1 -> reminder_2")
print("2. Escalation buttons: [Беру][Решено][Не могу]")
print("3. [Ответил ✓] now closes handover (same as [Решено])")
print("\nTest:")
print("1. Write 'позовите менеджера'")
print("2. New buttons: [Беру][Решено][Не могу]")
print("3. Can close directly with [Решено]")
print("4. 1 min -> reminder, 2 min -> URGENT")
