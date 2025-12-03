# SESSION — Текущее состояние

**Обновлено:** 2025-12-03

---

## СТАТУС

| Компонент | Статус | Заметки |
|-----------|--------|---------|
| Инфраструктура | ✅ | Docker, n8n, PostgreSQL, Redis, Qdrant |
| Knowledge Sync | ✅ | 5 мин интервал, self-healing (проверка Qdrant) |
| Webhook приём | ✅ | ChatFlow.kz |
| WhatsApp отправка | ✅ | ChatFlow.kz |
| RAG (Qdrant) | ✅ | Чистые данные после пересинка |
| Основной бот | ⚠️ | Дубликаты сообщений |

---

## ТЕКУЩАЯ ПРОБЛЕМА

**Дубликаты сообщений** — бот отвечает несколько раз на одно сообщение.

Возможные причины:
- ChatFlow шлёт webhook повторно (retry при timeout)
- WhatsApp delivery/read receipts
- Логика бота где-то дублирует

**Следующий шаг:** Диагностика через n8n API — посмотреть executions, найти паттерн.

---

## ЧТО СДЕЛАНО СЕГОДНЯ

1. Knowledge Sync — добавлена проверка Qdrant (self-healing)
2. Cron изменён на 5 минут
3. [object Object] в промпте — исправлено (JSON.stringify)
4. Реструктуризация документов (AGENTS.md, SESSION.md)
5. **Реструктуризация сервера:**
   - infrastructure/ — traefik + website (изолировано)
   - secrets/ — сертификаты
   - truffles/ — n8n, postgres, redis, qdrant + документы
   - _trash/ — старые файлы
6. Все документы перенесены на сервер ~/truffles/docs/
7. Git инициализирован на сервере
8. GitHub Truffles-Chat-Bot обновлён (force push)
9. SSH ключ создан на сервере (нужно добавить в GitHub)
10. Droid установлен на сервере

---

## СЛЕДУЮЩЕЕ

1. Добавить SSH ключ сервера в GitHub
2. Диагностика дубликатов
3. Переименовать volumes (client_zero → truffles) — опционально
4. Тест бота end-to-end

---

## КАК РАБОТАТЬ

```bash
ssh -p 222 zhan@5.188.241.234
cd ~/truffles
droid
```

Всё в одном месте на сервере.

---

*Детальный план v3: см. PROJECT_PLAN.md*
