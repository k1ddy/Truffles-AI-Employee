"""Minimal webhook package exports for the single-runtime ingress."""

from .decision import _process_outbox_rows
from .http import router

__all__ = ["_process_outbox_rows", "router"]
