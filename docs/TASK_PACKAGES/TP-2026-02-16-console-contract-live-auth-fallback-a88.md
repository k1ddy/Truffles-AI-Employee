# TP-2026-02-16 Console Contract Live Auth Fallback (a88)

## Название/цель
Устранить падение `console-contract-live` на main CI, когда токен по `CONSOLE_KEYCLOAK_*` не проходит `/console/v1/me` (401), хотя есть валидные `CONSOLE_E2E_*` креды.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `TECH.md`
- failing run: `https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/22078873597`

## Invariant
- `console-contract-live` остаётся обязательной post-deploy проверкой.
- Не отключаем job и не переводим его в unconditional skip.
- `deploy`, `core-eval`, `ci-livecheck` не изменяются.

## Scope
- `console-contract-live` job в `.github/workflows/ci.yml`:
  - добавить fallback creds `CONSOLE_E2E_USERNAME/PASSWORD`;
  - выбирать token-кандидат через probe `/console/v1/me`;
  - сохранять `SCHEMATHESIS_TOKEN_SOURCE` для прозрачной диагностики.

## Out of scope
- Изменения runtime API/роутеров.
- Изменения секретов в GitHub.
- Изменения livecheck suites.

## Touch-list
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-02-16-console-contract-live-auth-fallback-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-console-contract-live-auth-fallback-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Патч auth fallback в `console-contract-live`.
2. Проверка YAML + sanity bash condition.
3. PR и проверка `console-contract-live` на green.

## DoD
- `console-contract-live` больше не падает на 401 `/me`, если primary creds невалидны, но e2e creds валидны.
- YAML валиден, shell guard корректен.
- Есть session artifacts для session-gate.

## Checks
- `python3 - <<'PY' ... yaml.safe_load('.github/workflows/ci.yml') ... PY`
- bash sanity для guard-условия (truth table)
- `gh pr checks` после открытия PR

## Evidence
- run URL с ошибкой + строка `Resolve console selection headers` 401
- commit/PR URL
- новый CI run URL с green `console-contract-live`

## Rollback
- `git revert SHA_OF_FIX_COMMIT` для отката patch `.github/workflows/ci.yml`.

## No-go
- Не скрывать ошибку через отключение `console-contract-live`.
- Не трогать другие jobs без необходимости.

## Риски/блокеры
- Если и primary, и e2e creds невалидны/без доступа, job останется красным (ожидаемо и правильно).
