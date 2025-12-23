#!/usr/bin/env python3
"""Add summary loading to workflow"""
import json
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/workflow.json'
output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/workflow_final.json'

with open(input_file, 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Find Build Context position
build_ctx_pos = None
for node in workflow['nodes']:
    if node.get('name') == 'Build Context':
        build_ctx_pos = node.get('position', [-2064, 48])
        break

# Add Load Summary node
load_summary_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": """SELECT summary, key_facts, last_intent
FROM conversation_summaries
WHERE conversation_id = '{{ $('Upsert User').item.json.conversation_id }}'
LIMIT 1;""",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [build_ctx_pos[0] - 200, build_ctx_pos[1] + 150],
    "id": "load-summary-001",
    "name": "Load Summary",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# Add node
workflow['nodes'].append(load_summary_node)

# Add connection: Save User Message -> Load Summary (parallel with Load History)
# Find Save User Message connections
if 'Save User Message' in workflow['connections']:
    workflow['connections']['Save User Message']['main'][0].append({
        "node": "Load Summary",
        "type": "main",
        "index": 0
    })

# Load Summary -> Build Context (but Build Context already connected)
# We need to modify Build Context to use Load Summary data

# Find and update Build Context code
for node in workflow['nodes']:
    if node.get('name') == 'Build Context':
        old_code = node['parameters']['jsCode']
        
        # New code that uses summary
        new_code = """const input = $('Parse Input').first().json;
const history = $('Load History').all() || [];
const user = $('Upsert User').first().json;

// Get summary if exists
let summaryContext = '';
try {
  const summaryData = $('Load Summary').first()?.json;
  if (summaryData?.summary) {
    summaryContext = '[ПРЕДЫДУЩИЙ КОНТЕКСТ] ' + summaryData.summary + '\\n\\n';
  }
} catch (e) {
  // No summary yet
}

// Получаем intent: от classifier если был, иначе от routing
let currentIntent = 'unknown';
try {
  const classifyResult = $('Classify Intent').first()?.json?.output;
  if (classifyResult?.intent) {
    currentIntent = classifyResult.intent;
  }
} catch (e) {
  // Classifier был пропущен — используем routing hint
  const routing = input._routing || $('Intent Router').first()?.json?._routing || {};
  if (routing.isGreetingByText || routing.routeReason === 'greeting_on_topic') {
    currentIntent = 'greeting';
  } else if (routing.isShortAnswer || routing.routeReason === 'answer_in_dialog') {
    currentIntent = 'details';
  }
}

// Limit history if we have summary (only last 5 messages)
const historyLimit = summaryContext ? 5 : 10;
const recentHistory = history.slice(0, historyLimit);

const historyText = recentHistory
  .reverse()
  .map(m => `${m.json.role === 'user' ? 'Клиент' : 'Бот'}: ${m.json.content}`)
  .join('\\n') || '(новый диалог)';

// === ДЕТЕКТОР ТУПИКА (только через intent) ===
const isFrustration = currentIntent === 'frustration';
const isHumanRequest = currentIntent === 'human_request';
const isDeadlock = isFrustration || isHumanRequest;

let deadlockReason = null;
if (isDeadlock) {
  if (isFrustration) deadlockReason = 'frustration';
  else if (isHumanRequest) deadlockReason = 'human_request';
}

return [{
  json: {
    message: input.text,
    history: summaryContext + historyText,
    conversation_id: user.conversation_id,
    client_id: user.client_id,
    remoteJid: input.remoteJid,
    phone: input.phone,
    currentIntent,
    isDeadlock,
    deadlockReason
  }
}];"""
        
        node['parameters']['jsCode'] = new_code
        print("Updated Build Context to use summary")
        break

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}")
