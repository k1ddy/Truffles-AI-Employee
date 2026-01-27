#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
hooks_dir="$repo_root/.githooks"

if [[ ! -d "$hooks_dir" ]]; then
  echo "ERROR: .githooks directory not found." >&2
  exit 1
fi

chmod +x "$hooks_dir/pre-commit" "$hooks_dir/pre-push"

git -C "$repo_root" config core.hooksPath ".githooks"

echo "Hooks installed: $hooks_dir"
