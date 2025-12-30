# SELLING_TRUTHS — ЧТО МОЖНО ГОВОРИТЬ НА САЙТЕ

**Формат:** Claim → Proof → Boundary.

---

## 1) “Бот не выдумывает факты”
- Proof: truth‑first + policy‑gate в `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/routers/webhook.py`; тесты в `truffles-api/app/knowledge/demo_salon/EVAL.yaml`.
- Boundary: если факт отсутствует в Client Pack → уточнение/эскалация.

## 2) “Оплата/медицина/жалобы — только админ”
- Proof: policy‑gate (payment/medical/complaint) в `demo_salon_knowledge.py`, эскалация в webhook; EVAL кейсы.
- Boundary: правило работает при корректных policy‑настройках клиента.

## 3) “Заявки уходят менеджеру в Telegram”
- Proof: `handovers` + Telegram topics, `truffles-api/app/services/escalation_service.py`, `truffles-api/app/routers/telegram_webhook.py`.
- Boundary: это **заявка**, а не автоматическая запись в CRM.

## 4) “Сообщения не теряются”
- Proof: ACK‑first + outbox retries (`outbox_messages`), inbound dedup (`message_dedup`), ChatFlow msg_id idempotency.
- Boundary: провайдер WhatsApp может не доставить сообщение — это внешний риск.

## 5) “Бот отвечает быстро и стабильно”
- Proof: `/admin/metrics` даёт p50/p90 (outbox_latency_*); замеры в `STATE.md`.
- Boundary: время зависит от LLM/ChatFlow/Qdrant; без гарантий “мгновенно”.

## 6) “Мультитенантность и изоляция данных”
- Proof: фильтры по `client_slug` в RAG (`knowledge_service.py`) и сервис‑индексе, routing по client_slug.
- Boundary: формальные тесты на leakage ещё не оформлены.

## 7) “Обновления знаний без разработчика”
- Proof: Client Pack (`SALON_TRUTH.yaml`) + `ops/sync_client.py` для синка в Qdrant.
- Boundary: требуется ручная проверка/валидация перед публикацией.

## 8) “Есть трассировка решений”
- Proof: `decision_trace` (conversation.context) + `decision_meta` (messages.metadata) + `/admin/metrics`.
- Boundary: трассировка описывает решение бота, но не заменяет бизнес‑аналитику.
