#!/usr/bin/env python3
"""Check recent traces"""
import subprocess

SQL = """
SELECT 
    id,
    to_char(created_at, 'HH24:MI:SS') as time,
    phone,
    intent,
    ROUND(rag_top_score::numeric, 2) as score,
    LEFT(message, 30) as msg,
    LEFT(response, 40) as resp,
    needs_escalation as esc
FROM message_traces 
ORDER BY created_at DESC 
LIMIT 10;
"""

cmd = f'docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "{SQL}"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout if result.stdout else result.stderr)
