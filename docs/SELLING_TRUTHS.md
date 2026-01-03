# SELLING_TRUTHS — ЧТО МОЖНО ГОВОРИТЬ НА САЙТЕ

**Формат:** Claim → Proof → Boundary.

---

## 1) “Бот не выдумывает факты”
- Proof: truth‑first + policy‑gate в `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/routers/webhook.py`; тесты в `truffles-api/app/knowledge/demo_salon/EVAL.yaml`.
- Boundary: если факт отсутствует в Client Pack → уточнение/эскалация.

## 2) “Оплата/медицина/жалобы/перенос — только менеджер”
- Proof: policy‑gate (payment actions/medical/complaint/reschedule) в `demo_salon_knowledge.py`, эскалация в webhook; EVAL кейсы.
- Boundary: способы оплаты можно перечислять **только** если это разрешено policy‑gate в client_pack.

## 3) “Заявки уходят менеджеру в Telegram”
- Proof: `handovers` + Telegram topics, `truffles-api/app/services/escalation_service.py`, `truffles-api/app/routers/telegram_webhook.py`.
- Boundary: это **заявка**, а не автоматическая запись в CRM.

## 4) “Сообщения не теряются (at‑least‑once)”
- Proof: ACK‑first + outbox retries (`outbox_messages`), inbound dedup (`message_dedup`), ChatFlow msg_id idempotency.
- Boundary: провайдер WhatsApp может не доставить сообщение — это внешний риск.

## 5) “Есть трассировка решений”
- Proof: `decision_trace` (conversation.context) + `decision_meta` (messages.metadata) + `/admin/metrics`.
- Boundary: трассировка описывает решение бота, но не заменяет бизнес‑аналитику.

## 6) “Обновления знаний без разработчика”
- Proof: Client Pack (`SALON_TRUTH.yaml`) + `ops/sync_client.py` для синка в Qdrant.
- Boundary: требуется ручная проверка/валидация перед публикацией.

## 7) “Данные клиента не уходят другим салонам без согласия”
- Proof: tenant isolation в RAG (`client_slug`), конфиг `clients.config.data_sharing` в `SPECS/MULTI_TENANT.md`.
- Boundary: при opt-in разрешены только обезличенные агрегаты (без PII и текстов сообщений).

## 8) “Мы не дообучаем LLM на данных клиента”
- Proof: LLM использует RAG + Client Pack; изменения — через факты и policy, не через fine-tuning.
- Boundary: качество зависит от полноты Client Pack.
