#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
audit_doc="$repo_root/docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md"
shell_file="$repo_root/console-web/src/components/ConsoleShell.tsx"
rbac_file="$repo_root/console-web/src/lib/api-client.ts"
settings_file="$repo_root/console-web/src/app/settings/page.tsx"

if [[ ! -f "$audit_doc" ]]; then
  echo "doc-truth: SKIP (missing $audit_doc)"
  exit 0
fi

has_errors=0

function fail_claim() {
  local message="$1"
  echo "doc-truth: ERROR: $message" >&2
  has_errors=1
}

# Fact 1: Integrations nav item exists in Console shell.
if rg -q 'nav-integrations|label:\s*"Интеграции"' "$shell_file"; then
  if rg -n 'Integrations.*отсутств|отсутствует в навигации' "$audit_doc" >/dev/null; then
    fail_claim "audit doc still claims Integrations is missing while nav item exists"
  fi
fi

# Fact 2: Support has read-only provisioning surface in settings.
if rg -q 'canAccessConsole\(role,\s*"provisioning",\s*"read"\)' "$settings_file"; then
  if rg -n 'Support read.?only provisioning отсутствует|Settings недоступны support' "$audit_doc" >/dev/null; then
    fail_claim "audit doc still claims support provisioning is unavailable while settings gate allows provisioning:read"
  fi
fi

# Fact 3: Manager has Team read access in RBAC.
if rg -q 'team:\s*\{' "$rbac_file" && rg -q 'read:\s*\[[^]]*"manager"' "$rbac_file"; then
  if rg -n 'Team скрыт для manager|\[missing\].*Team directory.*manager' "$audit_doc" >/dev/null; then
    fail_claim "audit doc still claims manager team directory is missing while RBAC grants team:read"
  fi
fi

if [[ "$has_errors" -ne 0 ]]; then
  exit 1
fi

echo "doc-truth: OK"
