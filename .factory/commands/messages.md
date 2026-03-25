---
description: Показать последние сообщения из БД
arguments:
  - name: limit
    description: Количество сообщений (по умолчанию 10)
    required: false
---

Выполни SSH команду для получения последних сообщений:

```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec truffles_postgres_1 psql -U n8n -d chatbot -c 'SELECT created_at, role, LEFT(content, 80) as content FROM messages ORDER BY created_at DESC LIMIT ${limit:-10}'"
```

Покажи результат в читаемом виде.
