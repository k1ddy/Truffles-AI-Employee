"""Convenience re-exports for the webhook entrypoint."""

from __future__ import annotations

from importlib import util
from pathlib import Path
import sys

_entrypoint_path = Path(__file__).resolve().parent.parent / "webhook.py"
_spec = util.spec_from_file_location("app.routers._webhook_entrypoint", _entrypoint_path)
if _spec is None or _spec.loader is None:  # pragma: no cover - import sanity guard
    raise ImportError(f"Unable to load webhook entrypoint from {_entrypoint_path}")

_entrypoint = util.module_from_spec(_spec)
sys.modules[_spec.name] = _entrypoint
_spec.loader.exec_module(_entrypoint)

debug_webhook = _entrypoint.debug_webhook
handle_webhook = _entrypoint.handle_webhook
handle_webhook_direct = _entrypoint.handle_webhook_direct
handle_webhook_probe = _entrypoint.handle_webhook_probe
_process_outbox_rows = _entrypoint._process_outbox_rows
router = _entrypoint.router

__all__ = [
    "debug_webhook",
    "handle_webhook",
    "handle_webhook_direct",
    "handle_webhook_probe",
    "_process_outbox_rows",
    "router",
]
