#!/usr/bin/env python3
"""
Исправляем workflow для динамического instance_id:
1. Load Prompt загружает instance_id из clients
2. Prepare Prompt передаёт instance_id дальше
3. Send ноды используют динамический instance_id
"""
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

print("Downloading workflow...")
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = resp.json()

# 1. Изменить Load Prompt SQL - добавить instance_id из clients
for node in workflow["nodes"]:
    if node.get("name") == "Load Prompt":
        node["parameters"]["query"] = """SELECT 
  p.text as system_prompt,
  c.config->>'instance_id' as instance_id
FROM clients c
LEFT JOIN prompts p ON p.client_id = c.id AND p.name IN ('system', 'system_prompt') AND p.is_active = true
WHERE c.name = '{{ $('Parse Input').first().json.client_slug }}'
LIMIT 1;"""
        print("Updated Load Prompt query")

# 2. Изменить Prepare Prompt - передать instance_id
for node in workflow["nodes"]:
    if node.get("name") == "Prepare Prompt":
        code = node["parameters"]["jsCode"]
        # Добавить instance_id в output
        new_code = '''// Собираем полный prompt + instance_id
const ctx = $json; // от Add Knowledge
const loadedPrompt = $('Load Prompt').first().json;

const basePrompt = loadedPrompt.system_prompt || `Ты — AI-помощник. Отвечай кратко и по делу.`;
const instanceId = loadedPrompt.instance_id || '';

const fullPrompt = basePrompt + `

## ДАННЫЕ
История: ${ctx.history}
База знаний: ${ctx.knowledge}

Intent: ${ctx.currentIntent}
isInCooldown: ${ctx.isInCooldown}

## ЭСКАЛАЦИЯ (needs_escalation = true)
Ставь needs_escalation = true когда:
1. МАТ или ОСКОРБЛЕНИЯ в сообщении
2. Клиент ЯВНО просит менеджера/человека
3. Клиент 2+ раза выражал недовольство
4. Сложный вопрос вне базы знаний

## COOLDOWN
Если isInCooldown = true И intent НЕ human_request:
- НЕ эскалируй
- Ответь: "Менеджер уже в курсе."

## ПРАВИЛА
1. Коротко (3-4 предложения)
2. НЕ ВЫДУМЫВАЙ — только из базы знаний
3. Указывай SOURCE
4. Если нет инфо — скажи честно

## SOURCE
Укажи документ: faq.md, services.md, objections.md, rules.md, или 'none'
`;

return [{
  json: {
    ...ctx,
    full_prompt: fullPrompt,
    instance_id: instanceId
  }
}];'''
        node["parameters"]["jsCode"] = new_code
        print("Updated Prepare Prompt")

# 3. Изменить Prepare Response - передать instance_id
for node in workflow["nodes"]:
    if node.get("name") == "Prepare Response":
        code = node["parameters"]["jsCode"]
        # Добавить instance_id
        new_code = '''const prev = $('Build Context').first().json;
const generation = $('Generate Response').first().json.output;
const instanceId = $('Prepare Prompt').first().json.instance_id;

const escapeSQL = (str) => String(str || '').replace(/'/g, "''");

return [{
  json: {
    conversation_id: prev.conversation_id,
    client_id: prev.client_id,
    remoteJid: prev.remoteJid,
    phone: prev.phone,
    message: prev.message,
    response: generation.response,
    safe_message: escapeSQL(prev.message),
    safe_response: escapeSQL(generation.response),
    thinking: generation.thinking,
    has_answer: generation.has_answer,
    needs_escalation: generation.needs_escalation,
    source: generation.source || 'none',
    instance_id: instanceId
  }
}];'''
        node["parameters"]["jsCode"] = new_code
        print("Updated Prepare Response")

# 4. Изменить Send Response и другие Send ноды - использовать динамический instance_id
send_nodes = ["Send Response", "Me", "Send Fallback2"]
for node in workflow["nodes"]:
    if node.get("name") in send_nodes:
        params = node.get("parameters", {})
        query_params = params.get("queryParameters", {}).get("parameters", [])
        for p in query_params:
            if p.get("name") == "instance_id":
                p["value"] = "={{ $('Prepare Response').first().json.instance_id }}"
                print(f"Updated instance_id in {node.get('name')}")

# Send Off-Topic использует другой источник данных
for node in workflow["nodes"]:
    if node.get("name") == "Send Off-Topic":
        params = node.get("parameters", {})
        query_params = params.get("queryParameters", {}).get("parameters", [])
        for p in query_params:
            if p.get("name") == "instance_id":
                # Для Off-Topic нужно загрузить instance_id отдельно или передать через Build Off-Topic Response
                p["value"] = "={{ $('Load Prompt').first().json.instance_id }}"
                print(f"Updated instance_id in Send Off-Topic")

# Upload
print("\nUploading...")
allowed = ["name", "nodes", "connections", "settings", "staticData"]
clean = {k: v for k, v in workflow.items() if k in allowed}

resp = requests.put(
    "https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json=clean
)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text[:500]}")
else:
    print("SUCCESS!")
