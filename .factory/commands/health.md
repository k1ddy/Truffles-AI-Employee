---
description: Проверить статус системы (контейнеры, память, диск)
---

Выполни SSH команду для проверки статуса:

```bash
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "docker ps --format 'table {{.Names}}\t{{.Status}}' && echo '' && free -h | head -2 && echo '' && df -h / | tail -1"
```

Покажи статус всех контейнеров и ресурсов.
