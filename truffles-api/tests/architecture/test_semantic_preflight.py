from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def _load_module():
    script_path = SCRIPTS / "semantic_preflight.py"
    spec = importlib.util.spec_from_file_location("semantic_preflight", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_guard_only_bundle(bundle_dir: Path, *, valid: bool) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    manual_audit = bundle_dir / "manual_audit.md"
    manual_audit.write_text("guard-only bundle", encoding="utf-8")
    summary = {
        "status": "closed_proven",
        "closure_scope": "guard_only",
    }
    result = {
        "result": "closed_proven",
        "closure_scope": "guard_only",
        "artifacts": {
            "manual_audit": str(manual_audit),
            "proof_exact_live": str(bundle_dir / "proof_exact_live.json"),
            "narrow_remeasure": str(bundle_dir / "narrow_remeasure.json"),
        },
    }
    if valid:
        semantic_audit = {
            "scope": "guard_only",
            "raw_owner": "N/A",
            "final_runtime": "N/A",
            "rescue": "N/A",
            "note": "guard-only test bundle",
        }
        summary["semantic_audit"] = semantic_audit
        result["semantic_audit"] = semantic_audit
    _write_json(bundle_dir / "summary.json", summary)
    _write_json(bundle_dir / "result.json", result)


def test_run_preflight_passes_with_valid_guards_and_bundle(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module()
    bundle_dir = tmp_path / "bundle"
    _write_guard_only_bundle(bundle_dir, valid=True)

    monkeypatch.setattr(mod, "_run_guard", lambda _command: (0, "OK\n", ""))
    monkeypatch.setattr(mod, "_runtime_fingerprint_preflight", lambda **_kwargs: {"checked": False})

    payload = mod.run_preflight(repo_root=tmp_path, bundle_dir=bundle_dir)

    assert payload["valid"] is True
    assert [item["name"] for item in payload["repo_checks"]] == [
        "single_semantic_owner_guard.py",
        "semantic_contract_sync_guard.py",
        "closure_rescue_claim_guard.py",
    ]
    assert payload["runtime_fingerprint"] == {"checked": False}


def test_run_preflight_fails_on_runtime_mismatch(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module()

    monkeypatch.setattr(mod, "_run_guard", lambda _command: (0, "OK\n", ""))
    monkeypatch.setattr(
        mod,
        "_runtime_fingerprint_preflight",
        lambda **_kwargs: {
            "checked": True,
            "endpoint": "http://localhost:8000/admin/version",
            "expected_commit": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "runtime_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "runtime_version": "main",
            "valid": False,
            "reasons": ["git_commit_mismatch"],
        },
    )

    payload = mod.run_preflight(repo_root=tmp_path, base_url="http://localhost:8000")

    assert payload["valid"] is False
    assert payload["runtime_fingerprint"]["checked"] is True
    assert payload["runtime_fingerprint"]["valid"] is False
    assert any("git_commit_mismatch" in item for item in payload["failures"])


def test_run_preflight_fails_on_invalid_bundle_guard(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module()
    bundle_dir = tmp_path / "bundle"
    _write_guard_only_bundle(bundle_dir, valid=False)

    def _fake_run_guard(command: list[str]):
        label = Path(command[1]).name
        if label == "closure_rescue_claim_guard.py":
            return 1, "", "closure_rescue_claim_guard: FAIL: semantic_audit mapping missing for claim-bearing bundle\n"
        return 0, "OK\n", ""

    monkeypatch.setattr(mod, "_run_guard", _fake_run_guard)
    monkeypatch.setattr(mod, "_runtime_fingerprint_preflight", lambda **_kwargs: {"checked": False})

    payload = mod.run_preflight(repo_root=tmp_path, bundle_dir=bundle_dir)

    assert payload["valid"] is False
    assert any("closure_rescue_claim_guard.py" in item for item in payload["failures"])
    assert any("semantic_audit mapping missing" in item for item in payload["failures"])


def test_main_writes_output_json(monkeypatch, tmp_path: Path, capsys) -> None:
    mod = _load_module()
    output_path = tmp_path / "preflight.json"
    payload = {
        "valid": True,
        "repo_root": str(tmp_path),
        "bundle_dir": None,
        "repo_checks": [],
        "runtime_fingerprint": {"checked": False},
        "checked_at": "2026-04-14T00:00:00+00:00",
        "failures": [],
    }

    monkeypatch.setattr(mod, "run_preflight", lambda **_kwargs: payload)
    monkeypatch.setattr(sys, "argv", ["semantic_preflight.py"])
    result = mod.main()
    stdout = capsys.readouterr().out

    assert result == 0
    assert stdout.strip() == json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(sys, "argv", ["semantic_preflight.py", "--output", str(output_path)])
    result = mod.main()
    stdout = capsys.readouterr().out

    assert result == 0
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload
    assert stdout.strip() == json.dumps(payload, ensure_ascii=False)
