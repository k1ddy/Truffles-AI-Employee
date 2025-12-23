#!/usr/bin/env python3
"""Fix Build Context code"""
import json
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/workflow.json'
output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/workflow_fixed.json'

with open(input_file, 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Correct Build Context code
correct_code = """const input = $('Parse Input').first().json;
const history = $('Load History').all() || [];
const user = $('Upsert User').first().json;

// Get summary if exists
let summaryContext = '';
try {
  const summaryData = $('Load Summary').first()?.json;
  if (summaryData?.summary) {
    summaryContext = '[ПРЕДЫДУЩИЙ КОНТЕКСТ] ' + summaryData.summary + '\\n\\n';
  }
} catch (e) {}

// Check escalation cooldown
let isInCooldown = false;
let escalatedAt = null;
try {
  const escStatus = $('Load Escalation Status').first()?.json;
  isInCooldown = escStatus?.is_in_cooldown || false;
  escalatedAt = escStatus?.escalated_at;
} catch (e) {}

// Получаем intent
let currentIntent = 'unknown';
try {
  const classifyResult = $('Classify Intent').first()?.json?.output;
  if (classifyResult?.intent) {
    currentIntent = classifyResult.intent;
  }
} catch (e) {
  const routing = input._routing || {};
  if (routing.isGreetingByText || routing.routeReason === 'greeting_on_topic') {
    currentIntent = 'greeting';
  } else if (routing.isShortAnswer || routing.routeReason === 'answer_in_dialog') {
    currentIntent = 'details';
  }
}

// History
const historyLimit = summaryContext ? 5 : 10;
const recentHistory = history.slice(0, historyLimit);
const historyText = recentHistory
  .reverse()
  .map(m => `${m.json.role === 'user' ? 'Клиент' : 'Бот'}: ${m.json.content}`)
  .join('\\n') || '(новый диалог)';

// Deadlock detection (не используется напрямую, но для логирования)
const isFrustration = currentIntent === 'frustration';
const isHumanRequest = currentIntent === 'human_request';
const isDeadlock = isFrustration || isHumanRequest;
let deadlockReason = null;
if (isFrustration) deadlockReason = 'frustration';
else if (isHumanRequest) deadlockReason = 'human_request';

return [{
  json: {
    message: input.text,
    history: summaryContext + historyText,
    conversation_id: user.conversation_id,
    client_id: user.client_id,
    remoteJid: input.remoteJid,
    phone: input.phone,
    currentIntent,
    isInCooldown,
    escalatedAt,
    isDeadlock,
    deadlockReason
  }
}];"""

for node in workflow['nodes']:
    if node.get('name') == 'Build Context':
        node['parameters']['jsCode'] = correct_code
        print("Fixed Build Context")
        break

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}")
