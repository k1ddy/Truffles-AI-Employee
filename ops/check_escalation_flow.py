#!/usr/bin/env python3
import json

with open('/tmp/escalation.json', 'r') as f:
    w = json.load(f)

print("=== NODES ===")
for n in w.get('nodes', []):
    print(f"  {n['name']}")

print("\n=== CONNECTIONS ===")
for src, conns in w.get('connections', {}).items():
    if 'main' in conns:
        for i, branch in enumerate(conns['main']):
            targets = [c.get('node') for c in branch]
            if targets:
                print(f"  {src} [{i}] -> {targets}")
