#!/usr/bin/env python3
"""Fix Multi-Agent Search Qdrant - use single Code node like Knowledge Sync"""
import json
import uuid
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "4vaEvzlaMrgovhNz"

# Download current workflow
print("Downloading workflow...")
r = requests.get(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = r.json()

nodes = workflow['nodes']
connections = workflow['connections']

# Find Build Context position
build_context_pos = None
for n in nodes:
    if n['name'] == 'Build Context':
        build_context_pos = n['position']
        break

if not build_context_pos:
    build_context_pos = [-2000, 336]

# Remove old RAG nodes
nodes_to_remove = ['Embed Query', 'Search Qdrant', 'Format RAG Results']
nodes = [n for n in nodes if n['name'] not in nodes_to_remove]

for name in nodes_to_remove:
    if name in connections:
        del connections[name]

# Add single Code node for RAG
rag_search_node = {
    "parameters": {
        "jsCode": """const ctx = $json;

// 1. Get embedding from BGE-M3
const bgeResponse = await this.helpers.httpRequest({
    method: 'POST',
    url: 'http://bge-m3:80/embed',
    body: { inputs: ctx.message },
    json: true
});

const vector = bgeResponse[0];

// 2. Search Qdrant
const searchPayload = {
    vector: vector,
    limit: 5,
    with_payload: true
};

const searchResponse = await this.helpers.httpRequest({
    method: 'POST',
    url: 'http://qdrant:6333/collections/truffles_knowledge/points/search',
    headers: {
        'api-key': 'REDACTED_PASSWORD',
        'Content-Type': 'application/json'
    },
    body: searchPayload,
    json: true
});

const results = searchResponse.result || [];

// 3. Format knowledge
const knowledge = results
    .map(r => r.payload?.content || '')
    .filter(t => t)
    .join('\\n\\n---\\n\\n') || '(нет информации в базе)';

return {
    json: {
        ...ctx,
        knowledge: knowledge,
        rag_scores: results.map(r => r.score)
    }
};"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [build_context_pos[0] + 250, build_context_pos[1]],
    "id": str(uuid.uuid4()),
    "name": "RAG Search"
}
nodes.append(rag_search_node)

# Update Add Knowledge to pass through from RAG Search
for n in nodes:
    if n['name'] == 'Add Knowledge':
        n['parameters']['jsCode'] = """const prev = $('RAG Search').first().json;

return [{
    json: {
        ...prev
    }
}];"""
        break

# Update connections
connections['Build Context'] = {
    "main": [[{"node": "RAG Search", "type": "main", "index": 0}]]
}

connections['RAG Search'] = {
    "main": [[{"node": "Add Knowledge", "type": "main", "index": 0}]]
}

# Fix Is Deadlock connections if exists
if 'Is Deadlock' in connections:
    for i, conn_list in enumerate(connections['Is Deadlock'].get('main', [])):
        connections['Is Deadlock']['main'][i] = [
            {"node": "RAG Search", "type": "main", "index": 0} if c.get('node') in nodes_to_remove else c
            for c in conn_list
        ]

workflow['nodes'] = nodes
workflow['connections'] = connections

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
    print("SUCCESS! Multi-Agent workflow updated.")
    print("New 'RAG Search' node does:")
    print("  1. HTTP to BGE-M3 for query embedding")
    print("  2. HTTP to Qdrant for vector search")
    print("  3. Format results into knowledge")
else:
    print(f"FAILED: {r.status_code}")
    print(r.text)
