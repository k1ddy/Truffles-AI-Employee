#!/usr/bin/env python3
import json
w = json.load(open('/tmp/callback.json'))

print("=== CONNECTIONS ===")
for src, conns in w.get('connections', {}).items():
    if 'main' in conns:
        for i, branch in enumerate(conns['main']):
            targets = [c.get('node') for c in branch]
            print(f"{src} [branch {i}] -> {targets}")

print("\n=== WEBHOOK NODE ===")
for n in w.get('nodes', []):
    if n['name'] == 'Telegram Webhook':
        print(json.dumps(n, indent=2, ensure_ascii=False))
