from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RESTART_RELEASE = _REPO_ROOT / "scripts" / "restart_release.sh"
_RESTART_ACTIVATION_SERVICE = _REPO_ROOT / "scripts" / "restart_knowledge_activation_service.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _fake_docker_script(log_path: Path) -> str:
    return f"""#!/usr/bin/env python3
import sys
from pathlib import Path
log_path = Path({str(log_path)!r})
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open('a', encoding='utf-8') as fh:
    fh.write(' '.join(sys.argv[1:]) + '\\n')
args = sys.argv[1:]
if not args:
    raise SystemExit(0)
if args[0] == 'pull':
    raise SystemExit(0)
if args[:2] == ['image', 'inspect']:
    joined = ' '.join(args)
    if 'RepoDigests' in joined:
        print('ghcr.io/k1ddy/truffles-ai-employee@sha256:abc123')
    elif '{{{{.Id}}}}' in joined:
        print('img-123')
    raise SystemExit(0)
if args[0] == 'inspect':
    print('img-123')
    raise SystemExit(0)
raise SystemExit(0)
"""


def test_restart_release_can_include_activation_service(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    _write_executable(bin_dir / "docker", _fake_docker_script(docker_log))

    api_marker = tmp_path / "api.txt"
    workers_marker = tmp_path / "workers.txt"
    service_marker = tmp_path / "service.txt"
    _write_executable(tmp_path / "restart_api.sh", f"#!/bin/sh\nprintf 'api\n' > {api_marker!s}\n")
    _write_executable(tmp_path / "restart_workers.sh", f"#!/bin/sh\nprintf 'workers\n' > {workers_marker!s}\n")
    _write_executable(
        tmp_path / "restart_knowledge_activation_service.sh",
        f"#!/bin/sh\nprintf '%s\n' \"$KNOWLEDGE_ACTIVATION_SERVICE_ENABLED\" > {service_marker!s}\n",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "API_SCRIPT": str(tmp_path / "restart_api.sh"),
            "WORKERS_SCRIPT": str(tmp_path / "restart_workers.sh"),
            "KNOWLEDGE_ACTIVATION_SERVICE_SCRIPT": str(tmp_path / "restart_knowledge_activation_service.sh"),
            "RESTART_KNOWLEDGE_ACTIVATION_SERVICE": "1",
            "RUN_KNOWLEDGE_ACTIVATION_CANARY": "0",
            "PULL_IMAGE": "0",
            "REQUIRE_GHCR": "1",
            "IMAGE_NAME": "ghcr.io/k1ddy/truffles-ai-employee:main",
        }
    )

    result = subprocess.run(
        [str(_RESTART_RELEASE)],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert api_marker.read_text().strip() == "api"
    assert workers_marker.read_text().strip() == "workers"
    assert service_marker.read_text().strip() == "1"
    docker_calls = docker_log.read_text()
    assert "inspect --format {{.Image}} truffles-knowledge-activation-service" in docker_calls
    assert "Release parity OK: API, workers, and knowledge activation service share image id img-123" in result.stdout


def test_restart_release_can_run_activation_canary_guard(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    _write_executable(bin_dir / "docker", _fake_docker_script(docker_log))

    api_marker = tmp_path / "api.txt"
    workers_marker = tmp_path / "workers.txt"
    guard_output = tmp_path / "guard.json"
    _write_executable(tmp_path / "restart_api.sh", f"#!/bin/sh\nprintf 'api\n' > {api_marker!s}\n")
    _write_executable(tmp_path / "restart_workers.sh", f"#!/bin/sh\nprintf 'workers\n' > {workers_marker!s}\n")
    _write_executable(
        tmp_path / "fake_guard.py",
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
output_path = Path(sys.argv[sys.argv.index('--output') + 1])
output_path.write_text(json.dumps({'decision': 'go'}), encoding='utf-8')
""",
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "API_SCRIPT": str(tmp_path / "restart_api.sh"),
            "WORKERS_SCRIPT": str(tmp_path / "restart_workers.sh"),
            "RESTART_KNOWLEDGE_ACTIVATION_SERVICE": "0",
            "RUN_KNOWLEDGE_ACTIVATION_CANARY": "1",
            "KNOWLEDGE_ACTIVATION_CANARY_SCRIPT": str(tmp_path / "fake_guard.py"),
            "KNOWLEDGE_ACTIVATION_CANARY_OUTPUT": str(guard_output),
            "ACTIVATION_GUARD_PYTHON": sys.executable,
            "PULL_IMAGE": "0",
            "REQUIRE_GHCR": "1",
            "IMAGE_NAME": "ghcr.io/k1ddy/truffles-ai-employee:main",
        }
    )

    result = subprocess.run(
        [str(_RESTART_RELEASE)],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert api_marker.read_text().strip() == "api"
    assert workers_marker.read_text().strip() == "workers"
    assert guard_output.exists()
    assert "Knowledge activation canary artifact" in result.stdout


def test_restart_activation_service_accepts_ghcr_digest_ref(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_log = tmp_path / "docker.log"
    _write_executable(bin_dir / "docker", _fake_docker_script(docker_log))

    env_file = tmp_path / "activation.env"
    env_file.write_text("ENV=1\n", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "ENV_FILE": str(env_file),
            "REQUIRE_GHCR": "1",
            "PULL_IMAGE": "0",
            "VERIFY_HEALTH": "0",
            "KNOWLEDGE_ACTIVATION_SERVICE_ENABLED": "1",
            "IMAGE_NAME": "ghcr.io/k1ddy/truffles-ai-employee@sha256:abc123",
            "EXPECTED_IMAGE": "ghcr.io/k1ddy/truffles-ai-employee@sha256:abc123",
        }
    )

    result = subprocess.run(
        [str(_RESTART_ACTIVATION_SERVICE)],
        cwd=str(_REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    docker_calls = docker_log.read_text()
    assert "run -d --name truffles-knowledge-activation-service" in docker_calls
    assert "ghcr.io/k1ddy/truffles-ai-employee@sha256:abc123" in docker_calls
    assert "Knowledge Activation Service restarted: truffles-knowledge-activation-service" in result.stdout
