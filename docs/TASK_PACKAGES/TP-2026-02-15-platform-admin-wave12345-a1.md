Название/цель:
- Platform Admin Control Loop (1-5): запустить устойчивый цикл fact-first аудита, приоритизации, реализации, снижения сложности и KPI anti-drift для Console Plane.

Canon refs:
- AGENTS.md (Task Package, one-issue flow, stop-the-line, fitness)
- STATE.md NOW + docs/CONSOLE_AUDIT/UX_BACKLOG.md (UX-08..UX-12)
- docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md

Invariant:
- Не менять backend API contracts/RBAC semantics.
- Не ломать selection gate и tenant isolation.
- Любые изменения должны иметь проверку и evidence.

Scope:
- Fact-first audit артефакт для Platform Admin (runtime + code complexity + UX friction).
- Приоритизация (P0/P1/P2) с wave roadmap.
- Реализация минимум одного улучшения, улучшающего reliability/maintainability.
- Снижение сложности QA-контура (разгрузка smoke concentration).
- KPI anti-drift артефакт (snapshot + repeatable command).
- Follow-up wave `1+2`: outbox recovery threshold guard + UX validation recovery clarity (inline hints вместо toast-only в Platform Admin pages).

Out of scope:
- Изменение бизнес-политик и backend workflow state machine.
- Полная декомпозиция всех больших страниц в одном PR.

Touch-list:
- docs/CONSOLE_AUDIT/UX_BACKLOG.md
- docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md
- docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md
- docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md
- console-web/e2e/smoke.spec.ts
- console-web/e2e/platform-admin-*.spec.ts (new, if needed)
- console-web/package.json (scripts, if needed)
- console-web/src/app/tenants/page.tsx
- console-web/src/app/company-workspace/page.tsx
- ops/console_platform_admin_kpi_snapshot.py (new)
- docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md (new)
- docs/SESSIONS/SESSION-2026-02-15-platform-admin-wave12345-a1.md
- docs/SESSION_INDEX.md

Plan:
1) Собрать факт-срез: live health/version + текущие code metrics (LOC, error-surface, test concentration).
2) Обновить baseline report/backlog с severity и 30-day waves.
3) Реализовать reliability/maintainability improvement: снизить smoke concentration (route-focused suite extraction + scripts).
4) Добавить KPI snapshot tool + runbook для weekly anti-drift цикла.
5) Прогнать проверки (lint/build/tests), собрать evidence, открыть PR.

DoD:
- Есть обновленный фактовый report и backlog с P0/P1/P2 и actionable waves.
- Реализовано снижение QA complexity (smoke concentration reduced by extraction or equivalent measurable split).
- Есть repeatable KPI snapshot command + artifact format.
- Outbox guard поддерживает warning/critical thresholds + fail-fast exit для control-loop.
- Валидационные ошибки Platform Admin страниц сохраняются в inline summary (не только toast).
- Локальные проверки зелёные.

Checks:
- npm --prefix console-web run lint
- npm --prefix console-web run build
- npm --prefix console-web exec -- playwright test --list
- python3 ops/console_platform_admin_kpi_snapshot.py --help (and one dry run if network/env allows)
- python3 ops/console_platform_admin_kpi_snapshot.py --fail-on-breach --fail-level critical --pretty --output /tmp/platform_admin_kpi_gate.json

Evidence:
- PR URL + commit SHA
- lint/build/test outputs
- runtime snapshot outputs (health/version)
- generated KPI snapshot artifact path
- diff stat

Rollback:
- Revert PR merge commit.

No-go:
- Не подменять evidence вручную.
- Не подгонять логику под тест без контрактного обоснования.
- Не добавлять broad unsafe shortcuts в e2e.

Риски/блокеры:
- e2e может быть нестабилен из-за auth/storage state drift.
- live endpoints могут быть недоступны в момент run.

Branch / Worktree / Base / Merge / Cleanup:
- Branch: feat/2026-02-15-platform-admin-wave12345-a1
- Worktree: /home/zhan/worktrees/2026-02-15-platform-admin-wave12345-a1
- Base ref: origin/main
- Merge policy: PR to main after green local checks and CI
- Cleanup: remove worktree/branch post-merge by Brain/Top Architect
