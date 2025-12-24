#!/usr/bin/env python3
"""Добавляет ноду Load Prompt в Multi-Agent workflow"""
import requests
import json

API_KEY = "REDACTED_JWT"

print("Downloading workflow...")
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = resp.json()

# 1. Добавить ноду Load Prompt
load_prompt_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": "SELECT p.text as system_prompt\nFROM prompts p\nJOIN clients c ON c.id = p.client_id\nWHERE c.name = '{{ $('Parse Input').first().json.client_slug }}'\n  AND p.name IN ('system', 'system_prompt')\n  AND p.is_active = true\nLIMIT 1;",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [-2000, 320],
    "id": "load-prompt-001",
    "name": "Load Prompt",
    "credentials": {
        "postgres": {
            "id": "SUHrbh39Ig0fBusT",
            "name": "ChatbotDB"
        }
    }
}

# Проверить есть ли уже Load Prompt
existing = [n for n in workflow["nodes"] if n.get("name") == "Load Prompt"]
if existing:
    print("Load Prompt already exists, updating...")
    for n in workflow["nodes"]:
        if n.get("name") == "Load Prompt":
            n.update(load_prompt_node)
else:
    print("Adding Load Prompt node...")
    workflow["nodes"].append(load_prompt_node)

# 2. Изменить Generate Response - использовать динамический prompt
for node in workflow["nodes"]:
    if node.get("name") == "Generate Response":
        params = node.get("parameters", {})
        options = params.get("options", {})
        
        # Создаём новый systemMessage с динамическим промптом
        dynamic_prompt = """={{ 
const basePrompt = $('Load Prompt').first().json.system_prompt || 'Ты — AI-помощник.';
const context = `

## ДАННЫЕ
История: ${ $json.history }
База знаний: ${ $json.knowledge }

Intent: ${ $json.currentIntent }
isInCooldown: ${ $json.isInCooldown }

## ЭСКАЛАЦИЯ (needs_escalation = true)
Ставь needs_escalation = true когда:
1. МАТ или ОСКОРБЛЕНИЯ в сообщении
2. Клиент ЯВНО просит менеджера/человека
3. Клиент 2+ раза выражал недовольство в истории
4. Сложный вопрос вне базы знаний

## COOLDOWN ЭСКАЛАЦИИ
Если isInCooldown = true И intent НЕ human_request:
- НЕ ставь needs_escalation = true
- Ответь: "Менеджер уже в курсе и свяжется с вами."

## ПРАВИЛА ОТВЕТА
1. Отвечай по делу, коротко (3-4 предложения макс)
2. НЕ ВЫДУМЫВАЙ — только факты из базы знаний
3. Указывай SOURCE — откуда взял информацию
4. Если source = none — предупреди клиента

## SOURCE (ОБЯЗАТЕЛЬНО)
Укажи документ откуда взял информацию, или 'none'
`;
return basePrompt + context;
}}"""
        
        options["systemMessage"] = dynamic_prompt
        params["options"] = options
        node["parameters"] = params
        print("Updated Generate Response systemMessage")

# 3. Добавить connection: Save User Message → Load Prompt → Build Context
# Найти текущие connections
connections = workflow.get("connections", {})

# Добавить Load Prompt в цепочку после Save User Message
if "Save User Message" in connections:
    # Save User Message → Load Prompt
    connections["Save User Message"] = {
        "main": [[{"node": "Load Prompt", "type": "main", "index": 0}]]
    }

# Load Prompt → Build Context (или Load History)
connections["Load Prompt"] = {
    "main": [[{"node": "Build Context", "type": "main", "index": 0}]]
}

workflow["connections"] = connections

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
