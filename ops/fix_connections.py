#!/usr/bin/env python3
"""Исправляет connections в Multi-Agent workflow"""
import requests
import json

API_KEY = "REDACTED_JWT"

print("Downloading workflow...")
resp = requests.get(
    "https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = resp.json()

connections = workflow.get("connections", {})

# Правильная цепочка:
# Save User Message → Load History → Load Prompt → Build Context → RAG Search → ...

# Исправляем
connections["Save User Message"] = {
    "main": [[{"node": "Load History", "type": "main", "index": 0}]]
}

connections["Load History"] = {
    "main": [[{"node": "Load Prompt", "type": "main", "index": 0}]]
}

connections["Load Prompt"] = {
    "main": [[{"node": "Build Context", "type": "main", "index": 0}]]
}

# Build Context → RAG Search уже должен быть правильный

workflow["connections"] = connections

# Также исправим позицию Load Prompt чтобы был между Load History и Build Context
for node in workflow["nodes"]:
    if node.get("name") == "Load Prompt":
        # Позиция между Load History (-2224, 368) и Build Context (-2000, 368)
        node["position"] = [-2112, 320]

print("Fixed connections:")
print("  Save User Message → Load History → Load Prompt → Build Context")

# Upload
allowed = ["name", "nodes", "connections", "settings", "staticData"]
clean = {k: v for k, v in workflow.items() if k in allowed}

resp = requests.put(
    "https://n8n.truffles.kz/api/v1/workflows/4vaEvzlaMrgovhNz",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    json=clean
)
print(f"\nUpload status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Error: {resp.text[:300]}")
