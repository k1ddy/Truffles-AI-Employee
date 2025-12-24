#!/usr/bin/env python3
"""Fix chunking - filter out short/meta sections"""
import requests
import json
import uuid

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"
WORKFLOW_ID = "zTbaCLWLJN6vPMk4"

# Download
print("Downloading workflow...")
r = requests.get(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers={"X-N8N-API-KEY": API_KEY}
)
workflow = r.json()

# Find Parse Sections node and update
for node in workflow["nodes"]:
    if node["name"] == "Parse Sections":
        node["parameters"]["jsCode"] = """const data = $json;
const text = data.raw_content;

const sections = [];
const lines = text.split('\\n');
let currentSection = null;
let currentContent = [];

for (const line of lines) {
  const h2Match = line.match(/^##\\s+(.+)/);
  const h1Match = line.match(/^#\\s+(.+)/);
  
  if (h2Match || h1Match) {
    if (currentSection && currentContent.length > 0) {
      sections.push({
        title: currentSection,
        content: currentContent.join('\\n').trim()
      });
    }
    currentSection = (h2Match || h1Match)[1].trim();
    currentContent = [];
  } else if (currentSection) {
    currentContent.push(line);
  }
}

if (currentSection && currentContent.length > 0) {
  sections.push({
    title: currentSection,
    content: currentContent.join('\\n').trim()
  });
}

// Filter out:
// 1. Sections shorter than 100 chars (was 20)
// 2. Sections that are mostly meta/notes (start with ** or contain only ---)
const validSections = sections.filter(s => {
  const content = s.content.trim();
  
  // Too short
  if (content.length < 100) return false;
  
  // Only separators
  if (content.replace(/-/g, '').trim().length < 50) return false;
  
  // Meta text (RAG notes, instructions)
  if (content.startsWith('**Для RAG') || content.startsWith('> **RAG')) return false;
  
  return true;
});

const chunks = validSections.map((section, index) => ({
  id: `${data.client_id}-${data.doc_id}-${index}`,
  text: `## ${section.title}\\n\\n${section.content}`,
  metadata: {
    client_id: data.client_id,
    doc_id: data.doc_id,
    doc_name: data.doc_name,
    section_title: section.title,
    section_index: index,
    source: 'google_docs',
    updated_at: new Date().toISOString()
  }
}));

return [{
  json: {
    ...data,
    chunks: chunks,
    chunks_count: chunks.length
  }
}];"""
        print("Updated Parse Sections node")
        break

# Upload
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
    print("SUCCESS!")
    print("Changes:")
    print("  - Min chunk size: 20 -> 100 chars")
    print("  - Filter out separator-only sections")
    print("  - Filter out RAG meta notes")
else:
    print(f"FAILED: {r.status_code}")
    print(r.text)
