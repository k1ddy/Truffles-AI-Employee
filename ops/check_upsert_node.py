#!/usr/bin/env python3
import json

with open("/tmp/ks_v4.json") as f:
    d = json.load(f)

for n in d["nodes"]:
    if n["name"] == "Upsert to Qdrant":
        print("=== Upsert to Qdrant parameters ===")
        print(json.dumps(n["parameters"], indent=2))
    if n["name"] == "Prepare Qdrant Point":
        print("\n=== Prepare Qdrant Point code ===")
        print(n["parameters"].get("jsCode", "no code"))
