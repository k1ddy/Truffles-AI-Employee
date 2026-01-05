# ТЕХНИЧЕСКИЙ ROADMAP

**Цель:** управляемый LLM‑консультант для салонов с детерминированным ядром и “живым” ответом.

---

## КАНОН (не меняется)

1. **LAW‑гейты и truth‑first всегда.**
2. **Deterministic Core** для фактов (часы, адрес, услуги, цены, правила).
3. **LLM — для подачи и консультации**, не для бизнес‑решений.
4. **CORE‑eval в CI блокирует релиз**, long‑eval — отдельный tier.

---

## ПРИОРИТЕТЫ

### P0 — Детерминизм и релизная стабильность
- Base‑80 CORE: часы/адрес/услуги/цены/скидки/парковка/guest_policy без OpenAI.
- Taxonomy → Alias Expansion: ServiceSample расширяет aliases **только** для услуг салона.
- CI deploy без конфликтов; `/admin/version` всегда = HEAD.
- Core/long в CI раздельно; локальные тесты не являются gate.

### P1 — “Разумный хост”
- Goal‑stack и consult‑return при перебивках.
- Answer‑Interpreter: устойчивое понимание ответов клиента на вопрос бота.
- Router SLA <10% fallback с прозрачным `fallback_reason`.
- Long‑хаос 12–15 ходов в `EVAL_TIER=long`.

### P2 — Active Learning
- Очередь `learned_responses` + модерация.
- Калибровка по живым диалогам, tenant‑only, opt‑in.
- Метрики “где ломается” и регрессии.

### P3 — Enterprise слой
- Единый мониторинг качества (SLA/ошибки/регрессии).
- CRM/Calendar интеграции (Bitrix/Amo/Google Calendar).
- Версионирование client_pack и аудит фактов.

---

## ТЕКУЩИЙ СТАТУС (СВОДНО)

| Блок | Статус |
|------|--------|
| Base‑80 CORE | In Progress (E4xx фикс‑луп) |
| CI split core/long | ✅ Done |
| LLM Router + Answer‑Interpreter | ⚠️ Partial (SLA tuning) |
| Goal‑stack/consult‑return | ✅ Done |
| Active learning queue | 📋 Plan |
| Monitoring | ⚠️ Partial |

---

## БЛИЖАЙШИЕ ЗАДАЧИ (P0)

1. Закрыть Base‑80 CORE без OpenAI.
2. Авто‑обогащение aliases из ServiceSample для услуг салона.
3. Проверить стабильность CI‑deploy (без конфликтов контейнера).

---

*Обновлено: 2026-01-05*
