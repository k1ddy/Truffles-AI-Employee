# Page: Knowledge Studio

Route
- `/knowledge`

UI entry points
- `console-web/src/app/knowledge/page.tsx`

Roles
- Read: platform_admin, owner, admin, manager.
- Write (validate/publish/rollback): platform_admin, owner, admin.

Branch gate
- If the current branch context is missing or invalid, a branch selection gate is shown.
- Uses localStorage `console:branch_id` and refetches `/console/v1/me` after selection.

Flow (steps)
- Draft → Validate → Preview → Publish → History → Rollback.
- Step list in the left rail; content on the right.

Key UI elements
- Draft
  - Textarea for YAML/JSON draft.
  - "Загрузить current в draft" button.
- Validate
  - "Запустить валидацию" button.
  - Errors and warnings lists; warns if draft changed after validate.
- Preview
  - Diff view if validation returned diff; otherwise Current vs Draft panels.
- Publish
  - Status checklist (validation, warnings, draft dirty).
  - Warning acknowledgment checkbox.
  - "Опубликовать" button.
- History
  - List of versions with radio selection.
- Rollback
  - Requires selected version.
  - "Выполнить rollback" button opens confirmation modal.
  - Confirmation modal requires reason and calls confirmation + rollback.

API endpoints used
- Current: `GET /console/v1/knowledge/current`.
- Validate: `POST /console/v1/knowledge/validate`.
- Publish: `POST /console/v1/knowledge/publish`.
- History: `GET /console/v1/knowledge/history`.
- Rollback: `POST /console/v1/knowledge/rollback`.
- Confirmation: `POST /console/v1/confirmations` (action `knowledge_rollback`).

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_knowledge_current`, `validate_knowledge`, `publish_knowledge`, `list_knowledge_history`, `rollback_knowledge`.
- Confirmation guard: `app/services/console_confirmations.py`.

Data sources
- `knowledge_versions` (history, rollback).
- `client_settings`, `branches` (knowledge_tag, branch scope).
- Pack compiler services: `knowledge_registry_service`, `pack_compiler_service`.

System interactions
- Publish triggers pack validation + Qdrant sync (`sync_qdrant_from_pack`).
- Rollback requires confirmation ID; recorded in audit.

Related code
- UI: `console-web/src/app/knowledge/page.tsx`.
- Backend: `truffles-api/app/routers/console.py` (knowledge endpoints).
