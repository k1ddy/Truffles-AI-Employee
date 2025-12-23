#!/usr/bin/env python3
"""
Test RAG quality directly (without n8n workflow).
Usage: python3 test_rag.py [--limit N] [--category CAT]
"""
import requests
import json
import argparse

BGE_URL = "http://172.24.0.8:80/embed"
QDRANT_URL = "http://172.24.0.3:6333"
QDRANT_KEY = "Iddqd777!"
COLLECTION = "truffles_knowledge"

def search_rag(query, limit=5):
    """Search RAG for query"""
    # Get embedding
    r = requests.post(BGE_URL, json={"inputs": query})
    vector = r.json()[0]
    
    # Search Qdrant
    r = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        json={"vector": vector, "limit": limit, "with_payload": True},
        headers={"api-key": QDRANT_KEY}
    )
    
    results = r.json().get("result", [])
    return [
        {
            "score": r["score"],
            "content": r["payload"].get("content", "")[:300],
            "doc_name": r["payload"].get("metadata", {}).get("doc_name", "")
        }
        for r in results
    ]

def run_test(test):
    """Run single RAG test"""
    results = search_rag(test["question"])
    
    # Check if expected content is found in top results
    should_find = test.get("should_find")
    
    if should_find is None:
        # Test expects no specific document (escalation, off-topic)
        return {
            "test_id": test["id"],
            "question": test["question"],
            "passed": True,
            "note": "No RAG check needed",
            "top_score": results[0]["score"] if results else 0
        }
    
    # Check if should_find is in any of top 3 results
    found = False
    found_in = None
    for i, r in enumerate(results[:3]):
        if should_find.lower() in r["content"].lower():
            found = True
            found_in = i + 1
            break
    
    return {
        "test_id": test["id"],
        "question": test["question"],
        "category": test.get("category"),
        "passed": found,
        "should_find": should_find,
        "found_in_position": found_in,
        "top_score": results[0]["score"] if results else 0,
        "top_3_scores": [r["score"] for r in results[:3]],
        "top_content": results[0]["content"][:100] if results else ""
    }

def main():
    parser = argparse.ArgumentParser(description="Test RAG quality")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--category", type=str, help="Run only specific category")
    parser.add_argument("--test-file", type=str, default="/home/zhan/truffles/tests/test_cases.json")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    args = parser.parse_args()
    
    # Load tests
    with open(args.test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tests = data["tests"]
    
    # Filter tests that have RAG expectations
    tests = [t for t in tests if t.get("should_find") is not None]
    
    if args.category:
        tests = [t for t in tests if t.get("category") == args.category]
    
    if args.limit:
        tests = tests[:args.limit]
    
    print(f"Running {len(tests)} RAG tests...")
    print("=" * 70)
    
    results = []
    passed = 0
    failed = 0
    scores = []
    
    for test in tests:
        result = run_test(test)
        results.append(result)
        scores.append(result["top_score"])
        
        status = "✅" if result["passed"] else "❌"
        print(f"{status} [{result['test_id']:2d}] {result['question'][:45]:<45} score={result['top_score']:.3f}")
        
        if result["passed"]:
            passed += 1
        else:
            failed += 1
            if args.verbose:
                print(f"      Expected: {result['should_find']}")
                print(f"      Got: {result['top_content']}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} passed ({100*passed/len(tests):.0f}%)")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"\nRAG Scores:")
    print(f"  Avg: {sum(scores)/len(scores):.3f}")
    print(f"  Min: {min(scores):.3f}")
    print(f"  Max: {max(scores):.3f}")
    
    # Group by category
    categories = {}
    for r in results:
        cat = r.get("category", "other")
        if cat not in categories:
            categories[cat] = {"passed": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1
    
    print("\nBy category:")
    for cat, stats in sorted(categories.items()):
        pct = 100 * stats["passed"] / stats["total"]
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")
    
    # Show failed tests
    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  [{r['test_id']:2d}] {r['question'][:50]}")
                print(f"       Expected: '{r['should_find']}'")
    
    # Save results
    output_file = "/tmp/rag_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results: {output_file}")

if __name__ == "__main__":
    main()
