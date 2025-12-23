#!/usr/bin/env python3
"""
Правильное решение:
1. Добавить Code ноду Prepare Prompt
2. Исправить Generate Response systemMessage
3. Исправить connections
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

# 1. Добавить/обновить ноду Prepare Prompt
prepare_prompt_code = '''// Собираем полный prompt
const ctx = $json; // от Add Knowledge
const loadedPrompt = $('Load Prompt').first().json;

const basePrompt = loadedPrompt.system_prompt || `Ты — AI-помощник. Отвечай кратко и по делу.`;

const fullPrompt = basePrompt + `

## ДАННЫЕ
История: ${ctx.history}
База знаний: ${ctx.knowledge}

Intent: ${ctx.currentIntent}
isInCooldown: ${ctx.isInCooldown}

## ЭСКАЛАЦИЯ (needs_escalation = true)
Ставь needs_escalation = true когда:
1. МАТ или ОСКОРБЛЕНИЯ в сообщении -> response: 'Понимаю, передаю менеджеру.'
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
    full_prompt: fullPrompt
  }
}];'''

prepare_prompt_node = {
    "parameters": {
        "jsCode": prepare_prompt_code
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-1552, 320],
    "id": "prepare-prompt-001",
    "name": "Prepare Prompt"
}

# Удалить старую Prepare Prompt если есть, добавить новую
workflow["nodes"] = [n for n in workflow["nodes"] if n.get("name") != "Prepare Prompt"]
workflow["nodes"].append(prepare_prompt_node)
print("Added Prepare Prompt node")

# 2. Исправить Generate Response - простое выражение
for node in workflow["nodes"]:
    if node.get("name") == "Generate Response":
        params = node.get("parameters", {})
        options = params.get("options", {})
        options["systemMessage"] = "={{ $json.full_prompt }}"
        params["options"] = options
        node["parameters"] = params
        print("Fixed Generate Response systemMessage")

# 3. Исправить connections
# Add Knowledge → Prepare Prompt → Generate Response
connections = workflow.get("connections", {})

connections["Add Knowledge"] = {
    "main": [[{"node": "Prepare Prompt", "type": "main", "index": 0}]]
}

connections["Prepare Prompt"] = {
    "main": [[{"node": "Generate Response", "type": "main", "index": 0}]]
}

workflow["connections"] = connections
print("Fixed connections: Add Knowledge → Prepare Prompt → Generate Response")

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
