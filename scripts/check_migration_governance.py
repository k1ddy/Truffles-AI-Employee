#!/usr/bin/env python3
"""Migration governance guardrails for CI and local checks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STRICT_MIGRATION_NAME = re.compile(r"^(?P<prefix>\d{3})_[a-z0-9_]+\.sql$")

LEGACY_NON_STANDARD_FILENAMES = {
    "add_reminder_settings.sql",
}

LEGACY_DUPLICATE_PREFIXES = {
    "005": {
        "005_add_agent_memberships.sql",
        "005_add_conversations_branch_id_index.sql",
        "005_add_outbox_meta.sql",
    },
    "015": {
        "015_add_branch_onboarding_state.sql",
        "015_add_inbox_events.sql",
    },
}

FROZEN_OPS_MIGRATIONS = {
    "001_add_settings_and_escalations.sql",
    "002_create_learned_responses.sql",
    "003_add_escalation_reason.sql",
    "004_add_telegram_token.sql",
    "005_insert_demo_salon_settings.sql",
    "006_handover_messages.sql",
    "007_handover_assigned.sql",
    "008_topic_to_conversation.sql",
    "009_add_conversation_context.sql",
    "010_add_message_dedup.sql",
    "011_add_webhook_secret.sql",
    "012_add_outbox_messages.sql",
    "013_add_agents_and_learning_queue.sql",
    "014_add_branch_routing_settings.sql",
    "015_add_metrics_daily.sql",
    "016_add_asr_metrics.sql",
    "017_add_knowledge_backlog.sql",
    "018_add_outbox_meta.sql",
    "019_add_metrics_analytics_daily.sql",
}


def _list_sql_files(directory: Path) -> list[str]:
    if not directory.exists():
        raise RuntimeError(f"Directory not found: {directory}")
    if not directory.is_dir():
        raise RuntimeError(f"Path is not a directory: {directory}")
    return sorted(path.name for path in directory.iterdir() if path.is_file() and path.suffix == ".sql")


def check_truffles_api_migrations(filenames: list[str]) -> list[str]:
    errors: list[str] = []
    prefixes: dict[str, list[str]] = {}

    for name in filenames:
        match = STRICT_MIGRATION_NAME.match(name)
        if match is None:
            if name not in LEGACY_NON_STANDARD_FILENAMES:
                errors.append(
                    f"truffles-api/migrations/{name}: invalid name, expected NNN_snake_case.sql"
                )
            continue
        prefix = match.group("prefix")
        prefixes.setdefault(prefix, []).append(name)

    for prefix, names in sorted(prefixes.items()):
        if len(names) <= 1:
            continue
        expected_legacy = LEGACY_DUPLICATE_PREFIXES.get(prefix)
        actual = set(names)
        if expected_legacy is None:
            errors.append(
                f"truffles-api/migrations: duplicate prefix {prefix} for files: {', '.join(names)}"
            )
            continue
        if actual != expected_legacy:
            expected_str = ", ".join(sorted(expected_legacy))
            actual_str = ", ".join(sorted(actual))
            errors.append(
                "truffles-api/migrations: duplicate prefix "
                f"{prefix} changed from legacy allowlist. expected [{expected_str}], got [{actual_str}]"
            )

    for prefix, expected in sorted(LEGACY_DUPLICATE_PREFIXES.items()):
        actual = set(prefixes.get(prefix, []))
        if actual != expected:
            expected_str = ", ".join(sorted(expected))
            actual_str = ", ".join(sorted(actual)) if actual else "<none>"
            errors.append(
                f"truffles-api/migrations: legacy duplicate set for prefix {prefix} drifted. "
                f"expected [{expected_str}], got [{actual_str}]"
            )

    return errors


def check_ops_migrations_frozen(filenames: list[str]) -> list[str]:
    errors: list[str] = []
    current = set(filenames)
    missing = sorted(FROZEN_OPS_MIGRATIONS - current)
    unexpected = sorted(current - FROZEN_OPS_MIGRATIONS)

    if missing:
        errors.append(
            "ops/migrations: missing frozen files: " + ", ".join(missing)
        )
    if unexpected:
        errors.append(
            "ops/migrations: new files are not allowed (use truffles-api/migrations): "
            + ", ".join(unexpected)
        )
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate SQL migration governance rules")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable full governance checks (CI mode).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    api_dir = repo_root / "truffles-api" / "migrations"
    ops_dir = repo_root / "ops" / "migrations"

    api_files = _list_sql_files(api_dir)
    ops_files = _list_sql_files(ops_dir)

    errors: list[str] = []
    errors.extend(check_truffles_api_migrations(api_files))

    if args.strict:
        errors.extend(check_ops_migrations_frozen(ops_files))

    if errors:
        print("Migration governance check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    mode = "strict" if args.strict else "default"
    print(
        f"Migration governance OK ({mode}): truffles-api={len(api_files)} files, ops={len(ops_files)} files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
