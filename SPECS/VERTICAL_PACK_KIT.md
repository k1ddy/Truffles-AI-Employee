# VERTICAL PACK KIT — Minimum Data Contract

**Статус:** CANON (minimum data contract + safe‑mode semantics)  
**Owner:** Top Architect  
**Обновлено:** 2026-02-02  
**Scope:** минимальный контракт данных для каждой вертикали и условия SAFE_MODE.  
**Out of scope:** pack‑данные, runtime‑реализация, миграции, LLM‑промпты.  
**Links:** `STRATEGY/REQUIREMENTS.md`, `docs/PROCESSES.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `STATE.md`.

---

## 1. Зачем нужен Minimum Data Contract

Минимальный контракт данных фиксирует **обязательные факты** для безопасных ответов.
Если контракт не выполнен → включается SAFE_MODE (FACT/COLLECT/HANDOFF only).

---

## 2. Minimum Data Contract (client_pack)

**Принцип:** факты только из pack; отсутствие любого обязательного поля = safe‑mode.

### 2.1 Обязательные разделы (канонические пути)

**Идентификация и локация**
- `client_pack.salon.name`
- `client_pack.salon.city`
- `client_pack.salon.address.full`

**Часы работы**
- `client_pack.salon.hours.days`
- `client_pack.salon.hours.open`
- `client_pack.salon.hours.close`

**Языки**
- `client_pack.salon.communication.languages` включает `ru` и `kk` (`kz` допускается как alias для `kk`).

**Услуги и цены**
- `client_pack.services_catalog.services`
- `client_pack.price_list`

**Длительности**
- `client_pack.service_duration_estimates` (каноническая карта длительностей).

**Booking базовые поля**
- `client_pack.booking.collect_fields`
- `client_pack.booking.bot_can_confirm`

**Policy‑gates**
- `client_pack.policy.hard_law`
- `client_pack.policy.payment_info`
- `client_pack.policy.reschedule`
- `client_pack.policy.cancel`
- `client_pack.policy.medical`
- `client_pack.policy.legal`
- `client_pack.policy.complaint`
- `client_pack.policy.discounts`
- `client_pack.policy.guard_topics.refund`

**Guest rules**
- `client_pack.guest_policy`

**Required disclaimers**
- `client_pack.safety.medical_note` (медицинские/противопоказания → только администратор/мастер)
- `client_pack.pricing.price_from_reason` (объяснение цены “от”)
- `client_pack.quality.expectations_photo` (ожидания/референс и ограничения результата)

---

## 3. RU/KZ варианты (multi‑lang)

**Обязательное для вертикали:**
- `client_pack.salon.communication.languages` содержит `ru` + `kk`.
- `domain_pack.service_taxonomy.categories[*]` содержит `label_ru/label_kk`, `includes_ru/includes_kk`, `synonyms_ru/synonyms_kk`.
- `domain_pack.lexicons` и anchors имеют RU/KK варианты (без кодовых словарей).

**Примечание:** детальная проверка RU/KK‑вариантов для всех user‑facing строк в `client_pack`
требует расширения схем/валидатора; до появления единой схемы фиксируется как GAP.

---

## 4. SAFE_MODE semantics

**Когда включается**
- Любое отсутствие обязательного поля Minimum Data Contract.
- Языки не включают `ru` + `kk`.

**Allowed outcomes**
- `FACT`, `COLLECT`, `HANDOFF` only.
- `FACT` — только из подтверждённых pack‑фактов; без inference и без booking‑commit.
- SAFE_MODE — только runtime fallback; он не может считаться статусом readiness/go-live для онбординга.
