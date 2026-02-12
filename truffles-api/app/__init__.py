"""App package bootstrap."""

from __future__ import annotations

from pathlib import Path

from dotenv import find_dotenv, load_dotenv


def _load_environment() -> None:
    # Load service-local .env first, then fallback to cwd discovery.
    app_root = Path(__file__).resolve().parents[1]
    local_env = app_root / ".env"
    if local_env.exists():
        load_dotenv(dotenv_path=local_env, override=False)
    discovered_env = find_dotenv(usecwd=True)
    if discovered_env:
        load_dotenv(dotenv_path=discovered_env, override=False)


_load_environment()

