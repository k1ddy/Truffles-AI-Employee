---
description: Показать последние выполнения n8n workflows
arguments:
  - name: limit
    description: Количество (по умолчанию 5)
    required: false
---

Выполни SSH команду для получения последних executions через n8n API:

```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s -H 'X-N8N-API-KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMDE3ODI3YS01ODkzLTRjNDQtYTkwMC05ZDJlYzU0MmRlZTkiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY0MTkzNjI5fQ.I06M9VWLgBkZKCk14CqahwM3ntuvUn_VcA9XzEHQV0Q' 'https://n8n.truffles.kz/api/v1/executions?limit=${limit:-5}' | jq '.data[] | {id, status, startedAt, workflow: .workflowData.name}'"
```

Покажи результат.
