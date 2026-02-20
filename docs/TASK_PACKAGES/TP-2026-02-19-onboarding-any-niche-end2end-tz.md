# TP-2026-02-19-onboarding-any-niche-end2end-tz

- Название/цель: Canonical end-to-end ТЗ по onboarding any-niche (beauty first) с последовательным закрытием этапов readiness -> go/no-go -> delivery -> reference normalization без хардкода и без ослабления fail-closed контрактов.
- Canon refs: `AGENTS.md`, `STATE.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`.
- Invariant:
  - Продуктовый контракт FACT/COLLECT/HANDOFF неизменен.
  - Go-live gate остаётся fail-closed.
  - Pack-first + policy/data-driven подход без client-specific ветвлений.
- Scope:
  - Этап 1: Ops acceptance contour + evidence.
  - Этап 2: Hard-gate rollout (shadow/canary/enforced).
  - Этап 3: Onboarding Blueprint contract (`required_fields_profile`, `readiness_weights`).
  - Этап 4: Delivery contour stabilization (reason-aware blockers + remediation actions).
  - Этап 5: Reference branch normalization (production-like scope для fleet метрик/attention).
- Out of scope:
  - Переписывание webhook/runtime orchestration.
  - Ручные SQL bypass для прохождения gate.
  - Большие архитектурные перестройки без DEC.

## Реализация по этапам (факт)

1) Этапы `1/2/3` закрыты:
- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-step123-a131.md`
- Report: `docs/REPORTS/2026-02-19-onboarding-any-niche-step123-a131.md`
- Verdict: PASS

2) Этап `4` закрыт:
- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-delivery-contour-step2-a131.md`
- Report: `docs/REPORTS/2026-02-19-onboarding-delivery-contour-step2-a131.md`
- Verdict: implemented (reason-aware delivery gates + ops diagnose contour)

3) Этап `5` закрыт:
- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-reference-branch-normalization-step3-a131.md`
- Report: `docs/REPORTS/2026-02-19-onboarding-reference-branch-normalization-step3-a131.md`
- Verdict: PASS

## Acceptance contract

- A) Contract acceptance: py_compile + ruff + targeted pytest + OpenAPI contract check.
- B) Runtime acceptance: scorecard/go-live gate/autopilot evidence (decision_meta/trace aligned).
- C) Ops acceptance: fleet-check + quality-smoke + pack-quality + delivery stabilize evidence.

## Rollback

- `git revert COMMIT_SHA` per concrete step commit.

## No-go

- Не ослаблять hard-gate для «зеленого» статуса.
- Не делать client-specific hardcode.
- Не подменять evidence ручной правкой БД/trace.
