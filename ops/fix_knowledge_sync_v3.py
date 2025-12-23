#!/usr/bin/env python3
"""Fix Knowledge Sync - proper BGE-M3 and Qdrant integration"""
import json
import sys

def fix_workflow(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    for node in workflow['nodes']:
        # Fix Prepare Qdrant Point - create full upsert payload
        if node['name'] == 'Prepare Qdrant Point':
            node['parameters']['jsCode'] = """const chunk = $('Prepare Chunks').item.json;
const bgeResponse = $('Get BGE Embeddings').item.json;

// BGE-M3 returns [[...1024 floats...]], extract first array
const vector = bgeResponse[0];

// Generate positive integer ID from doc_id and section_index
const str = chunk.metadata.doc_id + '-' + String(chunk.metadata.section_index);
let hash = 0;
for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash = hash >>> 0; // Convert to unsigned
}

// Create full Qdrant upsert payload
const upsertPayload = {
    points: [{
        id: hash,
        vector: vector,
        payload: {
            content: chunk.pageContent,
            metadata: chunk.metadata
        }
    }]
};

return [{ json: upsertPayload }];"""
            print(f"Fixed: {node['name']}")
        
        # Fix Upsert to Qdrant - send $json directly (already formatted)
        if node['name'] == 'Upsert to Qdrant':
            node['parameters']['jsonBody'] = "={{ JSON.stringify($json) }}"
            print(f"Fixed: {node['name']}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ks_v3.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ks_v3_fixed.json"
    fix_workflow(input_path, output_path)
