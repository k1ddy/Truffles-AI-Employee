#!/usr/bin/env python3
"""Add summarization nodes to workflow"""
import json
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/workflow.json'
output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/workflow_updated.json'

with open(input_file, 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Find Me2 position for placing new nodes nearby
me2_pos = None
for node in workflow['nodes']:
    if node.get('name') == 'Me2':
        me2_pos = node.get('position', [-700, 200])
        break

if not me2_pos:
    print("Error: Me2 node not found")
    sys.exit(1)

# New nodes to add
summarize_node = {
    "parameters": {
        "jsCode": """const ctx = $('Build Context').first().json;
const prep = $('Prepare Response').first().json;

// Format conversation for summarization
const history = ctx.history || '';
const lastMessage = ctx.message;
const botResponse = prep.response;

const fullConversation = history + '\\nКлиент: ' + lastMessage + '\\nБот: ' + botResponse;

return [{
  json: {
    conversation_id: ctx.conversation_id,
    client_id: ctx.client_id,
    conversation: fullConversation,
    current_intent: ctx.currentIntent
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [me2_pos[0] + 200, me2_pos[1] + 200],
    "id": "summarize-prep-001",
    "name": "Prepare for Summary"
}

summarize_llm_node = {
    "parameters": {
        "promptType": "define",
        "text": "={{ $json.conversation }}",
        "hasOutputParser": True,
        "options": {
            "systemMessage": """Ты — суммаризатор диалогов. Сжми диалог в краткую выжимку.

ЧТО ВКЛЮЧАТЬ:
- Что хотел клиент (intent)
- Какой бизнес (если сказал)
- Что решили: interested, refused, thinking, unknown
- Важные детали

ЧТО НЕ ВКЛЮЧАТЬ:
- Приветствия, мат, жалобы
- Повторы

ФОРМАТ JSON:
{
  "summary": "1-2 предложения",
  "key_facts": {
    "intent": "что хотел",
    "business": "тип бизнеса или unknown",
    "decision": "interested | refused | thinking | unknown"
  },
  "last_intent": "последний intent"
}"""
        }
    },
    "type": "@n8n/n8n-nodes-langchain.agent",
    "typeVersion": 3,
    "position": [me2_pos[0] + 400, me2_pos[1] + 200],
    "id": "summarize-llm-001",
    "name": "Summarize Conversation"
}

summary_parser_node = {
    "parameters": {
        "schemaType": "manual",
        "inputSchema": """{
  "type": "object",
  "properties": {
    "summary": {"type": "string"},
    "key_facts": {
      "type": "object",
      "properties": {
        "intent": {"type": "string"},
        "business": {"type": "string"},
        "decision": {"type": "string", "enum": ["interested", "refused", "thinking", "unknown"]}
      }
    },
    "last_intent": {"type": "string"}
  },
  "required": ["summary", "key_facts", "last_intent"]
}"""
    },
    "type": "@n8n/n8n-nodes-langchain.outputParserStructured",
    "typeVersion": 1.3,
    "position": [me2_pos[0] + 400, me2_pos[1] + 350],
    "id": "summary-parser-001",
    "name": "Summary Parser"
}

summary_model_node = {
    "parameters": {
        "model": {
            "__rl": True,
            "value": "gpt-4.1-mini",
            "mode": "list",
            "cachedResultName": "gpt-4.1-mini"
        },
        "options": {}
    },
    "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    "typeVersion": 1.3,
    "position": [me2_pos[0] + 200, me2_pos[1] + 350],
    "id": "summary-model-001",
    "name": "Summary Model",
    "credentials": {
        "openAiApi": {
            "id": "C31JRkzPBiItNcOT",
            "name": "OpenAi account"
        }
    }
}

save_summary_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": """INSERT INTO conversation_summaries (conversation_id, summary, key_facts, last_intent)
VALUES (
  '{{ $('Prepare for Summary').item.json.conversation_id }}',
  '{{ $json.output.summary }}',
  '{{ JSON.stringify($json.output.key_facts) }}'::jsonb,
  '{{ $json.output.last_intent }}'
)
ON CONFLICT (conversation_id) DO UPDATE SET
  summary = EXCLUDED.summary,
  key_facts = EXCLUDED.key_facts,
  last_intent = EXCLUDED.last_intent,
  updated_at = NOW();""",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [me2_pos[0] + 600, me2_pos[1] + 200],
    "id": "save-summary-001",
    "name": "Save Summary",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# Add nodes
workflow['nodes'].extend([
    summarize_node,
    summarize_llm_node,
    summary_parser_node,
    summary_model_node,
    save_summary_node
])

# Add connections
if 'connections' not in workflow:
    workflow['connections'] = {}

# Me2 -> Prepare for Summary (parallel branch)
if 'Me2' not in workflow['connections']:
    workflow['connections']['Me2'] = {"main": [[]]}
    
# Add second output from Me2 to summarization
workflow['connections']['Me2']['main'].append([
    {"node": "Prepare for Summary", "type": "main", "index": 0}
])

# Prepare for Summary -> Summarize Conversation
workflow['connections']['Prepare for Summary'] = {
    "main": [[{"node": "Summarize Conversation", "type": "main", "index": 0}]]
}

# Summarize Conversation -> Save Summary
workflow['connections']['Summarize Conversation'] = {
    "main": [[{"node": "Save Summary", "type": "main", "index": 0}]]
}

# Summary Model -> Summarize Conversation (ai_languageModel)
workflow['connections']['Summary Model'] = {
    "ai_languageModel": [[{"node": "Summarize Conversation", "type": "ai_languageModel", "index": 0}]]
}

# Summary Parser -> Summarize Conversation (ai_outputParser)
workflow['connections']['Summary Parser'] = {
    "ai_outputParser": [[{"node": "Summarize Conversation", "type": "ai_outputParser", "index": 0}]]
}

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)

print(f"Added summarization nodes. Saved to {output_file}")
