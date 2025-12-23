#!/usr/bin/env python3
"""Fix Save Summary query to include client_id"""
import json
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/workflow.json'
output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/workflow_fixed.json'

with open(input_file, 'r', encoding='utf-8') as f:
    workflow = json.load(f)

new_query = """INSERT INTO conversation_summaries (conversation_id, client_id, summary, key_facts, last_intent)
VALUES (
  '{{ $('Prepare for Summary').item.json.conversation_id }}',
  '{{ $('Prepare for Summary').item.json.client_id }}',
  '{{ $json.output.summary.replace(/'/g, "''") }}',
  '{{ JSON.stringify($json.output.key_facts).replace(/'/g, "''") }}'::jsonb,
  '{{ $json.output.last_intent.replace(/'/g, "''") }}'
)
ON CONFLICT (conversation_id) DO UPDATE SET
  summary = EXCLUDED.summary,
  key_facts = EXCLUDED.key_facts,
  last_intent = EXCLUDED.last_intent,
  updated_at = NOW();"""

for node in workflow['nodes']:
    if node.get('name') == 'Save Summary':
        node['parameters']['query'] = new_query
        print("Fixed Save Summary query")
        break

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}")
