#!/usr/bin/env python3
"""Fix summarization connections"""
import json
import sys

input_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/workflow_final.json'
output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/workflow_fixed.json'

with open(input_file, 'r', encoding='utf-8') as f:
    workflow = json.load(f)

# Fix Me2 - keep only first output
if 'Me2' in workflow['connections']:
    me2_conn = workflow['connections']['Me2']['main']
    if len(me2_conn) > 1:
        # Remove second output (to Prepare for Summary)
        workflow['connections']['Me2']['main'] = [me2_conn[0]]
        print("Fixed Me2 connections - removed invalid second output")

# Add connection: Prepare Response -> Prepare for Summary
# Check Escalation has two outputs: [0] = needs_escalation true, [1] = false
# We want to trigger summarization when needs_escalation = true
# So add from Check Escalation output 0 to Prepare for Summary

if 'Check Escalation' in workflow['connections']:
    check_esc = workflow['connections']['Check Escalation']['main']
    # Output 0 = needs_escalation true (goes to Me2)
    # Add Prepare for Summary to same output (parallel with Me2)
    if len(check_esc) > 0:
        # Check if already has Prepare for Summary
        has_summary = any(c['node'] == 'Prepare for Summary' for c in check_esc[0])
        if not has_summary:
            check_esc[0].append({
                "node": "Prepare for Summary",
                "type": "main",
                "index": 0
            })
            print("Added Prepare for Summary to Check Escalation output 0")

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)

print(f"Saved to {output_file}")
