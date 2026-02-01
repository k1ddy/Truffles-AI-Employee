# TP-2026-02-01-pack-compiler-implementation

- Название/цель: Реализовать Pack‑Compiler + Policy/Signal DSL и перевести runtime на compiled artifacts; подготовить auto‑ingest approval flow и доказательства (golden eval + chaos‑sim + shadow replay по trace/meta).
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC‑019), `STATE.md` (NOW/PLAN), `STRATEGY/REQUIREMENTS.md`, `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `SPECS/ACTIVE_LEARNING.md`.
- Invariant: порядок стадий и intent/trace‑контракт неизменны; `_legacy.py` adapter‑only; факты только из packs/tools; trace/meta обязательны; LLM pack‑ref‑only; никаких бизнес‑лексиконов в коде.
- Scope:
  - Pack‑Compiler: компиляция packs → deterministic artifacts (pack‑index + signal graph + policy bundles) + hash/version/compiled_at.
  - Policy/Signal DSL: schemas + compile‑time validation + contract tests.
  - Runtime consumption: только compiled artifacts; raw packs не читаем (fallback запрещён без явного waiver).
  - Auto‑ingest: backlog/handovers → candidate cases → approval → packs → compiler publish.
  - Tests/evidence: golden eval + chaos‑sim + shadow replay (decision_meta/trace сравнение).
- Out of scope: смена порядка стадий, новые провайдеры/каналы/LLM, массовая миграция прод‑данных без DEC, прод‑роллаут без отдельного DoD.
- Touch-list:
  - `truffles-api/app/services/knowledge_registry_service.py`
  - `truffles-api/app/services/knowledge_snapshot_service.py`
  - `truffles-api/app/services/knowledge_validation.py`
  - `truffles-api/app/services/learning_service.py`
  - `truffles-api/app/services/pack_compiler_service.py` (new)
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/trace.py`
  - `truffles-api/app/knowledge/**`
  - `contracts/packs/**` (new)
  - `contracts/policy/**` (new)
  - `ops/shadow_replay.py` (new)
  - `truffles-api/tests/test_pack_compiler.py` (new)
  - `truffles-api/tests/test_policy_dsl.py` (new)
  - `truffles-api/tests/test_message_endpoint.py`
  - `docs/runbooks/CHAOS_SIM.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Plan:
  1) Инвентаризировать текущий pack‑index/Signal Snapshot pipeline и зафиксировать mapping → compiled artifacts.
  2) Реализовать compiler pipeline (inputs/outputs, deterministic hashing, storage, versioning).
  3) Добавить Policy/Signal DSL schemas + compile‑time validation + contract tests.
  4) Перевести runtime на compiled artifacts only; добавить guard/error при отсутствии compiled artifacts.
  5) Встроить auto‑ingest flow (candidate cases → approval → packs → compile publish).
  6) Добавить shadow‑replay tool + сравнение decision_meta/trace с baseline.
  7) Прогнать golden eval + chaos‑sim + shadow replay, зафиксировать evidence и обновить `STATE.md`.
- DoD:
  - Компилятор генерирует pack‑index + signal graph + policy bundles; hashes/version фиксируются и пишутся в decision_meta.
  - Runtime читает только compiled artifacts; raw packs не используются (без explicit waiver).
  - Policy/Signal DSL валидируется на compile, невалидные packs не публикуются.
  - Auto‑ingest создаёт кандидаты и требует approval до publish.
  - Golden eval + chaos‑sim + shadow replay проходят, сравнение по decision_meta/trace; CI зелёный.
- Checks:
  - `pytest -q truffles-api/tests/test_pack_compiler.py`
  - `pytest -q truffles-api/tests/test_policy_dsl.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot and pack_index"`
  - `EVAL_TIER=core pytest -q truffles-api/tests/test_demo_salon_eval.py::test_demo_salon_eval_cases`
  - `python3 ops/diagnose.py chaos-sim --count 5 --kinds booking --min-turns 10 --max-turns 12 --noise high --mode logic --skip-outbox --console-mode skip --sim-time "2026-01-24T12:00:00+06:00" --manager-mode skip --min-wait 0 --max-wait 0.2 --poll-timeout 6 --poll-interval 0.5 --dump-cases --output-dir /tmp/chaos_pack_compiler`
  - `python3 ops/shadow_replay.py --input /tmp/trace_bundle_pack_compiler.json --output /tmp/shadow_replay_pack_compiler.md`
- Evidence:
  - CI run URL + logs (`/tmp/pytest_pack_compiler_*.txt`, `/tmp/pytest_policy_dsl_*.txt`).
  - Golden eval/chaos‑sim artifacts (`/tmp/chaos_pack_compiler`, `/tmp/pytest_golden_eval_pack_compiler.txt`).
  - Shadow‑replay report (`/tmp/shadow_replay_pack_compiler.md`).
  - `STATE.md` entry with file paths and trace/meta diffs.
- Rollback: revert merge commit; redeploy предыдущий образ; удалить compiled artifacts только через rollback publish.
- No-go:
  - Чтение raw packs в runtime (кроме явного waiver).
  - Хардкод бизнес‑лексиконов/якорей в коде.
  - Изменение порядка стадий без DEC + snapshot‑test.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-01-pack-compiler-implementation-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-01-pack-compiler-implementation-a1`
  - Base: `origin/main` (после merge DEC‑019)
  - Merge: PR -> main
  - Cleanup: Top Architect
- Риски/блокеры: несоответствие существующих packs DSL/validation; отсутствие compiled artifacts для старых паков; производительность compile.
