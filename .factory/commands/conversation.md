---
description: Показать последний разговор (диалог)
---

Выполни SSH команду для получения последнего разговора:

```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker exec truffles_postgres_1 psql -U n8n -d chatbot -c \"SELECT role, content, created_at FROM messages WHERE conversation_id = (SELECT id FROM conversations ORDER BY created_at DESC LIMIT 1) ORDER BY created_at\""
```

Покажи диалог в читаемом виде: кто что сказал.
