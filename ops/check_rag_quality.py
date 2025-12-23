#!/usr/bin/env python3
"""Check RAG quality from executions"""
import requests
import json
import sys

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

def check_execution(exec_id):
    print(f"\n{'='*60}")
    print(f"EXECUTION {exec_id}")
    print('='*60)
    
    r = requests.get(
        f"{N8N_URL}/api/v1/executions/{exec_id}",
        headers={"X-N8N-API-KEY": API_KEY}
    )
    
    data = r.json()
    run_data = data.get("data", {}).get("resultData", {}).get("runData", {})
    
    # Get user message from Build Context
    build_ctx = run_data.get("Build Context", [{}])
    if build_ctx and build_ctx[0].get("data"):
        items = build_ctx[0]["data"].get("main", [[]])[0]
        if items:
            ctx = items[0].get("json", {})
            print(f"\n📱 USER MESSAGE: {ctx.get('message', 'N/A')}")
            print(f"📞 PHONE: {ctx.get('phone', 'N/A')}")
    
    # Get RAG results
    rag_node = run_data.get("RAG Search", [{}])
    if rag_node and rag_node[0].get("data"):
        items = rag_node[0]["data"].get("main", [[]])[0]
        if items:
            rag = items[0].get("json", {})
            scores = rag.get("rag_scores", [])
            knowledge = rag.get("knowledge", "")
            
            print(f"\n📊 RAG SCORES: {scores}")
            print(f"\n📚 KNOWLEDGE (first 500 chars):")
            print(knowledge[:500] if knowledge else "(empty)")
    
    # Get bot response
    prep_resp = run_data.get("Prepare Response", [{}])
    if prep_resp and prep_resp[0].get("data"):
        items = prep_resp[0]["data"].get("main", [[]])[0]
        if items:
            resp = items[0].get("json", {})
            print(f"\n🤖 BOT RESPONSE: {resp.get('response', 'N/A')}")
            print(f"💭 THINKING: {resp.get('thinking', 'N/A')[:200] if resp.get('thinking') else 'N/A'}")

if __name__ == "__main__":
    exec_ids = sys.argv[1:] if len(sys.argv) > 1 else ["762412", "762418"]
    for exec_id in exec_ids:
        check_execution(exec_id)
