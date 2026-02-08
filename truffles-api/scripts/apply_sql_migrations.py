import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

import psycopg2


TRACKING_TABLE = "schema_migrations"
MIGRATION_LOCK_KEY = 982451653
BOOTSTRAP_ACTION_SKIP = "skip"
BOOTSTRAP_ACTION_BOOTSTRAP = "bootstrap"
BOOTSTRAP_MODE_OFF = "off"
BOOTSTRAP_MODE_AUTO = "auto"
BOOTSTRAP_MODE_LEGACY = "legacy"
LEGACY_MARKER_TABLES = frozenset(
    {
        "clients",
        "branches",
        "users",
        "conversations",
        "messages",
    }
)


@dataclass(frozen=True)
class MigrationSpec:
    name: str
    path: Path
    checksum: str
    sql: str


def discover_migration_files(migrations_dir: Path) -> List[MigrationSpec]:
    if not migrations_dir.exists():
        raise RuntimeError(f"Migrations directory does not exist: {migrations_dir}")
    if not migrations_dir.is_dir():
        raise RuntimeError(f"Migrations path is not a directory: {migrations_dir}")

    migration_paths = sorted(
        path for path in migrations_dir.iterdir() if path.is_file() and path.suffix == ".sql"
    )

    migrations: List[MigrationSpec] = []
    for path in migration_paths:
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(
            MigrationSpec(
                name=path.name,
                path=path,
                checksum=checksum,
                sql=sql,
            )
        )
    return migrations


def build_migration_plan(
    migrations: Sequence[MigrationSpec],
    applied: Dict[str, str],
) -> tuple[List[MigrationSpec], List[MigrationSpec]]:
    pending: List[MigrationSpec] = []
    skipped: List[MigrationSpec] = []

    for migration in migrations:
        applied_checksum = applied.get(migration.name)
        if applied_checksum is None:
            pending.append(migration)
            continue
        if applied_checksum != migration.checksum:
            raise RuntimeError(
                "Migration checksum mismatch for "
                f"{migration.name}: applied={applied_checksum}, current={migration.checksum}"
            )
        skipped.append(migration)

    return pending, skipped


def _ensure_tracking_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
                name TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    conn.commit()


def _fetch_applied_checksums(conn) -> Dict[str, str]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT name, checksum FROM {TRACKING_TABLE}")
        rows = cur.fetchall()
    return {name: checksum for name, checksum in rows}


def _fetch_public_tables(conn) -> Set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        rows = cur.fetchall()
    return {str(name) for (name,) in rows}


def decide_bootstrap_action(
    *,
    applied_count: int,
    public_tables: Set[str],
    bootstrap_mode: str,
) -> str:
    if bootstrap_mode not in {BOOTSTRAP_MODE_OFF, BOOTSTRAP_MODE_AUTO, BOOTSTRAP_MODE_LEGACY}:
        raise RuntimeError(f"Unsupported bootstrap mode: {bootstrap_mode}")

    if applied_count > 0:
        return BOOTSTRAP_ACTION_SKIP

    user_tables = {name for name in public_tables if name != TRACKING_TABLE}
    if not user_tables:
        return BOOTSTRAP_ACTION_SKIP

    if bootstrap_mode == BOOTSTRAP_MODE_OFF:
        raise RuntimeError(
            "schema_migrations is empty but database already has user tables; "
            "rerun with --bootstrap auto|legacy"
        )

    if bootstrap_mode == BOOTSTRAP_MODE_AUTO:
        missing_markers = sorted(LEGACY_MARKER_TABLES - public_tables)
        if missing_markers:
            marker_list = ", ".join(missing_markers)
            raise RuntimeError(
                "schema_migrations bootstrap(auto) refused: legacy marker tables are missing: "
                f"{marker_list}. Rerun with --bootstrap legacy only if this is intentional."
            )

    return BOOTSTRAP_ACTION_BOOTSTRAP


def _bootstrap_legacy(conn, migrations: Sequence[MigrationSpec]) -> None:
    with conn.cursor() as cur:
        for migration in migrations:
            cur.execute(
                f"""
                INSERT INTO {TRACKING_TABLE} (name, checksum)
                VALUES (%s, %s)
                ON CONFLICT (name) DO NOTHING
                """,
                (migration.name, migration.checksum),
            )
    conn.commit()


def _apply_migration(conn, migration: MigrationSpec) -> None:
    with conn.cursor() as cur:
        cur.execute(migration.sql)
        cur.execute(
            f"INSERT INTO {TRACKING_TABLE} (name, checksum) VALUES (%s, %s)",
            (migration.name, migration.checksum),
        )
    conn.commit()


def _acquire_lock(conn) -> None:
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK_KEY,))
    conn.autocommit = False


def _release_lock(conn) -> None:
    try:
        conn.rollback()
    except Exception:
        pass

    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_KEY,))
    conn.autocommit = False


def apply_migrations(
    database_url: str,
    migrations_dir: Path,
    *,
    check_only: bool = False,
    bootstrap_mode: str = BOOTSTRAP_MODE_OFF,
) -> int:
    migrations = discover_migration_files(migrations_dir)
    if not migrations:
        raise RuntimeError(f"No SQL migrations found in: {migrations_dir}")

    conn = psycopg2.connect(database_url)
    try:
        _acquire_lock(conn)
        _ensure_tracking_table(conn)
        applied = _fetch_applied_checksums(conn)
        public_tables = _fetch_public_tables(conn)
        bootstrap_action = decide_bootstrap_action(
            applied_count=len(applied),
            public_tables=public_tables,
            bootstrap_mode=bootstrap_mode,
        )
        if bootstrap_action == BOOTSTRAP_ACTION_BOOTSTRAP:
            if check_only:
                print(
                    "Migration check failed: schema_migrations bootstrap is required. "
                    "Run apply with --bootstrap legacy|auto."
                )
                return 1
            print(f"Bootstrapping {TRACKING_TABLE} from legacy schema (mode={bootstrap_mode})")
            _bootstrap_legacy(conn, migrations)
            applied = _fetch_applied_checksums(conn)
        pending, skipped = build_migration_plan(migrations, applied)

        print(
            f"Migrations discovered={len(migrations)} pending={len(pending)} applied={len(skipped)}"
        )

        if check_only:
            if pending:
                print("Pending migrations:")
                for migration in pending:
                    print(f"  - {migration.name}")
                return 1
            print("Migration check OK: no pending migrations")
            return 0

        for migration in pending:
            print(f"Applying migration: {migration.name}")
            _apply_migration(conn, migration)

        print(f"Migration apply complete: applied_now={len(pending)}")
        return 0
    finally:
        try:
            _release_lock(conn)
        finally:
            conn.close()


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply SQL migrations for truffles-api")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL DSN (default: DATABASE_URL env)",
    )
    parser.add_argument(
        "--migrations-dir",
        default="/app/migrations",
        help="Directory with SQL migrations",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if pending migrations exist",
    )
    parser.add_argument(
        "--bootstrap",
        default=os.environ.get("MIGRATION_BOOTSTRAP_MODE", BOOTSTRAP_MODE_OFF),
        help="Bootstrap mode for legacy DB without schema_migrations: off|auto|legacy",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    database_url = (args.database_url or "").strip()
    if not database_url:
        print("ERROR: --database-url is required (or set DATABASE_URL)", file=sys.stderr)
        return 2
    bootstrap_mode = (args.bootstrap or "").strip().lower()
    if bootstrap_mode not in {BOOTSTRAP_MODE_OFF, BOOTSTRAP_MODE_AUTO, BOOTSTRAP_MODE_LEGACY}:
        print("ERROR: --bootstrap must be one of: off, auto, legacy", file=sys.stderr)
        return 2

    migrations_dir = Path(args.migrations_dir)

    try:
        return apply_migrations(
            database_url,
            migrations_dir,
            check_only=args.check,
            bootstrap_mode=bootstrap_mode,
        )
    except Exception as exc:
        print(f"ERROR: migration runner failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
