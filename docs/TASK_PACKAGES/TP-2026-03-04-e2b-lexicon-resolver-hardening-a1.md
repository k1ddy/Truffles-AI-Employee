# TP-2026-03-04-e2b-lexicon-resolver-hardening-a1

## Block identity
- `BLOCK_ID`: `E2b`
- `PARENT_BLOCK_ID`: `TP-2026-02-19-llm-first-firebreak-program`
- `DEPENDS_ON`: `TP-2026-03-04-e2a-interrupt-arbitration-owner-a1`
- `UNLOCKS`: `E2c` canonical replay/canary on firebreak fingerprint

## Название/цель
Закрыть языковой остаток после E2a: повысить детекцию info/master interrupt в реальных формулировках (`по цене`, `к специалисту`, `к мастеру`, `выбрать мастера`) без semantic hardcode в core-ветках.

## Canon refs
- `AGENTS.md`
- `STATE.md` (E2 in progress + E2a done with residual E2b)
- `STRATEGY/REQUIREMENTS.md` (`Interrupt lexicon robustness`, `Booking/info interrupt contract`)
- `docs/TASK_PACKAGES/TP-2026-03-04-e2a-interrupt-arbitration-owner-a1.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
  - `truffles-api/app/services/demo_salon_knowledge.py`
  - `truffles-api/app/services/pack_runtime_neutral_adapter.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_pack_runtime_service.py`
- `Baseline commands`:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "policy_collect_interrupt_arbitration_rewrites_question_like_master_signal"`
- `FACT findings`:
  - `price_keywords` не покрывают форму `по цене`/`цене` в `SYSTEM_LEXICONS.yaml`.
  - `_has_price_signal` в адаптерах в первую очередь опирается на lexicon hit; inflection misses остаются.
  - `resolve_master_intent` explicit=true only for direct_signal/person+action; phrasing типа `к специалисту` нуждается в direct-term coverage.
- `Detected drift (docs vs code)`: `none`.

## One web search (mandatory before implementation)
- **Query (exact):** `spaCy Russian lemmatization model official docs`
- **Date/time (local):** `2026-03-04 10:33, Asia/Almaty`
- **Why this query is precise:** Нужна проверка готового production-grade подхода к морфологии RU перед решением `reuse/integrate/build`.
- **Sources opened (from this query):**
  - spaCy API docs: `Lemmatizer` — https://spacy.io/api/lemmatizer
  - spaCy Russian models (official docs mirror) — https://nightly.spacy.io/models/ru
- **Existing solutions found:** Лемматизация через NLP pipeline (spaCy + ru model/lookups).
- **Decision:** `build` (lightweight deterministic hardening in existing lexicon/signal layer), без нового NLP runtime dependency.
- **Rejected options:**
  - full NLP lemmatizer dependency in core runtime path: повышает latency/ops complexity, не нужен для целевого E2b класса дефектов.
- **Open questions:** `none`.

## Root cause (mandatory)
- **Symptom:** E2 runtime failures показывают `info_section_miss` на price/master interrupts (`по цене`, `к специалисту`).
- **Minimal reproduction:**
  - `LLM-QUAL-booking-lock-20260304-firebreak-e2-a1-r13-008-03-100de8` (`У меня есть вопросы по цене.`)
  - `LLM-QUAL-booking-lock-20260304-firebreak-e2-a1-r13-004-13-52edaf` (`Как можно записаться к специалисту?`)
- **Evidence to capture:** deterministic helper tests (`_has_price_signal`, `resolve_master_intent`, arbitration refs) + existing endpoint tests.
- **Five Whys (or equivalent):**
  1. Why miss on `по цене`? Lexicon uses base forms (`цена`, `стоимость`) and misses common inflections.
  2. Why miss matters? E2a arbitration depends on detected info refs to rewrite collect->info.
  3. Why master phrase still risky? `resolve_master_intent` explicit path depends on direct-term/combined signal forms.
  4. Why not handled by LLM alone? deterministic boundary still needs robust signal extraction for stable contracts.
  5. Why systemic? Same signals reused across adapters/tenants, so misses repeat across flows.
- **Root cause statement:** Недостаточное морфологическое покрытие в deterministic signal layer (`price/master`), causing missed info refs before contract arbitration.
- **Fix mechanism:** Расширить lexicon + добавить lightweight regex fallback для price inflections + расширить master direct terms.

## Reuse-first plan (mandatory)
- **Internal reuse:** existing `SYSTEM_LEXICONS`, `_has_price_signal` adapter hooks, `resolve_master_intent` contract.
- **External reuse:** исследован spaCy lemmatizer pattern, не интегрируем.
- **Why not reinvent the wheel:** изменение ограничено контрактным signal layer без новых runtime систем.

## Invariant
- Не менять action contract (FACT/COLLECT/HANDOFF) и не вводить semantic hardcode в core decision branches.

## Scope
- Lexicon hardening for `price/master`.
- Adapter-level price inflection fallback.
- Deterministic tests proving new coverage.

## Out of scope
- Runtime acceptance replay/canary (`E2c`).
- Heavy NLP dependency integration.

## Touch-list
- `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `STATE.md`

## Plan (1..N)
1. Expand `price_keywords` and `master_query_direct_terms` lexicons with high-frequency phrase forms.
2. Add deterministic regex fallback for RU price inflections in adapters.
3. Add tests for price morphology + master booking phrase detection/arbitration.
4. Run targeted pytest + ruff.
5. Update `STATE.md` with evidence + residual debt.

## DoD
- `по цене` is detected as `pricing` in deterministic signal path.
- `к специалисту/к мастеру` triggers master-intent signal path for arbitration.
- New tests green; no lint regressions.

## Checks
- `pytest -q truffles-api/tests/test_pack_runtime_service.py -k "price_signal or master_intent"`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "policy_collect_interrupt_arbitration_rewrites_price_question_to_info or policy_collect_interrupt_arbitration_rewrites_question_like_master_signal"`
- `ruff check truffles-api/app/services/demo_salon_knowledge.py truffles-api/app/services/pack_runtime_neutral_adapter.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_message_endpoint.py`

## Evidence
- Deterministic test outputs.
- Git diff on listed touch files.
- STATE update with explicit residuals.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` (deterministic only in this block).
- **Fail-fast / scenario lock:** targeted `-k` subsets.
- **Stop condition:** 2 iterations without new failing assertion -> stop and reopen RCA.
- **Escalation path:** Brain/Top Architect for acceptance replay expansion.

## Release safety (mandatory for non-doc changes)
- **Strategy:** incremental deterministic hardening inside existing signal boundaries.
- **Go/no-go signals:** targeted deterministic tests + lint.
- **Rollback:** revert E2b commit.
- **Post-release monitoring window:** E2c replay/canary on same lock fingerprint.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
- `Drift closeout rule`:
  - if E2c not run in this block, keep E2 open with explicit next-block contract.

## Rollback
- `git revert <E2b-commit>`.

## No-go
- No regex/phrase branching in core decision routing as semantic owner replacement.
- No acceptance gate relaxation.

## Risks/Blockers
- Over-broad price stem may increase false positives.
- Lexicon-only updates may be insufficient for future multilingual tails.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: canonical runtime replay/canary evidence not produced here.
- `Why not in this block`: E2b is deterministic hardening slice.
- `Risk if deferred`: integration regressions may remain hidden until replay.
- `Linked follow-up Task Package(s)`: `TP-2026-03-04-e2c-canonical-replay-canary-a1` (to be created).
- `Expiry/trigger to stop deferral`: before claiming E2 closure in STATE/program TP.

## Next-block contract (mandatory)
- `Next block objective`: execute E2c guarded replay/canary and verify blockers removed on current fingerprint.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking_info_interrupt or policy_collect_interrupt_arbitration"`
- `Blocked-by conditions`: E2b deterministic suite green.
- `Owner role for closure`: `Hands` implementation, `Brain/Top Architect` acceptance.

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `SYSTEM_LEXICONS.yaml` then adapter `_has_price_signal`.
- `Do not touch`: acceptance chain/gates in `ops/diagnose.py`.
- `Open risks`: price false-positives.
- `First command to verify`: `pytest -q truffles-api/tests/test_pack_runtime_service.py -k "price_signal"`
