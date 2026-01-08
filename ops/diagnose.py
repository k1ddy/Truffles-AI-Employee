#!/usr/bin/env python3
"""
БЫСТРАЯ ДИАГНОСТИКА
Запуск: python3 ~/truffles-main/ops/diagnose.py

Показывает:
- Состояние conversations
- Состояние handovers
"""
import os
import subprocess
from datetime import datetime, timezone

def run_command(command):
    return subprocess.run(command, capture_output=True, text=True)

API_CONTAINER_HINT = "truffles-api"

def resolve_container_name():
    result = run_command(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name={API_CONTAINER_HINT}",
            "--format",
            "{{.Names}}",
        ]
    )
    if result.returncode != 0:
        return None, result.stderr.strip()
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not names:
        return None, ""
    if API_CONTAINER_HINT in names:
        return API_CONTAINER_HINT, ""
    return names[0], ""

def run_docker_exec(container_name, command):
    return run_command(["docker", "exec", "-i", container_name, "/bin/sh", "-lc", command])

def run_curl(url, headers=None):
    cmd = ["curl", "-s"]
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    cmd.append(url)
    return run_command(cmd)

print("=" * 60)
print("ДИАГНОСТИКА TRUFFLES")
print("=" * 60)

print("\n🔎 PRE-FLIGHT:")
print("-" * 40)
container_name, docker_error = resolve_container_name()
status = ""
if docker_error:
    print(f"docker error: {docker_error}")
    print("Skipping docker checks (no access).")
else:
    if container_name:
        print(f"truffles-api container: {container_name}")
        status_result = run_command(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name]
        )
        status = status_result.stdout.strip() if status_result.returncode == 0 else ""
        if status:
            print(f"truffles-api status: {status}")
        else:
            print("truffles-api status: UNKNOWN")
    else:
        print("truffles-api container: NOT FOUND (container missing?)")

if container_name:
    image_result = run_command(
        ["docker", "inspect", "--format", "{{.Config.Image}}", container_name]
    )
    if image_result.returncode == 0 and image_result.stdout.strip():
        print(f"truffles-api image: {image_result.stdout.strip()}")
    else:
        print("truffles-api image: UNKNOWN")
else:
    print("truffles-api image: UNKNOWN")

if status == "running":
    env_checks = [
        ("TEST_MODE", True),
        ("OUTBOUND_ALLOWLIST_JIDS", True),
        ("OUTBOX_WORKER_ENABLED", True),
        ("PUBLIC_BASE_URL", True),
        ("MEDIA_SIGNING_SECRET", False),
        ("MEDIA_URL_TTL_SECONDS", True),
        ("MEDIA_CLEANUP_TTL_DAYS", True),
        ("CHATFLOW_MEDIA_TIMEOUT_SECONDS", True),
        ("ALERTS_ADMIN_TOKEN", False),
    ]
    for name, show_value in env_checks:
        if show_value:
            cmd = (
                f'if [ -n "${name}" ]; then echo "{name}=${{{name}}}"; '
                f'else echo "{name}=MISSING"; fi'
            )
        else:
            cmd = (
                f'if [ -n "${name}" ]; then echo "{name}=SET"; '
                f'else echo "{name}=MISSING"; fi'
            )
        result = run_docker_exec(container_name, cmd)
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(f"{name}=UNKNOWN (env check failed)")
else:
    print("Skipping env checks (truffles-api not running).")

# 1. Database state
print("\n📁 БАЗА ДАННЫХ:")
print("-" * 40)

# Conversations
def resolve_db_user():
    env_user = os.environ.get("DB_USER")
    if env_user:
        return env_user
    result = run_command(
        ["docker", "exec", "-i", "truffles_postgres_1", "/bin/sh", "-lc", "printf '%s' \"${POSTGRES_USER:-}\""]
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "postgres"

db_user = resolve_db_user()
print(f"DB_USER={db_user}")

result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', db_user, '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN bot_status='muted' THEN 1 END) as muted, COUNT(telegram_topic_id) as with_topic FROM conversations;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Conversations: {parts[0].strip()} total, {parts[1].strip()} muted, {parts[2].strip()} with topic")

# Handovers
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', db_user, '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN status='pending' THEN 1 END) as pending, COUNT(CASE WHEN status='active' THEN 1 END) as active FROM handovers;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Handovers: {parts[0].strip()} total, {parts[1].strip()} pending, {parts[2].strip()} active")

print("\n📮 OUTBOX STATUS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT status, COUNT(*) FROM outbox_messages GROUP BY status;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🧩 DECISION_META (last 3):")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT metadata->'decision_meta' FROM messages ORDER BY created_at DESC LIMIT 3;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🧾 ПОСЛЕДНИЕ HANDOVERS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT created_at, status, conversation_id, channel_ref, telegram_message_id "
        "FROM handovers ORDER BY created_at DESC LIMIT 10;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🟡 PENDING/MANAGER_ACTIVE CONVERSATIONS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT id, state, telegram_topic_id, last_message_at "
        "FROM conversations WHERE state IN ('pending','manager_active') "
        "ORDER BY last_message_at DESC LIMIT 10;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🌐 ADMIN ENDPOINTS:")
print("-" * 40)
version_result = run_curl("http://localhost:8000/admin/version")
if version_result.returncode == 0 and version_result.stdout.strip():
    print(f"/admin/version: {version_result.stdout.strip()}")
else:
    print("/admin/version: FAILED")

health_result = run_curl("http://localhost:8000/admin/health")
if health_result.returncode == 0 and health_result.stdout.strip():
    print(f"/admin/health: {health_result.stdout.strip()}")
else:
    print("/admin/health: FAILED")

admin_token = ""
if container_name:
    token_result = run_docker_exec(
        container_name, 'printf "%s" "${ALERTS_ADMIN_TOKEN:-}"'
    )
    if token_result.returncode == 0:
        admin_token = token_result.stdout.strip()

if admin_token:
    metric_date = datetime.now(timezone.utc).date().isoformat()
    metrics_result = run_curl(
        f"http://localhost:8000/admin/metrics?client_slug=demo_salon&metric_date={metric_date}",
        headers={"X-Admin-Token": admin_token},
    )
    if metrics_result.returncode == 0 and metrics_result.stdout.strip():
        print(f"/admin/metrics: {metrics_result.stdout.strip()}")
    else:
        print("/admin/metrics: FAILED")
else:
    print("/admin/metrics: SKIPPED (ALERTS_ADMIN_TOKEN missing)")

print("\n" + "=" * 60)
