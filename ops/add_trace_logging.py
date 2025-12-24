#!/usr/bin/env python3
"""Add trace logging to Multi-Agent workflow"""
import requests
import json
import uuid

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

# Download workflow
print("Downloading workflow...")
r = requests.get(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = r.json()

nodes = workflow["nodes"]
connections = workflow["connections"]

# Find Prepare Response position
prep_resp_pos = None
for n in nodes:
    if n["name"] == "Prepare Response":
        prep_resp_pos = n["position"]
        break

if not prep_resp_pos:
    prep_resp_pos = [-336, 336]

# Add Save Trace node (PostgreSQL)
save_trace_node = {
    "parameters": {
        "operation": "executeQuery",
        "query": """INSERT INTO message_traces (
    phone,
    conversation_id,
    message,
    intent,
    rag_top_score,
    rag_top_doc,
    rag_scores,
    response,
    has_answer,
    needs_escalation
) VALUES (
    '{{ $('Build Context').first().json.phone }}',
    '{{ $('Build Context').first().json.conversation_id }}',
    '{{ $('Build Context').first().json.message.replace(/'/g, "''") }}',
    '{{ $('Build Context').first().json.currentIntent }}',
    {{ $('RAG Search').first().json.rag_scores[0] || 0 }},
    '{{ $('RAG Search').first().json.knowledge.substring(0, 50).replace(/'/g, "''") }}',
    '{{ JSON.stringify($('RAG Search').first().json.rag_scores || []) }}',
    '{{ $json.response.replace(/'/g, "''") }}',
    {{ $json.has_answer || false }},
    {{ $json.needs_escalation || false }}
);""",
        "options": {}
    },
    "type": "n8n-nodes-base.postgres",
    "typeVersion": 2.6,
    "position": [prep_resp_pos[0] + 300, prep_resp_pos[1] + 150],
    "id": str(uuid.uuid4()),
    "name": "Save Trace",
    "credentials": {
        "postgres": {
            "id": "6a8TkrGMQrGC3cuq",
            "name": "Postgres"
        }
    }
}

# Check if Save Trace already exists
exists = any(n["name"] == "Save Trace" for n in nodes)
if exists:
    print("Save Trace node already exists, skipping")
else:
    nodes.append(save_trace_node)
    print("Added Save Trace node")
    
    # Add connection: Prepare Response -> Save Trace
    if "Prepare Response" not in connections:
        connections["Prepare Response"] = {"main": [[]]}
    
    # Find existing connections from Prepare Response
    existing = connections["Prepare Response"].get("main", [[]])
    if len(existing) == 0:
        existing = [[]]
    
    # Add Save Trace as additional output
    existing[0].append({
        "node": "Save Trace",
        "type": "main",
        "index": 0
    })
    connections["Prepare Response"]["main"] = existing
    print("Added connection: Prepare Response -> Save Trace")

workflow["nodes"] = nodes
workflow["connections"] = connections

# Upload
print("Uploading workflow...")
update_payload = {
    "nodes": workflow["nodes"],
    "connections": workflow["connections"],
    "settings": workflow.get("settings", {}),
    "name": workflow.get("name", "Multi-Agent")
}
r = requests.put(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY},
    json=update_payload
)

if r.status_code == 200:
    print("SUCCESS! Trace logging added to Multi-Agent workflow")
else:
    print(f"FAILED: {r.status_code}")
    print(r.text)
