#!/usr/bin/env python3
"""Update Multi-Agent workflow to use BGE-M3 instead of OpenAI Embeddings"""
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
    
    # Find Build Context position
    build_context_pos = None
    for n in nodes:
        if n['name'] == 'Build Context':
            build_context_pos = n['position']
            break
    
    if not build_context_pos:
        build_context_pos = [-2000, 336]
    
    # Remove old RAG nodes
    nodes_to_remove = ['Embeddings OpenAI', 'Qdrant Vector Store', 'Reranker Cohere', 'Reranker Cohere1']
    nodes = [n for n in nodes if n['name'] not in nodes_to_remove]
    
    # Remove connections for removed nodes
    for name in nodes_to_remove:
        if name in connections:
            del connections[name]
    
    # Add new nodes
    
    # 1. Embed Query - HTTP Request to BGE-M3
    embed_query_node = {
        "parameters": {
            "method": "POST",
            "url": "http://bge-m3:80/embed",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ inputs: $json.message }) }}",
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
        "position": [build_context_pos[0] + 200, build_context_pos[1]],
        "id": generate_id(),
        "name": "Embed Query"
    }
    nodes.append(embed_query_node)
    
    # 2. Search Qdrant - HTTP Request
    search_qdrant_node = {
        "parameters": {
            "method": "POST",
            "url": "http://qdrant:6333/collections/truffles_knowledge/points/search",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": """={{ JSON.stringify({
  vector: $json[0],
  limit: 5,
  with_payload: true
}) }}""",
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
        "position": [build_context_pos[0] + 400, build_context_pos[1]],
        "id": generate_id(),
        "name": "Search Qdrant",
        "credentials": {
            "httpHeaderAuth": {
                "id": "tHgoKdaCF493jIDp",
                "name": "Qdrant_Local API Key"
            }
        }
    }
    nodes.append(search_qdrant_node)
    
    # 3. Format RAG Results - Code node
    format_results_node = {
        "parameters": {
            "jsCode": """const ctx = $('Build Context').first().json;
const searchResult = $('Search Qdrant').first().json;

const results = searchResult.result || [];

const knowledge = results
    .map(r => r.payload?.content || '')
    .filter(t => t)
    .join('\\n\\n---\\n\\n') || '(нет информации в базе)';

return [{
    json: {
        ...ctx,
        knowledge: knowledge,
        rag_scores: results.map(r => r.score)
    }
}];"""
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [build_context_pos[0] + 600, build_context_pos[1]],
        "id": generate_id(),
        "name": "Format RAG Results"
    }
    nodes.append(format_results_node)
    
    # Update Add Knowledge node to use Format RAG Results
    for n in nodes:
        if n['name'] == 'Add Knowledge':
            n['parameters']['jsCode'] = """const prev = $('Format RAG Results').first().json;

return [{
    json: {
        ...prev
    }
}];"""
            break
    
    # Update connections
    # Build Context -> Embed Query
    if 'Build Context' in connections:
        # Keep existing connections but replace Qdrant Vector Store with Embed Query
        for conn_type in connections['Build Context']:
            connections['Build Context'][conn_type] = [
                [{"node": "Embed Query", "type": "main", "index": 0}
                 if any(c.get('node') == 'Qdrant Vector Store' for c in conn_list)
                 else conn_list
                 for conn_list in connections['Build Context'][conn_type]][0]
            ]
    
    connections['Build Context'] = {
        "main": [[{"node": "Embed Query", "type": "main", "index": 0}]]
    }
    
    # Embed Query -> Search Qdrant
    connections['Embed Query'] = {
        "main": [[{"node": "Search Qdrant", "type": "main", "index": 0}]]
    }
    
    # Search Qdrant -> Format RAG Results
    connections['Search Qdrant'] = {
        "main": [[{"node": "Format RAG Results", "type": "main", "index": 0}]]
    }
    
    # Format RAG Results -> Add Knowledge
    connections['Format RAG Results'] = {
        "main": [[{"node": "Add Knowledge", "type": "main", "index": 0}]]
    }
    
    # Clean up Is Deadlock connections to use new flow
    if 'Is Deadlock' in connections:
        for i, conn_list in enumerate(connections['Is Deadlock'].get('main', [])):
            connections['Is Deadlock']['main'][i] = [
                {"node": "Embed Query", "type": "main", "index": 0} if c.get('node') == 'Qdrant Vector Store' else c
                for c in conn_list
            ]
    
    workflow['nodes'] = nodes
    workflow['connections'] = connections
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    
    print(f"Updated workflow saved to {output_path}")
    print(f"Nodes: {len(nodes)}")
    print("New nodes: Embed Query, Search Qdrant, Format RAG Results")
    print("Removed: Embeddings OpenAI, Qdrant Vector Store, Reranker Cohere")

if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/multi_agent.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/multi_agent_updated.json"
    update_workflow(input_path, output_path)
