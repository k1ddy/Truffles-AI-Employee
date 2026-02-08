# TP-2026-02-08-instance-routing-alias-a17

- Название/цель: Восстановить стабильную доставку `demo_salon` при drift `instanceId` (`client_id` в base64 payload меняется), не ломая strict tenant-guards и outbox idempotency.
- Canon refs: `AGENTS.md` (Fitness P0-4/P0-5/P1-7/P1-8), `STATE.md` (instance drift/Unknown instanceId в `demo_salon`, секции с `instance_drift=true` и live webhook failures), `SPECS/SYSTEM_REFERENCE.md` (Fast Debug SOP / live-check evidence).

- Invariant:
  - Не ослаблять tenant safety: cross-tenant события не должны маршрутизироваться.
  - Outbound должен оставаться deterministic/idempotent и не уходить в ложный `SENT`.
  - `decision_meta/trace` сохраняются на ранних возвратах.

- Scope:
  - Нормализация branch routing по `instanceId` с безопасным alias-match (same `uid`, different `client_id`).
  - Целевые тесты preflight/branch routing.
  - Runtime data fix для `demo_salon` (`branch.instance_id` -> рабочее canonical значение) без изменения бизнес-логики.

- Out of scope:
  - Изменение ChatFlow/WhatsApp внешней инфраструктуры.
  - Изменение LLM/policy/booking-flow.
  - Большой архитектурный рефактор webhook pipeline.

- Touch-list (файлы/таблицы):
  - `truffles-api/app/routers/webhook/http.py`
  - `truffles-api/app/routers/webhook/branch_selection.py`
  - `truffles-api/app/routers/webhook/instance_routing.py` (new helper, если нужен)
  - `truffles-api/tests/test_branch_routing_instance.py`
  - DB table: `branches` (`instance_id` only for `demo_salon/main`, one-row data fix)

- Plan (1..N):
  1. Подтвердить текущий failure path по логам/SQL (`Unknown instanceId` + outbound payload failure).
  2. Добавить безопасный resolver `instanceId`: exact match, затем alias-match по decoded `uid` с защитой от ambiguous matches.
  3. Встроить resolver в preflight и branch selection gate.
  4. Добавить/обновить тесты на alias-match и неизвестный/ambiguous instance.
  5. Применить runtime data fix `branch.instance_id` в canonical значение, которое подтвержденно отправляет outbound.
  6. Прогнать целевые pytest + `ops/diagnose.py explain` evidence.

- DoD:
  - Inbound с alias `instanceId` не получает `Unknown instanceId`, создаёт inbound row.
  - Outbound для `demo_salon` уходит через canonical instance и получает `SENT` на smoke check.
  - Все добавленные/изменённые тесты PASS.
  - Нет regressions по tenant mismatch guard.

- Checks:
  - `pytest -q truffles-api/tests/test_branch_routing_instance.py`
  - `pytest -q truffles-api/tests/test_provider_gateway_integration.py -k tenant`
  - `python3 ops/diagnose.py explain --client-slug demo_salon --receiver-phone 77015705555 --text test123 --minutes 60 --limit 5`
  - SQL evidence (`messages`, `outbox_messages`, `branches`) через `docker exec ... psql ...`

- Evidence:
  - Логи `truffles-traefik`/`truffles-outbox` с timestamp и instanceId.
  - SQL snapshot до/после (`branches.instance_id`, inbound row, outbox status).
  - Output pytest команд.
  - Обновление в `STATE.md` делает Brain/Top Architect до merge (если поведенческое изменение подтверждено).

- Rollback:
  - Откат git-коммита.
  - Вернуть прежний `branch.instance_id` SQL update по зафиксированному значению.
  - Повторный smoke-check `ops/diagnose.py explain`.

- No-go:
  - Не отключать strict tenant checks.
  - Не делать broad fallback “любой instance -> любой branch”.
  - Не править LLM quality/simulation logic в рамках этой задачи.
  - Не редактировать БД/trace для “красивого evidence”.

- Риски/блокеры:
  - Если alias UID совпадает у нескольких branch, resolver должен отказать (ambiguous) и поднять trace reason.
  - Если ChatFlow токен не валиден для canonical instance, потребуются внешние credential изменения (вне scope кода).
