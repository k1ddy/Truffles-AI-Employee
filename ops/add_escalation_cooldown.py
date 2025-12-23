#!/usr/bin/env python3
"""Add escalation cooldown logic to workflow"""
import json
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/workflow.json'
output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/workflow_updated.json'

with open(input_file, 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Find Build Context position
build_ctx_pos = None
for node in workflow['nodes']:
    if node.get('name') == 'Build Context':
        build_ctx_pos = node.get('position', [-2064, 48])
        break

# 1. Add node to load escalation status
load_escalation_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": """SELECT 
  escalated_at,
  CASE 
    WHEN escalated_at IS NULL THEN FALSE
    WHEN escalated_at > NOW() - INTERVAL '30 minutes' THEN TRUE
    ELSE FALSE
  END as is_in_cooldown
FROM conversations
WHERE id = '{{ $('Upsert User').item.json.conversation_id }}';""",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [build_ctx_pos[0] - 200, build_ctx_pos[1] - 100],
    "id": "load-escalation-status-001",
    "name": "Load Escalation Status",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# 2. Add node to update escalation timestamp after Me2
update_escalation_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": """UPDATE conversations 
SET escalated_at = NOW()
WHERE id = '{{ $('Build Context').first().json.conversation_id }}';""",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [-500, 300],
    "id": "update-escalation-001",
    "name": "Update Escalation Time",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# Add nodes
workflow['nodes'].append(load_escalation_node)
workflow['nodes'].append(update_escalation_node)

# 3. Update Build Context to include cooldown status
for node in workflow['nodes']:
    if node.get('name') == 'Build Context':
        old_code = node['parameters']['jsCode']
        
        # Add escalation cooldown check
        new_code = old_code.replace(
            "return [{",
            """// Check escalation cooldown
let isInCooldown = false;
let escalatedAt = null;
try {
  const escStatus = $('Load Escalation Status').first()?.json;
  isInCooldown = escStatus?.is_in_cooldown || false;
  escalatedAt = escStatus?.escalated_at;
} catch (e) {}

return [{"""
        )
        
        # Add to return object
        new_code = new_code.replace(
            "deadlockReason",
            "isInCooldown,\n    escalatedAt,\n    deadlockReason"
        )
        
        node['parameters']['jsCode'] = new_code
        print("Updated Build Context")
        break

# 4. Update Generate Response prompt to handle cooldown
for node in workflow['nodes']:
    if node.get('name') == 'Generate Response':
        old_prompt = node['parameters']['options']['systemMessage']
        
        # Add cooldown rule
        cooldown_rule = """
## COOLDOWN ЭСКАЛАЦИИ
Если в данных есть isInCooldown = true И intent НЕ human_request:
- НЕ ставь needs_escalation = true
- Ответь: "Менеджер уже в курсе и свяжется с вами."
- Исключение: если клиент ЯВНО просит менеджера (human_request) — эскалируй

"""
        new_prompt = old_prompt.replace("## ПРАВИЛА ОТВЕТА", cooldown_rule + "## ПРАВИЛА ОТВЕТА")
        
        # Add isInCooldown to data
        new_prompt = new_prompt.replace(
            "Intent: {{ $json.currentIntent }}",
            "Intent: {{ $json.currentIntent }}\nisInCooldown: {{ $json.isInCooldown }}"
        )
        
        node['parameters']['options']['systemMessage'] = new_prompt
        print("Updated Generate Response prompt")
        break

# 5. Add connection: Save User Message -> Load Escalation Status (parallel)
if 'Save User Message' in workflow['connections']:
    workflow['connections']['Save User Message']['main'][0].append({
        "node": "Load Escalation Status",
        "type": "main",
        "index": 0
    })
    print("Added connection Save User Message -> Load Escalation Status")

# 6. Add connection: Me2 -> Update Escalation Time (parallel with Prepare for Summary)
if 'Me2' in workflow['connections']:
    me2_conn = workflow['connections']['Me2']['main']
    if len(me2_conn) > 0:
        me2_conn[0].append({
            "node": "Update Escalation Time",
            "type": "main",
            "index": 0
        })
        print("Added connection Me2 -> Update Escalation Time")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}")
