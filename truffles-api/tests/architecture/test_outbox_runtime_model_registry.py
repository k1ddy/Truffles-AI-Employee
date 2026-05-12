from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = ROOT / "truffles-api"


def test_outbox_runtime_import_path_has_complete_model_registry() -> None:
    code = textwrap.dedent(
        """
        import app.services.outbox_runtime_service  # noqa: F401
        from sqlalchemy.orm import configure_mappers

        configure_mappers()
        print("ok")
        """
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_ROOT)
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert completed.stdout.strip() == "ok"
