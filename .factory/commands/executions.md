---
description: Показать последние выполнения n8n workflows
arguments:
  - name: limit
    description: Количество (по умолчанию 5)
    required: false
---

Выполни SSH команду для получения последних executions через n8n API:

```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "curl -s -H 'X-N8N-API-KEY: <REDACTED>_JWT' 'https://n8n.truffles.kz/api/v1/executions?limit=${limit:-5}' | jq '.data[] | {id, status, startedAt, workflow: .workflowData.name}'"
```

Покажи результат.
