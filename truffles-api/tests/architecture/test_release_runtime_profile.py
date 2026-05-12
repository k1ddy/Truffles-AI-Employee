from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_derive_outbox_worker_mode_promotes_livecheck_allowlist_to_local_debug() -> None:
    module = load_module("release_runtime_profile", SCRIPTS / "release_runtime_profile.py")

    mode, warnings = module.derive_outbox_worker_mode(
        {
            "EVAL_MODE": "livecheck",
            "TRANSPORT_SEND_MODE": "allowlist",
            "OUTBOX_WORKER_ENABLED": "1",
            "OUTBOX_WORKER_MODE": "off",
        }
    )

    assert mode == "local_debug"
    assert warnings == ["env OUTBOX_WORKER_MODE=off conflicts with derived release mode=local_debug"]


def test_build_release_runtime_profile_includes_network_subnets(monkeypatch) -> None:
    module = load_module("release_runtime_profile", SCRIPTS / "release_runtime_profile.py")

    def _fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["docker", "network", "inspect", "truffles_internal-net"],
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "IPAM": {
                            "Config": [
                                {"Subnet": "172.24.0.0/16"},
                                {"Subnet": "172.20.0.0/16"},
                            ]
                        }
                    }
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    payload = module.build_release_runtime_profile(
        {
            "EVAL_MODE": "livecheck",
            "TRANSPORT_SEND_MODE": "allowlist",
            "OUTBOX_WORKER_ENABLED": "1",
        },
        network="truffles_internal-net",
    )

    assert payload["outbox_worker_mode_override"] == "local_debug"
    assert payload["webhook_enqueue_only_override"] == "1"
    assert payload["database_local_cidrs"] == ["172.24.0.0/16", "172.20.0.0/16"]


def test_derive_webhook_enqueue_only_follows_outbox_worker_mode() -> None:
    module = load_module("release_runtime_profile", SCRIPTS / "release_runtime_profile.py")

    enabled, enabled_warnings = module.derive_webhook_enqueue_only(
        {},
        outbox_worker_mode="prod",
    )
    disabled, disabled_warnings = module.derive_webhook_enqueue_only(
        {},
        outbox_worker_mode="off",
    )

    assert enabled == "1"
    assert enabled_warnings == []
    assert disabled == "0"
    assert disabled_warnings == []
