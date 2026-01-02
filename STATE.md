# STATE — Состояние проекта

**Центральный хаб. Обновляется каждую сессию.**

---

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
- Деплой API: CI build/push → на проде `IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash /home/zhan/restart_api.sh` (локальная сборка — fallback; см. `TECH.md`).
- Инфра compose: `/home/zhan/infrastructure/docker-compose.yml` + `/home/zhan/infrastructure/docker-compose.truffles.yml`; `/home/zhan/truffles-main/docker-compose.yml` — заглушка.
- Новые документы: `docs/TECH_STATUS.md` и `docs/SELLING_TRUTHS.md` (что можно обещать и чем доказывать).
- Session Canon updated in `docs/SESSION_START_PROMPT.txt`.
- Pilot readiness checklist added.
- Pilot readiness run PASS (2025-12-31) зафиксирован в `docs/TECH_STATUS.md`.
- Док‑синхронизация: убраны дубли в `STATE.md`/`STRUCTURE.md`, `SPECS/CONSULTANT.md` обновлён под `webhook.py`, уточнён источник истины в `docs/SESSION_START_PROMPT.txt`.
- Док‑синхронизация: `SPECS/MULTI_TENANT.md` и `SPECS/ARCHITECTURE.md` приведены к текущей реализации (branch routing частично, pipeline/вход /webhook/{client_slug}, ChatFlow без retries).
- Док‑синхронизация: `SPECS/ESCALATION.md` приведён к факту (roles/agent_identities/learned_responses — схема есть, wiring pending; branch config перенесён в реализованное).
- Док‑синхронизация: `AGENTS.md` и `docs/SESSION_START_PROMPT.txt` обновлены под роли Top Architect / Brain / Hands.

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
- Проверка 2026-01-02: open handovers duplicates 0 (handovers.status IN pending/active) по conversation_id и по conversations.user_id (join); SQL `SELECT conversation_id, count(*) ... HAVING count(*) > 1` → 0; `SELECT c.user_id, count(*) ... HAVING count(*) > 1` → 0.
- Фиксация: шаблон рассуждений + обновление `STATE.md` каждый раз.
- Детальный бриф салона заполнен эталоном (фейковые данные): `Business/Sales/Бриф_клиента.md`.
- Demo salon knowledge pack обновлён под эталон (truth/intents/eval + обзор услуг).
- Knowledge backlog: webhook пишет misses (low_confidence/out_of_domain/llm_timeout/clarify) в `knowledge_backlog` через upsert; отчёт — `/admin/knowledge-backlog` и `ops/knowledge_backlog_top.sql`; безопасно для прода (нет влияния на ответы).
- `SALON_TRUTH.yaml` теперь разделён на `domain_pack` (общая таксономия/синонимы/типовые вопросы/ООД‑якоря) и `client_pack` (факты demo_salon); старые ключи сохранены, поэтому безопасно для прода.
- `ops/sync_client.py` получил валидацию обязательных полей `client_pack` (`--validate`/`--validate-only`), без генерации новых файлов.
- `services_index` (Qdrant) заполняется из `ops/sync_client.py` по `price_list` + `services_catalog`; после LLM low_confidence работает semantic matcher (match/suggest) с `decision_meta.source=service_semantic_matcher`, безопасно для прода (срабатывает только при low_confidence и OOD‑gate).
- Добавлен rewrite‑layer для semantic matcher (FAST LLM → JSON intent/query, 1.2s) — влияет только на подбор запроса, факты не меняет.
- Semantic question‑type (hours/pricing/duration) на эмбеддингах из `domain_pack.typical_questions`; multi_truth объединяет 2 ответа (hours+price/duration), учитывает сегменты/запятые; service matcher пропускает multi hours+price/duration; длительности берутся из `services_catalog.duration_text`.
- Цена/длительность выдаются только при явном `service_query` (intent_decomp или semantic_match); иначе — уточнение. В decision_meta/decision_trace пишутся `service_query`, `service_query_source`, `service_query_score`.
- Ambiguous price/duration → clarify (не отвечаем ценой при неуверенном типе).
- Booking gate блокирует инфо‑вопросы (pricing/hours/duration) без явного booking; сплит сегментов по ,;?!.; service slot только через semantic matcher, datetime — токен; trace/meta `booking_blocked_reason`. (нужен деплой)
- Booking: при expected_reply_type=time service‑вопросы (presence/price/duration) отвечаются по факту без роста clarify; service_query сохраняется в booking_context, дальше prompt времени.
- Live-check 2025-12-31: booking‑prompt + “маникюр делаете?” → price reply + повтор времени, clarify_attempt не растёт (commit 854b4f9).
- Context Manager: `current_goal` (info/consult/booking), `refusal_flags` (name/phone, TTL 10 сообщений), `clarify_attempts` (>=2 → эскалация), `compact_summary` (детерминированно; триггеры: intent_change/clarify_limit/12+ сообщений); всё пишется в decision_meta/trace.
- Intent Queue + Question Contract: `conversation.context.intent_queue` и `conversation.context.expected_reply_type` в webhook, чтобы держать очередь интентов и ожидаемый тип ответа.
- Booking + 2+ info (или total 3+) → defer booking, отвечаем на 1–2 info (service_query: price+duration; иначе location+hours), остаток в intent_queue, expected_reply_type=intent_choice.
- Standalone info-ответы (price/duration/hours/location) получают CTA "Хотите записаться?" только в bot_active без followup/booking-prompt; skip non-bot-active + если ответ уже про запись; EVAL E003l/E003m/E014d, negative E039b; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS.
- Soft price defense: `why_price_from`/`objection_price` реализованы в demo_salon knowledge + покрыты EVAL; SPECS/CONSULTANT.md Rule 4 синхронизирован (частично реализовано + мягкая защита цены). Tests: не запускались (doc sync). Evidence: `truffles-api/app/services/demo_salon_knowledge.py:2045-2053`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml:162-216`, `SPECS/CONSULTANT.md:209-248`.
- Night tone/timezone: `salon.timezone` в client_pack (Asia/Almaty) + quiet-hours notice использует локальное время и salon hours (open/close) в коде; исключения pending/manager_active + LAW/opt-out/OOD; EVAL `E014e/E014f`; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS (commit `8b08a71b985c458f388f3d6686b75a5431c6ec92`). Spec gap: SPECS/CONSULTANT.md задаёт фиксированное окно 22:00–09:00 → нужно решение (выровнять spec или код). Evidence: `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml:1-25`, `truffles-api/app/services/demo_salon_knowledge.py:161-188`, `truffles-api/app/routers/webhook.py:4386-4408`, `SPECS/CONSULTANT.md:162-166`.
- Doc sync (soft price defense + quiet hours): Rule 4 в SPECS/CONSULTANT.md отмечен как частично реализованный с мягкой защитой цены; quiet-hours правило в SPECS/CONSULTANT.md задаёт timezone‑source + окно 22:00–09:00, но код применяет “вне salon.hours” и при отсутствии timezone сейчас падает на UTC → нужен logic‑fix: skip, если timezone нет. Tests: not run (doc sync). Evidence: `SPECS/CONSULTANT.md:162-166`, `SPECS/CONSULTANT.md:209-248`, `truffles-api/app/services/demo_salon_knowledge.py:161-188`, `truffles-api/app/services/demo_salon_knowledge.py:2045-2053`, `truffles-api/app/knowledge/demo_salon/EVAL.yaml:162-216`.
- Quiet-hours fix: пропуск notice при отсутствующей/невалидной timezone (ZoneInfo) + подтверждённый деплой. CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20655575365 PASS; prod `/admin/version` git_commit `8a51d28b1a9932b302bca3626097dee751ccec3a`; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS. Evidence: `truffles-api/app/services/demo_salon_knowledge.py:116-181`.
- Agentic orchestration: закреплено, что “agentic” = логические роли стадий одного пайплайна `_handle_webhook_payload`, не отдельные рантайм‑агенты; роли сопоставлены с фактическим порядком стадий. Evidence: `SPECS/ARCHITECTURE.md:132-142`.
- E003m fix: сервисный матч больше не блокируется semantic question-type; guard проверяет явные сигналы hours/price/duration. Evidence: `truffles-api/app/services/demo_salon_knowledge.py:1912-1917`. CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20654965505 PASS; prod `/admin/version` git_commit `8b08a71b985c458f388f3d6686b75a5431c6ec92`; тест `docker exec -i truffles-api pytest /app/tests/test_demo_salon_eval.py -q` PASS.
- expected_reply_type=service_choice сохраняется при OOD/токсичности и возвращает к вопросу об услуге.
- expected_reply_type=service_choice при невалидном ответе без service/semantic/in-domain сигнала возвращает к вопросу об услуге (reason=invalid_choice).
- intent_choice: prefix/substring match по меткам очереди (>=4 символов); info-выбор отвечает и обновляет очередь, booking запускает booking-prompt; decision_meta пишет expected_reply_choice/intent_queue_remaining/expected_reply_next.
- Consult playbooks: `domain_pack.consult_playbooks` расширен (hair_aftercolor/hair_damage/hair_color_choice/nails_care/brows_lashes_care/sensitive_skin/style_reference/general_consult) с questions/options/next_step.

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
- Точка входа: `truffles-api/app/routers/webhook.py` → `_handle_webhook_payload()` + outbox coalesce.
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
- [ ] **Branch подключен частично** — выбор branch и запись `conversation.branch_id` есть в `webhook.py`, но Telegram per branch и RAG фильтры всё ещё по client → `SPECS/MULTI_TENANT.md`
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
| Kaspi Pay проверка | Автопроверка оплат | P2 | REQUIREMENTS |
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
- В `webhook.py` добавили `count_rate_limit` и выключили счётчик при `skip_persist=True` (outbox), чтобы лимиты не считались повторно.
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
   - Убрать client_slug if’ы из `webhook.py`.
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
- Встроили branch routing (by_instance/ask_user/hybrid) и remember_branch в `webhook.py`.
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
- В `webhook.py` и `message.py` OOD‑ответ только если strong OOD / intent=out_of_domain и **нет** уверенного RAG
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
- Задеплоили `webhook.py`, `message.py`, `intent_service.py` и перезапустили API.
- Добавили domain router config per-client (anchors + thresholds) в `clients.config`.
- Включили логирование domain scores через `DOMAIN_ROUTER_LOG_SCORES=1`.
- Перезалили `intent_service.py`, `webhook.py`, `message.py` и перезапустили API.

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

Ключевые файлы для отладки: `truffles-api/app/routers/webhook.py`, `truffles-api/app/routers/telegram_webhook.py`, `truffles-api/app/services/ai_service.py`, `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/services/state_service.py`, `ops/reset.sql`.

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
| `webhook.py` | Booking gate: info-вопросы распознаются по сегментам ?!.; блокировка очищает booking_state и отключает flow |
| `conversation.py` | Добавлен `context` (JSONB) для краткого контекста/слотов |
| `webhook.py` | Слот-филлинг записи + контекст диалога |
| `state_service.py` | Очистка контекста при resolve |
| `ops/reset.sql` | Сброс контекста при emergency reset |
| `reminder_service.py` | Авто‑закрытие handover + алерт “нет ответа” |
| `ai_service.py` | Возвращает `Result[Tuple[str, str]]` с confidence |
| `message.py` | Обработка low_confidence → эскалация |
| `webhook.py` | То же самое (ОБА файла обрабатывают сообщения!) |
| `learning_service.py` | СОЗДАН: `is_owner_response()`, `add_to_knowledge()` |
| `manager_message_service.py` | Добавлен вызов `add_to_knowledge()` для owner |
| `main.py` | Фоновый outbox worker (тик 2s, опционально через env) |
| `admin.py` | Outbox processing вынесен в общий хелпер |
| `webhook.py` | Добавлен `_process_outbox_rows()` для reuse в admin/worker |
| `schemas/telegram.py` | Добавлены `sender_chat`/`author_signature`, username у chat |
| `telegram_webhook.py` | sender_chat fallback для идентификации менеджера |
| `telegram_webhook.py` | unpin использует `handover.telegram_message_id` (fallback на callback message_id) |
| `manager_message_service.py` | Не затирает assigned_to при unknown, fallback на assigned_to для owner-check |
| `learning_service.py` | Owner match принимает отрицательные ID (sender_chat) |
| `message_service.py` | Выбор последнего содержательного user-сообщения для handover |
| `webhook.py` | human_request эскалируется с последним meaningful сообщением |
| `message.py` | То же поведение для `/message` |
| `webhook.py` | Decision engine (normalize → signals → resolve → action) + policy handler для truth gate |
| `webhook.py` | Валидация слотов записи (service/datetime/name) + запрет opt-out/фрустрации |
| `config.py` | Settings: игнорировать лишние env-поля (запуск тестов в окружении с .env) |
| `truffles-api/tests/test_cases.json` | Добавлены автоматизируемые кейсы для golden-прогона |
| `tests/test_message_endpoint.py` | Автотесты golden-cases (decision/signals) |
| `schemas/telegram.py` | Перевёл Pydantic Config на ConfigDict (убрал депрекейшн) |
| `demo_salon_knowledge.py` | Фикс ложной payment-эскалации: короткие ключи/фразы → word-boundary |
| `EVAL.yaml` | Добавлен кейс “какие услуги” для services_overview |
| `webhook.py` | Fast-intent: короткий путь (phrase/truth) до LLM |
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
| `webhook.py` | Запись decision_meta в metadata user-сообщений (fast_intent/LLM) |
| `admin.py` | Новый /admin/metrics (читает дневные метрики) |
| `ops/migrations/015_add_metrics_daily.sql` | Таблица дневных метрик SLA/LLM/эскалаций |
| `ops/metrics_daily_snapshot.sql` | SQL snapshot метрик по дню/клиенту |
| `truffles-api/tests/test_cases.json` | Добавлены fast_intent golden cases |
| `tests/test_message_endpoint.py` | Тесты fast_intent + LLM fallback |
| `.env.example` | Добавлены FAST_MODEL/SLOW_MODEL + таймауты |
| `webhook.py` | Outbox skip_persist пишет decision_meta (message_id/created_at fallback), messageId добавляется в payload |
| `demo_salon_knowledge.py` | Часы работы распознаются шире, “сколько” не триггерит прайс без price-сигнала |
| `EVAL.yaml` | Кейс “Во сколько вы открываетесь в будни?” → hours |
| `truffles-api/tests/test_cases.json` | Golden‑кейс для hours (fast_intent) |
| `ai_service.py` | LLM timeout default поднят до 6s |
| `intent_service.py` | Domain router: подсчёт hit‑якорей + strict in‑anchors для OOD override |
| `webhook.py` | OOD override по anchor hit + OOD проверка до style_reference; decision_trace/logs расширены |
| `ops/update_instance_demo.sql` | anchors_in/out расширены, добавлен anchors_in_strict + “кошачий глаз” |
| `tests/test_message_endpoint.py` | Demo domain_router config обновлён (anchors_in/out + strict) |
| `truffles-api/tests/test_cases.json` | Кейсы OOD/style/“кошачий глаз” для domain_router и fast_intent |
| `webhook.py` | Порядок гейтов обновлён: было policy/truth → booking → fast_intent → intent/domain → LLM; стало pending/opt-out/policy escalation → OOD (strong anchors) → booking guard/flow → LLM-first → truth gate fallback |
| `webhook.py` | LLM guard: темы оплат/медиц/жалоб/скидок/возвратов → эскалация + decision_meta `llm_primary_used` |
| `webhook.py` | Fast-intent теперь только smalltalk (greeting/thanks/ok), booking slang "маник" добавлен в keywords |
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
| `webhook.py` | Service matcher в LLM-first до LLM, source=service_matcher |
| `tests/test_message_endpoint.py` | Тест: service matcher шортсёркит LLM |
| `EVAL.yaml` | Кейсы: педикюр/массаж ног/адрес |
| `ai_service.py` | ASR default provider: ElevenLabs scribe_v1, fallback whisper-1 |
| `webhook.py` | ASR primary default aligned to ElevenLabs (scribe_v1) |

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

### 2026-01-02 — Fix: booking+info под coalesce (multi-intent)

**Что сделали:**
- Batch non‑booking selection игнорирует semantic service hints → "парковка есть?" не фильтруется как booking.
- Live‑check: info‑ответ + booking‑prompt в одном ответе; expected_reply_type=time; trace booking_interrupt + truth_gate.
- CI/деплой/pytest PASS; allowlist снят после успеха.

**Evidence:**
- Code: `truffles-api/app/routers/webhook.py` (allow_service flag + selection).
- CI: https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/20658445278 (commit 7b971713b4863094ce39910f03c5e60e97688b16).
- Prod: `/admin/version` commit 7b971713b4863094ce39910f03c5e60e97688b16.
- Live‑check: conversation `99306198-1ecf-44d6-9066-72bb4e76e915`, decision_meta.booking_info_interrupt=true.

*Последнее обновление: 2026-01-02 (Evidence: CI 20658445278 + /admin/version + live-check)*
