# CODEX_TASK_DEMO_SALON.md — Truth-first “Мира” (Phase 0 / Release Criteria)

## Контекст (обязательный)
Прод: **ACK-first + outbox** — ответы клиенту отправляются **только** при обработке outbox.

## Артефакты (истина)
Путь (предлагаемый):
`truffles-api/app/knowledge/demo_salon/`
- `POLICY.md`
- `SALON_TRUTH.yaml`
- `EVAL.yaml`
- `INTENTS_PHRASES_DEMO_SALON.yaml`
- `SYSTEM_PROMPT_DEMO_SALON.md`

## Цель
Сделать так, чтобы бот **уверенно закрывал базовую рутину** (адрес/график/цены/правила/акции) **даже при слабом RAG**, и эскалировал **только** по жёстким запретам/рискам.

---

## A) Реализовать Policy-Gate (самый первый шаг в пайплайне)
**До** любых RAG/LLM:
1) payment/предоплата/проверка оплат/возвраты → `ESCALATE_PAYMENT`
2) перенос записи/reschedule → `ESCALATE_RESCHEDULE`
3) discount_haggle → ответ без торга (цены фиксированные) + можно перечислить официальные акции
4) medical (беременность/аллергии/противопоказания) → `ESCALATE_MEDICAL`
5) complaint/негатив → `ESCALATE_COMPLAINT`

Критично: в ответах на payment **не перечислять способы оплаты**.

---

## B) Truth-first слой (до RAG)
Добавить детерминированные обработчики, которые отвечают **из SALON_TRUTH.yaml**:
- адрес / ориентиры / парковка
- график
- прайс (по названиям услуг + синонимы)
- правила: опоздание, можно ли с ребёнком/мужем/животными, прийти раньше
- стерилизация/бренды/подготовка (если есть в Truth)
- официальные акции

Если матч Truth найден → отвечаем без RAG.  
LLM допускается только как **перефразирование** (строго без добавления новых фактов).

---

## C) Склейка сообщений (coalescing) в outbox worker
Сейчас входящие обрабатываются по одному → теряется смысл (особенно “в 3 сообщения”).

Сделать буферизацию по `conversation_id`:
- собрать сообщения до “тишины” **6–10 секунд**
- затем одним запросом запускать пайплайн
- хранить буфер в Redis (TTL) или Postgres (pending batch)

---

## D) INTENTS_PHRASES_DEMO_SALON.yaml (фразы)
Использовать как быстрый keyword/phrase матч:
- для раннего распознавания payment/reschedule/booking/pricing/routine
- для off-topic (мягкий возврат к теме салона)

---

## E) Тесты (pytest) на EVAL.yaml
Добавить тест, который:
- читает `EVAL.yaml`
- прогоняет через “мозги” (можно через функцию-обёртку)
- проверяет:
  - `expected.action` = reply/escalate
  - `must_not` не встречается в ответе
  - если `must_include`/`must_include_any` — присутствует

---

## Acceptance (Phase 0 / Release Criteria)
- Все кейсы из `EVAL.yaml` проходят
- 0 ответов, где бот перечисляет способы оплаты/предоплату/«проверьте оплату»
- 0 обещаний переноса записи ботом
- База: адрес/график/прайс/правила отвечает даже при пустом RAG

---

## Где править (ориентиры по коду)
(Сверить по репо; названия из текущей архитектуры)
- `truffles-api/app/services/ai_service.py` — gate + generation
- `truffles-api/app/services/intent_service.py` — phrase matcher / router
- `truffles-api/app/services/outbox_service.py` (или воркер) — coalescing
- `truffles-api/app/routers/webhook.py` — state-machine/manager_active и вызов сервиса
