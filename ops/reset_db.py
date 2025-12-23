#!/usr/bin/env python3
import subprocess
sql = """
UPDATE conversations SET bot_status = 'active', bot_muted_until = NULL, no_count = 0;
UPDATE handovers SET status = 'resolved', resolved_at = NOW() WHERE status NOT IN ('resolved', 'timeout');
SELECT 'Reset done' as status;
"""
result = subprocess.run([
    'docker', 'exec', '-i', 'truffles_postgres_1',
    'psql', '-U', 'n8n', '-d', 'chatbot', '-c', sql
], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
