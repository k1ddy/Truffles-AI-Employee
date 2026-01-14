# SELLING_TRUTHS — ЧТО МОЖНО ГОВОРИТЬ НА САЙТЕ

**Формат:** Claim → Status → Proof → Boundary.
**Правило:** любое внешнее обещание должно быть в Capability Matrix ниже. Если пункта нет — статус FORBIDDEN.
**Связано с:** `STRATEGY/PRODUCT.md` (тарифы и обещания).

**Status legend:**
- LIVE: подтверждено в проде (evidence есть).
- BETA: работает частично/ограниченно, требуется подтверждение для каждого клиента.
- PLAN: не реализовано.
- FORBIDDEN: запрещено обещать.

---

## Capability Matrix (single source)

| Claim | Status | Proof | Boundary |
|-------|--------|-------|----------|
| “Бот не выдумывает факты” | BETA | §1 | Если факт отсутствует в Client Pack → уточнение/эскалация. |
| “Оплата/медицина/жалобы/перенос — только менеджер” | BETA | §2 | Способы оплаты только при policy‑gate из client_pack. |
| “Заявки уходят менеджеру в Telegram” | LIVE | §3 | Это заявка, не CRM‑запись. |
| “Сообщения не теряются (at‑least‑once)” | LIVE | §4 | Внешний риск у провайдера WhatsApp. |
| “Есть трассировка решений” | BETA | §5 | Trace не заменяет аналитику. |
| “Обновления знаний без разработчика” | BETA | §6 | Нужна ручная валидация перед публикацией. |
| “Данные клиента не уходят другим салонам без согласия” | BETA | §7 | Opt‑in только обезличенные агрегаты. |
| “Мы не дообучаем LLM на данных клиента” | LIVE | §8 | Качество зависит от полноты Client Pack. |

## 1) “Бот не выдумывает факты”
- Status: BETA
- Proof: truth‑first + policy‑gate в `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/routers/webhook/_legacy.py`; тесты в `truffles-api/app/knowledge/demo_salon/EVAL.yaml`.
- Boundary: если факт отсутствует в Client Pack → уточнение/эскалация.

## 2) “Оплата/медицина/жалобы/перенос — только менеджер”
- Status: BETA
- Proof: policy‑gate (payment actions/medical/complaint/reschedule) в `demo_salon_knowledge.py`, эскалация в webhook; EVAL кейсы.
- Boundary: способы оплаты можно перечислять **только** если это разрешено policy‑gate в client_pack.

## 3) “Заявки уходят менеджеру в Telegram”
- Status: LIVE
- Proof: `handovers` + Telegram topics, `truffles-api/app/services/escalation_service.py`, `truffles-api/app/routers/telegram_webhook.py`.
- Boundary: это **заявка**, а не автоматическая запись в CRM.

## 4) “Сообщения не теряются (at‑least‑once)”
- Status: LIVE
- Proof: ACK‑first + outbox retries (`outbox_messages`), inbound dedup (`message_dedup`), ChatFlow msg_id idempotency.
- Boundary: провайдер WhatsApp может не доставить сообщение — это внешний риск.

## 5) “Есть трассировка решений”
- Status: BETA
- Proof: `decision_trace` (conversation.context) + `decision_meta` (messages.metadata) + `/admin/metrics`.
- Boundary: трассировка описывает решение бота, но не заменяет бизнес‑аналитику.

## 6) “Обновления знаний без разработчика”
- Status: BETA
- Proof: Client Pack (`SALON_TRUTH.yaml`) + `ops/sync_client.py` для синка в Qdrant.
- Boundary: требуется ручная проверка/валидация перед публикацией.

## 7) “Данные клиента не уходят другим салонам без согласия”
- Status: BETA
- Proof: tenant isolation в RAG (`client_slug`), конфиг `clients.config.data_sharing` в `SPECS/MULTI_TENANT.md`.
- Boundary: при opt-in разрешены только обезличенные агрегаты (без PII и текстов сообщений).

## 8) “Мы не дообучаем LLM на данных клиента”
- Status: LIVE
- Proof: LLM использует RAG + Client Pack; изменения — через факты и policy, не через fine-tuning.
- Boundary: качество зависит от полноты Client Pack.

---

## Source Pack (копировать в внешние сервисы)

Использовать только факты ниже. **Не писать “AI/ИИ”**, продаём как “консультант + запись + эскалация”.
Пункты разрешены только при статусе LIVE/BETA из Capability Matrix.

- Продукт: управляемый консультант в WhatsApp для салонов красоты (консультация, запись, эскалация менеджеру).
- Клиентская ценность: ответ в любое время, без ожидания до утра.
- Бизнес‑ценность: бот закрывает типовые вопросы, менеджер подключается по правилам.
- Каналы: WhatsApp (клиенты) + Telegram (менеджер).
- Факты: адрес/часы/услуги/цены/правила — только из Client Pack (truth‑first).
- Запись: это **заявка**, не подтверждённый слот (без CRM — только сбор предпочтений).
- Жёсткие ограничения: оплата/медицина/жалобы/перенос → только менеджер (LAW‑gate).
- Скидки/оплата/алкоголь/гости/дети — только если разрешено в конфиге клиента.
- Данные: tenant‑only; opt‑in только агрегаты; PII и тексты не передаются в общий пул.
- Надёжность: сообщения не теряются (ACK‑first + outbox retries), но есть внешние риски у провайдера WhatsApp.
