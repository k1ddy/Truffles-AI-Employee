# Инструменты для Droid

## Выгрузка сообщений из БД

**Файл:** `Tech/get_messages.sql`

**Как использовать:**
```bash
scp -i C:\Users\user\.ssh\id_rsa -P 222 C:\Users\user\Downloads\TrufflesDocs\Truffles-AI-Employee\Tech\get_messages.sql zhan@5.188.241.234:/tmp/

ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234 "cat /tmp/get_messages.sql | docker exec -i client_zero_postgres_1 psql -U n8n -d truffles-chat-bot"
```

**Когда использовать:** Когда Жанбол говорит "покажи сообщения", "вытащи из БД", "что в базе".
