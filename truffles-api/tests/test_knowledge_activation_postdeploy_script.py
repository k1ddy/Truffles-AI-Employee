from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_POSTDEPLOY_SCRIPT = _REPO_ROOT / "scripts" / "knowledge_activation_postdeploy.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_postdeploy(tmp_path: Path, *, guard_decision: str = "go", closeout_decision: str = "go", extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    output_dir = tmp_path / "proof"
    guard_script = tmp_path / "fake_guard.py"
    closeout_script = tmp_path / "fake_closeout.py"

    _write_executable(
        guard_script,
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
decision = os.environ.get("FAKE_GUARD_DECISION", "go")
output_path = Path(sys.argv[sys.argv.index("--output") + 1])
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps({"decision": decision}), encoding="utf-8")
raise SystemExit(0 if decision == "go" else 1)
""",
    )
    _write_executable(
        closeout_script,
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
decision = os.environ.get("FAKE_CLOSEOUT_DECISION", "go")
output_path = Path(sys.argv[sys.argv.index("--output") + 1])
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps({"decision": decision}), encoding="utf-8")
raise SystemExit(0 if decision == "go" else 1)
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "KNOWLEDGE_ACTIVATION_PROOF_PYTHON": sys.executable,
            "KNOWLEDGE_ACTIVATION_GUARD_SCRIPT": str(guard_script),
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_SCRIPT": str(closeout_script),
            "KNOWLEDGE_ACTIVATION_PROOF_OUTPUT_DIR": str(output_dir),
            "KNOWLEDGE_ACTIVATION_SERVICE_TOKEN": "test-token",
            "FAKE_GUARD_DECISION": guard_decision,
            "FAKE_CLOSEOUT_DECISION": closeout_decision,
        }
    )
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        [str(_POSTDEPLOY_SCRIPT)],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_postdeploy_skips_closeout_without_target(tmp_path: Path) -> None:
    result = _run_postdeploy(tmp_path)

    assert result.returncode == 0, result.stderr
    manifest = _read_json(tmp_path / "proof" / "manifest.json")
    assert manifest["decision"] == "go"
    assert manifest["proof_mode"] == "guard_only"
    assert manifest["closeout"]["status"] == "skipped"
    assert manifest["closeout"]["reason"] == "closeout_target_not_configured"


def test_postdeploy_runs_closeout_when_target_is_configured(tmp_path: Path) -> None:
    result = _run_postdeploy(
        tmp_path,
        extra_env={
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_CLIENT_SLUG": "demo_salon",
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_BRANCH_SLUG": "main",
        },
    )

    assert result.returncode == 0, result.stderr
    manifest = _read_json(tmp_path / "proof" / "manifest.json")
    assert manifest["decision"] == "go"
    assert manifest["proof_mode"] == "guard_and_closeout"
    assert manifest["closeout"]["status"] == "executed"
    assert manifest["closeout"]["decision"] == "go"


def test_postdeploy_fails_on_partial_closeout_configuration(tmp_path: Path) -> None:
    result = _run_postdeploy(
        tmp_path,
        extra_env={"KNOWLEDGE_ACTIVATION_CLOSEOUT_CLIENT_SLUG": "demo_salon"},
    )

    assert result.returncode != 0
    manifest = _read_json(tmp_path / "proof" / "manifest.json")
    assert manifest["decision"] == "no_go"
    assert manifest["closeout"]["status"] == "invalid_configuration"
    assert manifest["closeout"]["reason"] == "closeout_target_incomplete"


def test_postdeploy_keeps_partial_explicit_override_invalid_even_with_defaults(tmp_path: Path) -> None:
    result = _run_postdeploy(
        tmp_path,
        extra_env={
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_CLIENT_SLUG": "demo_salon_override",
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_DEFAULT_CLIENT_SLUG": "demo_salon",
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_DEFAULT_BRANCH_SLUG": "main",
        },
    )

    assert result.returncode != 0
    manifest = _read_json(tmp_path / "proof" / "manifest.json")
    assert manifest["decision"] == "no_go"
    assert manifest["closeout"]["status"] == "invalid_configuration"
    assert manifest["closeout"]["reason"] == "closeout_target_incomplete"


def test_postdeploy_uses_default_target_when_closeout_is_required(tmp_path: Path) -> None:
    result = _run_postdeploy(
        tmp_path,
        extra_env={
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_DEFAULT_CLIENT_SLUG": "demo_salon",
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_DEFAULT_BRANCH_SLUG": "main",
            "KNOWLEDGE_ACTIVATION_PROOF_REQUIRE_CLOSEOUT": "1",
        },
    )

    assert result.returncode == 0, result.stderr
    manifest = _read_json(tmp_path / "proof" / "manifest.json")
    assert manifest["decision"] == "go"
    assert manifest["closeout"]["status"] == "executed"
    assert manifest["closeout"]["required"] is True
    assert manifest["target"]["client_slug"] == "demo_salon"
    assert manifest["target"]["branch_slug"] == "main"


def test_postdeploy_fails_closed_when_guard_is_no_go(tmp_path: Path) -> None:
    result = _run_postdeploy(tmp_path, guard_decision="no_go")

    assert result.returncode != 0
    manifest = _read_json(tmp_path / "proof" / "manifest.json")
    assert manifest["decision"] == "no_go"
    assert manifest["release_guard"]["decision"] == "no_go"
    assert "release_guard_failed" in manifest["reasons"]


def test_postdeploy_reuses_existing_guard_artifact(tmp_path: Path) -> None:
    output_dir = tmp_path / "proof"
    output_dir.mkdir(parents=True, exist_ok=True)
    guard_json = output_dir / "release_guard.json"
    guard_json.write_text(json.dumps({"decision": "go"}), encoding="utf-8")

    closeout_script = tmp_path / "fake_closeout.py"
    _write_executable(
        closeout_script,
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
output_path = Path(sys.argv[sys.argv.index("--output") + 1])
output_path.write_text(json.dumps({"decision": "go"}), encoding="utf-8")
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "KNOWLEDGE_ACTIVATION_PROOF_PYTHON": sys.executable,
            "KNOWLEDGE_ACTIVATION_GUARD_SCRIPT": str(tmp_path / "missing_guard.py"),
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_SCRIPT": str(closeout_script),
            "KNOWLEDGE_ACTIVATION_PROOF_OUTPUT_DIR": str(output_dir),
            "KNOWLEDGE_ACTIVATION_PROOF_GUARD_JSON": str(guard_json),
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_CLIENT_SLUG": "demo_salon",
            "KNOWLEDGE_ACTIVATION_CLOSEOUT_BRANCH_SLUG": "main",
            "KNOWLEDGE_ACTIVATION_SERVICE_TOKEN": "test-token",
        }
    )

    result = subprocess.run(
        [str(_POSTDEPLOY_SCRIPT)],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    manifest = _read_json(output_dir / "manifest.json")
    assert manifest["release_guard"]["decision"] == "go"
    assert manifest["closeout"]["status"] == "executed"
