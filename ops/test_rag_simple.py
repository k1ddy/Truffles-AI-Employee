#!/usr/bin/env python3
"""
Simple RAG test - just show what's found and scores.
Usage: python3 test_rag_simple.py [--limit N]
"""
import requests
import json
import argparse

BGE_URL = "http://172.24.0.8:80/embed"
QDRANT_URL = "http://172.24.0.3:6333"
QDRANT_KEY = "REDACTED_PASSWORD"
COLLECTION = "truffles_knowledge"

SCORE_THRESHOLD = 0.45  # Below this = poor match

def search_rag(query, limit=3):
    """Search RAG for query"""
    r = requests.post(BGE_URL, json={"inputs": query})
    vector = r.json()[0]
    
    r = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        json={"vector": vector, "limit": limit, "with_payload": True},
        headers={"api-key": QDRANT_KEY}
    )
    
    results = r.json().get("result", [])
    return [
        {
            "score": r["score"],
            "doc": r["payload"].get("metadata", {}).get("doc_name", "?"),
            "section": r["payload"].get("metadata", {}).get("section_title", "?"),
            "preview": r["payload"].get("content", "")[:80].replace("\n", " ")
        }
        for r in results
    ]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=45)
    parser.add_argument("--test-file", type=str, default="/home/zhan/truffles-main/tests/test_cases.json")
    args = parser.parse_args()
    
    with open(args.test_file, 'r', encoding='utf-8') as f:
        tests = json.load(f)["tests"][:args.limit]
    
    print(f"{'ID':<3} {'Score':<6} {'Doc':<15} {'Section':<25} Question")
    print("=" * 100)
    
    good = 0
    poor = 0
    scores = []
    
    for t in tests:
        results = search_rag(t["question"])
        if not results:
            continue
        
        top = results[0]
        scores.append(top["score"])
        
        status = "✅" if top["score"] >= SCORE_THRESHOLD else "⚠️"
        if top["score"] >= SCORE_THRESHOLD:
            good += 1
        else:
            poor += 1
        
        doc = top["doc"].replace(".md", "")[:14]
        section = top["section"][:24]
        q = t["question"][:35]
        
        print(f"{status} {t['id']:<2} {top['score']:.3f}  {doc:<14} {section:<24} {q}")
    
    print("=" * 100)
    print(f"\nScore >= {SCORE_THRESHOLD}: {good} ({100*good/(good+poor):.0f}%)")
    print(f"Score <  {SCORE_THRESHOLD}: {poor} ({100*poor/(good+poor):.0f}%)")
    print(f"\nAvg: {sum(scores)/len(scores):.3f}, Min: {min(scores):.3f}, Max: {max(scores):.3f}")

if __name__ == "__main__":
    main()
