import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "apply_sql_migrations.py"
SPEC = importlib.util.spec_from_file_location("apply_sql_migrations", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


MigrationSpec = MODULE.MigrationSpec
build_migration_plan = MODULE.build_migration_plan
decide_bootstrap_action = MODULE.decide_bootstrap_action
discover_migration_files = MODULE.discover_migration_files
TRACKING_TABLE = MODULE.TRACKING_TABLE


def test_discover_migration_files_returns_sorted_sql_only(tmp_path):
    (tmp_path / "010_second.sql").write_text("SELECT 2;\n", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("not a migration\n", encoding="utf-8")

    migrations = discover_migration_files(tmp_path)

    assert [migration.name for migration in migrations] == ["001_first.sql", "010_second.sql"]


def test_discover_migration_files_checksum_is_sha256(tmp_path):
    sql = "CREATE TABLE t(id INT);\n"
    migration_path = tmp_path / "001_create_table.sql"
    migration_path.write_text(sql, encoding="utf-8")

    migrations = discover_migration_files(tmp_path)

    assert len(migrations) == 1
    assert migrations[0].checksum == hashlib.sha256(sql.encode("utf-8")).hexdigest()


def test_build_migration_plan_splits_pending_and_applied():
    migration_1 = MigrationSpec(
        name="001_init.sql",
        path=Path("001_init.sql"),
        checksum="aaa",
        sql="SELECT 1;",
    )
    migration_2 = MigrationSpec(
        name="002_more.sql",
        path=Path("002_more.sql"),
        checksum="bbb",
        sql="SELECT 2;",
    )

    pending, skipped = build_migration_plan(
        [migration_1, migration_2],
        applied={"001_init.sql": "aaa"},
    )

    assert [migration.name for migration in skipped] == ["001_init.sql"]
    assert [migration.name for migration in pending] == ["002_more.sql"]


def test_build_migration_plan_raises_on_checksum_mismatch():
    migration = MigrationSpec(
        name="001_init.sql",
        path=Path("001_init.sql"),
        checksum="current",
        sql="SELECT 1;",
    )

    with pytest.raises(RuntimeError, match="checksum mismatch"):
        build_migration_plan([migration], applied={"001_init.sql": "applied"})


def test_decide_bootstrap_action_skip_when_schema_migrations_has_data():
    action = decide_bootstrap_action(
        applied_count=3,
        public_tables={TRACKING_TABLE, "clients", "messages"},
        bootstrap_mode="auto",
    )
    assert action == "skip"


def test_decide_bootstrap_action_skip_when_database_is_empty():
    action = decide_bootstrap_action(
        applied_count=0,
        public_tables={TRACKING_TABLE},
        bootstrap_mode="auto",
    )
    assert action == "skip"


def test_decide_bootstrap_action_raises_in_off_mode_for_legacy_schema():
    with pytest.raises(RuntimeError, match="schema_migrations is empty"):
        decide_bootstrap_action(
            applied_count=0,
            public_tables={TRACKING_TABLE, "clients", "messages"},
            bootstrap_mode="off",
        )


def test_decide_bootstrap_action_auto_bootstrap_when_markers_present():
    action = decide_bootstrap_action(
        applied_count=0,
        public_tables={
            TRACKING_TABLE,
            "clients",
            "branches",
            "users",
            "conversations",
            "messages",
        },
        bootstrap_mode="auto",
    )
    assert action == "bootstrap"


def test_decide_bootstrap_action_auto_raises_when_markers_missing():
    with pytest.raises(RuntimeError, match="marker tables are missing"):
        decide_bootstrap_action(
            applied_count=0,
            public_tables={TRACKING_TABLE, "clients", "messages"},
            bootstrap_mode="auto",
        )


def test_decide_bootstrap_action_legacy_bootstrap_without_marker_check():
    action = decide_bootstrap_action(
        applied_count=0,
        public_tables={TRACKING_TABLE, "clients", "messages"},
        bootstrap_mode="legacy",
    )
    assert action == "bootstrap"
