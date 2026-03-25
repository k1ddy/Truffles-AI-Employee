# TP-2026-02-10 Console Contract Live Flake Hardening (a26)

## Название/цель
Устранить нестабильность и неинформативные падения шага `console-contract-live` в CI (`Schemathesis GET-only smoke`) после деплоя на `main`.

## Canon refs
- `AGENTS.md`
- `STATE.md` (CI/live-check NOW/GAP)
- `STRUCTURE.md`
- `TECH.md`
- `.github/workflows/ci.yml`
- `contracts/console_api/schemathesis.toml`

## Invariant
- Контрактная проверка Console API после deploy сохраняется.
- CI не теряет сигнал о реальных auth/infra проблемах.
- Не ослаблять security-gate за счёт silent-pass.

## Scope
- Стабилизировать `console-contract-live`:
  - убрать флейк from coverage-phase в GET smoke;
  - добавить fallback для `X-Client-Id` / `X-Branch-Id` из secrets;
  - добавить auth preflight с ясной ошибкой, если `/me` недоступен и fallback отсутствует;
  - поднять request timeout.

## Out of scope
- Изменения runtime API behavior.
- Изменения livecheck suites (`ci-livecheck`) и их бизнес-логики.
- Ротация секретов в GitHub.

## Touch-list
- `.github/workflows/ci.yml`

## Plan
1. Внести deterministic guardrails в `console-contract-live`.
2. Ограничить Schemathesis phases для smoke (без `coverage`).
3. Прогнать локальную валидацию workflow (`act`-style недоступен -> static lint/readback).
4. Открыть PR с root-cause и эффектом на CI.

## DoD
- `console-contract-live` больше не падает из-за coverage timeout на случайных GET параметрах.
- При невалидном токене ошибка явная и короткая (preflight), либо используются fallback IDs.
- Workflow YAML корректный, diff минимальный.

## Checks
- `python3 -m compileall truffles-api` (sanity, no runtime code regressions expected)
- `gh run view 21858724686 --job 63082686753 --log` (evidence baseline)
- `gh pr checks` (после PR)

## Evidence
- CI run URL (до/после)
- failed step + ключевые строки ошибки
- PR URL

## Rollback
- Revert commit с изменениями в `.github/workflows/ci.yml`.

## No-go
- Не менять контракты API/OpenAPI.
- Не отключать `console-contract-live` целиком.
- Не переводить failure в unconditional skip.

## Риски/блокеры
- Если секреты auth реально сломаны, preflight будет падать предсказуемо (это ожидаемо).
- Fallback headers требуют наличия соответствующих secrets для полной устойчивости.
