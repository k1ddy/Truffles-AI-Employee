#!/usr/bin/env python3
"""Fix Prepare Qdrant Point node to use UUID"""
import json
import sys

def fix_workflow(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    for node in workflow['nodes']:
        if node['name'] == 'Prepare Qdrant Point':
            node['parameters']['jsCode'] = """const chunk = $('Prepare Chunks').item.json;
const embedding = $('Get BGE Embeddings').item.json;

// embedding is array of arrays, get first
const vector = Array.isArray(embedding) ? embedding[0] : embedding;

// Generate UUID from doc_id and section_index
const str = chunk.metadata.doc_id + '-' + chunk.metadata.section_index;
const hash = str.split('').reduce((a, b) => {
    a = ((a << 5) - a) + b.charCodeAt(0);
    return a & a;
}, 0);

// Create UUID-like string
const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = (hash + Math.random() * 16) % 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
});

const point = {
    id: uuid,
    vector: vector,
    payload: {
        content: chunk.pageContent,
        metadata: chunk.metadata
    }
};

return [{ json: point }];"""
            print(f"Fixed node: {node['name']}")
            break
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ks_fix.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ks_fixed.json"
    fix_workflow(input_path, output_path)
