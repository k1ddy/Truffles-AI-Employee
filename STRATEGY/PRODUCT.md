# ПРОДУКТ TRUFFLES (v2)

**Статус:** CANON
**Owner:** Жанбол
**Обновлено:** 2026-05-09
**Scope:** что продаём, go-live scope, тарифы, что НЕ обещаем, границы функционала.
**Out of scope:** реализация, внутренняя архитектура, “как именно работает” (см. SPECS).
**Links:** `docs/PRODUCT_SYSTEM_CANON.md`, `docs/DECISION_LEDGER.yaml`, `docs/SELLING_TRUTHS.md`, `STRATEGY/REQUIREMENTS.md`.

---

## Elevator pitch (как объяснять)

> Truffles — это платформа виртуального консультанта для сервисного бизнеса. Для клиента она выглядит как консультант в активном клиентском канале: отвечает по **фактам бизнеса**, собирает запись и, если не уверен или нужен человек, **сразу переводит на менеджера**.

Ключевой акцент: **LLM policy core + hard‑safety/policy слой**, а не “просто чатбот”.

---

## Что продаём на самом деле

Truffles — это не только runtime-бот. Канонический продукт состоит из четырёх связанных частей:

- **Consultant Runtime** — клиентский диалог в канале, который доводит разговор до `FACT / COLLECT / HANDOFF`.
- **Console Plane** — основной GUI для `Platform Admin`, `Platform Support`, `Owner`, `Admin`, `Manager`.
- **Knowledge / Data Plane** — tenant-scoped знания, capabilities, published packs, интеграции и изоляция данных.
- **Observability / Ops Plane** — health, alerts, traces, metrics, audit и deploy discipline.

## Первый go-live vertical — Beauty Salon v1

Первый коммерческий продукт Truffles:
- **салоны красоты** как beauty-first vertical на общей multi-tenant платформе.

Что обязано работать в `Beauty Salon v1`:
- **Runtime:** консультант в активном клиентском канале отвечает по фактам бизнеса (`адрес`, `часы`, `услуги`, `цены`, `длительность`, `мастера`, `правила`) и ведёт к следующему шагу.
- **Booking intake:** собираются `услуга`, `дата/время`, `имя`, и при необходимости контактные данные.
- **Booking commit:** запись создаётся в Console Calendar/Postgres `appointments`; Google Calendar/CRM — внешняя проекция или источник занятости, а не обязательный календарь.
- **Handoff:** передача менеджеру идёт со статусом и контекстом, а не как немой сброс.
- **Console Plane:** onboarding, provisioning, publish, activation, inbox, support и ops-диагностика доступны через основной web-интерфейс.
- **Observability / Ops:** build fingerprint, health, alerts, logs, traces, metrics и audit обязательны для production.

Что не входит в `Beauty Salon v1`:
- универсальный ассистент “на все темы”;
- платежи, возвраты и банковские операции;
- медицинские или юридические советы;
- выдуманные факты, цены, скидки, способы оплаты;
- обещание свободных слотов без внутреннего Console Calendar или подключённого provider доступности;
- обещание WhatsApp/Chatflow go-live, пока provider коммерчески недоступен или не оплачен;
- переписывание core под каждую новую нишу вместо `packs + tools + capabilities`.

Platform scaling rule:
- core is a reusable business capability platform;
- Beauty Salon v1 is the first proof vertical;
- future sales, retail, clinic, education, repair, or other service/product niches must enter through packs, capabilities, tools, data contracts, Console readiness, and observability proof;
- no niche may become a hidden core branch, regex path, or second semantic owner.

---

## Beauty Salon v1 Go-Live Acceptance Map

`Beauty Salon v1` нельзя считать готовым по одному зелёному runtime path. Для go-live каждая обязательная capability должна иметь proof в нужных planes.

| Capability | Что должно работать | Required planes | Minimum proof |
|------|----------------|-----------------|---------------|
| Fact answers | адрес, часы, услуги, цены, длительность, мастера, правила | Runtime + Knowledge/Data + Ops | runtime exact proof; trace/meta; факты только из pack/tool; observability на inbound |
| Booking intake | сбор `service -> datetime -> name -> phone if needed` без потери continuity | Runtime + Ops | representative booking matrix; `raw owner = green`; `final runtime = green`; `rescue = no` |
| Exact booking commit | запись создаётся через Console Calendar/Postgres или через явно подключённый provider | Runtime + Knowledge/Data + Ops | tool-backed commit proof; appointment row; trace/tool outcome; no fake slot promises |
| Handoff | передача менеджеру со статусом и контекстом | Runtime + Console + Ops | visible handoff state; manager context; outbox/provider proof; no silent drop |
| Onboarding / provisioning | новый клиент/филиал проходит путь до активного статуса без ручной магии | Console + Knowledge/Data + Ops | provisioning wizard/go-no-go gate; published pack; activation evidence; rollback path |
| Knowledge publish | draft -> validate -> publish -> rollback работает fail-closed | Console + Knowledge/Data + Ops | validation proof; publish history; rollback proof; invalid knowledge cannot go live |
| Inbox / support workflow | операторы и support видят контекст, статус, диагностику | Console + Ops | inbox visibility; role-based access; diagnostics gated; audit trail |
| Tenant isolation / RBAC | нет cross-tenant access и нет неявного tenant context | Console + Knowledge/Data + Ops | selection_required / branch_selection_required; tenant-scoped data access; audit evidence |
| Production readiness | deploy, health, traces, metrics, alerts, workers, fingerprint | Ops + Runtime + Console | immutable deploy; build fingerprint; health/readiness; correlated logs/traces/metrics; worker/outbox proof |

Эта таблица задаёт общий go-live oracle. Если строка не имеет нужного proof surface, продукт не готов, даже если отдельные paths выглядят зелёными.

---

## Граница обещаний (нельзя продавать)

**НЕЛЬЗЯ обещать клиентам и запрещено делать в продукте:**
- подтверждение/проверка оплат, возвраты, банковские операции (Hard‑LAW) → только эскалация;
- медицинские советы/противопоказания/аллергии/ожоги/кровь → только эскалация;
- скидки/способы оплаты — только если явно разрешено правилами в client_pack;
- “точные свободные слоты” без внутреннего Console Calendar или подключённого календаря/CRM → не обещать; только сбор предпочтений.
- WhatsApp/Chatflow как доступный production channel, пока коммерческий доступ не восстановлен и внешний canary не прошёл.
- ночью — только статус/ack без обещаний времени ответа; полный ответ в рабочие часы.

Другие verticals:
- возможны только после `Beauty Salon v1` и только как расширение общей платформы через `packs + tools + capabilities`.
- перед новым vertical required: capability map, data/tool contracts, acceptance pack, Console/Ops readiness mapping, and Decision Ledger entry.

---

## Тарифы

### Starter — 50,000 ₸/месяц

**Для кого:** малый бизнес, который теряет заявки в WhatsApp ночью/в выходные.

| Фича | Включено |
|------|----------|
| Консультант 24/7 (ночью статус/ack) | ✅ |
| Номеров WhatsApp | 1 |
| Сообщений/месяц | 1,000 |
| Data packs (client_pack/domain_pack) | ✅ |
| Эскалация менеджеру (Telegram‑UI) | ✅ |
| Русский + казахский | ⚠️ частично (по факту в `STATE.md`) |
| Настройка | 1–3 дня (BETA, best-effort) |
| Поддержка | Email, до 48ч (BETA, best-effort) |

**Чего нет:** dashboard, active learning (авто), CRM/Calendar интеграции, подтверждение оплат.

---

### Средний — 100,000 ₸/месяц (ПЛАН)
> ⚠️ Не продаём, пока нет evidence в `STATE.md`.

- 2 номера WhatsApp / филиалы
- базовая аналитика
- ручное обучение через очередь модерации

---

### Pro — 150,000 ₸/месяц (ПЛАН)
> ⚠️ Не продаём, пока нет evidence в `STATE.md`.

- расширенная аналитика
- интеграции (CRM/Calendar)
- авто + ручное обучение

---

### Enterprise — по запросу

- on‑premise или выделенный контур
- строгая изоляция, аудит, SLA (без обещаний минут/часов)
- кастомные интеграции

---

## Скидки

- Годовая оплата: 10% (если политика не изменена).

---

## Roadmap (правило)

- **Даты не обещаем.**
- Конкретный статус “сделано/не сделано” фиксируется только в `STATE.md` (с evidence).
- `STRATEGY/TECH_ROADMAP.md` — техническая карта развития.

---

## Связь с документацией

- Канон/суть: `STRATEGY/VISION.md`
- Поведение бота: `SPECS/CONSULTANT.md`
- Эскалация: `SPECS/ESCALATION.md`
- Мультитенант/филиалы: `SPECS/MULTI_TENANT.md`
- Инфра/качество: `SPECS/INFRASTRUCTURE.md`
- Тех. развитие: `STRATEGY/TECH_ROADMAP.md`
- Внешние обещания: `docs/SELLING_TRUTHS.md`
