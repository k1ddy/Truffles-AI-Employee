#!/usr/bin/env python3
"""Detailed RAG quality check"""
import requests
import json
import sys

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "REDACTED_JWT"

def get_node_data(run_data, node_name):
    node = run_data.get(node_name, [{}])
    if node and node[0].get("data"):
        items = node[0]["data"].get("main", [[]])[0]
        if items:
            return items[0].get("json", {})
    return {}

def check_execution(exec_id):
    print(f"\n{'='*70}")
    print(f"EXECUTION {exec_id}")
    print('='*70)
    
    r = requests.get(
        f"{N8N_URL}/api/v1/executions/{exec_id}?includeData=true",
        headers={"X-N8N-API-KEY": API_KEY}
    )
    
    data = r.json()
    run_data = data.get("data", {}).get("resultData", {}).get("runData", {})
    
    # Build Context
    ctx = get_node_data(run_data, "Build Context")
    print(f"\n📱 ЗАПРОС: {ctx.get('message', 'N/A')}")
    print(f"📞 Телефон: {ctx.get('phone', 'N/A')}")
    print(f"🎯 Intent: {ctx.get('currentIntent', 'N/A')}")
    
    # RAG Search
    rag = get_node_data(run_data, "RAG Search")
    scores = rag.get("rag_scores", [])
    knowledge = rag.get("knowledge", "")
    
    print(f"\n📊 RAG SCORES: {scores}")
    if scores:
        print(f"   Max: {max(scores):.4f}, Min: {min(scores):.4f}, Avg: {sum(scores)/len(scores):.4f}")
    
    print(f"\n📚 RETRIEVED KNOWLEDGE:")
    print("-" * 50)
    # Split by document separator
    docs = knowledge.split("\n\n---\n\n") if knowledge else []
    for i, doc in enumerate(docs[:3]):  # Show first 3 docs
        print(f"\n[Doc {i+1}] (score: {scores[i] if i < len(scores) else 'N/A'}):")
        print(doc[:300] + "..." if len(doc) > 300 else doc)
    
    # Response
    resp = get_node_data(run_data, "Prepare Response")
    print(f"\n🤖 ОТВЕТ БОТА:")
    print("-" * 50)
    print(resp.get("response", "N/A"))
    
    thinking = resp.get("thinking", "")
    if thinking:
        print(f"\n💭 THINKING: {thinking[:300]}...")

if __name__ == "__main__":
    exec_ids = sys.argv[1:] if len(sys.argv) > 1 else ["762412", "762418"]
    for exec_id in exec_ids:
        check_execution(exec_id)
