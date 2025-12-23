#!/usr/bin/env python3
"""
Run test cases against Truffles bot.
Usage: python3 run_tests.py [--limit N]
"""
import requests
import json
import time
import sys
import argparse

N8N_URL = "https://n8n.truffles.kz"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY1MDc2NzQxfQ.vnXGUX7k77dUNlu0QTw4T6oxMlXAzbHVws4525CyU_4"

# Test phone number
TEST_PHONE = "77770000001"

def send_message(text):
    """Send message via webhook and get execution ID"""
    # Trigger Multi-Agent workflow via webhook
    webhook_url = f"{N8N_URL}/webhook/multi-agent"
    payload = {
        "channel": "test",
        "user_id": TEST_PHONE,
        "session_id": f"test-{int(time.time())}",
        "sender_name": "Test User",
        "buffered_messages": [text],
        "buffered_count": 1,
        "merged_text": text,
        "has_audio": False,
        "has_image": False,
        "last_message_type": "text"
    }
    
    try:
        r = requests.post(webhook_url, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()
        else:
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def get_latest_execution(workflow_id="4vaEvzlaMrgovhNz"):
    """Get latest execution for Multi-Agent workflow"""
    r = requests.get(
        f"{N8N_URL}/api/v1/executions?workflowId={workflow_id}&limit=1&includeData=true",
        headers={"X-N8N-API-KEY": API_KEY}
    )
    data = r.json()
    if data.get("data") and len(data["data"]) > 0:
        return data["data"][0]
    return None

def analyze_execution(execution):
    """Extract test results from execution"""
    if not execution:
        return None
    
    run_data = execution.get("data", {}).get("resultData", {}).get("runData", {})
    
    result = {
        "execution_id": execution.get("id"),
        "status": execution.get("status")
    }
    
    # Get intent from Classify Intent
    classify = run_data.get("Classify Intent", [{}])
    if classify and classify[0].get("data"):
        items = classify[0]["data"].get("main", [[]])[0]
        if items:
            output = items[0].get("json", {}).get("output", {})
            result["intent"] = output.get("intent")
    
    # Get RAG results
    rag = run_data.get("RAG Search", [{}])
    if rag and rag[0].get("data"):
        items = rag[0]["data"].get("main", [[]])[0]
        if items:
            json_data = items[0].get("json", {})
            result["rag_scores"] = json_data.get("rag_scores", [])
            result["knowledge"] = json_data.get("knowledge", "")[:500]
    
    # Get response
    prep = run_data.get("Prepare Response", [{}])
    if prep and prep[0].get("data"):
        items = prep[0]["data"].get("main", [[]])[0]
        if items:
            json_data = items[0].get("json", {})
            result["response"] = json_data.get("response", "")
            result["needs_escalation"] = json_data.get("needs_escalation", False)
    
    return result

def run_test(test):
    """Run single test case"""
    print(f"\n[Test {test['id']}] {test['question'][:50]}...")
    
    # Send message
    response = send_message(test["question"])
    
    if "error" in response:
        return {
            "test_id": test["id"],
            "passed": False,
            "error": response["error"]
        }
    
    # Wait a bit for execution to complete
    time.sleep(2)
    
    # Get execution results
    execution = get_latest_execution()
    results = analyze_execution(execution)
    
    if not results:
        return {
            "test_id": test["id"],
            "passed": False,
            "error": "Could not get execution results"
        }
    
    # Check results
    checks = []
    
    # Check intent
    if test.get("expected_intent"):
        intent_match = results.get("intent") == test["expected_intent"]
        checks.append(("intent", intent_match, test["expected_intent"], results.get("intent")))
    
    # Check RAG found expected content
    if test.get("should_find"):
        knowledge = results.get("knowledge", "")
        found = test["should_find"].lower() in knowledge.lower()
        checks.append(("rag_content", found, test["should_find"], "found" if found else "not found"))
    
    # Check escalation
    if test.get("should_escalate") is not None:
        escalated = results.get("needs_escalation", False)
        escalation_match = escalated == test["should_escalate"]
        checks.append(("escalation", escalation_match, test["should_escalate"], escalated))
    
    passed = all(c[1] for c in checks)
    
    return {
        "test_id": test["id"],
        "question": test["question"],
        "passed": passed,
        "checks": checks,
        "intent": results.get("intent"),
        "rag_scores": results.get("rag_scores", [])[:3],
        "response": results.get("response", "")[:100],
        "execution_id": results.get("execution_id")
    }

def main():
    parser = argparse.ArgumentParser(description="Run Truffles bot tests")
    parser.add_argument("--limit", type=int, help="Limit number of tests")
    parser.add_argument("--category", type=str, help="Run only specific category")
    parser.add_argument("--test-file", type=str, default="/home/zhan/truffles/tests/test_cases.json")
    args = parser.parse_args()
    
    # Load tests
    with open(args.test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    tests = data["tests"]
    
    if args.category:
        tests = [t for t in tests if t.get("category") == args.category]
    
    if args.limit:
        tests = tests[:args.limit]
    
    print(f"Running {len(tests)} tests...")
    print("=" * 60)
    
    results = []
    passed = 0
    failed = 0
    
    for test in tests:
        result = run_test(test)
        results.append(result)
        
        if result["passed"]:
            passed += 1
            print(f"  ✅ PASSED")
        else:
            failed += 1
            print(f"  ❌ FAILED")
            for check in result.get("checks", []):
                if not check[1]:
                    print(f"     {check[0]}: expected {check[2]}, got {check[3]}")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} passed ({100*passed/len(tests):.0f}%)")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    
    # Show failed tests
    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - [{r['test_id']}] {r.get('question', '')[:40]}...")
    
    # Save results
    output_file = "/tmp/test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to {output_file}")

if __name__ == "__main__":
    main()
