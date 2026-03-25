---
description: Показать последние ошибки
arguments:
  - name: limit
    description: Количество (по умолчанию 5)
    required: false
---

Выполни SSH команду для получения последних ошибок:

```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec truffles_postgres_1 psql -U n8n -d chatbot -c 'SELECT * FROM error_logs ORDER BY created_at DESC LIMIT ${limit:-5}'"
```

Покажи ошибки и проанализируй что могло пойти не так.
