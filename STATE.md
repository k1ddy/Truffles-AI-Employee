# STATE — Состояние проекта

**Центральный хаб. Обновляется каждую сессию.**

---

## СЕССИОННЫЙ СНИМОК (читать первым)

**NOW (1 экран)**
- DONE: Webhook refactor checkpoint — модульный пакет `truffles-api/app/routers/webhook/` (PR #92‑#107 merged).
- DONE: Low-signal guard → off-topic reply (PR #108 merged; E744/E745 in core).
- DONE: Small talk ответы → коротко + мягкий редирект (greeting/thanks/ack).
- DONE: PR #109 (diagnose + smalltalk) и PR #111 (docs sync) merged; CI main зелёный.
- DONE: P0 offline устойчивость без `OPENAI_API_KEY` (offline controller fixed + test; PR #112 merged; CI main зелёный).
- DONE: Session Memory v1.1 reset на pending/manager (PR #114 merged; CI main зелёный).
- DONE: A1 shadow Decision Graph plan + roadmap hybrid/tools pinned (PR #117 https://github.com/k1ddy/Truffles-AI-Employee/pull/117; CI run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20890721660).
- DONE: Decision Graph stage trace skeleton (PR #118 https://github.com/k1ddy/Truffles-AI-Employee/pull/118; CI run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20890910843).
- DONE: A2 Decision Graph contract schemas (PR #119 https://github.com/k1ddy/Truffles-AI-Employee/pull/119; CI run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20890983862).
- DONE: TraceContract validation for decision trace payloads (PR #120 https://github.com/k1ddy/Truffles-AI-Employee/pull/120; CI run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20891043940).
- DONE: Context/intent contract validation in trace (PR #121 https://github.com/k1ddy/Truffles-AI-Employee/pull/121; CI run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20891209266).
- DONE: Fact/action/response contract validation in trace (PR #122 https://github.com/k1ddy/Truffles-AI-Employee/pull/122; CI run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20891463080).
- DONE: A6 policy rules‑as‑data (PR #131 merged; CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20894731972; live‑check conv_id b8c559d1-f8cd-4173-ae70-0a9683833e48, trace policy_gate=discounts + risk_level=low).
- DONE: A7 observability + budget gate + ASR tier (PR #133 merged; CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20895474177).
- DONE: A7 live‑budget verification in prod (SQL fallback on demo_salon; llm_budget.daily_max_calls=1) — evidence в истории 2026‑01‑11.
- DONE: Pending SLA ping spam fix (PR #147 merged; CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20922178070).
- DONE: No-response alert dedup cleanup + shield_drop suppression order (PR #154 merged; CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20944545548; live-check conv_id b8c559d1-f8cd-4173-ae70-0a9683833e48, msg_id 88173fb2-20f7-4c25-93dc-fd050a2ed248 shield_drop too_long; /reminders/process alerted=0).
- DONE: Consult clarify/short‑circuit (PR #153 merged; CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20943384712; live‑check evidence in истории 2026‑01‑13).
- DONE: PR #155 consult pack‑only + pending_wait trace merged; CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20945722911; live‑check evidence в истории 2026‑01‑13.
- DONE: truth_gate trace retention for pricing/duration/location (PR #180 merged; CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21013363387; live‑check conv_id b8c559d1-f8cd-4173-ae70-0a9683833e48, msg_id c921d20c-57d2-4778-aa83-b66c458f0b90 pricing, msg_id debe8959-cdc2-4716-ba86-5ae6431d7400 duration, msg_id 6847ad45-774a-4662-b20a-d6b6ebed16b3 location).
- DONE: Telegram→WhatsApp topic handover routing fix (PR #157 merged; CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20948893145; live‑check в истории 2026‑01‑13).
- DONE: Docs PR #158 (roadmap + tech status) merged; CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20949202225.
- DONE: P0 Legacy slice 5 — вынесены domain flows (booking/info/consult) без изменения поведения; CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21050469012; live‑check (prod) conv_id b8c559d1-f8cd-4173-ae70-0a9683833e48: msg_id cd3625fc-d16c-4c2b-832f-2d0b7c3e0dcd (info_bundle) decision_meta action=reply intent=location source=truth_gate info_sections=["address","hours","parking"]; msg_id 6d78cf61-cb15-4f4f-b121-6fb91d579658 (consult) decision_meta action=reply intent=consult_reply source=pack consult_playbook_id=hair_aftercolor; decision_trace stages truth_gate reply/location + consult_flow/consult reply consult_reply source=pack.
- BLOCKED: P0 Legacy slice 6 — вынесены LLM/response + post‑hooks (llm_guard/ai_response/rewrite/budget_gate/llm_degradation + consult_return) без изменения поведения; CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21051820513; live‑check consult_return conv_id b8c559d1-f8cd-4173-ae70-0a9683833e48 msg_id 1d3515d6-9dbc-4dea-9479-a5532d011a93 decision_meta consult_return=true; live‑check LLM‑path conv_id 590848f8-423c-4118-9de0-5f830c643a46 msg_id 99087746-9dcb-4785-804c-e90a32f3c930 decision_meta action=ai_response llm_degradation_reason=llm_skip; decision_trace stages rewrite(timeout) + llm_degradation(llm_skip) + ai_response(low_confidence_retry); BLOCKED: llm_guard/budget_gate не сработали (нет условий).
- BLOCKERS: нет.

- **Фокус:** P0 Ops hygiene (instanceId inbound, outbox latency, deploy latest CI image); дальше webhook не дробим.
- **Источник:** анализы из сессии зафиксированы в `STATE.md`; “не записано = не существует”.
- **Следующий шаг:** P1 follow-up — router_eligible sync с controller_attempted (CI + real inbound + SQL) — in progress.
- **DONE:** P1 Router SLA <10% + controller_attempted evidence (post-deploy real inbound) — см. запись 2026-01-14.
- **DONE:** P1 Category vs Service (services_overview guard) — см. запись 2026-01-14.
- **DONE:** GAP-017 Branch isolation evidence (branch_routing + RAG fallback + policy_gate + demo handover/Telegram) — см. запись 2026-01-14.
- **OPEN:** Outbox latency (P0 tail) — в конце.
- **TODO:** Real WA inbound live-check (ChatFlow) для PR #143 — pending.
- **Решение pending:** “полная перестройка системы” — требует отдельного решения в `docs/IMPERIUM_DECISIONS.yaml` и нового DoD.
- **Автоматизация проверки:** `ops/diagnose.py` расширен (version/health/metrics/outbox/decision_meta), ссылка в `docs/TECH_STATUS.md`.
- **Последняя диагностика:** 2026-01-08T15:46:51Z (ops/diagnose.py: outbox FAILED 12 / SENT 1235; `OUTBOX_WORKER_ENABLED=MISSING`; `/admin/version` `487a6ff9...`).

**IMPERIUM DoD (short)**
- Truth-first: ответ только из KB/правил; догадки запрещены; LAW/оплата/медицина/жалобы → эскалация.
- LLM = смысл (класс/цель/слоты), gates = контроль; low-signal/OOD → мягкий редирект.
- Booking-first: держим цель, допускаем 1–2 факта и возвращаемся к записи.
- Small talk: короткий ответ + мягкий редирект к салону/записи.
- Clarify policy: максимум 2 уточнения, дальше эскалация/hand over.
- Gates: CI core/long/ASR зелёные, offline без ключа, метрики/trace пишутся всегда.
## ТЕКУЩЕЕ СОСТОЯНИЕ

⚠️ Требует проверки: факты ниже нужно подтверждать через API/DB/логи, не полагаться на записи.
⚠️ Любая задача/риск в STATE — гипотеза до evidence; без проверки фиксы не делаем.

### БАЗОВЫЕ ФАКТЫ (читать первым делом)
- Verified 2025-12-31 (Evidence: `/admin/version` + `/admin/metrics` updated; see entries below).
- Рабочая среда — прод: `/home/zhan/truffles-main` (любые действия считаются продовыми).
- Тесты запускать внутри контейнера `truffles-api`: `docker exec -i truffles-api pytest ...` (на хосте python может отсутствовать).
- Источник истины по деплою/коммиту: `GET /admin/version` (git_commit).
- Для проверок метаданных: `messages.metadata.decision_meta` пишется на user‑сообщении, `conversation.context.decision_trace` — на диалоге.
- Price‑clarify спрашивает только услугу (без даты/времени).
- Входящие WhatsApp идут напрямую в API: `POST /webhook/{client_slug}` (direct ChatFlow). `POST /webhook` — legacy wrapper.
- `demo_salon` в ChatFlow направлен на `https://api.truffles.kz/webhook/demo_salon` + `webhook_secret` (секрет хранится в ChatFlow, не в git).
- `webhook_secret` всегда генерируем сами (не заказчик); хранится в ChatFlow/DB, не в git.
- `metadata.instanceId` отсутствует, если ChatFlow не передаёт. API принимает instanceId из query (`instanceId`/`instance_id`/`instance`), metadata или `nodeData`. Проверено: demo_salon после добавления query‑param — instanceId приходит, `conversation.branch_id` ставится.
- Outbox cron: `/etc/cron.d/truffles-outbox` → `/admin/outbox/process` раз в минуту.
- Outbox worker в API: фоновой цикл обрабатывает outbox каждые `OUTBOX_WORKER_INTERVAL_SECONDS` (дефолт 2s) при `OUTBOX_WORKER_ENABLED=1`; в pytest отключён.
- Outbox auto-heal: зависшие `PROCESSING` старше `OUTBOX_STALE_PROCESSING_SECONDS` возвращаются в `PENDING` или `FAILED` при исчерпании попыток.
- Outbound guard: при `TEST_MODE=1` отправка разрешена только для `OUTBOUND_ALLOWLIST_JIDS`, иначе SKIP + warn (возвращает `True` без ретраев).
- TEST_MODE=1, OUTBOUND_ALLOWLIST_JIDS=77015705555@s.whatsapp.net (тестовый номер) выставлены в `truffles-api/.env`; контейнер перезапущен с `ghcr.io/k1ddy/truffles-ai-employee:main` (2026-01-02).
- Деплой API: CI build/push → на проде `IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash /home/zhan/restart_api.sh` (локальная сборка — fallback; см. `TECH.md`).
- Инфра compose: `/home/zhan/infrastructure/docker-compose.yml` + `/home/zhan/infrastructure/docker-compose.truffles.yml`; `/home/zhan/truffles-main/docker-compose.yml` — заглушка.
- Новые документы: `docs/TECH_STATUS.md` и `docs/SELLING_TRUTHS.md` (что можно обещать и чем доказывать).
- Session Canon updated in `docs/SESSION_START_PROMPT.txt`.
- Pilot readiness checklist added.
- Pilot readiness run PASS (2025-12-31) зафиксирован в `docs/TECH_STATUS.md`.
- Док‑синхронизация: убраны дубли в `STATE.md`/`STRUCTURE.md`, `SPECS/CONSULTANT.md` обновлён под `webhook/_legacy.py`, уточнён источник истины в `docs/SESSION_START_PROMPT.txt`.
- Док‑синхронизация: `SPECS/MULTI_TENANT.md` и `SPECS/ARCHITECTURE.md` приведены к текущей реализации (branch routing частично, pipeline/вход /webhook/{client_slug}, ChatFlow без retries).
- Док‑синхронизация: `SPECS/ESCALATION.md` приведён к факту (roles/agent_identities/learned_responses — схема есть, wiring pending; branch config перенесён в реализованное).
- Док‑синхронизация: `AGENTS.md` и `docs/SESSION_START_PROMPT.txt` обновлены под роли Top Architect / Brain / Hands.
- Док‑канон обновлён: Hard‑LAW vs policy‑gates (скидки/оплата info), data_sharing opt‑in, long‑form eval и time‑awareness, behavioral shield и pricing‑media, policy‑гейты вынесены в client_pack; evidence: STRATEGY/REQUIREMENTS.md:41-69; STRATEGY/VISION.md:179-183; SPECS/CONSULTANT.md:9-112,150-191,240-252; SPECS/ESCALATION.md:151-188; SPECS/ARCHITECTURE.md:127-163; SPECS/MULTI_TENANT.md:151-225; SPECS/ACTIVE_LEARNING.md:23-41; docs/SESSION_START_PROMPT.txt:1-17; docs/SELLING_TRUTHS.md:11-36.
- Doc-sync: trace-first тестирование (CI gate + ASR-noise + nightly/manual) + Session Memory v1; ASR corpus v1=10. Evidence: `SPECS/ARCHITECTURE.md:185-204`, `SPECS/ARCHITECTURE.md:617-639`, `SPECS/CONSULTANT.md:637-640`, `/tmp/asr_corpus.jsonl`.
- Док-канон: LLM Dialogue Controller как единственный арбитр смысла; Session Memory v1.1 + pending-resume; контрактные гейты Basic-20/ASR/Long-chaos в CI. Evidence: `SPECS/ARCHITECTURE.md:128-236`, `SPECS/ARCHITECTURE.md:258-270`, `SPECS/ARCHITECTURE.md:236-247`, `SPECS/ARCHITECTURE.md:218-236`, `SPECS/CONSULTANT.md:119-133`.
- Док-канон (freeze): LLM/Memory/Action контракты синхронизированы с Pydantic; pipeline summary = intent+slots; SELLING_TRUTHS матрица выровнена с PRODUCT (trial/refund удалены) + Source Pack синхронизирован. Evidence: `SPECS/ARCHITECTURE.md:133`, `SPECS/ARCHITECTURE.md:252`, `SPECS/ARCHITECTURE.md:265`, `SPECS/ARCHITECTURE.md:337`, `docs/SELLING_TRUTHS.md:17`, `docs/SELLING_TRUTHS.md:132`, `STRATEGY/PRODUCT.md:132`.

### SYSTEM MAP (1‑page)
- Ingress: ChatFlow → `POST /webhook/{client_slug}` → outbox PENDING → worker/cron → `_handle_webhook_payload`.
- Hard gates: pending/manager_active/opt‑out → LAW escalation (payment/medical/complaint/discount/reschedule).
- OOD: early strong‑anchor OOD (soft return to salon topic).
- Booking: booking guard/flow; defer when booking + 2+ info; `expected_reply_type=time`; service‑Q allowed without clarify growth; clarify_limit → escalate.
- Info/Consult: deterministic info (service matcher + multi‑truth hours/price/duration), consult playbooks; then LLM‑first (RAG only) → truth fallback → low‑confidence clarify/escalate.
- Contracts: intent_queue + expected_reply_type (intent_choice/service_choice/time); invalid choice → return to question without reset.
- Data: `SALON_TRUTH.yaml` domain_pack/client_pack; Qdrant RAG + services_index; `knowledge_backlog` for misses.
- Observability: decision_meta on messages; decision_trace in conversations.context; `/admin/metrics`.
- Deploy/Test: GHCR + `/admin/version`; Core‑50 in CI, full eval manual; outbound allowlist when `TEST_MODE=1`.

### КЛЮЧЕВЫЕ МОЗГИ / РИСКИ / ПРОВЕРКИ (быстрый чек)
- Guest/parking lock + offline controller init: CI main (core/long + build/push + deploy) green https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20781852297, прод `/admin/version` → `{"version":"main","git_commit":"431bfadba04b819a3b00a8192ac4c49476ec351b","build_time":"2026-01-07T12:42:54Z"}`. Live WA allowlist via `/webhook` demo_salon PASS: “с подругой можно?” conv_id `d309fe65-c0a8-4893-a26c-ac19baa8458a`, user msg metadata.decision_meta action=reply intent=info_bundle source=class_router classes=["info_bundle","guest_policy"] controller_fallback_reason=low_confidence; decision_trace stage=info_class intents=["guest_policy","location"] info_sections=["address","hours","guest_policy"]; bot reply address+hours+guest_policy (без прайса/длительности). “где вы находитесь и до скольки?” conv_id `fb4c982b-0f6c-42f1-ac96-21f599733dcc`, decision_meta action=reply intent=location source=truth_gate info_sections=["address","hours"]; reply адрес+часы. “хочу записаться на маникюр” conv_id `d037f667-1180-4760-9a30-2442897ec454`, decision_meta action=booking_prompt intent=booking expected_reply_type=time source=booking; decision_trace booking prompt set, reply “На какую дату и время вам удобно?”. Evidence: `messages`/`conversations.context` rows for указанные conv_id.
- ASR-noise v1: добавлены long-tier кейсы E712–E731 из ASR корпуса (10 транскриптов). CI core/long + build-push + deploy PASS: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20746563649. Прод `/admin/version`: `{"version":"main","git_commit":"13dde7f3114dcb3c84c28c6da37096967442b2d0","build_time":"2026-01-06T11:13:20Z"}`. Evidence: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:7616`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml:7813`, `/tmp/asr_corpus.jsonl`, PR #57 https://github.com/k1ddy/Truffles-AI-Employee/pull/57.
- Pending-SLA lifecycle merged (PR #58). CI main PASS: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20747876918. Прод `/admin/version`: `{"version":"main","git_commit":"b222360481ba9d73f9d66111edd78c98c1d3ad56","build_time":"2026-01-06T12:11:32Z"}`. Live-check: `/reminders/process` pinged handover `ffc9dfa7-1bb2-4698-b885-250afd535cf3` (conv_id `3a0603a8-cd62-4ac2-8753-d60efd643997`), `pending_ack` → `bot_active` (conv_id `779b88d2-9ee6-4060-92e3-88442bfac99e`, decision_trace stage `pending_sla`/decision `pending_ack`), `pending_close` → handover `resolved` + `bot_status=muted` (conv_id `3a0603a8-cd62-4ac2-8753-d60efd643997`, decision_trace stage `pending_sla`/decision `pending_close`).
- Pending-SLA eval v1: добавлены кейсы E732–E737 (pending_sla_expected, pending_ack/pending_close). CI core/long PASS: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20748532250. Harness: pending_sla_expected триггерит /reminders/process в eval. Evidence: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:7822`, `truffles-api/tests/test_demo_salon_eval.py:474`, PR #63 https://github.com/k1ddy/Truffles-AI-Employee/pull/63, PR #61 https://github.com/k1ddy/Truffles-AI-Employee/pull/61.
- Session Memory reset ack + booking reset: явная команда reset (“другая тема”) отвечает “Ок, давайте новую тему…”, сбрасывает booking/service_hint и не тянет booking в следующий info. M2 live-check PASS: conv_id `bbaa4e0a-1afc-4349-8f9d-499b968adedc`, msg “другая тема” decision_meta action=smalltalk intent=reset; “где вы находитесь?” action=reply intent=info_bundle (без booking_prompt). PR #70 https://github.com/k1ddy/Truffles-AI-Employee/pull/70; CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20772049679; /admin/version `{"version":"main","git_commit":"e99ac931e4d61fd6b538218bf26b7b6ac91ca50a","build_time":"2026-01-07T05:52:11Z"}`.
- OOD guard in low-confidence: если router output = out_of_domain и нет in_signals — semantic matcher не вызывается, ответ OOD. Live-check PASS: conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, msg “Хотел у вас трусы купить, продаете?” decision_meta action=out_of_domain source=router_low_confidence; reply “Я помогаю по нашим услугам, записи и ценам…”. PR #71 https://github.com/k1ddy/Truffles-AI-Employee/pull/71; CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20772522219; /admin/version `{"version":"main","git_commit":"f6b21d44b73887604eefdb69b1409fe820a5614b","build_time":"2026-01-07T06:16:56Z"}`.
- P0-B/P0-C: LLM-router primary (no low_confidence fallback; router_low_confidence tag) + carryover isolation (explicit followup required, carryover_ignored) merged. PR #54 https://github.com/k1ddy/Truffles-AI-Employee/pull/54 (CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20743497446), PR #55 https://github.com/k1ddy/Truffles-AI-Employee/pull/55 (CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20743516841). Main CI (merge #54) build/push/deploy green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20743576724.
- P0-D complaint guard (consult fear → no complaint gate): PR #56 https://github.com/k1ddy/Truffles-AI-Employee/pull/56 (CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20745141282), main CI after merge https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20745202836. Evidence: conv_id `1f2e004f-6695-4087-8da0-36163045f0ee`, msg `54ec3920-b642-44d8-8951-b5043d176b7c` decision_meta `complaint_signal=true`, `consult_override=true`, `intent=consult_reply` (no escalation).
- Прод: `/admin/version` → `{"version":"main","git_commit":"85f0210f5e0e371ba7599a1780ec443b9f4c559d","build_time":"2026-01-06T10:16:25Z"}` после deploy `IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash /home/zhan/restart_api.sh`.
- Scenario B (consult + перебивки, pacing): conv_id `1f2e004f-6695-4087-8da0-36163045f0ee`; msg `a40b0bd0-1bd1-4d38-9331-11519391a1c0` decision_meta `intent=info_bundle`, `consult_return=true`; msg `a0033507-cf6c-463d-aebb-cfa5de85808d` decision_meta `action=booking_paused` on “спасибо” (no complaint/shield).
- Scenario C PASS (guest_policy + booking, pacing): conv_id `779b88d2-9ee6-4060-92e3-88442bfac99e`; msg `0c680b20-fabf-498a-812c-6aa07d110cfc` decision_meta `intent=info_bundle`, `info_sections=["address","hours","guest_policy"]`; msg `db1c090b-09ad-4489-8103-2ad97ac1a91e` decision_meta `expected_reply_type=time`; msg `20fbf9df-f569-46b0-b645-b9463bb66f0d` decision_meta `expected_reply_shortcircuit=true`, booking escalated (assistant reply “Передал менеджеру…”).
- Basic‑20 live‑check (reset между сценариями) PASS. conv_id: 1) где вы находитесь → bbb588c1-f300-45de-a9d0-008d1f5e113f; 2) до скольки сегодня → fac3518a-b0d4-4392-8fee-bb460c038c85; 3) можно с ребёнком → 24a7d049-37d8-4fb3-aa50-3cb242c47253; 4) можно с подругой → 434ff950-c0d4-42bf-92a6-f9b5cb65ddf1; 5) парковка → fcd6bde5-51f3-4c0e-967b-e52da1579ae0; 6) записаться можно → 564c7d8b-bc35-4aaf-a8a3-1d06a0b27147; 7) какая цена → db20fba1-ef83-415b-8286-2f1267d2258a; 8) сколько стоит стрижка машинкой → ab652dc5-12bc-4e78-9c28-1e0dcd929e28; 9) сколько длится маникюр с гель-лаком → 5f3d94a3-2bf1-424e-8b85-51450b35ae4a; 10) работаете ли в воскресенье → 5e1f70bb-8669-415e-9be0-4b5063663cf0. Evidence (decision_meta/trace + last messages): /tmp/basic20.jsonl.
- Мозги: `outbox → _handle_webhook_payload → pending/opt-out/policy escalation → OOD (strong anchors) → booking guard/flow → service matcher (услуги/цены) → LLM-first → truth gate fallback → low-confidence уточнение/эскалация`.
- Риски: payment/reschedule/medical/complaint — только эскалация; не озвучивать способы оплаты; branch‑gate для цен.
- LLM‑first критерии: отвечаем только по RAG; если RAG пуст/низкий → уточнение; если ответ содержит payment/medical/complaint/discount/refund → эскалация; decision_meta включает `llm_primary_used`.
- RAG: добавлен query-rewrite (FAST LLM ≤1s) + hybrid retrieval (vector+BM25); rewrite только для retrieval, в decision_meta/trace пишутся `rewrite_used`, `rewrite_text`, `rag_scores`, `rag_confident`, `rag_reason`.
- Метрики качества (день, target): rag_low_conf_rate <= 0.35; clarify_rate 0.05-0.20; clarify_success_rate >= 0.60.
- Проверки качества: `EVAL.yaml` + `pytest truffles-api/tests/test_<client>_eval.py` + sync KB (`ops/sync_client.py`).
- Battery v0: добавлены 100 кейсов в `truffles-api/app/knowledge/demo_salon/EVAL.yaml` + 25 manual в `truffles-api/tests/test_cases.json` (без изменения логики).
- Battery v1: добавлены +150 кейсов (E200–E349, всего 250) + 15 manual (TC069–TC083) без изменения логики.
- EVAL CI: `test_demo_salon_eval.py` теперь в CI гоняет Core‑50 (env `CI=true`), полный набор — только вручную (`EVAL_TIER=all`).
- Data fix: добавили `Стрижка машинкой` в `services_catalog.price_items`, чтобы прайс-ответы включали 2 000 ₸.
- Data fix: добавили алиасы "чёлку/челку" в `services_catalog`, примеры "Цена на челку?"/"Сколько стоит?"/"Почем?"/"Подравнивание кончиков сколько стоит?" в `typical_questions.pricing`, и сервисы под прайс‑позиции (покрытие/укрепление/снятие/наращивание).
- Multi-truth: pricing/duration теперь добавляются по явным сигналам, чтобы не зависеть от semantic_question_type/эмбеддингов.
- Multi-truth: hours добавляются по _looks_like_hours_question; price_item может переопределить широкий service_query при более точном совпадении.
- Multi-truth: single-сегмент (без пунктуации) с 2+ сигналами (hours/price/duration) даёт детерминированный ответ.
- Инструменты фактов: `docker logs truffles-api --tail 200`, SQL по `outbox_messages`/`handovers`.
- Early OOD guard: блок только при `out_hits>0`, `strict_in_hits==0`, без `booking_signal`; booking/intents проходят к booking/truth. Evidence: `truffles-api/app/routers/webhook/_legacy.py:5888-5916`; EVAL `E359` ("хочу записаться" → booking_intake) и `E360` ("какая погода" → off_topic) в `truffles-api/app/knowledge/demo_salon/EVAL.yaml:3974-3995`; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS (2026-01-02, 108.6s).
- Live-check (prod, test number 77015705555@s.whatsapp.net): "хочу записаться" → booking prompt (no OOD), conversation_id=99306198-1ecf-44d6-9066-72bb4e76e915, decision_meta action=booking_prompt; "какая погода" → out_of_domain early_block, same conversation, decision_meta action=out_of_domain, trace stage=out_of_domain/out_hits=1/strict_in_hits=0. Messages at 2026-01-02 15:02:11Z and 15:02:50Z; bot replies 15:02:22Z and 15:02:53Z. CI PASS https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20660665559; /admin/version git_commit 616c66f68da7a98246ce427ea02d6128261f156a (build_time 2026-01-02T15:12:34Z).
- Clarify diagnostics (2026-01-02): pricing queries (“Сколько стоит?”, “Какая цена?”) получают clarify из-за отсутствия service_query (service_query=null, service_query_source=none; e.g. msg dd8eee2b-b7f4-4cd4-8516-e1fa4e6ccb46, 6995cc99-d204-4a4d-856c-786d72e432c2). Booking prompts (“а парковка есть?”, “хочу записаться”) тоже без service_query (source=intent_decomp). SQL: SELECT ... ILIKE '%clarify%' LIMIT 50; SELECT ... ILIKE '%clarify%' AND ... '%service_query%' LIMIT 50.
- Clarify root cause (pricing/duration): 71 user messages with clarify meta, только 2 с непустым service_query; топ-5 кейсов показывают отсутствие упоминания услуги (“Сколько стоит?”, “Какая цена?”, “парковка”, “хочу записаться”) при наличии услуг в catalog → data/input gap, не баг intent_decomp. Evidence: SQL counts (clarify total/with service_query), samples with service_query_source=none/intent_decomp (ids dd8eee2b…, 96ed57b0…, 6995cc99…, d019abfb…, 34978f55…). Рекомендация: data/process — требовать услугу в вопросах о цене/парковке или добавить авто-подстановку default услуги, logic-fix не требуется по текущим примерам.
- Процессный запрет: локальный `pytest` без разрешения нельзя; единственный gate — CI, core и long гоняются отдельными джобами. Любое нарушение → stop-line и фиксация в STATE (команда/контекст).
- Service carryover on expected reply: matched `expected_reply_type=service_choice` now сохраняет `service_carryover` (service_query=value, source=expected_reply, score=1.0) → pricing follow-up использует контекст. Evidence: `truffles-api/app/routers/webhook/_legacy.py:4478-4504`; new eval conversation `E361` (маникюр → “сколько стоит?”) in `truffles-api/app/knowledge/demo_salon/EVAL.yaml:3980-3995`. Tests: `pytest truffles-api/tests/test_demo_salon_eval.py -q` (local env) FAIL due to OOD case E360 returning error (“Извините, произошла ошибка…”) when services_index/embed not available; needs rerun in full env.
- Проверка 2026-01-02: open handovers duplicates 0 (handovers.status IN pending/active) по conversation_id и по conversations.user_id (join); SQL `SELECT conversation_id, count(*) ... HAVING count(*) > 1` → 0; `SELECT c.user_id, count(*) ... HAVING count(*) > 1` → 0.
- Фиксация: шаблон рассуждений + обновление `STATE.md` каждый раз.
- Детальный бриф салона заполнен эталоном (фейковые данные): `Business/Sales/Бриф_клиента.md`.
- Demo salon knowledge pack обновлён под эталон (truth/intents/eval + обзор услуг).
- Knowledge backlog: webhook пишет misses (low_confidence/out_of_domain/llm_timeout/clarify) в `knowledge_backlog` через upsert; отчёт — `/admin/knowledge-backlog` и `ops/knowledge_backlog_top.sql`; безопасно для прода (нет влияния на ответы).
- `SALON_TRUTH.yaml` теперь разделён на `domain_pack` (общая таксономия/синонимы/типовые вопросы/ООД‑якоря) и `client_pack` (факты demo_salon); старые ключи сохранены, поэтому безопасно для прода.
- Client_pack уточнён под политику/команду: promo stacking_notes (акции/сертификаты/промокоды не комбинируем), guest_limit/children_rules/alcohol/food, early_arrival; опыт мастеров (ногти 4–6 лет, волосы 5+, брови/ресницы 3–5, лицо 4+) отдан в client_pack. Evidence: `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml:185-231,267-271,885-901`.
- `ops/sync_client.py` получил валидацию обязательных полей `client_pack` (`--validate`/`--validate-only`), без генерации новых файлов.
- `services_index` (Qdrant) заполняется из `ops/sync_client.py` по `price_list` + `services_catalog`; после LLM low_confidence работает semantic matcher (match/suggest) с `decision_meta.source=service_semantic_matcher`, безопасно для прода (срабатывает только при low_confidence и OOD‑gate).
- Добавлен rewrite‑layer для semantic matcher (FAST LLM → JSON intent/query, 1.2s) — влияет только на подбор запроса, факты не меняет.
- Semantic question‑type (hours/pricing/duration) на эмбеддингах из `domain_pack.typical_questions`; multi_truth объединяет 2 ответа (hours+price/duration), учитывает сегменты/запятые; service matcher пропускает multi hours+price/duration; длительности берутся из `services_catalog.duration_text`.
- Цена/длительность выдаются только при явном `service_query` (intent_decomp или semantic_match); иначе — уточнение. В decision_meta/decision_trace пишутся `service_query`, `service_query_source`, `service_query_score`.
- Eval long set нормализован на `turns` (без поля `messages`), добавлены E401–E410; E406 переписан, чтобы оставаться в ногтевой консультации без LLM (трек: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:4019-4202`). Тесты (local venv): `. .venv/bin/activate && cd truffles-api && pytest -q tests/test_demo_salon_eval.py` PASS (33.68s); `. .venv/bin/activate && cd truffles-api && EVAL_TIER=long pytest -q tests/test_demo_salon_eval.py` PASS (16.39s).
- Добавлены E411–E416 long-form (страх стерильности, отказ в скидке/стэкинг, хаотичный перенос услуги/времени, “спасите сейчас”, гость с ребёнком/лимитом мест, парковка+время/ожидание) — трек `truffles-api/app/knowledge/demo_salon/EVAL.yaml:4203-4322`.
- Shield pre-gate до LAW/policy: спам-бёрст/слишком длинные — drop; toxic/бессвязные — эскалация. EVAL core E362 (spam drop), E363 (toxic escalate), E364 (booking проходит). Тесты в контейнере PASS: `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` (369.20s); `... -o EVAL_TIER=long` (367.71s). Prod `/admin/version`: `{"version":"main","git_commit":"b79fe5cf4825cdc219d59135661dbbd3f51da082","build_time":"2026-01-03T10:58:33Z"}`.
- Hygiene intent vs policy: policy_gate игнорирует medical-эскалацию для гигиенических вопросов (HYGIENE_KEYWORDS), E417 long отвечает стерилизацией без эскалации. CI green (core+long+secret-scan) https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20677418197; prod `/admin/version` `{"version":"main","git_commit":"4a329fadfdbf127c8d92a79beb896e42c9920b9b","build_time":"2026-01-03T12:50:51Z"}`.
- CI (main@634f1e1) green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20675214358. Предыдущий прогон (20674885954) падал на `secret-scan` из-за `System.Text.EncoderFallbackException: Unable to translate Unicode character \\uD83E...` (job 59361181850); rerun устранил, build-push/deploy проходят.
- CI (main@fe6de46) green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20675908361 (build/push/deploy).
- Прод: `/admin/version` → `{"version":"main","git_commit":"634f1e1cfc23d42e62b943eb17df4c0450031ccc","build_time":"2026-01-03T09:09:15Z"}` (команда `docker exec -i truffles-api python - <<'PY' ...`).
- Прод: `/admin/version` → `{"version":"main","git_commit":"fe6de46323d8c2a116a8ece262ecd4b3ebef22eb","build_time":"2026-01-03T10:17:03Z"}`.
- Контейнерные EVAL-тесты PASS: `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` (366.96s); `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q -o EVAL_TIER=long` (373.01s).
- Ambiguous price/duration → clarify (не отвечаем ценой при неуверенном типе).
- Booking gate блокирует инфо‑вопросы (pricing/hours/duration) без явного booking; сплит сегментов по ,;?!.; service slot только через semantic matcher, datetime — токен; trace/meta `booking_blocked_reason`. (нужен деплой)
- Booking: при expected_reply_type=time service‑вопросы (presence/price/duration) отвечаются по факту без роста clarify; service_query сохраняется в booking_context, дальше prompt времени.
- Live-check 2025-12-31: booking‑prompt + “маникюр делаете?” → price reply + повтор времени, clarify_attempt не растёт (commit 854b4f9).
- Context Manager: `current_goal` (info/consult/booking), `refusal_flags` (name/phone, TTL 10 сообщений), `clarify_attempts` (>=2 → эскалация), `compact_summary` (детерминированно; триггеры: intent_change/clarify_limit/12+ сообщений); всё пишется в decision_meta/trace.
- Intent Queue + Question Contract: `conversation.context.intent_queue` и `conversation.context.expected_reply_type` в webhook, чтобы держать очередь интентов и ожидаемый тип ответа.
- Booking + 2+ info (или total 3+) → defer booking, отвечаем на 1–2 info (service_query: price+duration; иначе location+hours), остаток в intent_queue, expected_reply_type=intent_choice.
- Standalone info-ответы (price/duration/hours/location) получают CTA "Хотите записаться?" только в bot_active без followup/booking-prompt; skip non-bot-active + если ответ уже про запись; EVAL E003l/E003m/E014d, negative E039b; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS.
- Soft price defense: `why_price_from`/`objection_price` реализованы в demo_salon knowledge + покрыты EVAL; SPECS/CONSULTANT.md Rule 4 синхронизирован (частично реализовано + мягкая защита цены). Tests: не запускались (doc sync). Evidence: `truffles-api/app/services/demo_salon_knowledge.py:2045-2053`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml:162-216`, `SPECS/CONSULTANT.md:209-248`.
- Night tone/timezone: `salon.timezone` в client_pack (Asia/Almaty) + quiet-hours notice использует локальное время и salon hours (open/close) в коде; исключения pending/manager_active + LAW/opt-out/OOD; EVAL `E014e/E014f`; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS (commit `8b08a71b985c458f388f3d6686b75a5431c6ec92`). Spec gap: SPECS/CONSULTANT.md задаёт фиксированное окно 22:00–09:00 → нужно решение (выровнять spec или код). Evidence: `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml:1-25`, `truffles-api/app/services/demo_salon_knowledge.py:161-188`, `truffles-api/app/routers/webhook/_legacy.py:4386-4408`, `SPECS/CONSULTANT.md:162-166`.
- Doc sync (soft price defense + quiet hours): Rule 4 в SPECS/CONSULTANT.md отмечен как частично реализованный с мягкой защитой цены; quiet-hours правило в SPECS/CONSULTANT.md задаёт timezone‑source + окно 22:00–09:00, но код применяет “вне salon.hours” и при отсутствии timezone сейчас падает на UTC → нужен logic‑fix: skip, если timezone нет. Tests: not run (doc sync). Evidence: `SPECS/CONSULTANT.md:162-166`, `SPECS/CONSULTANT.md:209-248`, `truffles-api/app/services/demo_salon_knowledge.py:161-188`, `truffles-api/app/services/demo_salon_knowledge.py:2045-2053`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml:162-216`.
- Quiet-hours fix: пропуск notice при отсутствующей/невалидной timezone (ZoneInfo) + подтверждённый деплой. CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20655575365 PASS; prod `/admin/version` git_commit `8a51d28b1a9932b302bca3626097dee751ccec3a`; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS. Evidence: `truffles-api/app/services/demo_salon_knowledge.py:116-181`.
- Agentic orchestration: закреплено, что “agentic” = логические роли стадий одного пайплайна `_handle_webhook_payload`, не отдельные рантайм‑агенты; роли сопоставлены с фактическим порядком стадий. Evidence: `SPECS/ARCHITECTURE.md:132-142`.
- E003m fix: сервисный матч больше не блокируется semantic question-type; guard проверяет явные сигналы hours/price/duration. Evidence: `truffles-api/app/services/demo_salon_knowledge.py:1912-1917`. CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20654965505 PASS; prod `/admin/version` git_commit `8b08a71b985c458f388f3d6686b75a5431c6ec92`; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS.
- expected_reply_type=service_choice сохраняется при OOD/токсичности и возвращает к вопросу об услуге.
- expected_reply_type=service_choice при невалидном ответе без service/semantic/in-domain сигнала возвращает к вопросу об услуге (reason=invalid_choice).
- intent_choice: prefix/substring match по меткам очереди (>=4 символов); info-выбор отвечает и обновляет очередь, booking запускает booking-prompt; decision_meta пишет expected_reply_choice/intent_queue_remaining/expected_reply_next.
- Consult playbooks: `domain_pack.consult_playbooks` расширен (hair_aftercolor/hair_damage/hair_color_choice/nails_care/brows_lashes_care/sensitive_skin/style_reference/general_consult) с questions/options/next_step.
- CI (main@8a6164f) green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20678138128 (head_sha 8a6164fac4607260f09c63e60a7fee3d96a2961c, conclusion=success).
- Прод: `/admin/version` → `{"version":"main","git_commit":"8a6164fac4607260f09c63e60a7fee3d96a2961c","build_time":"2026-01-03T13:49:12Z"}` (команда `curl -s http://localhost:8000/admin/version`).
- Info-combo bundle: location/hours (и pricing/duration при сигнале адрес/парковка/гость) объединяют адрес+часы, опционально парковку/гостей, пишут info_sections meta. Evidence: `truffles-api/app/services/demo_salon_knowledge.py:207-285`, `truffles-api/app/routers/webhook/_legacy.py:3408-3465`.
- Core EVAL расширен инфо-комбо кейсами (адрес/часы/парковка/guest/quiet/clarify) E422–E428. Evidence: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:4484-4558`.
- Class-router info-bundle: при info-интентах отвечает bundle по приоритету + пишет class_carryover (TTL 4), decision_meta `intent=info_bundle`/`class_router`/`info_sections`. Evidence: `truffles-api/app/routers/webhook/_legacy.py:2102-2365`, `truffles-api/app/routers/webhook/_legacy.py:7866-7967`.
- Long EVAL info-bundle paraphrases E429–E434 добавлены. Evidence: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:4564-4688`.
- CI (main@e36337e) green с build/push/deploy: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20687244044.
- Прод: `/admin/version` → `{"version":"main","git_commit":"e36337e63780619e598176f3370680b86573f8bb","build_time":"2026-01-04T03:55:04Z"}` (команда `curl -s https://api.truffles.kz/admin/version`).
- Live-check (prod, test number 77015705555@s.whatsapp.net): "Где вы находитесь и до скольки работаете?" → info_bundle reply (адрес+часы); conversation_id=624c6087-cbd6-4197-8131-4091cec563d0; decision_meta action=reply intent=info_bundle source=class_router; trace stages info_class + class_carryover set (SQL queries in session).
- Doc sync PR #7: "Canonize info_bundle carryover invariants" merged (commit `eb3477ce1bbc118a38561b76a726ca4b3c0b4e16`): https://github.com/k1ddy/Truffles-AI-Employee/pull/7.
- P0 fix info_bundle hours follow-up (PR #8): CI core/long PASS https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20688985111; prod `/admin/version` → `{"version":"main","git_commit":"6a90da1d4c465592c17b2b8cd14dd6805322ea9a","build_time":"2026-01-04T06:40:40Z"}`; live-check R3 (gap ~1.7s) conv_id `c0ab977f-0434-496a-ae66-05fface8fb7b`, user msg `aefc48a9-4b06-4ae3-9854-c3f5bac203ed`: decision_meta question_type=hours, service_query=null, class_router carryover_class=info_bundle, carryover_info_sections=["address","hours"]; trace info_class question_type=hours; reply address+hours (assistant msg `24bf46a8-1992-488e-a31d-431a58fd4dc7`).
- Base-80 battery (8 классов, core 5–6 turns + long 10 turns + 10 перефразов на класс) добавлена E435–E530. Evidence: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:4704-5680`.
- Class stability: anchor boost для pricing/duration/hours/location + class_router.in_signals пишет `info_anchor_*`. Evidence: `truffles-api/app/routers/webhook/_legacy.py:2608-2801`.
- CI (main@2d8bf94) build/push/deploy green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20689515956.
- Прод: `/admin/version` → `{"version":"main","git_commit":"2d8bf940313178fdf43ad0270325f9008842a9e6","build_time":"2026-01-04T07:28:48Z"}`.
- Live-check (prod): paraphrase “На каком перекрёстке вы?” → info_bundle; conv_id `a271e3d0-053d-4d83-9852-f3ea3167efe9`, user msg `cca7722f-8e03-45e4-9119-8deafaed2478` class_router.in_signals `info_anchor_location`; reply `c54d7be2-81db-4d52-b607-b53d857da061` (address+hours).
- Live-check (prod): chaotic follow-up “Когда заканчиваете работу?” после price+parking → info_bundle; conv_id `4f9026c2-9c94-4b38-8248-b5aacf635cdf`, user msg `0e679f43-08dd-40e4-932f-7c0022811788` class_router.in_signals `info_anchor_hours`, `info_anchor_pricing`; reply `6489ceb6-27cc-474d-bd73-8609b081e749` (hours+address+pricing).
- Live-check (prod): booking+info interrupt “Где вы находитесь и до скольки работаете?” после “Хочу записаться” → info reply + intent choice; conv_id `cd10fbb4-a5b9-4d98-87fb-b7dbb16a6766`, user msg `4cd2d8a9-2ae6-4652-9264-e08a6985247c` decision_meta intent=multi_intent_info booking_deferred=true info_sections=["address","hours"]; reply `425f22fe-6234-4e09-80fb-c4de27c65b90`.
- Канон LLM-router: источник класса = LLM-router (doc commit `49c81ba`).
- LLM-router внедрён как источник класса с fallback на детерминизм + запись router output в trace/meta; prompt fallback встроен для контейнера. Evidence: `truffles-api/app/routers/webhook/_legacy.py:2839`, `truffles-api/app/routers/webhook/_legacy.py:6597`, `truffles-api/app/services/intent_service.py:32`, `truffles-api/app/services/intent_service.py:323`, `prompts/intent_classifier.md`.
- Router eval: инварианты класса (перефраз/перестановка/хаотичный follow-up) E531–E537 добавлены. Evidence: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:5687`.
- CI (main@223fe9f) build/push/deploy green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20690022936.
- Прод: `/admin/version` → `{"version":"main","git_commit":"223fe9f12bec2f030fc40d878f644868d2fdd631","build_time":"2026-01-04T08:16:45Z"}`.
- Live-check (prod): info_bundle paraphrase “Подскажите, где находитесь и до скольки работаете?” → info_bundle reply; conv_id `f86b64bc-46ba-41e5-bcba-d94562f0376b`, user msg `msg-218c5af6630b46fa89771a48554abece` decision_meta action=reply intent=info_bundle source=class_router (router error=timeout fallback); trace info_class info_sections=["address","hours"]; reply `4069a1a6-2b94-4fb4-a737-120dbdfdd29f` (address+hours + CTA).
- Live-check (prod): booking+info в одном сообщении “Хочу записаться на маникюр, где вы находитесь и до скольки работаете?” → info reply + intent choice; conv_id `5792475d-5cbf-43a1-88c9-7d1d680d5102`, user msg `msg-8d7e152b294c4b0f8c37d8c9db99d22c` decision_meta booking_deferred=true info_sections=["address","hours"]; trace intent_queue defer_booking; reply `724c6afc-895e-4a9d-9530-489c263996da` (address+hours + intent choice).
- Live-check (prod): consult + перебивка “Посоветуйте уход для сухих волос” → consult reply, затем “Кстати, где вы находитесь?” → info_bundle reply; conv_id `acc4589c-f0d1-4eb1-83a7-3973a75319b6`, user msg `msg-0e4e1baeb03743ffbcd592a6895c115b` decision_meta consult_reply (source=consult), user msg `msg-16564c13b8844e3fbe3dba6f94c0478f` decision_meta info_bundle source=class_router (router error=timeout fallback); reply `0de2e7a4-4e28-46bd-8bac-a267311b58a8` (consult) + `e0f4f3df-b021-4dd6-9abb-8f47bce98d01` (address+hours).
- Router reliability: temp=0.0, max_tokens=140, timeout=3.0 + timeout retry; router output fields router_llm_ms/router_error/router_retry; router model defaults to gpt-4o-mini when FAST_MODEL=gpt-5 (override `ROUTER_MODEL`). Evidence: `truffles-api/app/services/intent_service.py:32`, `truffles-api/app/services/intent_service.py:410`, `truffles-api/app/services/intent_service.py:494`, `truffles-api/app/services/intent_service.py:565`.
- CI (main@06f74fb) build/push/deploy green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20691314210.
- Прод: `/admin/version` → `{"version":"main","git_commit":"06f74fbb24ee9d239a12cb78c7d7c92d76e482b0","build_time":"2026-01-04T10:09:05Z"}`.
- Live-check (prod): info_bundle “Подскажите, где вы находитесь и до скольки работаете?” → info_bundle reply; conv_id `624c6087-cbd6-4197-8131-4091cec563d0`, user msg `msg-189872d0-6d2c-4ee1-85e4-7cb823434e0b` decision_meta class_router.router.output router_error=none router_retry=false router_llm_ms=2699.99; reply `8b634364-2b04-419e-a656-90257c682fe3` (address+hours + CTA).
- Live-check (prod): booking+info “Хочу записаться на маникюр, где вы находитесь и до скольки работаете?” → info reply + intent choice; conv_id `624c6087-cbd6-4197-8131-4091cec563d0`, user msg `msg-5edb34f7-9651-4048-9aa7-9174bc3a5e5a` decision_meta booking_deferred=true info_sections=["address","hours"] expected_reply_type=intent_choice; reply `055b7a04-d801-477e-9f03-d4366f70cd06` (address+hours + intent choice).
- Live-check (prod): consult + перебивка “Посоветуйте уход для сухих волос.” → consult reply `af9fe942-cbc1-4032-8467-b5fd9c3646fb`, затем “Кстати, где вы находитесь?” → info_bundle reply; conv_id `624c6087-cbd6-4197-8131-4091cec563d0`, user msg `msg-ffdc3336-87d0-48a2-a8e5-37afda5f7e91` decision_meta class_router.router.output router_error=none router_retry=false router_llm_ms=2069.72; reply `a43d61dc-d999-4bbb-a442-1054e194b682` (address+hours + CTA).
- Discounts policy gate: скидки/акции → policy_gate=discounts (без pricing fallback), ответы только из client_pack.discounts; E544/E545 добавлены. CI (main@baffbf2) build/push/deploy green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20693070009. Прод: `/admin/version` → `{"version":"main","git_commit":"baffbf2bcbd8a563242f96770f742d7790f42a0a","build_time":"2026-01-04T12:43:02Z"}`. Live-check (prod): "Есть скидки или акции?" → policy reply; conv_id `a2034d97-64d3-4d3d-9f4f-3ddbc37a4305`, user msg `893ae6b2-78f5-4e0a-8d7e-aba64afcbfb1` decision_meta policy_gate=discounts service_query=null; trace stage=policy_gate policy_gate=discounts; reply `dd71b7d9-ad1b-47cb-8427-197f59264437` (без прайса).
- Info_bundle dedupe: base bundle отвечает один раз при multiple info intents (pricing+location), без повторов адрес/часы; PR #23. CI (main@6a51bac) build/push/deploy green: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20693678478. Прод: `/admin/version` → `{"version":"main","git_commit":"6a51bacf65e5d9c2c9ffd5598a83eeef937934de","build_time":"2026-01-04T13:32:56Z"}`. Live-check (prod): “Сколько стоит маникюр и где вы находитесь?” → reply с одним блоком адрес/часы + прайс; conv_id `a271e3d0-053d-4d83-9852-f3ea3167efe9`, user msg `eb97dfbd-a480-4b4b-90c6-a50532f1e50b` decision_meta intent=info_bundle source=class_router info_sections=["address","hours"]; trace stage=info_class intents=["pricing","location"]; reply `c2e0a61d-01c6-4d5c-a4f6-93bef36843a7`.
- Answer contract priority: matched expected_reply форсирует booking shortcircuit (expected_reply_shortcircuit=true), booking_signal override и без info/service matcher (no pricing on time replies). Evidence: `truffles-api/app/routers/webhook/_legacy.py:5226-5346`, `truffles-api/app/routers/webhook/_legacy.py:5718-5732`, `truffles-api/app/routers/webhook/_legacy.py:6667-6687`; PR #28 https://github.com/k1ddy/Truffles-AI-Employee/pull/28; CI core/long PASS https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20709873371.
- EVAL: кейс time reply “в субботу вечером” без прайса, требуется expected_reply_shortcircuit=true (E559). Evidence: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:6191-6209`; PR #29 https://github.com/k1ddy/Truffles-AI-Employee/pull/29; CI core/long PASS https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20709890713.
- CI deploy fail (main): run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20709918013, job deploy, step “Deploy to VPS”, cmd `IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash ~/restart_api.sh`, error: container name "/truffles-api" already in use (status 125). Manual deploy with sha image; prod `/admin/version` → `{"version":"main","git_commit":"4a38f0f41fa41810e6923d5658ca867655125f5b","build_time":"2026-01-05T08:48:20Z"}`.
- Live-check (prod): “хочу записаться” → “в субботу вечером” → booking продолжился на имя, без прайса. conv_id `fc2ff625-f678-4544-a477-1fc2c9b93b63`; last 4 msgs: user “хочу записаться” → assistant “На какую услугу хотите записаться?” → user “в субботу вечером” → assistant “Как вас зовут?”. decision_meta expected_reply_shortcircuit=true (message_id `live3-time-1767603759193`); decision_trace stage=question_contract decision=matched expected_reply_type=service_choice expected_reply_shortcircuit=true.

### ПОСЛЕДНЯЯ ПРОВЕРКА (prod, 2025-12-31; Evidence: `curl -s http://localhost:8000/admin/health` → `checked_at=2025-12-31T07:12:59.570689+00:00`)
- Preflight: truffles-api running, image `ghcr.io/k1ddy/truffles-ai-employee:main`.
- Env: `PUBLIC_BASE_URL=https://api.truffles.kz`, `MEDIA_SIGNING_SECRET=SET`, `MEDIA_URL_TTL_SECONDS=3600`, `MEDIA_CLEANUP_TTL_DAYS=7`, `CHATFLOW_MEDIA_TIMEOUT_SECONDS=90`.
- `/admin/version` (2025-12-31): version `main`, git_commit `67bd61d6606e6fbdc2ad2d83936dc932a41a77c8`, build_time `2025-12-31T07:04:22Z`. Evidence: `curl -s http://localhost:8000/admin/version` → `{"version":"main","git_commit":"67bd61d6606e6fbdc2ad2d83936dc932a41a77c8","build_time":"2025-12-31T07:04:22Z"}`.
- `/admin/health` (2025-12-31): conversations bot_active 280, pending 0, manager_active 0; handovers pending 0, active 0 (checked_at `2025-12-31T07:12:59.570689+00:00`). Evidence: `curl -s http://localhost:8000/admin/health` → `{"conversations":{"bot_active":280,"pending":0,"manager_active":0},"handovers":{"pending":0,"active":0},"checked_at":"2025-12-31T07:12:59.570689+00:00"}`.
- `/admin/metrics` (2025-12-31): demo_salon OK; p50 7.06s, p90 13.36s, clarify_rate 0.2632, clarify_success_rate 0.8, escalation_rate 0.0526. Evidence: `TOKEN=$(docker exec -i truffles-api /bin/sh -lc 'printf "%s" "$ALERTS_ADMIN_TOKEN"')` + `curl -s -H "X-Admin-Token: $TOKEN" "http://localhost:8000/admin/metrics?client_slug=demo_salon&metric_date=2025-12-31"`.
- Live-check consult mode: care/color → consult replies with consult_intent meta; price → pricing path; booking → clarify; allergy → escalation; consult replies without prices/availability/masters.
- Live-check context manager: refusal_flag.name set and booking skips name; 2x clarify → 3rd escalates; booking → consult switch updates current_goal + summary (consult reply, no prices/availability/masters).
- Live-check PR-3 rewrite+hybrid: address slang → address (rewrite timeout, rag_scores logged); "манник" → service_semantic match; "скок стоит педик" → price; "какая погода" → OOD; "хочу записаться" → booking-clarify.
- Live-check PR-4 metrics: demo_salon test messages wrote `rag_scores` + `rag_confident`/`rag_reason`; daily snapshot includes rag_low_conf_rate/clarify_rate/clarify_success_rate.
- Live-check PR-5 consult/booking/carryover: consult precedence ("ничего страшного") → consult reply; booking info interrupt returns duration + booking prompt; duration-only stays info; carryover "сколько стоит?" uses `service_query_source=context` and returns price list; OOD works.
- Tests: `docker exec -i truffles-api pytest /app/tests/test_message_endpoint.py -q` (85 passed).
- Tests: `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` (1 passed).
- CI: `lint-test/build-push/deploy` passed (commit `6a4b7ef`).
- Deploy: prod on `67bd61d6606e6fbdc2ad2d83936dc932a41a77c8`. Evidence: `curl -s http://localhost:8000/admin/version` → `{"version":"main","git_commit":"67bd61d6606e6fbdc2ad2d83936dc932a41a77c8","build_time":"2025-12-31T07:04:22Z"}`.
- DB messages (2025-12-31): total_msgs 2838, with_decision_meta 344. Evidence: `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot -c "SELECT count(*) AS total_msgs, count(*) FILTER (WHERE metadata ? 'decision_meta') AS with_decision_meta FROM messages;"` with `DB_USER=n8n` → `total_msgs=2838, with_decision_meta=344`.
- DB conversations (2025-12-31): conv_with_branch 14, total_conversations 280. Evidence: `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot -c "SELECT count(*) FILTER (WHERE branch_id IS NOT NULL) AS conv_with_branch, count(*) AS total_conversations FROM conversations;"` with `DB_USER=n8n` → `conv_with_branch=14, total_conversations=280`.
- DB outbox (2025-12-31): FAILED 12, SENT 767. Evidence: `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot -c "SELECT status, count(*) FROM outbox_messages GROUP BY status;"` with `DB_USER=n8n` → `FAILED=12, SENT=767`.

### MEDIA RUNBOOK (амнезия, 3–5 минут)
- Точка входа: `truffles-api/app/routers/webhook/_legacy.py` → `_handle_webhook_payload()` + outbox coalesce.
- Guardrails: тип/размер/rate‑limit → `clients.config.media` (см. `SPECS/ARCHITECTURE.md`).
- Хранение: `/home/zhan/truffles-media/<client>/<conversation>/` + мета в `messages.metadata.media`.
- Forward: Telegram `sendPhoto/sendAudio/sendVoice/sendDocument` (см. `truffles-api/app/services/telegram_service.py`).
- Outbox: если в батче медиа — обработка по одному (иначе теряются вложения).
- Быстрые факты (SQL):
  `SELECT payload_json->'body'->>'messageType', payload_json->'body'->'mediaData' FROM outbox_messages ORDER BY created_at DESC LIMIT 1;`
  `SELECT metadata->'media' FROM messages ORDER BY created_at DESC LIMIT 1;`

### Что мешало быстрому входу (зафиксировано)
- Было несколько корней кода и часть ссылок указывала на несуществующие пути (`/home/zhan/truffles`, `/home/zhan/Truffles-AI-Employee`) → команды/доки расходились.
- Inbound payload для медиа: в коде добавлено сохранение + ответ, но на проде без деплоя всё ещё отбрасывается.
- В репо лежали workflow JSON и упоминания n8n → удалены, чтобы не вводить в заблуждение.
- Git worktree был сломан: `.git` указывал на несуществующий gitdir → восстановлено, commit/push работают.
- В спеках и ops были старые инструкции со scp по деплою → выровнено с CI/GHCR и `/home/zhan/restart_api.sh`.

### Что работает
- [x] Бот отвечает на сообщения WhatsApp
- [x] RAG поиск по базе знаний (Qdrant)
- [x] Классификация интентов
- [x] Booking interrupt при склейке: info‑ответ + возврат к booking‑prompt (live‑check PASS 2026‑01‑02)
- [x] Эскалация в Telegram (кнопки Беру/Решено)
- [x] Ответ менеджера → клиенту
- [x] Напоминания (15 мин, 1 час) — cron
- [x] Мультитенант (truffles, demo_salon)

### Что не работает / в процессе
- [ ] **⚠️ Новая архитектура эскалации/обучения** — схема БД/модели/миграции внедрены, но wiring потоков (модерация, очередь, Telegram per branch) ещё не подключён
- [ ] **⚠️ Эскалация всё ещё частая на реальные вопросы** — KB неполная, score часто < 0.5 → создаётся заявка; мелкие сообщения ("спасибо", "ок?") больше не должны создавать заявки (whitelist + guardrails)
- [ ] **⚠️ Active Learning частично** — owner-ответ → auto-upsert в Qdrant работает (логи 2025-12-25: "Owner response detected" / "Added to knowledge"), но нет модерации/метрик
- [ ] **⚠️ Ответы медленные (outbox)** — обновлено: `OUTBOX_COALESCE_SECONDS=1`, `OUTBOX_WINDOW_MERGE_SECONDS=2.5`, `OUTBOX_WORKER_INTERVAL_SECONDS=1`; safe intents (SAFE5) total_s 2.72–2.86s; LLM ветка (CMPX6-3/6-5/7-4/7-5/8-1) total_s 8.35–9.52s (avg 8.99, p90 9.48) → SLA <10s для LLM достигнут
- [ ] **⚠️ Model routing + LLM timeout** — `FAST_MODEL=gpt-5-mini`, `SLOW_MODEL=gpt-5-mini`, `INTENT_TIMEOUT_SECONDS=1.5`, `LLM_TIMEOUT_SECONDS=4`, `FAST_MODEL_MAX_CHARS=160`, `LLM_MAX_TOKENS=600`, `LLM_HISTORY_MESSAGES=6`, `LLM_KNOWLEDGE_CHARS=1500`, `LLM_CACHE_TTL_SECONDS=86400`; llm_ms ~4.3s (timeout=true) → SLA по времени достигнут, но таймауты всё ещё происходят
- [ ] **⚠️ Out‑of‑domain gate до booking/truth** — ранний OOD‑ответ без LLM (код обновлён, нужен деплой/проверка)
- [ ] **⚠️ OOD anchors (data-driven)** — demo_salon: anchors_in/out расширены (животные/погода/политика/кулинария/код/советы/анекдоты + style/booking/адрес/часы), offtopic_examples дополнил; SQL зафиксирован в `ops/update_instance_demo.sql`, нужен деплой, если API ещё на старом образе
- [ ] **⚠️ Закрепы заявок в Telegram** — фикс в коде: `unpin` теперь использует `handover.telegram_message_id` (fallback на callback message_id); нужен деплой/проверка
- [ ] **⚠️ Дубли заявок на одного клиента** — владельцу неудобно; нужен guard: при open handover не создавать новый, а писать в текущий топик
- [ ] **Branch подключен частично** — выбор branch и запись `conversation.branch_id` есть в `webhook/_legacy.py`, но Telegram per branch и RAG фильтры всё ещё по client → `SPECS/MULTI_TENANT.md`
- [ ] **⚠️ by_instance зависит от instanceId** — demo_salon исправлен (query‑param даёт instanceId), остальным клиентам нужно прокинуть
- [ ] **⚠️ demo_salon truth-gate даёт цену на "как у/в стиле"** — нет правила style_reference, фото не поддерживаются; нужен отдельный ответ/эскалация
- [ ] **⚠️ Медиа (аудио/фото/документы)** — guardrails + Telegram forward + локальное хранение + транскрипция коротких PTT добавлены в код (нужен деплой); длинные аудио/видео и OCR/vision отсутствуют
- [ ] **⚠️ ASR контур (ElevenLabs scribe_v1 primary + whisper-1 fallback)** — добавлены ASR настройки/таймаут/минимальная длина, цепочка fallback, сообщение при fail, метаданные в messages.metadata.asr + метрика asr_fail_rate (миграция `ops/migrations/016_add_asr_metrics.sql`), нужен деплой/проверка
- ASR low-confidence → подтверждение распознавания (“Я услышал… да/нет”), `asr_confirm_pending` в `conversation.context`.
- multi-intent split for long messages (primary intent only, secondary clarified).
- [ ] Метрики (Quality Deflection, CSAT) — план: `SPECS/ESCALATION.md`, часть 6
- [ ] Dashboard для заказчика — backlog
- [ ] Quiet hours для напоминаний — P2

### Блокеры
- **docker-compose** — инфра‑стек жив и разделён: `traefik/website` → `/home/zhan/infrastructure/docker-compose.yml`, core stack → `/home/zhan/infrastructure/docker-compose.truffles.yml` (env: `/home/zhan/infrastructure/.env`); был кейс `KeyError: 'ContainerConfig'` на `up/build`; API деплой через `/home/zhan/restart_api.sh` (CI image через `IMAGE_NAME` + `PULL_IMAGE=1`, локальный `docker build` — fallback); `/home/zhan/truffles-main/docker-compose.yml` — заглушка

---

## РЕГЛАМЕНТ: МОЗГИ БОТА (каждая сессия)

- Старт: минимальный пакет памяти — `docs/SESSION_START_PROMPT.txt` (Brain Pack), `SPECS/CONSULTANT.md`, `SPECS/ESCALATION.md`, пакет клиента `truffles-api/app/knowledge/<client_slug>/`.
- Паттерн работы: проблема → диагностика (1–2 шага) → решение → тест → запись в `STATE.md`.
- Источник истины (без дублей): факты только в `SALON_TRUTH.yaml`, политика только в `POLICY.md`, фразы только в `INTENTS_*.yaml`, тесты только в `EVAL.yaml`.
- Обязательный остаток до "идеального консультанта": см. `SPECS/CONSULTANT.md` → раздел "Идеальный консультант — обязательный остаток".
- Проверка: `pytest truffles-api/tests/test_<client>_eval.py` + sync KB в Qdrant (`ops/manual_sync_demo.py` или `ops/sync_client.py`).

---

## PHASE 0 — RELEASE CRITERIA (DoD)

См. `STRATEGY/REQUIREMENTS.md` → раздел "DEFINITION OF DONE — PHASE 0".

Кратко:
- Safety/Law: оплата/предоплата/проверка/возврат, перенос, скидки, medical/complaint → только эскалация/шаблон.
- Core value: truth‑first по базовым вопросам + сбор лида на запись.
- Reliability: ACK‑first + outbox; coalescing 8s; без дублей/потерь.
- Evidence: pytest+eval+ruff зелёные + smoke‑check на проде.

---

## ТЕКУЩИЙ ПЛАН

> Источники: `STRATEGY/TECH_ROADMAP.md`, `STRATEGY/REQUIREMENTS.md`

### Протокол задач (единый источник правды)

- Любая задача/приоритет существует только если записана в этом разделе (иначе “не существует”).
- Формат задачи для Brain (6 строк): Goal / Scope / Steps / Evidence / Tests / Stop.
- Формат отчёта Hands (7 строк): GOAL / FILES / TESTS / LIVE-CHECK / EVIDENCE / COMMIT / RISKS.
- One-issue flow: 1 проблема → 1 правка → 1 проверка → запись в `STATE.md`.
- RCA-first: сначала причина + evidence (код/trace/SQL/CI), потом решение; без доказательств — стоп.
- Offline-resolver: масштаб через data-lexicon + готовые библиотеки; regex/словари в коде — только временный fallback.

### Канон (North Star / DoD / Epics / порядок)

- **North Star:** бережный консультант‑хост, truth‑first, держит цель booking; эскалация всегда доступна пользователю.
- **P0 DoD:** см. `docs/TECH_STATUS.md:135-141` (LAW, truth‑first, outbox/dedup, /admin/version, Core‑50 CI, smoke‑run).
- **Эпики P0:** диалоговая устойчивость (intent_queue/expected_reply/booking_interrupt/answer‑interpreter), truth/policy (info‑bundle/CTA/policy‑gates), эскалация+AL (takeover + auto‑upsert, роли/очередь/moderation/branch pending), ops/infra (diagnose/backup/ пилот‑чеклист).
- **Confidence router:** multi‑level confidence сейчас P2 в `SPECS/CONSULTANT.md:914-920`; если повышаем приоритет — фиксируем отдельным решением.
- **Порядок закрытия:** 1) repo‑audit через CI (локальный pytest запрещён) 2) DoD‑чек 3) закрыть P0 gaps 4) live‑check 5) update `STATE.md`.
- **Открытые вопросы:** retention (рекомендовано 6 мес архив → delete), dashboard (P2–P3), media/ASR/OCR (fallback сейчас, расширение позже).

### Сейчас (эта сессия / неделя)
1. [x] Аудит документов и структуры
2. [x] **Gap в спеке: state=manager_active без топика** (P0) ✅
3. [x] **Промпт: бот представляется** (Закон РК об ИИ) ✅
   - Бот говорит "Я виртуальный помощник" при приветствии
4. [x] **Confidence threshold** — score < 0.5 → не выдумывать ✅
   - Реализовано в ai_service.py
5. [x] **Low confidence: уточнить → потом заявка** — теперь 1–2 уточнения + подтверждение перед эскалацией
6. [x] Контракт поведения: приоритеты интентов + матрица state × intent → action (SPECS/CONSULTANT.md, SPECS/ESCALATION.md)
7. [x] Policy engine: normalize → detect signals → resolve → action; demo_salon вынесен в policy handler (без client-specific if в flow)
8. [x] Модель слотов записи: валидаторы service/datetime/name + запрет opt-out/фрустрации в слотах
9. [x] Golden-scenarios: автопрогон ключевых кейсов из truffles-api/tests/test_cases.json (decision/signals)

### Возобновить (P0 — план остановлен, нужен DoD/верификация)

1. [ ] Offline устойчивость без `OPENAI_API_KEY`
   - DoD: CI core/long/ASR зелёные без ключа; offline controller возвращает фиксированный class/goal; тесты не вызывают LLM.
2. [ ] Session Memory v1.1 (goal_stack/pending_slots/unanswered/TTL=24h)
   - DoD: короткие ответы ("да/ок/в субботу") маппятся к последнему вопросу; reset по "новая тема"/pending/manager.
3. [ ] ASR battery + long-chaos (12-15 ходов) как блокирующий gate CI, без OpenAI
   - DoD: CI конфигирует gate и проходит в оффлайне.
4. [ ] Monitoring/observability
   - DoD: trace/meta полей controller_used/confidence/error, info_semantic_match_skip_reason, session_memory_update; алерты clarify/escalation/latency.
5. [ ] Pending SLA ping/auto-close (15 мин / 4 ч) + pending_ack/close intent + meta pending_action
   - DoD: подтверждённые интервалы/trace/meta + CI evidence.

### P0 — Молчание/живость (операционный триаж)

1. [x] Outbound guard + outbox worker (TEST_MODE/allowlist/worker)
   - DoD: подтверждено по логам/метрикам, что outbound не скипается и outbox не копится.
   - Evidence (ops, 2026-01-08): TEST_MODE=1, allowlist=77015705555@s.whatsapp.net; logs show "Outbox worker started"; /admin/health pending=0; outbox status counts SENT=1222, FAILED=12; /admin/outbox/process POST (container token) returned {"claimed":0,"sent":0,"failed":0,"retry_scheduled":0}.
2. [x] Qdrant headers при отсутствии API key
   - DoD: headers не содержат None; knowledge search не падает.
   - Evidence: PR #77 https://github.com/k1ddy/Truffles-AI-Employee/pull/77, merge `f31bdd2`; CI (core/long + build/push + deploy) https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20805150698; prod `/admin/version` → `{"version":"main","git_commit":"f31bdd26bdfdf68f24f80954afa95e1af69cbc01","build_time":"2026-01-08T04:08:40Z"}`.
3. [x] Carryover follow-up для коротких pricing-вопросов
   - DoD: `test_service_carryover_applies_for_pricing` зелёный.
   - Evidence: PR #78 https://github.com/k1ddy/Truffles-AI-Employee/pull/78; CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20805338690; prod `/admin/version` → `{"version":"main","git_commit":"4bdfcf1d020f11d7b1d8f4a7aef061e3304438ef","build_time":"2026-01-08T04:18:53Z"}`. Note: CI jobs run eval only; unit test not in CI.
4. [x] `/webhook/debug` закрыт/защищён
   - DoD: доступ только с админ‑токеном или флагом DEBUG_WEBHOOK_ENABLED.
   - Evidence: CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20805515456; prod `/admin/version` → `{"version":"main","git_commit":"d0da998ae6c1181da2f2b3ae78628f2e1df8e4ce","build_time":"2026-01-08T04:29:12Z"}`.
5. [x] Answer‑Interpreter для expected_reply + datetime fallback
   - DoD: короткие ответы времени/услуги маппятся без цикла уточнений.
   - Evidence: CI main https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20805662030; prod `/admin/version` → `{"version":"main","git_commit":"bb11f104a5523688d16e8c835ae5ea99b05dd80f","build_time":"2026-01-08T04:37:50Z"}`.

### P0 — Ops hygiene (после триажа)

1. [x] Fix warning в `ops/diagnose.py` (datetime.utcnow deprecation)
   - DoD: diagnose без warning.
   - Evidence: 2026-01-08T04:55:38Z, diagnose output без DeprecationWarning.
2. [x] Metrics daily snapshot отсутствует для текущей даты
   - DoD: `/admin/metrics` возвращает данные для валидной даты (today или latest), evidence через SQL snapshot/endpoint.
   - Evidence: metrics_daily max=2026-01-06 → snapshot run for 2026-01-08 (INSERT 0 1); /admin/metrics OK (payload with metric_date=2026-01-08).

### P1 — Структурные риски (из анализов)

1. [ ] Sync HTTP вызовы внутри async пайплайна
   - DoD: ChatFlow/Qdrant/LLM вызовы не блокируют event loop (async/threads), есть общий клиент/pool.
2. [ ] Mutable defaults в моделях JSONB
   - DoD: default=dict для JSONB полей; нет shared mutable.
3. [ ] Legacy `app/webhook.py`
   - DoD: файл удалён или явно помечен LEGACY + исключён из документации.
4. [ ] Demo‑only ветвления
   - DoD: core‑логика не зависит от `client_slug == "demo_salon"`; policy handlers по policy_type.
5. [ ] Несостыковка промпта/логики (disclosure/телефон)
   - DoD: решение записано и промпт приведён к фактическому поведению.
6. [ ] Централизация env‑конфигурации
   - DoD: ключевые env читаются через Settings, тесты могут подменять.
7. [ ] Outbox failsafe
   - DoD: если worker отключён, webhook явно сигналит или запускает sync‑процесс.
8. [ ] CI coverage для unit‑тестов роутера
   - DoD: `tests/test_message_endpoint.py` (или таргетные кейсы) запускаются в CI.

### Webhook refactor checkpoint (2026-01-08)

- **Сделано:** монолит `webhook.py` разнесён на модули в `truffles-api/app/routers/webhook/`; активная оркестрация остаётся в `truffles-api/app/routers/webhook/_legacy.py`, совместимость — через `truffles-api/app/routers/webhook/__init__.py`.
- **Модули уже выделены:** `parsing.py`, `dedup.py`, `booking.py`, `info.py`, `policy.py`, `decision.py`, `pending.py`, `session_memory.py`, `media.py`, `shield.py`, `guards.py`, `trace.py`, `response.py`.
- **Evidence (merged PRs):** #92–#102 (trace/parsing/dedup/booking/info/policy/decision/pending+session_memory/media/shield/guards) — https://github.com/k1ddy/Truffles-AI-Employee/pulls?q=is%3Apr+is%3Amerged+webhook+extract
- **Устаревшие PR закрыты:** #81, #82, #83, #87 (obsolete после реальных модулей).
- **Следующий блок выноса (рекомендован):** контекст/контроллер диалога (expected_reply_type, context_manager, carryover, confirmations) → новый модуль `context_manager.py`; затем booking update/prompt; затем branch selection; затем router/outbox.
- **Merged:** PR #103 “Extract webhook context manager helpers” — https://github.com/k1ddy/Truffles-AI-Employee/pull/103 (merge commit 140aa7b88c9e81583a1ad296e2dffc7784b97587).
- **Merged:** PR #104 “Extract webhook booking prompt helpers” — https://github.com/k1ddy/Truffles-AI-Employee/pull/104 (merge commit d286beaaaa1b80fdaf65b0fc669c74ec558b9c3a).
- **Merged:** PR #105 “Extract webhook branch selection helpers” — https://github.com/k1ddy/Truffles-AI-Employee/pull/105 (merge commit 41442837cb430106bd130758fe9ccc1f85c5dc8c).
- **Merged:** PR #106 “Extract webhook outbox helpers” — https://github.com/k1ddy/Truffles-AI-Employee/pull/106 (merge commit 9ab3196d905a744eee73ed026a24e0f1b446b6a3).
- **Merged:** PR #107 “Extract webhook HTTP routing helpers” — https://github.com/k1ddy/Truffles-AI-Employee/pull/107 (merge commit b39712735ae41684e1c967e1adc5fb56f3f3898e).
- **Осталось в `_legacy.py` (сводка):** оркестратор `_handle_webhook_payload`; wrapper `_process_outbox_rows` (compat); observability/RAG meta/backlog; эвристики booking/policy/carryover/time; controller/router logic; refusal flags; response composition helpers; convo/handover DB helpers; low-confidence retry.

### Следующее (по порядку)

**НЕДЕЛЯ 1: Критичная инфраструктура [P0]** → `SPECS/INFRASTRUCTURE.md` ✅ DONE
1. [x] Секреты → .env (убрать из кода)
2. [x] Бэкап PostgreSQL (cron ежедневно 3:00)
3. [x] Бэкап Qdrant (cron воскресенье 4:00)
4. [x] Алерты в Telegram (сервис готов, нужно интегрировать)

**НЕДЕЛЯ 2: Качество кода [P1]** ✅ DONE
5. [x] Базовые тесты (91 тест, pytest проходит)
6. [x] Логирование (JSON, 46 print→0)
7. [x] CI/CD (GitHub Actions)
8. [x] Линтер (ruff)
9. [x] Интеграция alert_service в код

**НЕДЕЛЯ 3: Защита кода [P0]** → `SPECS/ARCHITECTURE.md` ЧАСТЬ 10 ✅ DONE
10. [x] Result pattern — `services/result.py` (11 тестов)
11. [x] State service — атомарные переходы с транзакциями (13 тестов)
12. [x] Health service — self-healing (6 тестов)
13. [x] SQL Constraint — `migrations/003_add_state_constraint.sql`
14. [x] Рефакторинг webhook.py — использует state_service
15. [x] Health endpoints — GET/POST /admin/health, /admin/heal

**НЕДЕЛЯ 4: Функционал** ⚠️ ЧАСТИЧНО (есть проблема)
16. [x] Эскалация при низком confidence — РЕАЛИЗОВАНО (MID=0.5, HIGH=0.85 + whitelist/guardrails)
17. [x] Active Learning — owner ответы автоматически в Qdrant
18. [ ] Multi-level confidence (в продукте: 0.85/0.5/low_confidence + уточнения)
19. [ ] Telegram кнопки модерации [В базу] [Отклонить] для не-owner

**АРХИТЕКТУРА ЭСКАЛАЦИИ/ОБУЧЕНИЯ [P0] — НОВОЕ РЕШЕНИЕ**
20. [ ] Роли + идентичности (agents/agent_identities) — схема БД/модели есть, wiring pending
21. [ ] Очередь обучения (learned_responses: pending/approved/rejected) — схема БД есть, модерация/флоу pending
22. [ ] Telegram per branch (branches.telegram_chat_id) — pending (branch routing в webhook уже есть)

**⚠️ ПРОБЛЕМА:** Эскалация срабатывает слишком часто — даже на "ты еще здесь?"
- **Причина:** KB неполная → RAG score часто < 0.5 на реальные вопросы
- **Решения:**
  1. Threshold уже понижен до 0.5 (MID) + HIGH=0.85
  2. Whitelist/guardrails уже добавлены (greeting/thanks/ok/???)
  3. Добавить базовые ответы в knowledge base
  4. Добавить «уточнение перед заявкой» (см. пункт 5 в плане)

---

## BACKLOG (хотелки)

> Идеи на потом. НЕ ДЕЛАТЬ пока не в плане.

| Идея | Зачем | Приоритет | Откуда |
|------|-------|-----------|--------|
| **Омниканальность (Channel)** | Instagram, Telegram bot, CRM — без переделки | P2 | архитектура |
| **Branch к роутингу** | Несколько номеров WhatsApp у одного клиента | P2 | архитектура |
| **Implementation Brain (внедрения/поддержка)** | Быстрее запускать клиентов, фиксировать паттерны и ошибки | P1 | стратегия |
| Алерт "бот пронёс хуйню" | Критичные ошибки сразу владельцу | P1 | my_notes |
| Dashboard для заказчика | Видеть статистику | P2 | REQUIREMENTS |
| Telegram чат для владельца | Модерация, обсуждение, быстрая связь | P2 | my_notes |
| Ежедневный отчёт владельцу | Сколько диалогов, эскалаций, проблем | P2 | my_notes |
| Аргументы для сбора данных | В договор — почему выгодно делиться | P2 | my_notes |
| CRM интеграция | Синхронизация | P3 | Идея |
| Голосовые сообщения | Расшифровка | P3 | Идея |
| Google Drive для баз знаний | Заказчик сам обновляет FAQ | P3 | my_notes |
| Скрипт синхронизации knowledge/ → Qdrant | Автозагрузка базы знаний | P1 | папки |
| Скрипт загрузки prompts/ → БД | Автозагрузка промптов | P2 | папки |
| Использовать context/intents/ в классификаторе | Улучшить intent detection | P2 | папки |
| Автотесты из truffles-api/tests/test_cases.json | Проверка качества бота | P2 | папки |
| Исследование LLM моделей | Найти оптимальные модели для задач | P2 | сессия |
| Сжатие диалогов (summarizer) | Киллер-фича для длинных разговоров | P2 | сессия |
| Скрипт update_parameter | Управление параметрами с защитой от дураков | P2 | сессия |
| Веб-интерфейс (личный кабинет) | Заказчик сам меняет параметры | P3 | сессия |

---

## КАРТА ДОКУМЕНТОВ

| Область | Документ | Когда обновлять |
|---------|----------|-----------------|
| **Принципы** | `AGENTS.md` | Редко, только важное |
| **Состояние** | `STATE.md` | Каждую сессию |
| **Структура** | `STRUCTURE.md` | При добавлении/удалении файлов |
| **Техника** | `TECH.md` | При изменении доступов/команд |
| **Инфра compose** | `/home/zhan/infrastructure/docker-compose.yml`, `/home/zhan/infrastructure/docker-compose.truffles.yml` | При изменении инфраструктуры |
| **Контекст** | `docs/IMPERIUM_CONTEXT.yaml` | При изменении фактов/архитектуры |
| **Решения** | `docs/IMPERIUM_DECISIONS.yaml` | При изменении CEO-level policy |
| **Gaps** | `docs/IMPERIUM_GAPS.yaml` | При закрытии/открытии критических пробелов |
| **Старт сессии** | `docs/SESSION_START_PROMPT.txt` | При изменении правил запуска |
| **Сводка** | `SUMMARY.md` | После инвентаризации/крупных изменений |
| **Анкета** | `CHATGPT_QUESTIONS_ANSWERS.md` | При обновлении ответов |
| | | |
| **Эскалация** | `SPECS/ESCALATION.md` | handovers, напоминания, Telegram |
| **Поведение бота** | `SPECS/CONSULTANT.md` | промпт, правила ответов |
| **Автообучение** | `SPECS/ACTIVE_LEARNING.md` | модерация, Qdrant |
| **Архитектура** | `SPECS/ARCHITECTURE.md` | новые сервисы, потоки данных |
| **Инфраструктура** | `SPECS/INFRASTRUCTURE.md` | безопасность, CI/CD, тесты |
| **CI/CD** | `.github/workflows/ci.yml` | При изменении pipeline |
| **Pre-commit** | `.pre-commit-config.yaml` | При изменении hooks/сканеров |
| **Мультитенант** | `SPECS/MULTI_TENANT.md` | онбординг, новые клиенты |
| | | |
| **Миграции** | `ops/migrations/*.sql` | при изменении схемы БД |
| **Миграции** | `ops/migrations/011_add_webhook_secret.sql` | webhook secret per tenant |
| **Миграции** | `ops/migrations/014_add_branch_routing_settings.sql` | настройки branch routing + auto-approve |
| **Требования** | `STRATEGY/REQUIREMENTS.md` | Требования Жанбола |
| **Roadmap** | `STRATEGY/TECH_ROADMAP.md` | Технический план |
| **Продукт** | `STRATEGY/PRODUCT.md` | Тарифы, фичи |
| **Рынок** | `STRATEGY/MARKET.md` | Исследования, метрики |
| | | |
| **База знаний** | `knowledge/*.md`, `knowledge/demo_salon/*.md` | FAQ, примеры, сленг, демо-салон |
| **Интенты** | `context/intents/*.txt` | Новые интенты |
| **Промпты** | `prompts/*.md` | Системный промпт |

---

## ШАБЛОН ДЛЯ ФИКСАЦИИ РАССУЖДЕНИЙ (1–2 минуты)

- Боль/симптом: что именно ломает качество (факт/лог/пример)
- Почему важно: риск для клиента/бизнеса
- Диагноз: почему это происходит
- Решение: что меняем и где (файлы/правила)
- Проверка: команда/результат
- Осталось: что ещё не закрыто и следующий шаг

---

## ИСТОРИЯ СЕССИЙ

### 2026-01-13 — Сессия: статус и уроки (канон/trace)

**Что закрепили:**
- Consult clarify/short‑circuit подтверждён (см. запись 2026‑01‑13 ниже).
- No-response dedup + shield_drop suppression и pending SLA ping spam исправлены (см. записи 2026‑01‑13 и 2026‑01‑12 ниже).

**Уроки/инварианты:**
- JSONB `conversation.context`: in-place не сохраняется → только copy/assign или `flag_modified`.
- decision_trace/meta обязательны на каждый user‑msg; pending/policy gaps = stop‑line.
- Simulated inbound — только по явному waiver; иначе live‑check = BLOCKED.

**Открыто:**
- No-response pipeline hardening (OpenAI 400 temp, WebhookResponse None) — pending.
- P0 outbox latency — tail.

### 2026-01-14 — P1-1 Router SLA + controller_attempted evidence (post-deploy real inbound)

**Что сделали:**
- Синхронизировали controller_* мета с class_router в info_class flows (PR #167) и подтвердили на real inbound post-deploy.

**Evidence:**
- PR #167: https://github.com/k1ddy/Truffles-AI-Employee/pull/167
- CI PR: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20982624189
- Deploy: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20982653913
- /admin/version: `{"version":"main","git_commit":"f46944cc084a66b17604b80d5969196fe520d510","build_time":"2026-01-14T04:44:48Z"}`
- Real inbound post-deploy (conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`):
  - msg_id `6bc30dbc-3929-49ae-9da8-3412e66bd296` (messageId `3EB02FF2BA5FCE055E4E6F`) — controller_attempted=true, low_confidence=true, controller_fallback_reason=NULL; class_router.controller.* совпадает.
  - msg_id `7780bb42-84b5-440d-8663-3bc141f25437` (messageId `3EB044DD426A7045DC8850`) — controller_attempted=true, low_confidence=true, controller_fallback_reason=NULL; class_router.controller.* совпадает.
  - msg_id `4ef63a6e-2b4b-476f-98b2-0bbdc3a1f1db` (messageId `3EB0648EF05C4F5562C39E`) — truth_gate, router_eligible=false, class_router отсутствует.
- SLA:
  - baseline 7d: avg_fallback_rate=0.0582, max=1.0000
  - post-deploy: avg_fallback_rate=0.0000, max=0.0000
- low_confidence check: attempts=2, low_confidence=2, bad_low_confidence_fallbacks=0.

### 2026-01-14 — P1 Category vs Service: services_overview guard

**Что сделали:**
- Добавили guard для services_overview перед service_matcher + RU/KZ services_overview lexicon, подтвердили на real inbound post-deploy.

**Evidence:**
- PR #170: https://github.com/k1ddy/Truffles-AI-Employee/pull/170
- CI PR: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20985182973
- Deploy: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20985204021
- /admin/version: `{"version":"main","git_commit":"f8d73928ae9e7886881ebba0c513e4e01abb644d","build_time":"2026-01-14T06:51:26Z"}`
- Real inbound post-deploy (conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`):
  - msg_id `5ad1313c-47f1-4774-8174-c0097a689622` (messageId `3EB00B785919F1F301CDA7`) — intent=services_overview, source=truth_gate, service_semantic_score=NULL.
  - msg_id `7820c3f3-e469-4cf5-804d-6b646872859f` (messageId `3EB00D604467F28D634348`) — intent=services_overview, source=truth_gate, service_semantic_score=NULL.
  - msg_id `3b41ca5c-ea4a-42af-94b1-7783eeb06290` (messageId `3EB096B413ADC6E015AA77`) — intent=services_overview, source=truth_gate, service_semantic_score=NULL.
- Trace (decision_trace, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, recorded_at >= `2026-01-14T06:51:26Z`): service_semantic_matcher rows=0.

### 2026-01-14 — Guest policy + consult pack (post-merge PR #179)

**Что сделали:**
- Подтвердили guest_policy (pack‑lexicon) и consult pack‑reply на реальном inbound после мержа PR #179.

**Evidence:**
- /admin/version: `{"version":"main","git_commit":"df258b353a4c84ee61e2c3b2ca49736898a72695","build_time":"2026-01-14T23:11:50Z"}`
- Live inbound (allowlist JID 77015705555):
  - guest_policy: msg `dec06e10-1412-4eda-a9b6-ec5ddb17522c` (messageId `3EB07BDB44C820A0BBE8FF`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`) decision_meta `intent=info_bundle`, `info_sections=["address","hours","guest_policy"]`, `source=class_router`; assistant reply `acda6da0-6cfe-4ad0-a431-cd1c7cca1ea9` содержит “зона ожидания”.
  - consult pack: msg `9a83a6a3-5838-44be-92d6-67800346a953` (messageId `3EB080517E51CCA1ECA027`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`) decision_meta `intent=consult_reply`, `source=pack`, `consult_playbook_id=general_consult`, `consult_variant_id=3eca06b5`, `tips_used` (3 пункта).
- consult_flow trace: `{"stage":"consult_flow","state":"bot_active","reason":"consult_pack","decision":"consult_reply","recorded_at":"2026-01-14T23:16:34.513798+00:00","consult_variant_id":"3eca06b5","consult_playbook_id":"general_consult"}`.

### 2026-01-14 — GAP-017 Branch Isolation (RAG + Escalation)

**Что сделали:**
- Подтвердили branch_routing + decision_meta.branch_id на demo_salon и truffles (две instanceId).
- Подтвердили RAG fallback на client-level при `branch_filter_empty`.
- Подтвердили policy_gate hard_law (refund) на demo_salon и truffles; demo_salon создал handover + Telegram notification.

**Evidence:**
- PR #172: https://github.com/k1ddy/Truffles-AI-Employee/pull/172
- CI PR: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20993762935
- Deploy: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20993826140
- /admin/version: `{"version":"main","git_commit":"682943b3e78bce6c5d6391a59519284444465fbe","build_time":"2026-01-14T12:19:41Z"}`
- truffles inbound (policy_gate):
  - msg_id `9aac1bd2-81f7-4ceb-8807-3d7a512cf540` (messageId `3EB01EC14C05FDE0BE7002`), conv_id `d868cc92-837e-463e-b8e1-ea39a1baccea` — intent=refund, source=policy_pack, action=escalate, policy_gate=hard_law, branch_id `cf86bee7-e38f-4c8c-a087-aa4961911e0b`, routing_source=conversation, router_eligible=false, controller_eligible=false.
  - policy_gate trace: `{"stage": "policy_gate", "state": "bot_active", "intent": "refund", "source": "policy_pack", "decision": "escalate", "risk_level": "high", "policy_gate": "hard_law", "policy_type": "demo_salon", "recorded_at": "2026-01-14T13:24:42.091625+00:00", "policy_section": "refund", "router_eligible": false, "controller_eligible": false, "router_skipped_reason": "law_gate", "controller_skipped_reason": "law_gate"}`
- demo_salon inbound (policy_gate):
  - msg_id `5e946f31-6b93-4327-bc51-1946374fd419` (messageId `3EB0FE6008D22620692E98`), conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48` — intent=refund, source=policy_pack, action=escalate, policy_gate=hard_law, branch_id `b7f75692-951e-421a-aae6-f5db97394799`, routing_source=conversation, router_eligible=false, controller_eligible=false.
  - policy_gate trace: `{"stage": "policy_gate", "state": "pending", "intent": "refund", "source": "policy_pack", "decision": "escalate", "risk_level": "high", "policy_gate": "hard_law", "policy_type": "demo_salon", "recorded_at": "2026-01-14T13:39:40.293881+00:00", "policy_section": "refund", "router_eligible": false, "controller_eligible": false, "router_skipped_reason": "law_gate", "controller_skipped_reason": "law_gate"}`
- branch_routing trace:
  - truffles: `{"stage":"branch_routing","decision":"resolved","branch_id":"cf86bee7-e38f-4c8c-a087-aa4961911e0b","recorded_at":"2026-01-14T13:14:26.813156+00:00","knowledge_tag":null,"routing_source":"conversation"}`
  - demo_salon: `{"stage":"branch_routing","decision":"resolved","branch_id":"b7f75692-951e-421a-aae6-f5db97394799","recorded_at":"2026-01-14T13:17:13.433005+00:00","knowledge_tag":null,"routing_source":"conversation"}`
- RAG branch_filter_empty (bm25_filter):
  - messageId `3EB077B8FDA58B3D33D970` (demo_salon): `{"branch_id": null, "client_slug": "demo_salon", "filter_mode": "client_fallback", "filter_reason": "branch_filter_empty", "knowledge_tag": null}`
  - messageId `3EB0A5CD36A9DA5C38768E` (truffles): `{"branch_id": null, "client_slug": "truffles", "filter_mode": "client_fallback", "filter_reason": "branch_filter_empty", "knowledge_tag": null}`
- demo_salon handover + Telegram:
  - handover `75ce7362-bb94-4b12-9129-4a86d01b9bbd` status=pending, telegram_message_id=1191, notified_at `2026-01-14T13:39:39.968019+00:00`
  - conversation state=pending, telegram_topic_id=625
  - branch telegram_chat_id `-1003412216010`, client_settings manager_scope=branch
- Note: truffles policy_pack was enabled via `policy_type=demo_salon` at `2026-01-14T13:24:12Z` and cleared at `2026-01-14T13:25:52Z` for hard_law verification.

### 2026-01-15 — GAP-017 Strict branch filter (RAG uses branch_id/knowledge_tag)

**Что сделали:**
- Передали branch_id/knowledge_tag в timing_context после branch routing, чтобы RAG/BM25 строго фильтровал по branch.
- Убрали client-level fallback: `branch_filter_empty` возвращает 0 результатов без подмены фильтра.

**Evidence:**
- PR #185: https://github.com/k1ddy/Truffles-AI-Employee/pull/185
- CI (PR workflow_dispatch): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21014440864
- CI main + deploy: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21014503341
- /admin/version: `{"version":"main","git_commit":"7473358ac50435c2b85a00125e758f9d5fe98220","build_time":"2026-01-15T00:09:47Z"}`
- demo_salon inbound (branch filter applied):
  - msg_id `03bbec13-6cad-4914-948e-c64da1964a0c` (messageId `sim-branch-demo-1768435920`), conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`
  - decision_meta.rag_scores.bm25_filter: `{"branch_id":"b7f75692-951e-421a-aae6-f5db97394799","client_slug":"demo_salon","filter_mode":"branch","filter_reason":"branch_id","knowledge_tag":null}`
  - decision_trace (rag_retrieve): `{"filter_mode":"branch","filter_reason":"branch_id","branch_id":"b7f75692-951e-421a-aae6-f5db97394799"}`
- truffles inbound (strict empty result, no fallback):
  - msg_id `2acc8edb-cc97-4424-8c8d-b1265cc9aca7` (messageId `sim-branch-truffles-1768435932`), conv_id `d868cc92-837e-463e-b8e1-ea39a1baccea`
  - decision_meta.rag_scores.bm25_filter: `{"branch_id":"cf86bee7-e38f-4c8c-a087-aa4961911e0b","client_slug":"truffles","filter_mode":"branch","filter_reason":"branch_filter_empty","knowledge_tag":null}`
  - decision_trace (rag_retrieve): `{"filter_mode":"branch","filter_reason":"branch_filter_empty","branch_id":"cf86bee7-e38f-4c8c-a087-aa4961911e0b"}`
### 2026-01-13 — Consult clarify short‑circuit live‑check (prod)

**Что сделали:**
- Подтвердили consult‑clarify и short‑circuit (service known) на реальном ChatFlow inbound, без эскалации.

**Evidence:**
- PR #153: https://github.com/k1ddy/Truffles-AI-Employee/pull/153
- CI PR: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20943384712 (core/long/asr/lint/unit зелёные)
- Deploy: 2026-01-13T03:25:43Z (local build + restart_api; /admin/version=unknown)
- SQL (messages, role=user, content ILIKE 'Что посоветуете%'):
  - msg_id `3EB01D467DF68F8EA2954A`, created_at `2026-01-13T03:29:05.858671+00`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, action=reply, intent=consult_reply, expected_reply_type=service_choice, controller_low_confidence=false, controller_fallback_reason=NULL.
  - msg_id `3EB03F40311BAB0B6DA29A`, created_at `2026-01-13T03:29:44.059528+00`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, action=booking_prompt, intent=booking, expected_reply_type=time, expected_reply_shortcircuit=true, controller_fallback_reason=NULL.
- SQL (decision_trace, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`):
  - consult_flow: [{"stage":"consult_flow","reason":"consult_clarify","decision":"consult_clarify","expected_reply_type":"service_choice","state":"bot_active"},{"stage":"consult_flow","reason":"service_hint","decision":"short_circuit","consult_topic":"Что посоветуете по маникюру?","service_query":"Маникюр"}]
  - question_contract: expected_reply_type service_choice set → matched → expected_reply_type time set (booking_prompt).
- Conversation state: bot_active (no escalation) at `2026-01-13T03:29:45.547916+00`.

### 2026-01-13 — P1 Task A/B evidence (consult pack‑only + pending_wait + policy_gate)

**Что сделали:**
- Live‑check real WA inbound для consult pack‑only, pending_wait и policy_gate.
- Смёржили PR #155 (consult pack‑only + pending_wait trace).

**Evidence:**
- PR #155: https://github.com/k1ddy/Truffles-AI-Employee/pull/155
- CI PR (core/long/asr/lint/unit): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20945722911
- Merge commit: `863dab8dd706b0842eb2a8a1245d5f92e25153af` (merged_at 2026-01-13T07:42:20Z)
- consult pack‑only (messages.decision_meta):
  - msg_id `75278778-dad6-4224-a8aa-1f8703a79e6f`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`
  - consult_playbook_id `hair_aftercolor`, consult_variant_id `f2b3e084`, tips_used (3 пункта), source `pack`
- consult trace (decision_trace):
  - {"stage":"consult_flow","state":"bot_active","reason":"consult_pack","decision":"consult_reply","recorded_at":"2026-01-13T06:44:59.940363+00:00","consult_variant_id":"f2b3e084","consult_playbook_id":"hair_aftercolor"}
  - NOTE: decision_trace живёт в conversation.context и очищается при manager_resolve; запись была зафиксирована до reset.
- pending_wait (messages.decision_meta):
  - msg_id `317c573a-b1a2-467f-920f-91eca4b3ea21`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, pending_action `pending_wait`
- pending_wait trace (decision_trace):
  - {"stage":"pending_wait","state":"pending","decision":"pending_wait","recorded_at":"2026-01-13T07:08:42.052369+00:00","router_eligible":false,"controller_eligible":false}
- policy_gate (messages.decision_meta):
  - msg_id `43b8cd43-5789-41ea-adb2-97f31e90a49b`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, source `policy_gate`, policy_gate `discounts`
- policy_gate trace (decision_trace):
  - {"stage":"policy_gate","state":"bot_active","intent":"discounts","decision":"reply","risk_level":"low","policy_gate":"discounts","policy_type":"demo_salon","recorded_at":"2026-01-13T07:24:53.451704+00:00"}

### 2026-01-13 — TP-LAW-02 /message hard-law gate live-check (CI deploy)

**Что сделали:**
- CI workflow_dispatch deploy PR #161 (tp-law-02-message-gate) и live-check /message для Hard-LAW.

**Evidence:**
- PR #161: https://github.com/k1ddy/Truffles-AI-Employee/pull/161
- CI (workflow_dispatch + deploy): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20953644071
- CI main (post-merge #161): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20953969528
- Note: workflow_dispatch gitleaks uses `--no-git` (working tree only); push/PR keep full history scan.
- Prod `/admin/version`: `{"version":"tp-law-02-message-gate","git_commit":"7bf83d57222f31d955b631f6a51839f6dfd3ba18","build_time":"2026-01-13T10:39:59Z"}`
- Live-check /message (Hard-LAW text "Хочу оплатить картой"): response `По оплате уточню у администратора — передам администратору ваш вопрос.`
- SQL (messages.decision_meta, conv_id `4f9026c2-9c94-4b38-8248-b5aacf635cdf`):
  - msg_id `message-273a4147-7fe5-4a7d-9e51-793e3a14c253`, created_at `2026-01-13 10:42:46.006241+00`, policy_gate=hard_law, policy_section=payment_info, llm_used=false.
- SQL (decision_trace, conv_id `4f9026c2-9c94-4b38-8248-b5aacf635cdf`):
  - {"stage":"policy_gate","policy_gate":"hard_law","policy_section":"payment_info","decision":"escalate","recorded_at":"2026-01-13T10:42:57.824276+00:00","router_skipped_reason":"law_gate","controller_skipped_reason":"law_gate"}

### 2026-01-13 — GAP-014/016 policy_pack source + non-demo live-check (PR #163)

**Что сделали:**
- Исправили `source=policy_pack` при наличии policy_pack и отметку `policy_pack_missing` при отсутствии (PR #163).
- CI workflow_dispatch deploy PR #163 и live-check для demo_salon + truffles (Hard-LAW refund).
- Ops: синхронизировали instance_id для truffles (clients/branches), временно включали policy_pack для live-check и восстановили.

**Evidence:**
- PR #163 (code): https://github.com/k1ddy/Truffles-AI-Employee/pull/163
- CI PR (core/long/asr/lint/unit): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20957054441
- Deploy (workflow_dispatch): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20960699106, deployed_at 2026-01-13T14:39:55Z
- demo_salon real inbound:
  - msg_id 3EB079A3A91F8B6CE456B5, conv_id b8c559d1-f8cd-4173-ae70-0a9683833e48
  - decision_meta: policy_gate=discounts, source=policy_pack, llm_used=false, risk_level=low
  - decision_trace: stage=policy_gate, policy_gate=discounts, risk_level=low
- non-demo truffles (temporary policy_pack):
  - msg_id 3EB0419E97F90CADB430AA, conv_id d868cc92-837e-463e-b8e1-ea39a1baccea
  - decision_meta: policy_gate=hard_law, policy_section=refund, source=policy_pack, llm_used=false, risk_level=high
  - decision_trace: stage=policy_gate, policy_gate=hard_law, policy_section=refund, risk_level=high
- SQL (messages, role=user, content in ["Есть скидки?", "Хочу вернуть деньги"]):
  - demo_salon: msg_id `3EB079A3A91F8B6CE456B5`, created_at `2026-01-13 14:42:45.360258+00`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, decision_meta policy_gate=discounts, source=policy_pack, llm_used=false, risk_level=low, action=reply.
  - truffles: msg_id `3EB0419E97F90CADB430AA`, created_at `2026-01-13 14:43:00.892848+00`, conv_id `d868cc92-837e-463e-b8e1-ea39a1baccea`, decision_meta policy_gate=hard_law, policy_section=refund, source=policy_pack, llm_used=false, risk_level=high, action=escalate.
- SQL (decision_trace, stage=policy_gate):
  - conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`: policy_gate=discounts, source=policy_pack, decision=reply, risk_level=low, recorded_at `2026-01-13T14:42:59.001386+00:00`.
  - conv_id `d868cc92-837e-463e-b8e1-ea39a1baccea`: policy_gate=hard_law, policy_section=refund, source=policy_pack, decision=escalate, risk_level=high, recorded_at `2026-01-13T14:43:04.123589+00:00`.
- Live-check: user confirmed receiving `Передал менеджеру. Могу чем-то помочь пока ждёте?` после refund.
- Restore: /tmp/truffles_restore_truffles_voVWxl.sql applied (`cat /tmp/truffles_restore_truffles_voVWxl.sql | docker exec -i truffles_postgres_1 psql -U n8n -d chatbot`).

### 2026-01-13 — Fix: Telegram topic handover routing (manager replies → WhatsApp)

**Что сделали:**
- `find_conversation_by_telegram` теперь приоритетно ищет active handover по `topic_id`, чтобы не падать на закрытую conversation.
- Live‑check: сообщение менеджера из Telegram топика дошло до WhatsApp.

**Evidence:**
- PR #157: https://github.com/k1ddy/Truffles-AI-Employee/pull/157
- CI PR (core/long/asr/lint/unit): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20948893145
- Merge commit: `16ed46dd01481d47475696a34e5d6327f24d6ee7` (merged_at 2026-01-13T07:54:07Z)
- DB (messages role=manager): msg_id `e0559543-2985-4e0e-850d-3c6b3a717a24`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, content `еткст`.
- Handover: `1015928a-4b82-42a0-abad-9c83597879e7`, manager_response `еткст`, resolved_by `Zh`.
- Note: оператор увидел WARNING “Learning success” с point_id `f0f1e359-b1c8-49a1-ae2a-6a6c566b6ce9` на этом ответе; решение — оставляем как есть.

### 2026-01-12 — A3/A4/A5 verification (evidence-only)

**Что сделали:**
- Подтвердили A3 (state machine инварианты), A4 (fact resolver/gate), A5 (memory contract/reset) через статик‑чек + live‑check, без изменения кода.

**Evidence:**
- A3 direct assignment только в `truffles-api/app/services/state_service.py:252` и `truffles-api/app/services/state_service.py:274`; `transition_state` используется в live/escalation/manager/background: `truffles-api/app/routers/webhook/_legacy.py:1646`, `truffles-api/app/services/escalation_service.py:216`, `truffles-api/app/services/manager_message_service.py:205`, `truffles-api/app/services/reminder_service.py:123`, `truffles-api/app/services/health_service.py:58`, `truffles-api/app/services/reminder_service.py:194`; инварианты: `truffles-api/app/services/state_service.py:202`, вызов внутри `transition_state` — `truffles-api/app/services/state_service.py:254`.
- A4 fact_meta в info: `truffles-api/app/routers/webhook/info.py:209`, `truffles-api/app/routers/webhook/info.py:220`, `truffles-api/app/routers/webhook/info.py:254`, `truffles-api/app/routers/webhook/info.py:263`; trace `fact_resolver`: `truffles-api/app/routers/webhook/_legacy.py:2411`; fact_guard off: `truffles-api/app/routers/webhook/_legacy.py:776`. Live‑check: message_id `db18df09-7fc0-42b4-922c-84af36033693`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, decision_meta `fact_source=service_matcher`, trace содержит `stage=fact_resolver`.
- A5 MemoryContract: `truffles-api/app/schemas/webhook.py:78-90`; нормализация: `truffles-api/app/routers/webhook/session_memory.py:24`, вызов: `truffles-api/app/routers/webhook/_legacy.py:2478`, trace contract_error: `truffles-api/app/routers/webhook/_legacy.py:2486-2493`. Live‑check reset: message_id `1e8894ff-59ed-46ed-b1ff-c8b5136fb9fe`, conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, decision_meta `session_memory_reset=explicit_reset`, trace `stage=session_memory` (reset/reset_ack). Опциональный expiry/re‑entry не запускали.

### 2026-01-12 — A5 RCA (expiry/re-entry trace eviction)

**Что сделали:**
- Провели RCA: очистили `decision_trace`, форсировали expiry, отправили сообщение, проверили trace‑стадии.

**Evidence:**
- conv_id: `b8c559d1-f8cd-4173-ae70-0a9683833e48`
- message_id: `live-a5-rca-1768200205` (row `9d871f4c-02c8-4f1e-83c1-9543354ac313`, created_at `2026-01-12T06:43:25.813984+00:00`)
- decision_trace очищен перед проверкой (`[]`)
- expiry forced: `session_memory.last_updated_at = 2026-01-10 06:42:06.166608+00`
- после сообщения: `trace_len = 12`, стадии: rewrite, llm_degradation, rag_retrieve (x2), class_router, intent, service_semantic_matcher, fact_resolver, contract (intent/fact/action/response); **нет** `stage=session_memory` и `stage=re_entry`
- вывод: **eviction** (trace заполнен другими стадиями, критичные выпали)
- backup/restore: `/tmp/a5_rca_b8c559d1_context.b64`

### 2026-01-12 — A5 expiry live‑check PASS (post‑fix)

**Что сделали:**
- Повторили expiry‑проверку после фикса trace‑merge; trace теперь содержит `session_memory` и `re_entry`.

**Evidence:**
- conv_id: `b8c559d1-f8cd-4173-ae70-0a9683833e48`
- message_id: `live-a5-expiry-postfix-1768203247` (row `ff33241f-dcc1-4e8c-bf7d-a2827a952db0`, created_at `2026-01-12T07:34:08.238979+00:00`)
- trace: `{"stage":"re_entry","decision":"required","reason":"expired"}` и `{"stage":"session_memory","decision":"reset","reason":"expired",...}`
- decision_meta: `session_memory_reset=expired`
- backup/restore: `/tmp/a5_expiry_postfix_b8c559d1-f8cd-4173-ae70-0a9683833e48.b64`

### 2026-01-12 — ChatFlow inbound instanceId verification (prod)

**Что сделали:**
- Подтвердили, что реальный ChatFlow inbound включает `instanceId`, ветка ставится, и outbox сохраняет тот же `instanceId`.

**Evidence:**
- message_id: `3EB01C2DA80C15E49107DE` (created_at `2026-01-12T06:54:53.495473+00:00`)
- re-verified canonical instanceId: message_id `3EB04512C9026FF2E5F8AD` (created_at `2026-01-12T07:20:28.918488+00:00`), outbox_id `f84ae22e-ff9e-4a14-af37-7e5cc8324768`
- conv_id: `b8c559d1-f8cd-4173-ae70-0a9683833e48`
- branch_id: `b7f75692-951e-421a-aae6-f5db97394799`
- instanceId: `eyJ1aWQiOiJhTFpMend0d1AzUnBCWHpHNlNzbG1aNWNTOTZib1F5YyIsImNsaWVudF9pZCI6ImRlbW9zYWxvbiJ9`
- DoD: `messages.metadata.instanceId` заполнен; `conversations.branch_id` не NULL; `branches.instance_id` совпадает; `outbox_messages.payload_json` содержит тот же `instanceId`.

### 2026-01-12 — RU/KZ datetime resolver + escalation live-check (simulated inbound)

**Что сделали:**
- Live-check на allowlist JID через simulated inbound `/webhook` (waiver от Жанбола).
- RU/KZ datetime resolver: “сенбі кешке” → запрос имени.
- Эскалация: “жалоба” → pending/handover, без “AI error”.

**Evidence:**
- CI PR #143: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20917324127
- RU/KZ resolver: conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, msg `live-dt-1768218583-10`, trace `stage=question_contract` `decision=matched` `answer_slot=datetime` `expected_reply_type=time`; bot reply “Как вас зовут?”
- Escalation: conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, msg `live-esc-1768218660-5`, trace `stage=policy_gate` `intent=complaint` `risk_level=high`, handover `d306c4b5-9c80-48f2-9edf-6c32f0a4ba06` `pending`; bot reply “Жаль, что так вышло. Передам администратору…”
- TODO: Real WA inbound live-check (ChatFlow) — pending.

### 2026-01-12 — Docs sync (ritual + RCA-first + resolver-first + gaps)

**Что сделали:**
- Зафиксировали session-start ritual, RCA-first и resolver-first в `docs/SESSION_START_PROMPT.txt`.
- Добавили RU/KZ resolver в P1 roadmap и обновили fix plan в `docs/TECH_STATUS.md`.
- Расширили `docs/IMPERIUM_GAPS.yaml` (GAP-014..019: LAW/policy, /message bypass, branch isolation, LLM facts, ops/Qdrant).

**Evidence:**
- PR #144: https://github.com/k1ddy/Truffles-AI-Employee/pull/144 (docs-only, CI не требуется).

### 2026-01-11 — A7: observability + budget gate + ASR tier

**Что сделали:**
- Влили PR #133 с бюджетным gate, trace/meta деградаций и ASR tier в CI.

**Evidence:**
- PR #133: https://github.com/k1ddy/Truffles-AI-Employee/pull/133
- CI main: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20895474177 (core/long/asr/lint/unit/secret-scan зелёные)
- CI PR: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20895399334 (core/long/asr/lint/unit/secret-scan зелёные)

### 2026-01-11 — A7 Live-budget gate (SQL fallback)

**Что сделали:**
- Временно включили `client.config.llm_budget.daily_max_calls=1` для demo_salon, отправили 2 LLM‑сообщения, зафиксировали budget_gate trace + llm_degradation_reason, восстановили config из backup.

**Evidence:**
- conv_id: `b8c559d1-f8cd-4173-ae70-0a9683833e48`
- trace: `conversations.context.decision_trace` содержит `stage=budget_gate` и `llm_degradation_reason=budget_exceeded` (rag_rewrite/response).
- meta: `messages.metadata.decision_meta` для `live-budget-1768137927-2` и `live-budget-1768138285-3` содержит `llm_degradation_reason=budget_exceeded` и `router_error=budget_exceeded`.
- /admin/version: `{"version":"main","git_commit":"9af211db046328a2f3914b2e97ce80c13573a1cb","build_time":"2026-01-11T13:25:43Z"}`
- backup: `/tmp/demo_salon_config_backup.json`

### 2026-01-03 — Канон: class‑router + info‑bundle инварианты

**Что сделали:**
- Зафиксировали intent lattice (class‑router), info‑bundle и class‑carryover в `SPECS/ARCHITECTURE.md`.
- Обновили `SPECS/CONSULTANT.md`: info‑bundle инвариант, class‑carryover, LLM как языковой слой; shield = реализовано.
- Добавили DoD‑инварианты в `STRATEGY/REQUIREMENTS.md` (устойчивость к перефразам + info‑bundle).
- Обновили `SPECS/MULTI_TENANT.md`: anchors как boost, info‑bundle зависит от client_pack, OOD только при out‑signals без in‑signals.
- Обновили `SPECS/ESCALATION.md`: info‑комбо не эскалируются без Hard‑LAW/policy.
- Дописали канон в `docs/SESSION_START_PROMPT.txt` (class‑routing).

**Разбор (шаблон):**
- Боль/симптом: перестановка слов ломает ответы; ветка прыгает между info/booking/OOD, “детские” запросы дают урезанный ответ.
- Почему важно: UX и доверие к “супер‑хосту” ломаются.
- Диагноз: канон не фиксировал class‑routing и info‑bundle как инварианты; anchors воспринимались как основной сигнал.
- Решение: зафиксировали intent lattice, info‑bundle и class‑carryover в SPECS/STRATEGY/SESSION.
- Проверка: docs‑sync (tests не требуются для docs).
- Осталось: реализация class‑router/info‑bundle в коде + CI core/long + live‑check 10–15 turns.

### 2025-12-29 — PR-1 Consult Mode (demo_salon)

**Что сделали:**
- Добавили consult_intent/consult_topic/consult_question в intent_decomp и запись decision_meta/trace для consult.
- Добавили `domain_pack.consult_playbooks` и `build_consult_reply()`; подключили consult-роутинг до booking/truth.
- Закончили LAW эскалацию через `policy_legal`, обновили `get_demo_salon_decision` для consult.
- Обновили `EVAL.yaml` и добавили тест consult-роутинга в `tests/test_message_endpoint.py`.

**Разбор (шаблон):**
- Боль/симптом: нужен безопасный консультативный ответ без фактов/цен/наличия и без booking-триггеров.
- Почему важно: риски обещаний/цен и лишние триггеры записи ломают доверие и SLA.
- Диагноз: в маршрутизации не было consult-режима и playbook-ответов, LAW не эскалировался.
- Решение: intent_decomp + consult_playbooks + consult gate до booking/truth + policy_legal; запись meta/trace.
- Проверка: `docker exec -i truffles-api pytest /app/tests/test_message_endpoint.py -q`; `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q`.
- Осталось: деплой и live-check 5 кейсов consult/price/booking/escalation.

### 2025-12-26 — Outbox: policy trigger_type violation fix

**Что сделали:**
- В demo_salon policy‑gate поменяли `trigger_type` с `policy` на `intent` (валидное значение).

**Разбор (шаблон):**
- Боль/симптом: outbox worker падал, voice‑сообщения зависали в PROCESSING; бот “молчал” на голосовые.
- Почему важно: потеря ответов и зависшие сообщения.
- Диагноз: `handovers_trigger_type_check` не допускает `policy`, вставка handover падала.
- Решение: использовать `trigger_type="intent"` с `trigger_value=decision.intent`.
- Проверка: деплой + голосовые проходят, outbox не падает.
- Осталось: перевыставить старые PROCESSING при необходимости.

### 2025-12-26 — Prod: audio transcription enabled

**Что сделали:**
- Включили ASR для коротких PTT: `AUDIO_TRANSCRIPTION_ENABLED=1`, `AUDIO_TRANSCRIPTION_MAX_MB=2`, `AUDIO_TRANSCRIPTION_MODEL=whisper-1`, `AUDIO_TRANSCRIPTION_LANGUAGE=ru`.
- Перезапустили API.

**Разбор (шаблон):**
- Боль/симптом: бот отвечал “файл получил…” на голосовые без понимания.
- Почему важно: теряем смысл сообщения и точность ответа.
- Диагноз: транскрибация была выключена (env не задан).
- Решение: включили ASR и рестарт.
- Проверка: отправить PTT → в `messages.metadata.media.transcript` появляется текст; бот отвечает по смыслу.
- Осталось: проверить поведение в `pending/manager_active`.

### 2025-12-26 — Media: без авто‑handover + голосовые транскрипты + safe auto‑learning

**Что сделали:**
- Входящее медиа в `bot_active` больше не создаёт handover автоматически; референсы/«как на фото» эскалируются, остальное — по смыслу текста/транскрипта.
- Добавили транскрибацию коротких PTT‑голосовых (env‑гейты) и проброс транскрипта в Telegram.
- Для pending добавили системный hint: бот собирает детали, не обещает результат.
- Автообучение фильтрует “мусор” (placeholder/короткие/ack).
- Обновили спеки и TECH по новым правилам и env.

**Разбор (шаблон):**
- Боль/симптом: любое медиа сразу открывало заявку и плодило эскалации; голосовые не понимались ботом; автообучение рисковало брать мусор.
- Почему важно: лишняя нагрузка на менеджера + бот не закрывает 80% вопросов, риск плохих ответов.
- Диагноз: правило “media → handover” и отсутствие ASR для PTT; слабые фильтры в learning.
- Решение: перевести медиа на текст‑first (caption/ASR), эскалировать только style‑reference; добавить ASR‑гейты и фильтры learning.
- Проверка: юнит‑тесты не гонял; требуется деплой + проверка медиа/голосовых на проде.
- Осталось: задать env для транскрипции и проверить сценарии (бот_active/pending/manager_active).

### 2025-12-26 — Prod: media env values set

**Что сделали:**
- Добавили `MEDIA_URL_TTL_SECONDS`, `MEDIA_CLEANUP_TTL_DAYS`, `CHATFLOW_MEDIA_TIMEOUT_SECONDS` в `/home/zhan/truffles-main/truffles-api/.env`.
- Перезапустили API через `/home/zhan/restart_api.sh` на `ghcr.io/k1ddy/truffles-ai-employee:main`.

**Разбор (шаблон):**
- Боль/симптом: preflight показывал MISSING для media TTL/cleanup/timeout при активном медиа.
- Почему важно: ссылки могут жить бесконечно, нет регулярной очистки, риск таймаутов при отправке медиа.
- Диагноз: переменные не заданы в `truffles-api/.env`.
- Решение: задать значения и перезапустить контейнер.
- Проверка: `python3 ops/diagnose.py` → значения есть в preflight.
- Осталось: при необходимости выполнить `/admin/media/cleanup` (dry_run) и проверить отправку медиа.

### 2025-12-26 — Prod: stale pending handover закрыт

**Что сделали:**
- Закрыли pending handover `27403967-0389-42ee-9d09-a5d4eaf08f26` по conversation `4b355349-15bc-41df-b26d-4c76a6e7be41` через `manager_resolve` (system), добавили `resolution_type=other` и `resolution_notes`.
- Pending стало 0.

**Разбор (шаблон):**
- Боль/симптом: один pending handover висел с 2025-12-21.
- Почему важно: мусор в очереди, риск ложных сигналов и пропущенных действий.
- Диагноз: менеджер не ответил, заявка не была закрыта.
- Решение: ручное закрытие handover и возврат conversation в `bot_active`.
- Проверка: `python3 ops/diagnose.py` → pending=0.
- Осталось: при необходимости проверить топик 551 в Telegram.

### 2025-12-25 — Topic binding: one topic per client (P0 safety)

**Что сделали:**
- Канон: `users.telegram_topic_id`; `conversations.telegram_topic_id` — копия для активного диалога.
- Убрали fallback “последний handover без топика” в менеджерских ответах: сообщения принимаются только из топика клиента.
- Эскалация/создание топика теперь используют user‑topic; при пропаже темы пересоздание и синк.
- Health‑heal восстанавливает `conversation.telegram_topic_id` из `users.telegram_topic_id` вместо сброса стейта.

**Статус:**
- Нужен деплой и ретест: менеджер пишет только в топике, без темы — “не доставлено”.

### 2025-12-25 — Prod verification: media/manager/TTL checks

**Что проверили:**
- Диагностика: `python3 ops/diagnose.py` (handovers/pending — пусто).
- Логи: `docker logs truffles-api --tail 200 | rg -n "Escalated|topic|telegram|handover|media"` → есть "Manager media received" (photo).
- SQL:
  - `SELECT ... FROM handovers ORDER BY created_at DESC LIMIT 10;`
  - `SELECT ... FROM conversations WHERE state IN ('pending','manager_active');`
  - `SELECT created_at, content, metadata->'media' FROM messages WHERE metadata ? 'media' ORDER BY created_at DESC LIMIT 5;`

**Статус:**
- В контейнере `MEDIA_SIGNING_SECRET` и `PUBLIC_BASE_URL` отсутствуют → signed URL не генерится, `messages.metadata.media.public_url` пустой.
- TTL cleanup (dry_run) отрабатывает: `total_files=1`, `total_bytes=59579`, `deleted_files=0`.

**Разбор (шаблон):**
- Боль/симптом: manager→client медиа не получает `public_url`, signed URL проверить нельзя.
- Почему важно: клиент не получает медиа, ломается менеджерский поток.
- Диагноз: env `MEDIA_SIGNING_SECRET`/`PUBLIC_BASE_URL` не заданы в API.
- Решение: добавить env и перезапустить API.
- Проверка: менеджер шлёт медиа → в `messages.metadata.media` есть `public_url` и `storage_path`, `curl -I <public_url>` отдаёт файл.
- Осталось: ручные WA/Telegram проверки (handover + media), повторить SQL/логи после env-фікса.

### 2025-12-25 — Manager→client media: ChatFlow требует caption

**Что нашли:**
- Логи: `ChatFlow media response: success=false, message="Parameter [token, instance_id, caption, jid, imageurl] are required!"`
- `public_url` генерится и `/media/...` отдаёт файл, но ChatFlow отказывает без caption.

**Решение:**
- В `send_whatsapp_media` всегда прокидывать `caption` для image/doc/video (если нет — отправлять пробел).

**Статус:**
- Код обновлён, нужен деплой и ретест отправки медиа.

### 2025-12-25 — Manager→client media: ChatFlow timeout + ложные "Не доставлено"

**Что нашли:**
- Логи: `Error sending WhatsApp media: The read operation timed out` спустя ~30s после `process_manager_media`.
- Итог: медиа доходит с задержкой, но в топике появляется `❌ Не доставлено`.

**Диагноз:**
- ChatFlow media endpoint отвечает дольше 30s; синхронный webhook ловит timeout и считает отправку проваленной.

**Решение:**
- Отправку медиа от менеджера вынесли в background task (Telegram webhook отвечает сразу).
- Для ChatFlow media увеличен timeout (env `CHATFLOW_MEDIA_TIMEOUT_SECONDS`, дефолт 90s).

**Проверка:**
- Отправить фото/док/аудио в топик → нет `❌ Не доставлено`, WA получает медиа; в логах `ChatFlow media response: success=true`.

### 2025-12-25 — Manager→client media + signed URL + TTL cleanup

**Что сделали:**
- Добавили signed‑URL выдачу медиа (`/media/{path}`) и валидацию подписи.
- Реализовали manager→client медиа: Telegram file_id → download → локальное хранение → ChatFlow send‑image/audio/doc/video.
- Добавили admin endpoint `/admin/media/cleanup` для TTL‑очистки и алерта при превышении объёма.

**Статус:**
- Нужен деплой; требуется `MEDIA_SIGNING_SECRET` + `PUBLIC_BASE_URL` в env.

**Разбор (шаблон):**
- Боль/симптом: менеджер отправляет медиа → клиент его не получает (нет ChatFlow media API в коде).
- Почему важно: менеджер не может передавать фото/документы клиенту → ломается процесс.
- Диагноз: отсутствует Telegram download + public URL, нет ChatFlow send‑media.
- Решение: download в `/home/zhan/truffles-media`, signed‑URL выдача, ChatFlow send‑media, TTL‑cleanup.
- Проверка: менеджер шлёт фото/аудио/док/видео → клиент получает файл; `/media/...` отдаёт файл по подписи; cleanup удаляет старые файлы.
- Осталось: деплой + настройка env; интеграционные проверки.

### 2025-12-25 — Human request escalation (rule-based fallback)

**Что сделали:**
- В `intent_service.py` добавили rule‑based детект запроса менеджера до LLM, чтобы эскалация не зависела от классификатора.
- В `message_service.py` расширили паттерны human_request (склонения/опечатки), чтобы корректно отбирать контекст для handover.
- Добавили unit‑тесты на детект human_request.

**Статус:**
- Нужен деплой; `pytest` недоступен (не установлен).

**Разбор (шаблон):**
- Боль/симптом: пользователь пишет “позвать менеджера”, бот отвечает “передал администратору”, но handover не создаётся, Telegram‑топик не появляется.
- Почему важно: пользователь получает ложный статус, менеджер не видит заявку.
- Диагноз: human_request определялся только LLM, из‑за промахов классификации/опечаток эскалация не запускалась.
- Решение: добавить детерминированный regex‑детект human_request перед LLM и расширить паттерны.
- Проверка: отправить “позвать менеджера” → появляется handover + topic, в ответе MSG_ESCALATED.
- Осталось: деплой и проверка на проде.

### 2025-12-25 — Media: rate-limit double count + fast-forward storage

**Что сделали:**
- В `webhook/_legacy.py` добавили `count_rate_limit` и выключили счётчик при `skip_persist=True` (outbox), чтобы лимиты не считались повторно.
- В fast-forward (enqueue_only) сохраняем медиа до отправки в Telegram, используем `stored_path` при отправке.
- В metadata сообщения пишем `storage_path/stored/storage_error/sha256`, чтобы storage не повторялся.

**Статус:**
- Нужен деплой и проверка на проде.

**Разбор (шаблон):**
- Боль/симптом: в Telegram приходят `[image]/[audio]/[document]`, в `messages.metadata.media.decision` — `rate_limited`.
- Почему важно: менеджер не видит медиа клиента → теряются заявки/контекст.
- Диагноз: rate‑limit считался повторно при outbox (skip_persist), fast‑forward в `manager_active` форвардил URL без локального хранения.
- Решение: отключить счётчик лимитов при `skip_persist`, сохранять медиа перед fast‑forward и отправлять файл с диска.
- Проверка: отправить 3–4 медиа подряд → decision.allowed=true, Telegram получает файл; `storage_path` заполнен.
- Осталось: ChatFlow media API для manager→client, TTL‑очистка хранилища.

### 2025-12-25 — Media: fix trigger_type constraint + rate limits

**Что сделали:**
- Обновили `handovers_trigger_type_check` (добавили `media`), чтобы эскалации по медиа не падали.
- Смягчили лимиты медиа: 5/10 мин, 20/сутки, 30MB/10 мин.
- PTT аудио с `audio/mpeg` теперь шлём как audio (не voice).

**Статус:**
- Требуется проверка на проде: аудио/документы должны доходить в Telegram как файлы.

**Разбор (шаблон):**
- Боль/симптом: audio/doc приходят как `[audio]/[document]`, outbox падал по constraint.
- Почему важно: медиа не доходит менеджеру, outbox ломается.
- Диагноз: trigger_type не допускает `media`, rate‑limit слишком жёсткий, PTT mime не совпадает с voice.
- Решение: расширили constraint, подняли лимиты, отправка PTT как audio при `audio/mpeg`.
- Проверка: отправить фото+аудио+док → в Telegram приходят файлы, в логах нет CheckViolation.
- Осталось: manager→client media, ASR/обработка.

### 2025-12-25 — Media guardrails + Telegram forwarding

**Что сделали:**
- Guardrails для медиа: allowlist типов, max‑size, rate‑limit (policy через `clients.config.media`).
- Отправка медиа в Telegram (sendPhoto/sendAudio/sendDocument/sendVoice) + caption.
- Локальное хранение медиа + метаданные в `messages.metadata.media`.
- Outbox: при медиа в батче — обработка по одному (без coalesce), чтобы не терять вложения.

**Статус:**
- Нужен деплой.

**Разбор (шаблон):**
- Боль/симптом: фото/аудио/документы не доходили менеджеру и могли убивать ресурсы.
- Почему важно: теряются лиды и растут риски по ресурсам/стоимости.
- Диагноз: только текстовый forward, нет лимитов и storage.
- Решение: guardrails + локальное хранение + Telegram media forward + media‑safe outbox.
- Проверка: отправить фото/аудио → файл в Telegram топике, бот отвечает шаблоном; лимиты режут спам.
- Осталось: деплой; TTL очистка хранилища; ChatFlow media API для manager→client; ASR/обработка файлов.

### 2025-12-25 — CI gitleaks warning fix

**Что сделали:**
- Убрали unsupported `args` из `gitleaks/gitleaks-action@v2` (warning “Unexpected input(s) 'args'”).

**Статус:**
- Готово, ждём прогон CI.

### 2025-12-29 — CI gitleaks license

**Что сделали:**
- В CI secret-scan добавили прокидывание `GITLEAKS_LICENSE` из GitHub Secrets.

**Статус:**
- Нужно добавить секрет `GITLEAKS_LICENSE` в GitHub и повторить прогон CI.

### 2025-12-25 — Fast-forward inbound to Telegram (pending/manager_active)

**Что сделали:**
- В enqueue_only: если `state=pending/manager_active` и есть `telegram_topic_id` — сообщение сразу форвардится в Telegram.
- В outbox: переносим `forwarded_to_telegram` и пропускаем повторный форвард.
- Добавили поле `forwarded_to_telegram` в `WebhookMetadata`.

**Статус:**
- Нужен деплой.

**Разбор (шаблон):**
- Боль/симптом: при active/pending сообщение клиента доходит до менеджера с задержкой outbox.
- Почему важно: менеджер отвечает медленнее → хуже конверсия записи.
- Диагноз: форвард в Telegram делается только при обработке outbox.
- Решение: fast-forward на входе + флаг, чтобы не было дублей.
- Проверка: написать клиентом в WA при `manager_active` и сравнить задержку.
- Осталось: деплой и проверка на проде.

### 2025-12-25 — Multi-intent booking (batch-aware)

**Что сделали:**
- Добавили batch-aware booking: детект записи по нескольким сообщениям (service+datetime) + предзаполнение слотов.
- Demo_salon: эскалация policy по каждому сообщению в батче; price sidecar при booking, если найдена конкретная услуга.
- Outbox: передаёт список сообщений в обработчик (batch_messages).
- Тесты: добавлены unit-тесты на batch booking helpers.

**Статус:**
- Нужен деплой; `pytest` недоступен в окружении.

**Разбор (шаблон):**
- Боль/симптом: multi-intent “цена+запись” теряется при склейке.
- Почему важно: теряются лиды на запись, растут эскалации.
- Диагноз: coalescing + demo_salon truth gate отвечают ценой до booking; booking детект только по ключевым словам.
- Решение: batch-aware сигналы + booking prefill; demo_salon policy → сначала, price sidecar → вместе с booking.
- Проверка: `pytest truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_demo_salon_eval.py` (не запускалось: `pytest` отсутствует).
- Осталось: деплой и проверка на проде.

### 2025-12-26 — Booking: service hint между сообщениями

**Что сделали:**
- При price-query сохраняем service hint в `conversations.context` (demo_salon).
- Booking flow подхватывает свежий hint (окно 120 мин) если в сообщении нет услуги; после использования очищаем.
- Добавили unit-тесты на срок жизни service hint.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: "сколько стоит маникюр" → "запишите на завтра" → бот снова просит услугу.
- Почему важно: теряется контекст и конверсия записи.
- Диагноз: booking flow видит только текущий батч и не помнит услугу из price-query.
- Решение: сохранять service hint из price-query и применять при старте booking.
- Проверка: ruff ok; требуется ручной тест на проде.
- Осталось: деплой и проверка в боевом диалоге.

### 2025-12-26 — Reminders: auto_close_timeout

**Что сделали:**
- Обнаружено: `auto_close_timeout=3` мин → заявки закрывались до напоминаний (30/60 мин).
- Обновили `client_settings.auto_close_timeout` до 120 мин для demo_salon и truffles.

**Статус:**
- Настройки обновлены в БД; нужен ручной тест напоминаний.

**Разбор (шаблон):**
- Боль/симптом: напоминаний не было.
- Почему важно: менеджер не получает пинга, клиент ждёт.
- Диагноз: auto-close закрывал заявки раньше таймаутов напоминаний.
- Решение: поднять auto_close_timeout до 120 мин (после reminder_2).
- Проверка: SQL выборка + ожидание reminder_1/2 на реальной заявке.
- Осталось: открыть заявку и проверить Telegram-напоминания.

### 2025-12-26 — Booking flow: opt-out/фрустрация не превращаются в заявку

**Что сделали:**
- Opt‑out теперь bypass’ит booking/truth-gate, чтобы “не пиши мне” не становилось именем.
- Фрустрация **не** блокирует booking; слоты не заполняются из opt‑out/мата.
- При opt‑out во время booking — сбрасываем booking context + service hint.
- Добавили тесты: составной opt‑out и запрет имени из ругани.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: “не хочу чтобы ты писал…/иди нахуй” в booking → “Передал менеджеру”.
- Почему важно: нарушает правило “нет значит нет”, портит UX.
- Диагноз: booking flow мог принять opt‑out/мат за слот “имя” и эскалировать.
- Решение: bypass booking/truth-gate для opt‑out + защита слотов от мата.
- Проверка: ruff ok; нужен ручной тест после деплоя.
- Осталось: деплой и проверка сценария.

### 2025-12-26 — Решение: hybrid логика mute/booking

**Решение (реализовано):**
- **Hybrid:** booking сильнее mute, но при конфликте opt‑out + booking в одном батче → просим подтверждение “Хотите снова общаться? да/нет”.
- Если booking пришёл **после** mute (без opt‑out в сообщении) → снимаем mute и продолжаем запись.
- Фрустрация + явный booking → **не эскалировать**, вести запись (если нет `human_request`).

**Почему нужно:**
- Сейчас mute ранним return делает поведение “молчание навсегда”, Telegram пустой и клиент теряется.

**Что сделали:**
- Ранний mute return пропускает booking: unmute при booking‑сигнале.
- Добавили `reengage_confirmation` в `conversation.context` с TTL.
- При opt‑out+booking: подтверждение “да/нет”, без заявки.
- Обновили тесты на подтверждение и на защиту слотов.

**Статус:** реализовано, нужен деплой и ручной тест.

### 2025-12-26 — Decision trace для re-engage/mute

**Что сделали:**
- В `conversation.context` пишется `decision_trace` (список до 12 событий) по ключевым веткам: re‑engage, mute, booking, demo truth‑gate, intent/escalation, out‑of‑domain, AI‑ответ.
- Добавлены manual тесты в `truffles-api/tests/test_cases.json` для hybrid‑сценариев.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: сложно понять “почему бот молчит/почему размьют”.
- Почему важно: нужен воспроизводимый дебаг и контроль регресса.
- Диагноз: решения не фиксировались ни в БД, ни в логах.
- Решение: сохранять decision trace в `conversation.context` + сценарные тесты.
- Проверка: проверить `conversations.context->'decision_trace'` на новых сообщениях.

### 2025-12-26 — План полной переработки (черновик)

**Цель:** предсказуемая логика + масштабируемость + дебаг.

1) **Контракт поведения**
   - Формальная матрица `state × intent × signals → action`.
   - Чёткие приоритеты: opt‑out vs booking vs frustration vs human_request.

2) **Policy Engine**
   - Убрать client_slug if’ы из `webhook/_legacy.py`.
   - Правила/порог/таймауты в конфиге (DB/YAML), код — исполнитель.

3) **Slot Manager**
   - Явная модель слотов записи + валидаторы.
   - Запрещённые токены для слотов (opt‑out/мат).

4) **Decision Trace**
   - Лог + таблица: intent, policy_rule, chosen_action, confidence.
   - Использовать для AI‑дебага и регресса.

5) **Golden Scenarios**
   - Набор “что‑если” диалогов, CI‑проверка.
   - Тесты на батч/коалесинг/повторные сообщения.

6) **Observability**
   - Метрики: escalation rate, mute‑break, no‑response.
   - Алерты на противоречия (например, booking→mute).

### 2025-12-26 — Booking flow в pending (price+booking)

**Что сделали:**
- Разрешили booking flow при `state=pending`, чтобы batch "цена+запись" не перехватывался truth-gate.
- При pending не создаём новый handover: отвечаем пользователю и закрываем booking context.
- Добавили routing matrix/gates для booking/truth-gate и unit-тесты на правила.

**Статус:**
- Нужен деплой и повторный ручной тест; `pytest` отсутствует в окружении.

**Разбор (шаблон):**
- Боль/симптом: "сколько стоит маникюр" + "запишите на завтра" в pending → ответ "подскажите услугу".
- Почему важно: теряется контекст услуги, ухудшается конверсия записи.
- Диагноз: booking flow запускался только в bot_active; в pending срабатывал demo_salon truth gate.
- Решение: включить booking flow в pending, без создания нового handover.
- Проверка: повторить тест в pending — должен спросить имя + дать цену (sidecar); тесты не запускались (нет pytest).
- Осталось: деплой.

### 2025-12-26 — Routing matrix расширена (эскалация/малый чат)

**Что сделали:**
- Привязали smalltalk, out‑of‑domain и intent‑эскалацию к routing policy.
- Добавили guard: при pending human_request/frustration → ответ “уже передал”, без нового handover.
- Добавили unit‑тест на `_should_escalate_to_pending` и пересечения policy.

**Статус:**
- Ruff OK; pytest по‑прежнему отсутствует в окружении.

**Разбор (шаблон):**
- Боль/симптом: ветки реагируют по-разному в зависимости от state, возможны коллизии.
- Почему важно: логические баги на пересечениях “state × intent”.
- Диагноз: state‑гейты размазаны по веткам, нет единого решения.
- Решение: routing policy + единый gate для эскалаций/ответов.
- Проверка: `ruff check app tests` (ok), unit‑тесты добавлены.
- Осталось: pytest‑прогон в окружении с зависимостями.

### 2025-12-26 — Opt-out / агрессия в intent‑детекторе

**Что сделали:**
- Расширили opt‑out (“не пиши”, “отпишись”, “заткнись/заткнитесь”) → `Intent.REJECTION`.
- Эвристики агрессии/мата (“заебал” и т.п.) → `Intent.FRUSTRATION`.
- В pending‑эскалации для фрустрации отвечаем коротко без просьбы уточнить.

**Статус:**
- Ruff OK; pytest не запускался (нет pytest).

**Разбор (шаблон):**
- Боль/симптом: “не хочу чтобы ты писал мне / заткнись” → ответ “уже передал… уточните”.
- Почему важно: нарушается правило “нет значит нет”.
- Диагноз: LLM не ловит opt‑out/фрустрацию, падаем в low‑confidence.
- Решение: локальные эвристики + корректный ответ в pending.
- Проверка: ruff ok; нужен ручной тест после деплоя.

### 2025-12-25 — Media fallback (non-text)

**Что сделали:**
- Перестали отбрасывать non-text payload: сохраняется в outbox, ответ “опишите текстом”.
- В messages добавлен `message_type/has_media` в metadata для входящих.

**Статус:**
- Нужен деплой, чтобы fallback начал работать; ASR/OCR/vision не реализованы.

### 2025-12-25 — Truffles instanceId prep

**Что сделали:**
- Создали branch `main` для `truffles` с `instance_id`.
- Сгенерировали `webhook_secret` для `truffles` (значение выдано Жанболу).

**Статус:**
- Обновили ChatFlow webhook URL и проверили: instanceId приходит, `conversation.branch_id` ставится.

### 2025-12-25 — InstanceId in inbound payload

**Что сделали:**
- Добавили `instanceId` в webhook (query‑param) для demo_salon.
- Проверили: instanceId пришёл в payload, `conversation.branch_id` проставился (main).

**Статус:**
- Работает для demo_salon; нужно повторить для остальных клиентов.

### 2025-12-25 — Outbox latency check

**Что сделали:**
- Измерили задержку outbox по БД (created_at → updated_at для SENT).
- Разложили задержку на wait (coalesce+interval) и processing по логам.

**Статус:**
- Avg 17s, p90 25s, max 26s за последний час; цель <10s не достигнута.
- Breakdown: wait ~8.7s, processing ~6.6s (выборка 4 батча).

### 2025-12-25 — Amnesia-mode checklist

**Что сделали:**
- Добавили короткий режим "амнезии" в `docs/SESSION_START_PROMPT.txt` для быстрого входа и сохранения знаний.

### 2025-12-25 — Human_request uses last meaningful message

**Что сделали:**
- Для handover при `human_request` берём последнее содержательное user-сообщение вместо "позови менеджера".
- Добавлен helper и тесты для выбора meaningful сообщения.
- В БД: выставлен `client_settings.owner_telegram_id` для `demo_salon` = `1969855532`.

**Статус:**
- Требуется деплой и проверка: handover.user_message теперь содержит реальный вопрос клиента.

### 2025-12-25 — Outbox worker + owner learning fallback

**Что сделали:**
- Добавили outbox worker в API (тик 2s) и вынесли обработку outbox в общий хелпер.
- Telegram: sender_chat fallback для идентификации менеджера.
- Auto-learning: не затирает assigned_to при unknown; fallback на assigned_to для owner-check; поддержка отрицательных ID.

**Статус:**
- Проверено по логам: "Owner response detected" + "Added to knowledge" (2025-12-25); latency < 10с ещё не проверена.

### 2025-12-25 — Demo salon: law-safe KB + policy keywords

**Что сделали:**
- Почистили demo_salon FAQ/возражения/правила: оплаты/перенос/medical/жалобы → эскалация, убран телефон администратора.
- Обновили `SALON_TRUTH.yaml`: убрали блок оплат, оставили только medical_note.
- Расширили policy-ключевые слова в `demo_salon_knowledge.py` (оплата/перенос/medical/жалобы/скидки).
- Обновили фразы и `EVAL.yaml` под новые кейсы.
- Добавили ответ на “ты тут?/алло” через `is_bot_status_question` в `ai_service.py`.
- Обновили sync-скрипты: BGE/Qdrant URL берутся из env или docker IP, Qdrant key из env (с trim).

**Статус:**
- KB demo_salon синхронизирована в Qdrant через `ops/manual_sync_demo.py` (34 points).

### 2025-12-24 — Admin settings for branch routing

**Что сделали:**
- Расширили `/admin/settings` под branch routing + auto-approve роли.
- Починили маппинг reminder_* → `reminder_timeout_*` в настройках.
- Добавили миграцию `ops/migrations/014_add_branch_routing_settings.sql`.
- Встроили branch routing (by_instance/ask_user/hybrid) и remember_branch в `webhook/_legacy.py`.
- Дефолт auto-approve обновлён на `owner,admin` (спека/модель/миграция).
- **Prod fix:** применили миграцию 013/014 (не было `conversations.branch_id` → webhook падал).

### 2025-12-24 — Спеки + скелет архитектуры обучения

**Что сделали:**
- Обновили `SPECS/ESCALATION.md`, `SPECS/ARCHITECTURE.md`, `SPECS/ACTIVE_LEARNING.md` (роли/идентичности, очередь обучения, Telegram per branch).
- Зафиксировали решение в `docs/IMPERIUM_DECISIONS.yaml` (DEC-008).
- Добавили модели `Agent`, `AgentIdentity`, `LearnedResponse` и миграцию `ops/migrations/013_add_agents_and_learning_queue.sql` (branch_id для агентов и обучения).
- Обновили `STRUCTURE.md` и `STATE.md`.

**Статус:**
- Код пока не подключён к потокам Telegram/обучения — это следующий шаг.

### 2025-12-24 — Sync: latency + multi-intent + git hygiene

**Что выяснили:**
- Задержка ответов/пересылки в Telegram: ACK-first + cron `/admin/outbox/process` раз в минуту + `OUTBOX_COALESCE_SECONDS=8` → 8–60 сек.
- Demo_salon multi-intent ломается: coalescing склеивает сообщения, truth-first возвращает цену до booking → запись теряется.

**Что сделали:**
- Создали `CHATGPT_QUESTIONS_ANSWERS.md` (ответы на анкету).
- Обновили `STATE.md` и `STRUCTURE.md` (новые проблемы и приоритеты).
- EVAL: `test_demo_salon_eval.py` — 1 passed (локальный venv).
- Git hygiene: секреты вынесены в env vars в docs/ops; добавлен gitleaks в CI и pre-commit; `/.venv/` добавлен в `.gitignore`.

### 2025-12-24 — Ротация OpenAI ключа (prod)

**Проблема:** 401 `invalid_api_key` после CI (ключ утёк).

**Что сделали:**
- Обновили `OPENAI_API_KEY` в `/home/zhan/truffles-main/truffles-api/.env` (из `/home/zhan/secrets/openaikey.txt`)
- Перезапустили API через `/home/zhan/restart_api.sh`
- Проверка: `docker logs truffles-api --tail 50` — ошибок 401 нет

### 2025-12-23 — Hotfix: outbox delivery + ChatFlow idempotency

**Проблема:** бот молчал при обработке outbox.

**Диагностика:**
- В логах `send_bot_response() got an unexpected keyword argument 'idempotency_key'`
- 401 от OpenAI (ключ в контейнере невалиден)

**Что сделали:**
- `chatflow_service.send_bot_response()` принимает `idempotency_key`/`raise_on_fail`
- `send_whatsapp_message()` прокидывает `msg_id` (idempotency)

**Статус:**
- Код запушен в `main`, CI должен собрать/задеплоить.
- OpenAI ключ всё ещё возвращает 401 — нужен валидный ключ.

### 2025-12-23 — Demo salon truth-first + outbox coalescing (repo)

**Что сделали:**
- Реализован truth-first/policy-gate для demo_salon (до RAG/LLM) + EVAL pytest
- Добавлена склейка сообщений в outbox (coalescing по conversation_id, 6–10 сек тишины)
- Введён канон `knowledge/demo_salon/` для синка (fallback на `ops/demo_salon_docs`)
- Документы обновлены: `docs/SESSION_START_PROMPT.txt`, `TECH.md`, `STRUCTURE.md`

**Важно:** код в репо обновлён; чтобы изменения заработали на проде, нужен `docker build` + `bash ~/restart_api.sh` (restart без build не подтягивает код).

### 2025-12-23 — Outbound retries/idempotency + EVAL fixes (prod)

**Что сделали:**
- Добавлены retry/backoff для ChatFlow + msg_id idempotency в webhook/outbox
- Outbox: повторные попытки с backoff до `OUTBOX_MAX_ATTEMPTS`
- Исправлены EVAL кейсы demo_salon (guest_policy, бренды, рескейджул, прайс токены)
- Документы обновлены: `TECH.md`, `docs/IMPERIUM_GAPS.yaml`, `SUMMARY.md`

**Тесты:**
- `pytest -q` (145 passed; Pydantic warnings)

**Деплой:**
- `docker build -t truffles-api_truffles-api .` + `bash /home/zhan/restart_api.sh`

### 2025-12-22 — PR-004: Outbox + ACK-first (prod)

**Что сделали:**
- Добавили таблицу `outbox_messages` + сервис outbox
- `/webhook` теперь ACK-first: сохраняет входящее, кладёт в outbox, возвращает 200 без LLM
- Добавили `POST /admin/outbox/process` (X-Admin-Token) для обработки очереди
- Задеплоено на прод, проверка: enqueue → process → SENT

### 2025-12-22 — PR-002: Alerts endpoint restored on prod

**Что сделали:**
- Добавили router `/alerts/test` + защита `ALERTS_ADMIN_TOKEN`
- Прописали `ALERTS_ADMIN_TOKEN` в `truffles-api/.env`, пересобрали и перезапустили API
- Проверка: `/alerts/test` → 401 без токена, 200 с токеном

**Статус:** PR-002 DONE on prod

### 2025-12-21 — Sync: перенос реализаций из truffles_origin

**Что сделали:**
- Вернули domain router + guardrails (бот статус/оффтоп) в webhook/message
- Добавили low_confidence retries (до 2) + подтверждение handover (yes/no)
- Включили DB dedup через `message_dedup`
- В learning_service добавлены alert_warning на skip/success
- Обновили тест `tests/test_intent.py` под `Intent.OUT_OF_DOMAIN`

### 2025-12-21 — Runbook: health/webhook/outbound

**Диагностика:**
- `curl http://localhost:8000/health` из текущей оболочки → connection refused; внутри контейнера `/health` и `/db-check` дают 200
- `POST /webhook` (demo_salon + remoteJid) → 200; в логах есть `ChatFlow response` и `Delivered`
- В контейнере `OPENAI_API_KEY` отсутствовал → 401 от OpenAI
- В контейнере `QDRANT_API_KEY` отсутствовал → ошибки knowledge search
- Alert service использует `ALERT_BOT_TOKEN`/`ALERT_CHAT_ID` (эндпоинта `/alerts/test` в контейнере нет)
- `truffleskz_bot` был с webhook на `rocket-api...` → менеджерские ответы/кнопки не доходили
- `alert_service` ломался на сообщениях с `_` из-за Markdown parse errors
- Репозиторий не содержал `app/main.py`, `app/services/knowledge_service.py`, `app/services/learning_service.py` → сборка API падала

**Что сделали:**
- Обновили `truffles-api/.env`: `OPENAI_API_KEY`, `QDRANT_API_KEY`, `ALERT_BOT_TOKEN`, `ALERT_CHAT_ID=1969855532`
- Обновили `client_settings.telegram_bot_token` для `truffles` и `demo_salon`
- Поставили webhook для `truffleskz_bot` и `salon_mira_bot` → `https://api.truffles.kz/telegram-webhook`
- Восстановили `app/` из последнего рабочего образа (`9abdfaf8c85e`) и пересобрали `truffles-api_truffles-api`
- Переписали `app/services/alert_service.py` на HTML-экранирование (устойчиво к `_`)
- Перезапустили API через `/home/zhan/restart_api.sh`
- Проверка: `/health` и `send_alert` → OK

### 2025-12-21 — Диагностика: inbound молчит

**Диагностика:**
- В БД по `77015705555@s.whatsapp.net` нет новых user сообщений после 2025-12-20 12:16 (12-21 были тестовые с `sender=test`)
- Значит ChatFlow не стучится в webhook / не принимает WhatsApp входящие

**Следующий шаг:**
- Проверить в ChatFlow webhook URL `https://api.truffles.kz/webhook/{client_slug}` и статус инстанса

### 2025-12-21 — Direct webhook

**Что сделали:**
- Добавлен endpoint `POST /webhook/{client_slug}` для прямого ChatFlow (без промежуточной обёртки)
- Добавлен fallback-парсер для разных форматов webhook payload + логирование недостающих полей
- Добавлен CORS middleware + `GET /webhook/{client_slug}` для UI-проверок
- Для UI-теста с пустым body добавлен мягкий ответ `success=true` ("Empty payload")
- Убрали 400 от OpenAI на intent (temperature=1.0 для gpt-5-mini)
- Обработан `ClientDisconnect` в webhook (не валит логи)
- Direct webhook теперь отвечает сразу (async processing), чтобы ChatFlow не слал “Ошибка вызова вебхука”
- Domain router: добавлен keyword override для цен/записи/адреса, чтобы не ловить false out-of-domain

**Действие:**
- В ChatFlow указать webhook `https://api.truffles.kz/webhook/{client_slug}`

### 2025-12-21 — Out-of-domain: строгий фильтр + RAG override

**Что сделали:**
- Добавили "strong out-of-domain" с более строгими порогами + min_len (консервативный OOD)
- Добавили `get_rag_confidence()` и проверку RAG перед OOD‑ответом
- В `webhook/_legacy.py` и `message.py` OOD‑ответ только если strong OOD / intent=out_of_domain и **нет** уверенного RAG
- Добавили логи "Domain out-of-domain gate" при `DOMAIN_ROUTER_LOG_SCORES=1`

### 2025-12-21 — Webhook auth + тесты

**Что сделали:**
- Вернули проверку `webhook_secret` для `/webhook` (401 до валидации payload)
- Добавили `webhook_secret` в `ClientSettings` модель + `alert_warning` при отсутствии секрета
- Прогнали тесты в отдельном образе: `123 passed`

### 2025-12-21 — Direct webhook auth + async fix

**Что сделали:**
- `/webhook/{client_slug}` теперь проверяет `webhook_secret` и отдаёт 401 при отсутствии/невалидном секрете
- Async обработчик теперь вызывает общий обработчик корректно (без сломанной подписи)
- Тест обновлён: direct webhook без секрета → 401
- В БД добавлен `client_settings.webhook_secret` и задан секрет для `demo_salon`
- API пересобран и перезапущен
- ChatFlow для `demo_salon` переключён на `https://api.truffles.kz/webhook/demo_salon?webhook_secret=...`

### 2025-12-20 — Health check: убрали ложные алерты

**Диагностика:**
- `ops/health_check.py` использовал статические IP контейнеров → после рестарта IP меняются, «Connection refused».
- `https://api.truffles.kz/healthz` возвращает 404 → алерты даже при живом API.

**Что сделали:**
- `ops/health_check.py` теперь получает IP контейнера через `docker inspect`.
- Health-check допускает 200/30x/401/403.
- Qdrant API key берётся из env (fallback на старый).

### 2025-12-20 — Traefik не видел docker → API недоступен

**Диагностика:**
- Traefik отдавал 404 по `api.truffles.kz`.
- В логах: `client version 1.24 is too old` → docker provider не поднимался.

**Что сделали:**
- Обновили Traefik до `v2.11` в `/home/zhan/infrastructure/docker-compose.yml`.
- Перезапустили контейнер, docker provider поднялся, маршруты появились.

### 2025-12-20 — Консолидация: один корень `/home/zhan/truffles-main`

**Диагностика:**
- Было 3 корня: `/home/zhan/truffles-main`, `/home/zhan/Truffles-AI-Employee`, `/home/zhan/truffles`.
- Команды/доки ссылались на разные пути → путаница.

**Что сделали:**
- Скопировали актуальные документы и директории в `/home/zhan/truffles-main`.
- Перенесли API‑код в `/home/zhan/truffles-main/truffles-api`.
- Обновили пути в `restart_api.sh` и документах.
- Архивировали старый `/home/zhan/Truffles-AI-Employee` в `/home/zhan/_trash`.

### 2025-12-20 - Guardrails: оффтоп и "бот молчит" без заявок

**Диагностика:**
- Оффтоп ("трусы") и вопрос "почему не отвечает?" уходили в low_confidence/frustration → создавалась заявка.

**Что сделали:**
- Добавили intent `out_of_domain` в классификатор.
- Ответ на `out_of_domain` без эскалации (возврат к теме салона).
- Guardrail на вопросы "бот не отвечает" → шаблонный ответ без заявки.
- Подняли `DEBOUNCE_INACTIVITY_SECONDS` до 3.0 (лучше склейка коротких сообщений).
- Обновили FAQ demo_salon ("Чем вы занимаетесь?") и пересинхронизировали KB.
- Intent классификатор перевели на `temperature=0.0` (меньше случайных эскалаций).
- Для low_confidence добавили до 2 уточнений перед эскалацией.

### 2025-12-20 — Domain router + подтверждение эскалации

**Диагностика:**
- Off-topic и низкая уверенность всё ещё могли создавать заявки менеджерам.

**Что сделали:**
- Добавили embedding-based domain router (якоря in/out) и ранний оффтоп-ответ без эскалации.
- Добавили подтверждение эскалации после low_confidence (да/нет) с окном 15 минут.
- Исправили битые domain anchors (кодировка).
- Протянули логику в `/webhook` и legacy `/message`.
- Задеплоили `webhook/_legacy.py`, `message.py`, `intent_service.py` и перезапустили API.
- Добавили domain router config per-client (anchors + thresholds) в `clients.config`.
- Включили логирование domain scores через `DOMAIN_ROUTER_LOG_SCORES=1`.
- Перезалили `intent_service.py`, `webhook/_legacy.py`, `message.py` и перезапустили API.

### 2025-12-19 - AL наблюдаемость + дедуп + KB sync

**Диагностика:**
- Нет видимости успехов/пропусков AL; дедуп messageId опирался на Redis/БД сообщений; KB demo могла быть несинхронна.

**Что сделали:**
- AL: alert_warning на skip (нет текста/слишком коротко/нет client_slug) и на success (point_id, длины).
- Дедуп: таблица message_dedup + INSERT ON CONFLICT, логируем дубли.
- KB: пересобрали demo_salon (faq/objections/rules/services) — 34 chunks в Qdrant.



### 2025-12-18 — Active Learning: owner detection

**Диагностика:**
- Owner response не детектился → автообучение не запускалось.

**Что сделали:**
- Разрешили список `owner_telegram_id` через запятую/пробел (username или numeric id).
- Добавили диагностические логи при mismatch owner vs manager.
- Обновили тесты `is_owner_response`.



### 2025-12-18 — Стабильность: авто‑закрытие и алерты “нет ответа”

**Диагностика:**
- Зависшие handover без закрытия.
- Нет алерта, когда пользователь написал, а бот не ответил.

**Что сделали:**
- Авто‑закрытие pending/active по `client_settings.auto_close_timeout` в `/reminders/process`.
- Алерт “вход есть — ответа нет” при задержке > `NO_RESPONSE_ALERT_MINUTES`.

### 2025-12-18 — Диалоговый контур: слоты записи + контекст

**Диагностика:**
- Короткие ответы и “странные” клиенты ломают контекст, особенно в сценариях записи.

**Что сделали:**
- Добавили `conversations.context` (JSONB) для хранения краткого контекста/слотов.
- Слот‑филлинг для записи: услуга → дата/время → имя, с передачей админу.
- Очистка контекста при reset/resolve/новой сессии.

### 2025-12-18 — Приветствия и whitelist: убрали ложные “уточните”

**Диагностика:**
- Сообщения типа “добрый день + …” считались whitelisted → LLM отвечал “вслепую”.
- “ДД” попадал в low-signal и выдавал уточнение вместо приветствия.

**Что сделали:**
- Добавили распознавание приветствий/благодарности, включая “дд”.
- `is_whitelisted_message` теперь только точное совпадение, без `startswith`.
- Приветствия/спасибо больше не считаются low-signal; отдельный shortcut в webhook.

### 2025-12-18 — Контекст для “да/нет” + FAQ “туалет”

**Диагностика:**
- Короткие ответы “да/нет” после вопроса бота уходили в low-signal и теряли контекст.
- В FAQ не было ответа про туалет.

**Что сделали:**
- Разрешили short-confirmation после yes/no вопроса использовать историю (contextual RAG).
- Добавили FAQ “есть ли туалет” в demo_salon.

### 2025-12-18 — Дебаунс: убрать дублирование контента в prompt

**Диагностика:**
- При буфере сообщений объединенный текст добавлялся поверх уже сохраненной истории → дубли в LLM и лишние токены.

**Что сделали:**
- Добавили флаг `append_user_message` и выключаем его при буфере, чтобы не повторять контент.
- Прокинули флаг через `generate_bot_response` → `generate_ai_response`.

### 2025-12-18 — Автообучение owner + дедуп по messageId

**Диагностика:**
- Owner auto-learning мог не срабатывать при `owner_telegram_id` в формате username или при сообщениях без `from_user` (анонимный админ).

**Что сделали:**
- `is_owner_response` теперь матчится по id или username (case-insensitive) и принимает `manager_username`; добавлен warning, если `from_user` отсутствует.
- Дедуп по `metadata.messageId`: Redis SETNX + fallback на БД (`messages.metadata.message_id`), сохраняем `message_id` в metadata входящих сообщений.
- `get_system_prompt` ищет `system`, а при отсутствии — `system_prompt` (обратная совместимость).
- Пересинхронизировали KB для `demo_salon` из `~/truffles/ops/demo_salon_docs` (22 chunks).
- Добавлен буфер сообщений поверх debounce (склеивание нескольких сообщений в одно перед обработкой).
- Обновлены шаблоны промптов: явное правило для вопросов вне темы бизнеса.
- Промпт `demo_salon` обновлён: оффтоп (маркетинг/продвижение) → вернуть к теме салона.
- Прод: `DEBOUNCE_INACTIVITY_SECONDS=2.0`.
- KB `demo_salon` расширена под полный FAQ/запись/гигиена/услуги/конфликты (34 chunks).
- Тест: `python -m pytest truffles-api/tests/test_learning_service.py -q` (16 passed).

### 2025-12-17 — Фикс “бот молчит” + защита заявок

**Диагностика:**
- “Бот молчит” часто означает не баг, а состояние `manager_active` — по протоколу бот должен молчать и только форвардить в Telegram-топик.
- На проде были зависшие заявки (`handovers.pending/active`) и один опасный случай mismatch `handover.channel_ref` (риск ответить не тому клиенту).

**Что сделали:**
- Emergency reset: `ops/reset.sql` теперь (1) чинит `channel_ref` у открытых заявок, (2) закрывает все open handovers, (3) возвращает диалоги в `bot_active`.
- Защита: self-heal чинит mismatch `channel_ref`, а ответы менеджера отправляются по `user.remote_jid` (source of truth).
- Reminders: напоминания теперь идут по всем open handovers (`pending` + `active`), чтобы заявки не висели бесконечно.
- Debounce: в FastAPI `POST /webhook` добавлен Redis-debounce — при серии быстрых сообщений бот отвечает один раз (последнее сообщение после паузы). Параметры: `DEBOUNCE_ENABLED` (default=on), `DEBOUNCE_INACTIVITY_SECONDS` (default=1.5), `REDIS_URL` (default=`redis://truffles_redis_1:6379/0`). Быстрый откат: поставить `DEBOUNCE_ENABLED=0` в `.env` и `bash ~/restart_api.sh`.

### 2025-12-12 (вечер) — Неделя 4: ПРОВАЛ

---

## ⚠️ КРИТИЧНО ДЛЯ СЛЕДУЮЩЕЙ СЕССИИ

**Состояние бота: ЧАСТИЧНО РАБОТАЕТ, НО ПЛОХО**

Важно:
- Если клиент пишет в WA и “бот молчит” — первым делом проверить `conversation.state`: в `manager_active` это ожидаемое поведение.
- Если заявки зависли и нужно срочно “оживить” бота — использовать `ops/reset.sql`.
- **Outbox требует планировщика:** cron `*/1` → `POST /admin/outbox/process` (см. `/etc/cron.d/truffles-outbox`).
- **Новая архитектура эскалации/обучения принята:** роли/идентичности + очередь обучения + Telegram per branch; см. `SPECS/ESCALATION.md`, `SPECS/ARCHITECTURE.md`, `SPECS/ACTIVE_LEARNING.md`, миграция `ops/migrations/013_add_agents_and_learning_queue.sql`.

Протокол проверки (10 минут, без догадок):
1. Проверить прод-состояние: `curl -s http://localhost:8000/admin/health` (через SSH на сервере).
2. Если `pending/active > 0` и это тесты — закрыть: `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot < ~/truffles-main/ops/reset.sql`.
3. Прогнать WA тест-диалог с номера `+77015705555`: приветствие → попросить менеджера → менеджер ответил → [Решено].
4. Смотреть `docker logs truffles-api --tail 200` и убедиться что видно `remote_jid`, `state` и что не происходит loop `pending → pending`.
5. Если есть “молчание”, но нет открытых заявок — выполнить `POST /admin/heal` и проверить инварианты (state/topic/handover).

Runbook (если “всё странно” или сессия оборвалась):
1. Подключиться на прод: `ssh -p 222 zhan@5.188.241.234`.
2. Быстро понять “это заявка или баг”: `curl -s http://localhost:8000/admin/health`.
3. Если `handovers.pending/active > 0` и это тестовый мусор — одним выстрелом очистить: `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot < ~/truffles-main/ops/reset.sql`.
4. Если “бот молчит” у конкретного клиента — проверить состояние диалога (пример для `+77015705555`):
   `docker exec -i truffles_postgres_1 psql -U $DB_USER -d chatbot -c "SELECT c.id, c.state, c.telegram_topic_id, c.last_message_at FROM conversations c JOIN users u ON u.id=c.user_id WHERE u.remote_jid='77015705555@s.whatsapp.net' ORDER BY c.started_at DESC LIMIT 3;"`
5. Если `state=manager_active` — это НЕ баг: бот обязан молчать, а сообщения должны улетать в Telegram-топик.
6. Если `state=bot_active`, но бот “молчит” — смотреть логи доставки: `docker logs truffles-api --tail 300`.

Правило тестов (чтобы самому себе не ломать картину):
- Не мешать сценарии в одну кашу: отдельно “прайс/запись”, отдельно “эскалация”, отдельно “жалоба”.
- Быстрые сообщения подряд (“подскажите/…/…”) теперь debounced на уровне API → промежуточные сообщения сохраняются в историю, но бот отвечает один раз (по последнему сообщению после паузы).
- После тестов закрывать заявки кнопкой [Решено] или делать `reset.sql`, чтобы диалоги не оставались в `pending/manager_active`.

Ключевые файлы для отладки: `truffles-api/app/routers/webhook/_legacy.py`, `truffles-api/app/routers/telegram_webhook.py`, `truffles-api/app/services/ai_service.py`, `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/services/state_service.py`, `ops/reset.sql`.

Что работает:
- Бот отвечает при RAG score ≥ 0.5 (medium/high), а приветствия/«спасибо»/«ок?»/«???» — без заявок (guardrails)
- В `pending` бот отвечает и не создаёт повторную заявку (но сообщения всё равно форвардятся в Telegram-топик)
- Кнопки [Беру] [Решено] работают (после починки traefik labels)
- Заявки создаются

Что НЕ работает:
- Low confidence всё ещё часто уходит в заявку из-за неполной базы знаний (нужно «уточнение перед заявкой»)
- Active Learning по owner-ответам подтверждён логами (2025-12-25), но нужна модерация/метрики

---

## МОИ ОШИБКИ (архитектор)

1. **Написал код не понимая систему.** Добавил learning_service.py, не проверив как сообщения менеджера вообще доходят до API.

2. **Не читал документацию.** В SPECS/ARCHITECTURE.md описан путь сообщения менеджера. В ops/README.md написано куда настроен Telegram webhook. Я не читал.

3. **Отчитывался "сделано" когда ничего не проверил.** Сказал что Active Learning работает, хотя ни разу не проверил логи.

4. **Спрашивал Жанбола то, что должен найти сам.** "Как твоё сообщение дошло до клиента?" — это я должен был выяснить из кода, не спрашивать.

5. **Извинялся вместо того чтобы делать.** Извинения — мусор. Нужны действия.

---

## ФАКТЫ (что точно известно)

### Из логов:
```
"сколько стоит маникюр?" → score 0.742 → бот ответил сам ✓
"сколько стоит постричь ногти?" → score 0.655 → эскалация
"спасибо" → score 0.535 → эскалация ← ПЛОХО
"ты еще здесь?" → эскалация ← ПЛОХО
```

### Outbox latency (DB факт):
- `outbox_messages` SENT за последний час: avg 17s, p90 25s, max 26s (created_at → updated_at)
- Последние 10 сообщений: 9-21s

### Outbox latency breakdown (логи+DB, выборка 4 батча):
- Wait до старта обработки (start - last_created): avg 8.7s, p90 9.9s → совпадает с coalesce+interval
- Processing (processed - start): avg 6.6s, p90 12.7s
- End-to-end от последнего сообщения: avg 15.4s, p90 21.3s
- В outbox есть старые `PROCESSING` (3) и `FAILED` (2) записи (возраст ~1.5–1.9 дня) — потенциальный мусор/ретраи
- Пример (08:55 местн, сообщение “Добрый день. Это мое сообщение”): wait 9.3s, processing 17.7s, total 27.0s

### 2025-12-27 — Fast-intent timing (после LLM timeout + fast-intent)
- Safe intents (5 кейсов): outbox_total_ms 2160–2241ms, без intent_ms/llm_ms; send_ms ~0.58–0.62s
- LLM кейс ("как ухаживать за гель-лаком"): intent_ms 8517ms, rag_ms 415ms, llm_ms 8314ms (timeout), outbox_total_ms 19473ms

### 2025-12-27 — Model routing (FAST/SLOW) + таймауты
- Параметры: FAST_MODEL=gpt-5-mini, SLOW_MODEL=gpt-5-mini, INTENT_TIMEOUT_SECONDS=2, LLM_TIMEOUT_SECONDS=6, FAST_MODEL_MAX_CHARS=160
- Safe intents (safe3, без LLM): outbox_total 5.38–6.18s, llm_ms отсутствует
- LLM ветка (llm5): outbox_total 15.14–16.71s; llm_ms 6.31s (timeout=true, model_tier=fast)

### 2025-12-27 — Coalesce=1 + window-merge + context caps
- OUTBOX: COALESCE=1s, WINDOW_MERGE=2.5s, WORKER_INTERVAL=1s
- LLM caps: LLM_MAX_TOKENS=600, LLM_HISTORY_MESSAGES=6, LLM_KNOWLEDGE_CHARS=1500
- Safe intents (SAFE4): total_s 2.19–2.79s, без llm_ms
- LLM ветка (CMPX3-1, CMPX5-1/2/4/5): total_s 10.93–12.61s; llm_ms 6.31–7.67s (timeout=true)

### 2025-12-27 — LLM cache + timeout 4s
- Таймауты: INTENT=1.5s, LLM=4s; cache TTL=24h (key: normalized text + client_slug + policy_version)
- Safe intents (SAFE5): total_s 2.72–2.86s
- LLM ветка (CMPX6-3/6-5/7-4/7-5/8-1): total_s 8.35–9.52s (avg 8.99, p90 9.48)

### 2025-12-27 — Top-вопросы без LLM (demo_salon)
- Top-30 из DB: добавлены новые truth intents (aftercare/prep/combo/style/manicure/classic/webhook-error) + фразы в INTENTS.
- Тесты: `python -m pytest /app/tests/test_demo_salon_eval.py /app/tests/test_message_endpoint.py -q` → 52 passed (docker exec).
- Live-check (7 запросов, новые remote_jid): ответы из truth-gate (aftercare/prep/combo/style/manicure/classic/system_error).

### Кнопки:
- Сначала не работали — traefik labels были пустые
- После `ops/restart_api.sh` — заработали
- Скрипт `ops/restart_api.sh` — правильный способ деплоя

### Обучение (Active Learning):
- Код написан: `learning_service.py`, вызов в `manager_message_service.py`
- В логах есть `"Owner response detected"` и `"Added to knowledge"` (2025-12-25) → auto-upsert в Qdrant сработал
- Жанбол писал "5000 тысяч" в топик — сообщение дошло до клиента

### Telegram webhook:
- В ops/README.md зафиксирован webhook `https://api.truffles.kz/telegram-webhook` (прямой в API)
- В коде ожидается: `api.truffles.kz/telegram-webhook`
- Я предположил что это причина — но Жанбол сказал что это хуйня

### Прод (2025-12-24):
- API падал на `/webhook` из-за отсутствия `conversations.branch_id` (миграция 013 не была применена) — применено, падение исчезло.
- `/etc/cron.d/truffles-outbox` есть и дергает `/admin/outbox/process` каждую минуту (через `ALERTS_ADMIN_TOKEN`).
- Inbound payload не нёс `metadata.instanceId` (раньше), поэтому by_instance не работал; после добавления query‑param для demo_salon instanceId приходит.
- Demo_salon: запросы вида "как у/в стиле" → отвечают прайсом (truth-gate), нужно отдельное правило.

### Branch routing (DB факт):
- `demo_salon`: `branch_resolution_mode=by_instance`, `remember_branch_preference=true`, `require_branch_for_pricing=true`, `auto_approve_roles=owner,admin`, `webhook_secret` установлен.
- `truffles`: `branch_resolution_mode=hybrid`, `remember_branch_preference=true`, `require_branch_for_pricing=true`, `auto_approve_roles=owner,admin`, `webhook_secret` установлен; branch `main` с `instance_id` подключён (ChatFlow webhook обновлён).

### Branches (DB факт):
- `demo_salon` имеет 1 активный branch (`slug=main`) с `instance_id` и `telegram_chat_id`.
- `truffles` имеет 1 активный branch (`slug=main`) с `instance_id`.

### Inbound payload (DB факт):
- Ранее в `outbox_messages.payload_json.body.metadata` были только `sender`, `messageId`, `remoteJid`, `timestamp` → `instanceId` отсутствовал.
- Теперь при webhook с query‑param `instanceId` присутствует (пример: "второе сообщение", 2025‑12‑25 04:22 UTC) и `conversation.branch_id` = `b7f75692-951e-421a-aae6-f5db97394799` (main).
- Проверка:
```
SELECT payload_json->'body'->'metadata' AS metadata
FROM outbox_messages
ORDER BY created_at DESC
LIMIT 1;
```
- Пример текстового payload (из `outbox_messages.payload_json`):
```
{"body": {"message": "вот мое просто сообщение", "metadata": {"sender": "Zh.", "messageId": "3EB0747A962FBC720E44FF", "remoteJid": "77015705555@s.whatsapp.net", "timestamp": 1766582383}, "messageType": "text"}, "client_slug": "demo_salon"}
```
- Пример нетекстового payload (из логов, `has_message=false`): ключи `messageType`, `message`, `metadata`, `to`, `mediaData`, `nodeData`.
- Сейчас такие payload на проде отбрасываются (“Empty message”); после деплоя будут сохраняться и получать ответ “опишите текстом”.

---

## ЧТО МЕНЯЛОСЬ В КОДЕ

| Файл | Изменение |
|------|-----------|
| `demo_salon_knowledge.py` | Multi-truth: семантика часов/услуги → один reply; presence re-rank по семантике; guest_policy до question_type |
| `demo_salon_knowledge.py` | Multi-truth: только semantic_question_type + semantic_service_match; short-message gate для сервисного матча (len<=2 без ?) |
| `SALON_TRUTH.yaml` | Добавлен шаблон `services_catalog.service_presence_reply` |
| `SALON_TRUTH.yaml` | Добавлены RU/KZ примеры для `domain_pack.typical_questions.hours` |
| `EVAL.yaml` | Кейс multi-truth (часы + маникюр) |
| `tests/test_message_endpoint.py` | Тест multi-truth: часы+услуга без booking, "ислам" не создаёт заявку |
| `webhook/_legacy.py` | Booking gate: info-вопросы распознаются по сегментам ?!.; блокировка очищает booking_state и отключает flow |
| `conversation.py` | Добавлен `context` (JSONB) для краткого контекста/слотов |
| `webhook/_legacy.py` | Слот-филлинг записи + контекст диалога |
| `state_service.py` | Очистка контекста при resolve |
| `ops/reset.sql` | Сброс контекста при emergency reset |
| `reminder_service.py` | Авто‑закрытие handover + алерт “нет ответа” |
| `ai_service.py` | Возвращает `Result[Tuple[str, str]]` с confidence |
| `message.py` | Обработка low_confidence → эскалация |
| `webhook/_legacy.py` | То же самое (ОБА файла обрабатывают сообщения!) |
| `learning_service.py` | СОЗДАН: `is_owner_response()`, `add_to_knowledge()` |
| `manager_message_service.py` | Добавлен вызов `add_to_knowledge()` для owner |
| `main.py` | Фоновый outbox worker (тик 2s, опционально через env) |
| `admin.py` | Outbox processing вынесен в общий хелпер |
| `webhook/_legacy.py` | Добавлен `_process_outbox_rows()` для reuse в admin/worker |
| `schemas/telegram.py` | Добавлены `sender_chat`/`author_signature`, username у chat |
| `telegram_webhook.py` | sender_chat fallback для идентификации менеджера |
| `telegram_webhook.py` | unpin использует `handover.telegram_message_id` (fallback на callback message_id) |
| `manager_message_service.py` | Не затирает assigned_to при unknown, fallback на assigned_to для owner-check |
| `learning_service.py` | Owner match принимает отрицательные ID (sender_chat) |
| `message_service.py` | Выбор последнего содержательного user-сообщения для handover |
| `webhook/_legacy.py` | human_request эскалируется с последним meaningful сообщением |
| `message.py` | То же поведение для `/message` |
| `webhook/_legacy.py` | Decision engine (normalize → signals → resolve → action) + policy handler для truth gate |
| `webhook/_legacy.py` | Валидация слотов записи (service/datetime/name) + запрет opt-out/фрустрации |
| `config.py` | Settings: игнорировать лишние env-поля (запуск тестов в окружении с .env) |
| `truffles-api/tests/test_cases.json` | Добавлены автоматизируемые кейсы для golden-прогона |
| `tests/test_message_endpoint.py` | Автотесты golden-cases (decision/signals) |
| `schemas/telegram.py` | Перевёл Pydantic Config на ConfigDict (убрал депрекейшн) |
| `demo_salon_knowledge.py` | Фикс ложной payment-эскалации: короткие ключи/фразы → word-boundary |
| `EVAL.yaml` | Добавлен кейс “какие услуги” для services_overview |
| `webhook/_legacy.py` | Fast-intent: короткий путь (phrase/truth) до LLM |
| `ai_service.py` | Model routing FAST/SLOW + LLM timeout (6s) + model_tier в логах |
| `intent_service.py` | Intent классификация на FAST_MODEL + timeout 2s + timing logs |
| `services/llm/base.py` | generate() принимает timeout_seconds |
| `services/llm/openai_provider.py` | timeout_seconds прокинут в httpx |
| `demo_salon_knowledge.py` | Добавлены truth-intent ответы: уход за гель-лаком, подготовка бровей/ресниц, совмещение процедур, style reference, маникюр-прайс, уточнение “классический”, обработка ошибки вебхука |
| `SALON_TRUTH.yaml` | Добавлены aftercare/preparation/procedure_compatibility/style_reference/price_quick_answers/system_messages |
| `INTENTS_PHRASES_DEMO_SALON.yaml` | Расширены фразы (greeting/thanks/booking) + новые intent фразы под top-вопросы |
| `EVAL.yaml` | Новые кейсы: уход/подготовка/совмещение/style/маникюр/классический/webhook-error |
| `truffles-api/tests/test_cases.json` | Golden cases для новых fast-intent |
| `tests/test_message_endpoint.py` | Обновлён fallback case для LLM |
| `ai_service.py` | Добавлены флаги `llm_used`/`llm_timeout` в timing_context для метрик |
| `webhook/_legacy.py` | Запись decision_meta в metadata user-сообщений (fast_intent/LLM) |
| `admin.py` | Новый /admin/metrics (читает дневные метрики) |
| `ops/migrations/015_add_metrics_daily.sql` | Таблица дневных метрик SLA/LLM/эскалаций |
| `ops/metrics_daily_snapshot.sql` | SQL snapshot метрик по дню/клиенту |
| `truffles-api/tests/test_cases.json` | Добавлены fast_intent golden cases |
| `tests/test_message_endpoint.py` | Тесты fast_intent + LLM fallback |
| `.env.example` | Добавлены FAST_MODEL/SLOW_MODEL + таймауты |
| `webhook/_legacy.py` | Outbox skip_persist пишет decision_meta (message_id/created_at fallback), messageId добавляется в payload |
| `demo_salon_knowledge.py` | Часы работы распознаются шире, “сколько” не триггерит прайс без price-сигнала |
| `EVAL.yaml` | Кейс “Во сколько вы открываетесь в будни?” → hours |
| `truffles-api/tests/test_cases.json` | Golden‑кейс для hours (fast_intent) |
| `ai_service.py` | LLM timeout default поднят до 6s |
| `intent_service.py` | Domain router: подсчёт hit‑якорей + strict in‑anchors для OOD override |
| `webhook/_legacy.py` | OOD override по anchor hit + OOD проверка до style_reference; decision_trace/logs расширены |
| `ops/update_instance_demo.sql` | anchors_in/out расширены, добавлен anchors_in_strict + “кошачий глаз” |
| `tests/test_message_endpoint.py` | Demo domain_router config обновлён (anchors_in/out + strict) |
| `truffles-api/tests/test_cases.json` | Кейсы OOD/style/“кошачий глаз” для domain_router и fast_intent |
| `webhook/_legacy.py` | Порядок гейтов обновлён: было policy/truth → booking → fast_intent → intent/domain → LLM; стало pending/opt-out/policy escalation → OOD (strong anchors) → booking guard/flow → LLM-first → truth gate fallback |
| `webhook/_legacy.py` | LLM guard: темы оплат/медиц/жалоб/скидок/возвратов → эскалация + decision_meta `llm_primary_used` |
| `webhook/_legacy.py` | Fast-intent теперь только smalltalk (greeting/thanks/ok), booking slang "маник" добавлен в keywords |
| `ai_service.py` | GREETING_PHRASES расширен ("сәлем") для smalltalk |
| `ai_service.py` | THANKS_PHRASES расширен ("пожалуйста") для smalltalk |
| `demo_salon_knowledge.py` | Price сигнал: добавлен сленг "скок/скока", маникюр распознаётся как "маник" |
| `truffles-api/tests/test_cases.json` | Golden cases: fast-intent оставлен только для smalltalk |
| `tests/test_message_endpoint.py` | Тесты: fast-intent smalltalk, truth-gate fallback после LLM low_confidence, LLM guard эскалирует |
| `truffles-api/tests/test_cases.json` | Fast-intent golden cases обновлены (services/address/hours теперь не матчатся) |
| `EVAL.yaml` | Добавлены сленговые кейсы: "скок стоит маник", "чо по адресу", "записаться на маник" |
| `SPECS/CONSULTANT.md` | Зафиксировано: LLM-first с жёсткими правилами и fallback |
| `SALON_TRUTH.yaml` | Добавлен services_catalog с алиасами и базовыми подсказками услуг |
| `demo_salon_knowledge.py` | Service matcher по услугам (data-driven) + обработка "сколько стоит" |
| `webhook/_legacy.py` | Service matcher в LLM-first до LLM, source=service_matcher |
| `tests/test_message_endpoint.py` | Тест: service matcher шортсёркит LLM |
| `EVAL.yaml` | Кейсы: педикюр/массаж ног/адрес |
| `ai_service.py` | ASR default provider: ElevenLabs scribe_v1, fallback whisper-1 |
| `webhook/_legacy.py` | ASR primary default aligned to ElevenLabs (scribe_v1) |

**owner_telegram_id:** было `@ent3rprise` (НЕ РАБОТАЛО), исправлено на `1969855532`

---

## ВОПРОСЫ БЕЗ ОТВЕТА

1. **Как сообщение менеджера доходит до клиента?** Нужна трассировка от Telegram webhook до ChatFlow отправки.

2. **Правильный ли threshold?** Сейчас в коде: MID=0.5, HIGH=0.85. Дальше тюнить только по фактам (сколько эскалаций/качество ответов).

---

## СЛЕДУЮЩАЯ СЕССИЯ — ЧТО ДЕЛАТЬ

### 1. СНАЧАЛА РАЗОБРАТЬСЯ, ПОТОМ ДЕЛАТЬ

Прежде чем что-то менять:
1. Прочитать SPECS/ARCHITECTURE.md полностью
2. Прочитать SPECS/ESCALATION.md
3. Проследить путь сообщения менеджера в коде

### 2. КОНКРЕТНЫЕ ЗАДАЧИ

| Приоритет | Задача | Как проверить |
|-----------|--------|---------------|
| P0 | Вкатить latest CI image на прод (pull GHCR) | В `/admin/version` новый коммит; поведение соответствует изменениям |
| P0 | Прокинуть `instanceId` в inbound payload (ChatFlow) для всех клиентов | `payload.body.metadata.instanceId` есть; `conversation.branch_id` ставится (demo_salon + truffles ok) |
| P0 | Снизить задержку ответов (outbox): сейчас avg 17s, p90 25s | Avg/p90 < 10s |
| P0 | DONE 2026‑01‑02: multi‑intent при склейке (booking+info) | Live‑check PASS + trace booking_interrupt |
| P1 | Убрать дубли заявок на одного клиента | Проверка 2026-01-02: open handovers duplicates 0 (conversation_id + join user_id); DoD: при open handover новые не создаются, идёт ответ в существующий топик |
| P1 | Пины в Telegram снимаются после "Решено" | После resolve закреп исчезает всегда |
| P1 | Проработать UX Telegram для владельца/менеджеров | Спека: как работать с заявками без хаоса |
| P1 | Добавить базовые фразы в knowledge base | "ты еще здесь?" → бот отвечает сам |
| P1 | demo_salon: правило style_reference (как у/в стиле) | Ответ без фото/без выдумок, с объяснением зависимости от базы |

### 3. КАК ДЕПЛОИТЬ

```bash
# CI build/push → pull image
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash ~/restart_api.sh"

# Проверить логи
ssh -p 222 zhan@5.188.241.234 "docker logs truffles-api --tail 50"

# Локальная сборка (fallback)
ssh -p 222 zhan@5.188.241.234 "docker build -t truffles-api_truffles-api /home/zhan/truffles-main/truffles-api"
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```

---

## УРОК

Жанбол прав: проблема не в том что я "несу хуйню". Проблема в контекстном окне и амнезии. Много информации, много файлов — и я теряю контекст.

Решение: ЧИТАТЬ ДОКУМЕНТАЦИЮ ПЕРЕД ТЕМ КАК ДЕЛАТЬ. Не спрашивать Жанбола — искать самому. Не извиняться — делать.

---

**Коммиты:** `8e10fa8`, `379ba4c`, `2f74e1b`, `736139e`

---

### 2025-12-12 — Неделя 2 + Неделя 3 + Улучшение workflow

**Что сделали:**

*Неделя 2 (качество кода):*
- ruff, logging (JSON), alerts integration, CI/CD, 91 тест
- Закоммичено и запушено

*Неделя 3 (защита кода):*
- Result pattern — `services/result.py`
- State service — атомарные переходы с транзакциями
- Health service — self-healing
- SQL constraint — `migrations/003_add_state_constraint.sql`
- Рефакторинг webhook.py — использует state_service
- Health endpoints — /admin/health, /admin/heal
- 121 тест всего

*Улучшили workflow архитектора:*
- Добавили секцию "ГДЕ ИСКАТЬ ОТВЕТЫ" — карта документов
- Правило: сначала grep, спрашивать только если не нашёл
- Убрали MVP-менталити из документов

**Ключевой урок:**
Все ответы уже есть в документах. Архитектор ищет, не спрашивает.

**Следующая сессия:**
- Неделя 4: Эскалация при низком confidence, Active Learning

---

### 2025-12-10 (вечер) — Архитектура мультитенанта + Дройды

**Что сделали:**

*Архитектура:*
- Разобрали иерархию Company → Client → Branch
- Обнаружили: Branch существует в БД, но не подключен к роутингу
- Добавили в план: подключить Branch (conversation.branch_id вместо client_id)
- Добавили в backlog: омниканальность (Channel) для Instagram/Telegram

*Дройды:*
- truffles-architect.md — добавили: СТАРТ СЕССИИ, РАБОТА С ЖАНБОЛОМ, ДИАГНОСТИКА, РЕВЬЮ КОДЕРА
- truffles-coder.md — добавили: СТАНДАРТ КАЧЕСТВА
- AGENTS.md — добавили: ошибка #0 "Экономлю на качестве"

*Документы:*
- SPECS/ARCHITECTURE.md — обновили схему БД (companies, branches)
- SPECS/MULTI_TENANT.md — добавили полную иерархию, роли, текущее vs конечное

**Затронутые файлы:**
- [x] STATE.md
- [x] SPECS/ARCHITECTURE.md
- [x] SPECS/MULTI_TENANT.md
- [x] AGENTS.md
- [x] .factory/droids/truffles-architect.md
- [x] .factory/droids/truffles-coder.md

**Почему так решили:**
- Документы не отражали реальную архитектуру БД → синхронизировали
- Дройд не понимал контекст на старте → добавили СТАРТ СЕССИИ
- AI экономил на качестве → добавили СТАНДАРТ КАЧЕСТВА как принцип #0
- Не было диагностики проблем → добавили раздел ДИАГНОСТИКА

**Следующая сессия:**
- [ ] Диагностика: бот не отвечает (блокер)
- [ ] Подключить Branch к роутингу
- [ ] Мозги LLM — промпт

---

### 2025-12-10 — Аудит документов + Мозги LLM

**Что сделали:**

*Часть 1: Документы и структура*
- Обновили все SPECS/ документы (синхронизация с кодом)
- Добавили метрики North Star в ESCALATION.md
- Добавили чеклист онбординга 35 мин в MULTI_TENANT.md
- Создали STRUCTURE.md — карту проекта
- Создали HOW_TO_WORK.md — инструкция для Жанбола
- Создали droid'ы: truffles-architect, truffles-coder
- Удалили мусор из ops/ (~175 файлов → архив)
- Создали STATE.md — центральный хаб
- Добавили .gitignore (исключает .archive/ops_old/)

*Часть 2: Мозги LLM*
- Проанализировали как работает бот: webhook → intent → RAG → LLM
- Нашли проблему: промпт слишком общий, бот обещает то что не умеет
- Создали API для управления промптами: `PUT /admin/prompt/{client_slug}`
- Создали API для управления настройками: `PUT /admin/settings/{client_slug}`
- Создали скрипт: `ops/update_prompt.py` с защитой от дураков
- Создали шаблон промпта: `ops/templates/prompt_template.md`

**Затронутые документы/файлы:**
- [x] STATE.md — создан, обновлён
- [x] STRUCTURE.md — создан
- [x] HOW_TO_WORK.md — создан
- [x] SPECS/ESCALATION.md — добавлены метрики
- [x] SPECS/MULTI_TENANT.md — добавлен чеклист онбординга
- [x] .factory/droids/truffles-architect.md — создан
- [x] .factory/droids/truffles-coder.md — создан
- [x] truffles-api/app/routers/admin.py — создан (API управления)
- [x] truffles-api/app/main.py — добавлен admin router
- [x] ops/update_prompt.py — скрипт управления промптами
- [x] ops/templates/prompt_template.md — шаблон промпта
- [x] .gitignore — создан

**Архитектура LLM (для справки):**
```
Сообщение → Webhook 
    → classify_intent() [LLM #1]
    → Решение (эскалация/мьют/ответ)
    → generate_ai_response() [LLM #2]
        → get_system_prompt() из БД
        → search_knowledge() из Qdrant (RAG)
        → full_prompt = system + RAG_context
        → history (10 сообщений)
        → LLM.generate()
```

**Почему так решили:**
- Документы были разрознены → создали карту и хаб
- Нет удобного управления промптами → создали API
- Промпт не ограничивал бота → создали шаблон с чёткими границами
- Хардкод SQL — плохо → API + скрипт с валидацией

**Следующая сессия:**
- [ ] Обновить промпт truffles через новый API
- [ ] Тестировать что бот не обещает лишнего
- [ ] Confidence threshold (не выдумывать если RAG пустой)
- [ ] Эскалация — добить

---

### 2026-01-13 — Fix: no_response dedup + shield_drop suppression

**Что сделали:**
- Очистили `check_no_response_alerts`: guard `shield_drop` до записи алерта, один dedup write, JSONB context сохраняется через копию.
- Восстановили тесты no_response (dedup + shield_drop).
- PR #154 merged → deploy main.

**Evidence:**
- PR: https://github.com/k1ddy/Truffles-AI-Employee/pull/154
- CI main (build/push/deploy): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20944545548
- Prod `/admin/version`: `{"version":"main","git_commit":"959ffa5ab6fb38b74be5417a542da9181ad9af6e","build_time":"2026-01-13T04:20:47Z"}`
- Live-check (real inbound, test JID 77015705555@s.whatsapp.net, 09:57 local):
  - decision_meta (shield_drop):
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT m.id, m.created_at, m.metadata->>'messageId' AS message_id, m.metadata->'decision_meta' AS decision_meta, c.id AS conversation_id FROM messages m JOIN conversations c ON c.id = m.conversation_id WHERE m.metadata->>'remoteJid' = '77015705555@s.whatsapp.net' ORDER BY m.created_at DESC LIMIT 1;"`
    - output: `id=88173fb2-20f7-4c25-93dc-fd050a2ed248; message_id=3EB09CCE4B9B1409FC04F9; conversation_id=b8c559d1-f8cd-4173-ae70-0a9683833e48; decision_meta.action=shield_drop; shield_reason=too_long`
  - decision_trace (last):
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT context->'decision_trace'->(jsonb_array_length(context->'decision_trace')-1) AS last_trace FROM conversations WHERE id = 'b8c559d1-f8cd-4173-ae70-0a9683833e48';"`
    - output: `{"stage":"shield","decision":"drop","reason":"too_long","message_length":1278,...}`
  - /reminders/process (after 3+ min):
    - cmd: `curl -s -X POST http://localhost:8000/reminders/process`
    - output: `{"no_response_alerts":{"alerted":0,"items":[]},...}`
  - dedup not created:
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT context->'alerts' AS alerts FROM conversations WHERE id = 'b8c559d1-f8cd-4173-ae70-0a9683833e48';"`
    - output: `NULL`

### 2026-01-12 — Fix: pending SLA ping spam

**Что сделали:**
- Исправили сохранение `pending_sla.ping_sent_at` (контекст копируется, чтобы JSONB фиксировался).
- Добавили регресс‑тест: два запуска `process_pending_sla` → один пинг.
- PR #147 merged → deploy main.
- Баг pending SLA ping spam закрыт.

**Evidence:**
- PR: https://github.com/k1ddy/Truffles-AI-Employee/pull/147
- CI PR: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20922142372
- CI main (build/push/deploy): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20922178070
- Prod `/admin/version`: `{"version":"main","git_commit":"6175fab86439492be5c440cd1666882ea93687ea","build_time":"2026-01-12T14:05:21Z"}`
- /reminders/process: pinged=1 (first), pinged=0 (second) — curl outputs сохранены в истории сессии.
- Note: `conversations.escalated_at` временно выставлен `NOW() - INTERVAL '20 minutes'` для пинга и восстановлен на `2026-01-12 13:59:09.002251+00`.
- SQL (conv_id `b8c559d1-f8cd-4173-ae70-0a9683833e48`, run_at=2026-01-12T14:08:20Z):
  - pending_sla saved
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT context->'pending_sla' AS pending_sla FROM conversations WHERE id = 'b8c559d1-f8cd-4173-ae70-0a9683833e48';"`
    - output: `{"ping_sent_at": "2026-01-12T14:08:12.990209+00:00"}`
  - reminders (last 10)
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT id, created_at, content FROM messages WHERE conversation_id = 'b8c559d1-f8cd-4173-ae70-0a9683833e48' AND content ILIKE 'Напоминаю: менеджер ещё не подключился%' ORDER BY created_at DESC LIMIT 10;"`
    - output: last row `03b56844-dc1e-4693-adc7-eb1f47c921a7 | 2026-01-12 14:08:13.872299+00 | Напоминаю: менеджер ещё не подключился. Я на связи — напишите, что нужно уточнить.`

### 2026-01-12 — P1-0 baseline metrics (decision_trace/meta + long-eval)

**Что сделали:**
- Сняли baseline по decision_meta/decision_trace (demo_salon, last 7 days) перед изменениями.
- Зафиксировали fallback_rate, expected_reply match-rate, question_contract matched/missed.
- Проверили long-eval (long-chaos) статус по CI.

**Evidence:**
- SQL (demo_salon, last 7 days, run_at=2026-01-12T08:30:15Z):
  - fallback_rate
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "WITH base AS (SELECT metadata->'decision_meta' AS meta FROM messages WHERE role='user' AND client_id='c839d5dd-65be-4733-a5d2-72c9f70707f0' AND created_at >= NOW() - INTERVAL '7 days' AND metadata ? 'decision_meta') SELECT COUNT(*) AS total_msgs, COUNT(*) FILTER (WHERE meta->>'router_fallback_reason' IS NOT NULL AND meta->>'router_fallback_reason' <> '') AS fallback_msgs, ROUND(COUNT(*) FILTER (WHERE meta->>'router_fallback_reason' IS NOT NULL AND meta->>'router_fallback_reason' <> '')::numeric / NULLIF(COUNT(*),0), 4) AS fallback_rate FROM base;"`
    - output: total_msgs=302 fallback_msgs=19 fallback_rate=0.0629
  - fallback_reason breakdown
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "WITH base AS (SELECT metadata->'decision_meta' AS meta FROM messages WHERE role='user' AND client_id='c839d5dd-65be-4733-a5d2-72c9f70707f0' AND created_at >= NOW() - INTERVAL '7 days' AND metadata ? 'decision_meta') SELECT meta->>'router_fallback_reason' AS fallback_reason, COUNT(*) AS total FROM base WHERE meta->>'router_fallback_reason' IS NOT NULL AND meta->>'router_fallback_reason' <> '' GROUP BY 1 ORDER BY total DESC;"`
    - output: low_confidence=16, budget_exceeded=2, timeout=1
  - expected_reply match-rate
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "WITH base AS (SELECT metadata->'decision_meta' AS meta FROM messages WHERE role='user' AND client_id='c839d5dd-65be-4733-a5d2-72c9f70707f0' AND created_at >= NOW() - INTERVAL '7 days' AND metadata ? 'decision_meta') SELECT COUNT(*) AS expected_reply_msgs, COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' = 'true') AS matched, COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' = 'false') AS missed, COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' IS NULL OR meta->>'expected_reply_matched' NOT IN ('true','false')) AS missing_flag, ROUND(COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' = 'true')::numeric / NULLIF(COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' IN ('true','false')), 0), 4) AS match_rate FROM base WHERE meta->>'expected_reply_type' IS NOT NULL AND meta->>'expected_reply_type' <> '';"`
    - output: expected_reply_msgs=104 matched=37 missed=31 missing_flag=36 match_rate=0.5441
  - expected_reply_type breakdown
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "WITH base AS (SELECT metadata->'decision_meta' AS meta FROM messages WHERE role='user' AND client_id='c839d5dd-65be-4733-a5d2-72c9f70707f0' AND created_at >= NOW() - INTERVAL '7 days' AND metadata ? 'decision_meta') SELECT meta->>'expected_reply_type' AS expected_reply_type, COUNT(*) AS total, COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' = 'true') AS matched, COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' = 'false') AS missed, COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' IS NULL OR meta->>'expected_reply_matched' NOT IN ('true','false')) AS missing_flag, ROUND(COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' = 'true')::numeric / NULLIF(COUNT(*) FILTER (WHERE meta->>'expected_reply_matched' IN ('true','false')), 0), 4) AS match_rate FROM base WHERE meta->>'expected_reply_type' IS NOT NULL AND meta->>'expected_reply_type' <> '' GROUP BY 1 ORDER BY total DESC;"`
    - output: time total=56 matched=21 missed=23 missing_flag=12 match_rate=0.4773; service_choice total=25 matched=3 missed=0 missing_flag=22 match_rate=1.0000; name total=21 matched=12 missed=8 missing_flag=1 match_rate=0.6000; intent_choice total=2 matched=1 missed=0 missing_flag=1 match_rate=1.0000
  - question_contract matched/missed (decision_trace)
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "WITH traces AS (SELECT (trace->>'recorded_at')::timestamptz AS recorded_at, trace->>'decision' AS decision FROM conversations c JOIN LATERAL jsonb_array_elements(c.context->'decision_trace') AS trace ON true WHERE c.client_id='c839d5dd-65be-4733-a5d2-72c9f70707f0' AND c.context ? 'decision_trace' AND trace->>'stage'='question_contract' AND (trace->>'recorded_at')::timestamptz >= NOW() - INTERVAL '7 days') SELECT decision, COUNT(*) AS total FROM traces WHERE decision IN ('matched','missed') GROUP BY decision ORDER BY total DESC;"`
    - output: matched=4 missed=3
- question_contract trace samples (decision_trace):
  - missed time: conv_id `1f2e004f-6695-4087-8da0-36163045f0ee` recorded_at `2026-01-06T10:22:26.975811+00:00`
  - matched service_choice: conv_id `94c3797f-bbb7-4fc0-8bb1-61080553cc89` recorded_at `2026-01-06T09:30:59.304500+00:00`
- CI long-eval (long-chaos): run https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20912389895, job https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20912389895/job/60077823041, conclusion=success.

---

### 2026-01-12 — P1-2 Router SLA: normalize low_confidence fallback

**Что сделали:**
- Нормализовали controller fallback: low_confidence больше не записывается как `controller_fallback_reason`, флаги `controller_*` стабилизированы в decision_meta.
- PR смержен, CI main build/push/deploy выполнен, версия на проде обновлена.

**Evidence:**
- PR: https://github.com/k1ddy/Truffles-AI-Employee/pull/145
- Merge commit: https://github.com/k1ddy/Truffles-AI-Employee/commit/1a16fbea8421c792bdd8c8369141771c2aed24ad
- CI PR core/long: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20921140704 (success)
- CI main build/push/deploy: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20921181882 (success)
- Deploy time (CI run updatedAt): `2026-01-12T13:33:14Z`
- Prod `/admin/version`: `{"version":"main","git_commit":"1a16fbea8421c792bdd8c8369141771c2aed24ad","build_time":"2026-01-12T13:31:55Z"}`
- SQL (post-deploy window, created_at >= `2026-01-12T13:33:14Z`):
  - low_confidence not counted as fallback
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT COUNT(*) FILTER (WHERE (metadata->'decision_meta'->>'controller_attempted')::boolean) AS attempts, COUNT(*) FILTER (WHERE (metadata->'decision_meta'->>'controller_low_confidence')::boolean) AS low_confidence, COUNT(*) FILTER (WHERE (metadata->'decision_meta'->>'controller_low_confidence')::boolean AND (metadata->'decision_meta'->>'controller_fallback_reason') IS NOT NULL) AS bad_low_confidence_fallbacks FROM messages WHERE created_at >= '2026-01-12T13:33:14Z' AND metadata ? 'decision_meta';"`
    - output: attempts=0 low_confidence=0 bad_low_confidence_fallbacks=0
  - fallback_reason breakdown
    - cmd: `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -c "SELECT metadata->'decision_meta'->>'controller_fallback_reason' AS reason, COUNT(*) AS count FROM messages WHERE created_at >= '2026-01-12T13:33:14Z' AND (metadata->'decision_meta'->>'controller_fallback_reason') IS NOT NULL GROUP BY reason ORDER BY count DESC;"`
    - output: (no rows)
- Note: post-deploy window contains only `pending_sla_ping` meta; no controller_attempted rows yet (needs real inbound to validate low_confidence).

---

### 2026-01-12 — P1 working agreement (resolver-first, no regex growth)

**Что решили:**
- RU/KZ вариативность закрываем resolver-слоем (data-lexicon + ready libs), а не расширением regex/словников.
- EVAL — доказательство, а не источник логики; минимальные варианты для RU/KZ mix вместо “миллион кейсов”.
- Любой fix начинается с RCA и evidence; задачи без доказательств не выполняются.

**Почему:**
- Иначе CI превращается в бесконечный цикл “кейсы → хардкод”, что противоречит `STRATEGY/REQUIREMENTS.md`.

---

### 2026-01-02 — Fix: booking+info под coalesce (multi-intent)

**Что сделали:**
- Batch non‑booking selection игнорирует semantic service hints → "парковка есть?" не фильтруется как booking.
- Live‑check: info‑ответ + booking‑prompt в одном ответе; expected_reply_type=time; trace booking_interrupt + truth_gate.
- CI/деплой/pytest PASS; allowlist снят после успеха.

**Evidence:**
- Code: `truffles-api/app/routers/webhook/_legacy.py` (allow_service flag + selection).
- CI: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20658445278 (commit 7b971713b4863094ce39910f03c5e60e97688b16).
- Prod: `/admin/version` commit 7b971713b4863094ce39910f03c5e60e97688b16.
- Live‑check: conversation `99306198-1ecf-44d6-9066-72bb4e76e915`, decision_meta.booking_info_interrupt=true.

---

### 2026-01-04 — P1-A/P1-B/P1-C: router SLA + chaos long eval + deploy + live-check

**Что сделали:**
- P1-A: router SLA + fallback reasons (PR #24).
- P1-B: добавлены long chaos кейсы E546–E551 (PR #25).
- P1-C: merge → CI build/push/deploy → live-check 3 сценария.

**Evidence:**
- PR #24: https://github.com/k1ddy/Truffles-AI-Employee/pull/24
- PR #25: https://github.com/k1ddy/Truffles-AI-Employee/pull/25
- CI main: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20694618301 (build-push+deploy)
- Prod `/admin/version`: `{"version":"main","git_commit":"9c58a3b86835d84fa4fb949331c3949187fd998c","build_time":"2026-01-04T14:49:30Z"}`
- Live-check (decision_trace.class_router: router_error=none, router_fallback_reason=null, fallback_rate_flag=false):
  - chaos → conversation `3c41f05b-7229-44cd-b0d3-32221644aefe` (msg `live7-chaos-1767539630470-1`)
  - discount+booking → conversation `04957432-fde4-46eb-abb6-4bea70d1a388` (msg `live7-discount_booking-1767539630962-1`)
  - consult+перебивка → conversation `d7107767-58a7-4e4f-96ed-6f457313c8e2` (msg `live7-consult_interrupt-1767539631375-1`)

*Последнее обновление: 2026-01-07 (Evidence: CI 20772049679 + /admin/version + M2 reset live-check)*

---

### 2026-01-05 — Consult keeper + consult eval expansion + live-check

**Что сделали:**
- Consult keeper: при перебивках (info/booking) attach consult_return и удерживаем `current_goal=consult`.
- EVAL: добавлены комбинированные ответы E560–E563 и long стабильность consult E564–E569.
- Merge 3 PR → CI core/long PASS → deploy HEAD.

**Evidence:**
- Code: `truffles-api/app/routers/webhook/_legacy.py:2762`, `truffles-api/app/routers/webhook/_legacy.py:6766`, `truffles-api/app/routers/webhook/_legacy.py:7963`.
- EVAL cases: `truffles-api/app/knowledge/demo_salon/EVAL.yaml:6210`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml:6390`.
- PRs: https://github.com/k1ddy/Truffles-AI-Employee/pull/30, https://github.com/k1ddy/Truffles-AI-Employee/pull/31, https://github.com/k1ddy/Truffles-AI-Employee/pull/32.
- CI core/long: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20711370449, https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20711403858, https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20711520186.
- Prod `/admin/version`: `{"version":"main","git_commit":"80e864edce7237cc4b72080ad2bd7b3087c02e13","build_time":"2026-01-05T09:51:39Z"}`.
- Live-check consult+перебивка+возврат: conv_id `a271e3d0-053d-4d83-9852-f3ea3167efe9`; last messages: "Посоветуйте уход после окрашивания" → consult reply; "Где вы находитесь?" → address+hours + "Если вернуться..."; decision_meta (msg `267c740e-733b-48f5-aae4-eb3d1221bcdf`) consult_return=true current_goal=consult consult_topic=hair_aftercolor; decision_trace stage=consult_return recorded_at `2026-01-05T10:00:46.100141+00:00`.

---

### 2026-01-05 — Router SLA guard + expected reply shortcircuit

**Что сделали:**
- Router SLA: low_confidence не считается fallback при signal_match.
- Expected reply (time): shortcircuit в booking, без ухода в pricing.

**Evidence:**
- PR #38: https://github.com/k1ddy/Truffles-AI-Employee/pull/38
- CI main (build/push/deploy): https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20713718956
- Prod `/admin/version`: `{"version":"main","git_commit":"f78bcad487281e150588133bcfdd5dea2d8c3d76","build_time":"2026-01-05T11:17:49Z"}`
- Live-check router SLA: conv_id `ec380df5-e32d-4deb-b2d6-f52889edca24`, user msg `d9d57d09-f906-457b-ae58-4a52ba890f43` decision_meta class_router.router.sla fallback_rate=0.0 fallback_rate_flag=false (signal_match=true, fallback_reason=low_confidence).
- Expected reply shortcircuit: conv_id `d1a3116d-5334-4a70-a6a5-3088301f34d1`, user msg `24768482-e2bf-48a3-bb7e-65ba1d878cde` decision_meta expected_reply_shortcircuit=true answer_slot=datetime answer_value="в субботу вечером", no pricing (assistant asked name).

---

### 2026-01-06 — Base-80 CORE aliases gate + deploy + live-check

**Что сделали:**
- PR #42: добавили Base-80 alias IDs (E571–E711) в CORE_EVAL_IDS → CI core/long + build/push/deploy PASS.
- Deploy HEAD; `/admin/version` соответствует main.
- Live-check 5 alias кейсов (service_match/price/duration/hours/parking) — PASS.
- Doc sync: Source Pack добавлен в `docs/SELLING_TRUTHS.md` (commit f155bf1).

**Evidence:**
- PR #42: https://github.com/k1ddy/Truffles-AI-Employee/pull/42
- CI main: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20738453824
- Prod `/admin/version`: `{"version":"main","git_commit":"8fc94307da217a4235d0197c562f08e866bb9b65","build_time":"2026-01-06T04:53:46Z"}`
- Live-check (alias cases):
  - service_match → conv_id `82b5e451-cc29-48fe-9bf3-2003bf4334ae`, msg `live-alias2-service-1767675856-1`; decision_meta intent=service_match service_query="Брови и ресницы"; last msgs: "лами ресницы делаете?" → "Ламинирование ресниц — 6 000 ₸..."
  - pricing → conv_id `58f78885-3361-4e66-b430-03251d534755`, msg `live-alias2-price-1767675856-2`; decision_meta intent=info_bundle intents=["pricing"] service_query="Стрижка машинкой"; last msgs: "сколько стоит стрижка машинкой?" → "Стрижка машинкой — 2 000 ₸..."
  - duration → conv_id `fda91938-a44f-464d-bc13-3a0103561034`, msg `live-alias2-duration-1767675856-3`; decision_meta question_type=duration service_query="Маникюр + гель-лак"; last msgs: "сколько длится маникюр с гель-лаком?" → "Обычно 45–90 минут..."
  - hours → conv_id `54796bbb-29db-4efe-8ba6-44403653e58e`, msg `live-alias2-hours-1767675856-4`; decision_meta info_sections=["address","hours"]; last msgs: "до скольки вы открыты?" → "Работаем ... с 9:00 до 21:00."
  - parking → conv_id `7a67ed30-ff2c-46f1-894d-fdf7a2c41d2f`, msg `live-alias2-parking-1767675856-5`; decision_meta info_sections=["address","hours","parking"]; last msgs: "можно припарковаться у вас?" → "Парковка: Бесплатная парковка во дворе..."
- Doc sync: `docs/SELLING_TRUTHS.md:41` (Source Pack), commit f155bf1761ee14c5af5b3f044caae90fbf822c92.

---

### 2026-01-06 — Info_bundle/guest_policy lock + explicit service override

**Что сделали:**
- PR #52/#53: guest_policy и info_bundle блокируют semantic_match без явного service-сигнала; явная услуга в тексте побеждает carryover.
- Deploy HEAD; `/admin/version` соответствует main.
- Live-check 3 кейса (guest_policy/address+hours/pricing+address) — PASS.

**Evidence:**
- PRs: https://github.com/k1ddy/Truffles-AI-Employee/pull/52, https://github.com/k1ddy/Truffles-AI-Employee/pull/53
- CI main: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20741714343
- Prod `/admin/version`: `{"version":"main","git_commit":"58053a50bb4a84d441d6410fab02a353327a42dc","build_time":"2026-01-06T07:46:31Z"}`
- Live-check (conv_id `fc2ff625-f678-4544-a477-1fc2c9b93b63`):
  - guest_policy → msg `2d482756-b6de-4839-9d12-a04b6d2847a9` decision_meta info_semantic_match_skip_reason=guest_policy_lock, service_query=null; reply msg `c5fff20b-0c29-4e87-9b80-7001d3150b9d` (guest_policy + address/hours, без прайса/длительности).
  - address+hours → msg `2c4323eb-216a-43f6-91e6-630951151f85` decision_meta info_semantic_match_skip_reason=info_bundle_lock; reply msg `756c409d-5aa9-45bf-b139-681b06b61aa1` (address+hours, без прайса/длительности).
  - pricing+address → msg `c517a1ea-2794-42d5-a785-db13a98d05a7` decision_meta question_type=pricing service_query="Маникюр"; reply msg `0244ce5e-c86e-402a-b561-b609853f799e` (address+маникюр прайс).
