#!/bin/bash
API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY0MTkzNjI5fQ.I06M9VWLgBkZKCk14CqahwM3ntuvUn_VcA9XzEHQV0Q"
N8N_URL="http://172.22.0.4:5678"

echo "=== Последние executions ==="
curl -s -H "X-N8N-API-KEY: $API_KEY" "$N8N_URL/api/v1/executions?limit=30" | jq -r '.data[] | "\(.id) \(.workflowId) \(.startedAt)"' | head -20

echo ""
echo "=== Workflows ==="
curl -s -H "X-N8N-API-KEY: $API_KEY" "$N8N_URL/api/v1/workflows?limit=50" | jq -r '.data[] | "\(.id) \(.name)"' | grep -iE "whatsapp|chat|message|webhook|adapter"
