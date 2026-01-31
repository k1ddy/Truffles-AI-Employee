# Task Package: Console media upload + send (photo/audio/document)

Title/Goal
- Add console media upload + send for photo/audio/document (video forbidden), reusing the signed URL + outbox media pipeline and Telegram echo.

Canon refs
- AGENTS.md
- STATE.md (add GAP: "Console media upload/send missing")
- docs/CONSOLE_GUIDE.md
- SPECS/ARCHITECTURE.md
- SPECS/ESCALATION.md
- SPECS/SYSTEM_REFERENCE.md
- contracts/console_api/openapi.v1.yaml
- contracts/integrations/media_send.v1.jsonschema

Invariant
- Media async send + signed URL + TTL must remain intact.
- Outbox idempotency stays enforced (no duplicate sends).
- Console router remains thin (no orchestration in entrypoints).
- Video remains forbidden from Console.

Scope
- Backend: console endpoint for media upload + send, store to /home/zhan/truffles-media, build signed URL, enqueue outbox media (or direct send when outbox disabled), Telegram echo.
- Frontend: add file upload in Inbox composer, send multipart, show attachment metadata in chat.
- Contract: OpenAPI update + regenerated types.
- Tests: add console media coverage (allowlist + video rejection + outbox payload).

Out of scope
- Inbound media policy changes.
- Provider Gateway refactors.
- Video support.
- Any DB schema changes.

Touch-list
- truffles-api/app/routers/console.py
- truffles-api/app/schemas/console.py
- truffles-api/app/services/manager_message_service.py (reuse or extract helper)
- truffles-api/app/services/chatflow_service.py (signed URL helper)
- truffles-api/app/routers/webhook/media.py (Telegram media helper reuse)
- truffles-api/tests/test_console_media.py (new)
- contracts/console_api/openapi.v1.yaml
- console-web/src/components/ChatInterface.tsx
- console-web/src/components/CaseConversation.tsx (if rendering attachment preview)
- console-web/src/app/api/proxy/[...path]/route.ts
- console-web/src/lib/api.ts
- console-web/src/types/api.generated.ts (regen)
- docs/CONSOLE_GUIDE.md
- docs/TASK_PACKAGES/TP-2026-01-31-console-media-sync.md

Plan
1) Add backend console media endpoint (multipart), validate allowlist (photo/audio/document), reject video.
2) Store media, build signed URL, save message metadata, enqueue outbox media (or direct send if outbox disabled), echo to Telegram.
3) Update schemas + OpenAPI for console media request/response and error codes.
4) Update console-web to upload media via FormData and display attachment metadata in chat.
5) Add tests, regenerate types, run lint/tests, capture evidence.

DoD
- Console uploads and sends photo/audio/document.
- Video is rejected with clear error code/message.
- Message metadata contains media info + signed URL (TTL).
- Outbox event enqueued when OUTBOX_WORKER_ENABLED=1; direct send otherwise.
- Telegram topic shows console media echo.
- Tests and lint pass; OpenAPI/types synced.

Checks
- pytest -q truffles-api/tests/test_console_media.py
- npm --prefix console-web run generate:api
- npm --prefix console-web run lint

Evidence
- /tmp/console_media_pytest_20260131.txt
- /tmp/console_web_generate_api_20260131.txt
- /tmp/console_web_lint_console_media_20260131.txt
- Console media event sample (outbox payload or log snippet)
- STATE.md updated by Brain/Top Architect with evidence

Rollback
- git revert COMMIT_SHA

No-go
- Enabling video from Console.
- Sending media without signed URL + TTL.
- Bypassing outbox idempotency.
- Orchestration in console router.

Branch
- feat/2026-01-31-console-media-sync-a1

Worktree path
- /home/zhan/worktrees/2026-01-31-console-media-sync-a1

Base ref
- origin/main

Merge policy
- PR to main, no rebase.

Cleanup
- scripts/session_end.sh; remove worktree/branch after merge.

Risks/Blockers
- console proxy currently forces JSON; must allow multipart for upload.
- ChatFlow media API requires caption for image/document; ensure non-empty caption fallback.
- MEDIA_SIGNING_SECRET and PUBLIC_BASE_URL must be configured for signed URL delivery.
