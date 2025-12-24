#!/usr/bin/env python3
import os
import subprocess
import sys

sql_file = sys.argv[1] if len(sys.argv) > 1 else "add_demo_salon_prompt.sql"

with open(f"/home/zhan/truffles-main/ops/{sql_file}") as f:
    sql = f.read()

db_user = os.environ.get("DB_USER", "postgres")

result = subprocess.run([
    'docker', 'exec', '-i', 'truffles_postgres_1',
    'psql', '-U', db_user, '-d', 'chatbot'
], input=sql, capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print("Errors:", result.stderr)
