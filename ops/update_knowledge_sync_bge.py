#!/usr/bin/env python3
"""Update Knowledge Sync workflow to use BGE-M3 instead of OpenAI Embeddings"""
import json
import sys
import uuid

def generate_id():
    return str(uuid.uuid4())

def update_workflow(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    nodes = workflow['nodes']
    connections = workflow['connections']
    
    # Find and remove OpenAI Embeddings, Default Data Loader, Character Text Splitter
    nodes_to_remove = ['OpenAI Embeddings', 'Default Data Loader', 'Character Text Splitter', 'Qdrant Vector Store']
    nodes = [n for n in nodes if n['name'] not in nodes_to_remove]
    
    # Remove connections for removed nodes
    for name in nodes_to_remove:
        if name in connections:
            del connections[name]
    
    # Clean up connections that reference removed nodes
    for node_name in list(connections.keys()):
        for conn_type in list(connections[node_name].keys()):
            connections[node_name][conn_type] = [
                [c for c in conn_list if c['node'] not in nodes_to_remove]
                for conn_list in connections[node_name][conn_type]
            ]
    
    # Find Prepare Chunks position for placing new nodes
    prepare_chunks_pos = None
    for n in nodes:
        if n['name'] == 'Prepare Chunks':
            prepare_chunks_pos = n['position']
            break
    
    if not prepare_chunks_pos:
        prepare_chunks_pos = [400, 976]
    
    # Add new nodes
    
    # 1. Get BGE Embeddings - HTTP Request to BGE-M3
    bge_embed_node = {
        "parameters": {
            "method": "POST",
            "url": "http://bge-m3:80/embed",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ inputs: $json.pageContent }) }}",
            "options": {
                "response": {
                    "response": {
                        "responseFormat": "json"
                    }
                }
            }
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [prepare_chunks_pos[0] + 250, prepare_chunks_pos[1]],
        "id": generate_id(),
        "name": "Get BGE Embeddings"
    }
    nodes.append(bge_embed_node)
    
    # 2. Prepare Qdrant Point - Code node to format data for Qdrant
    prepare_point_node = {
        "parameters": {
            "jsCode": """const chunk = $('Prepare Chunks').item.json;
const embedding = $('Get BGE Embeddings').item.json;

// embedding is array of arrays, get first
const vector = Array.isArray(embedding) ? embedding[0] : embedding;

const point = {
    id: chunk.metadata.doc_id + '-' + chunk.metadata.section_index,
    vector: vector,
    payload: {
        content: chunk.pageContent,
        metadata: chunk.metadata
    }
};

return [{ json: point }];"""
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [prepare_chunks_pos[0] + 500, prepare_chunks_pos[1]],
        "id": generate_id(),
        "name": "Prepare Qdrant Point"
    }
    nodes.append(prepare_point_node)
    
    # 3. Upsert to Qdrant - HTTP Request
    upsert_node = {
        "parameters": {
            "method": "PUT",
            "url": "http://qdrant:6333/collections/truffles_knowledge/points",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ points: [$json] }) }}",
            "options": {}
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [prepare_chunks_pos[0] + 750, prepare_chunks_pos[1]],
        "id": generate_id(),
        "name": "Upsert to Qdrant",
        "credentials": {
            "httpHeaderAuth": {
                "id": "tHgoKdaCF493jIDp",
                "name": "Qdrant_Local API Key"
            }
        }
    }
    nodes.append(upsert_node)
    
    # Update connections
    # Prepare Chunks -> Get BGE Embeddings
    connections['Prepare Chunks'] = {
        "main": [[{"node": "Get BGE Embeddings", "type": "main", "index": 0}]]
    }
    
    # Get BGE Embeddings -> Prepare Qdrant Point
    connections['Get BGE Embeddings'] = {
        "main": [[{"node": "Prepare Qdrant Point", "type": "main", "index": 0}]]
    }
    
    # Prepare Qdrant Point -> Upsert to Qdrant
    connections['Prepare Qdrant Point'] = {
        "main": [[{"node": "Upsert to Qdrant", "type": "main", "index": 0}]]
    }
    
    # Upsert to Qdrant -> Aggregate Results
    connections['Upsert to Qdrant'] = {
        "main": [[{"node": "Aggregate Results", "type": "main", "index": 0}]]
    }
    
    workflow['nodes'] = nodes
    workflow['connections'] = connections
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    
    print(f"Updated workflow saved to {output_path}")
    print(f"Nodes: {len(nodes)}")
    print("New nodes added: Get BGE Embeddings, Prepare Qdrant Point, Upsert to Qdrant")
    print("Removed nodes: OpenAI Embeddings, Default Data Loader, Character Text Splitter, Qdrant Vector Store")

if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/knowledge_sync.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/knowledge_sync_updated.json"
    update_workflow(input_path, output_path)
