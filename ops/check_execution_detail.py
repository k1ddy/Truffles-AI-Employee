#!/usr/bin/env python3
import requests
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

resp = requests.get(
    "https://n8n.truffles.kz/api/v1/executions/762641?includeData=true",
    headers={"X-N8N-API-KEY": API_KEY}
)
d = resp.json()

print("Status:", resp.status_code)
print("Keys:", list(d.keys())[:10])

# Find Parse Input and RAG Search results
data = d.get("data", {})
if isinstance(data, dict):
    result_data = data.get("resultData", {})
    run_data = result_data.get("runData", {})
    print("Nodes found:", list(run_data.keys())[:10] if run_data else "none")
    
    # Check Parse Input
    if "Parse Input" in run_data:
        try:
            pi = run_data["Parse Input"][0]["data"]["main"][0][0]["json"]
            print("Parse Input client_slug:", pi.get("client_slug"))
        except Exception as e:
            print("Parse Input error:", e)
    
    # Check RAG Search  
    if "RAG Search" in run_data:
        try:
            rag = run_data["RAG Search"][0]["data"]["main"][0][0]["json"]
            print("RAG Search client_slug:", rag.get("client_slug"))
            print("RAG scores:", rag.get("rag_scores"))
        except Exception as e:
            print("RAG Search error:", e)
else:
    print("Data is not dict:", type(data))
