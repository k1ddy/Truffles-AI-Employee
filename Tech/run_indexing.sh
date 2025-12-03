#!/bin/bash
# Скрипт для запуска индексации FAQ в Qdrant

API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY0MTkzNjI5fQ.I06M9VWLgBkZKCk14CqahwM3ntuvUn_VcA9XzEHQV0Q"
N8N_URL="http://172.22.0.4:5678"

echo "=== Поиск workflow cronUpdateDocs ==="
WORKFLOWS=$(curl -s -H "X-N8N-API-KEY: $API_KEY" "$N8N_URL/api/v1/workflows?limit=100")
echo "$WORKFLOWS" | jq -r '.data[] | "\(.id) \(.name) active=\(.active)"' | grep -i "update\|cron\|rag"

echo ""
echo "=== Запуск workflow ==="
# Попробуем найти и запустить
WF_ID=$(echo "$WORKFLOWS" | jq -r '.data[] | select(.name | test("cronUpdate|UpdateDocs"; "i")) | .id' | head -1)

if [ -n "$WF_ID" ]; then
    echo "Found workflow ID: $WF_ID"
    curl -s -X POST -H "X-N8N-API-KEY: $API_KEY" -H "Content-Type: application/json" "$N8N_URL/api/v1/workflows/$WF_ID/run"
else
    echo "Workflow not found. Listing all workflows:"
    echo "$WORKFLOWS" | jq -r '.data[] | "\(.id) \(.name)"'
fi
