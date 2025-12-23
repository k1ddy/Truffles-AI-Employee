#!/usr/bin/env python3
import subprocess
import sys

sql_file = sys.argv[1] if len(sys.argv) > 1 else "add_demo_salon_prompt.sql"

with open(f"/home/zhan/truffles/ops/{sql_file}") as f:
    sql = f.read()

result = subprocess.run([
    'docker', 'exec', '-i', 'truffles_postgres_1',
    'psql', '-U', 'n8n', '-d', 'chatbot'
], input=sql, capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)
