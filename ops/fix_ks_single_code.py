#!/usr/bin/env python3
"""Replace BGE + Qdrant nodes with single Code node that does everything"""
import json
import sys
import uuid
import requests

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"
WORKFLOW_ID = "zTbaCLWLJN6vPMk4"

# Download current workflow
print("Downloading workflow...")
r = requests.get(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = r.json()

nodes = workflow['nodes']
connections = workflow['connections']

# Remove old nodes
nodes_to_remove = ['Get BGE Embeddings', 'Prepare Qdrant Point', 'Upsert to Qdrant']
nodes = [n for n in nodes if n['name'] not in nodes_to_remove]

for name in nodes_to_remove:
    if name in connections:
        del connections[name]

# Find Prepare Chunks position
prep_chunks_pos = None
for n in nodes:
    if n['name'] == 'Prepare Chunks':
        prep_chunks_pos = n['position']
        break

if not prep_chunks_pos:
    prep_chunks_pos = [400, 976]

# Add single Code node that does BGE + Qdrant
embed_and_store_node = {
    "parameters": {
        "mode": "runOnceForEachItem",
        "jsCode": """const chunk = $json;

// 1. Get embedding from BGE-M3
const bgeResponse = await this.helpers.httpRequest({
    method: 'POST',
    url: 'http://bge-m3:80/embed',
    body: { inputs: chunk.pageContent },
    json: true
});

// BGE-M3 returns [[...floats...]], extract first array
const vector = bgeResponse[0];

// 2. Generate integer ID
const idStr = chunk.metadata.doc_id + '-' + String(chunk.metadata.section_index);
let hash = 0;
for (let i = 0; i < idStr.length; i++) {
    hash = ((hash << 5) - hash) + idStr.charCodeAt(i);
    hash = hash >>> 0;
}

// 3. Upsert to Qdrant
const qdrantPayload = {
    points: [{
        id: hash,
        vector: vector,
        payload: {
            content: chunk.pageContent,
            metadata: chunk.metadata
        }
    }]
};

const qdrantResponse = await this.helpers.httpRequest({
    method: 'PUT',
    url: 'http://qdrant:6333/collections/truffles_knowledge/points',
    headers: {
        'api-key': 'Iddqd777!',
        'Content-Type': 'application/json'
    },
    body: qdrantPayload,
    json: true
});

return {
    json: {
        success: true,
        point_id: hash,
        qdrant_status: qdrantResponse.status
    }
};"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [prep_chunks_pos[0] + 300, prep_chunks_pos[1]],
    "id": str(uuid.uuid4()),
    "name": "Embed and Store"
}
nodes.append(embed_and_store_node)

# Update connections
connections['Prepare Chunks'] = {
    "main": [[{"node": "Embed and Store", "type": "main", "index": 0}]]
}

connections['Embed and Store'] = {
    "main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]
}

workflow['nodes'] = nodes
workflow['connections'] = connections

# Upload updated workflow - only send allowed fields
print("Uploading workflow...")
update_payload = {
    "nodes": workflow["nodes"],
    "connections": workflow["connections"],
    "settings": workflow.get("settings", {}),
    "name": workflow.get("name", "Knowledge Sync")
}
r = requests.put(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY},
    json=update_payload
)

if r.status_code == 200:
    print("SUCCESS! Workflow updated.")
    print("New approach: single Code node 'Embed and Store' does:")
    print("  1. HTTP to BGE-M3 for embedding")
    print("  2. HTTP to Qdrant for upsert")
    print("  No JSON.stringify issues.")
else:
    print(f"FAILED: {r.status_code}")
    print(r.text)
