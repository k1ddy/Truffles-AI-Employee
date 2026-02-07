import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import psycopg2


TRACKING_TABLE = "schema_migrations"
MIGRATION_LOCK_KEY = 982451653


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
) -> int:
    migrations = discover_migration_files(migrations_dir)
    if not migrations:
        raise RuntimeError(f"No SQL migrations found in: {migrations_dir}")

    conn = psycopg2.connect(database_url)
    try:
        _acquire_lock(conn)
        _ensure_tracking_table(conn)
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
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    database_url = (args.database_url or "").strip()
    if not database_url:
        print("ERROR: --database-url is required (or set DATABASE_URL)", file=sys.stderr)
        return 2

    migrations_dir = Path(args.migrations_dir)

    try:
        return apply_migrations(database_url, migrations_dir, check_only=args.check)
    except Exception as exc:
        print(f"ERROR: migration runner failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
