#!/usr/bin/env python3
"""Send one ChatFlow message (sender-only instance)."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def _build_marker(prefix: str) -> str:
    normalized = (prefix or "").strip().replace(" ", "_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{normalized}-{timestamp}"


def _send_chatflow_message(api_url: str, token: str, instance_id: str, jid: str, message: str, timeout: float):
    params = {
        "token": token,
        "instance_id": instance_id,
        "jid": jid,
        "msg": message,
    }
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{api_url}?{query}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one ChatFlow message.")
    parser.add_argument("--text", default=None)
    parser.add_argument("--marker-prefix", default=None)
    parser.add_argument("--append-marker", action="store_true")
    parser.add_argument("--token", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--jid", default=None)
    parser.add_argument(
        "--api-url",
        default=os.environ.get("CHATFLOW_API_URL", "https://app.chatflow.kz/api/v1/send-text"),
    )
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token = args.token or os.environ.get("CHATFLOW_TOKEN")
    instance_id = args.instance_id or os.environ.get("CHATFLOW_INSTANCE_ID")
    jid = args.jid or os.environ.get("CHATFLOW_JID")
    timeout = args.timeout
    if timeout is None:
        timeout = float(os.environ.get("CHATFLOW_TIMEOUT_SECONDS", "30"))
    if not token or not instance_id or not jid:
        raise SystemExit("Missing token/instance-id/jid (use args or env).")

    marker = None
    text = args.text
    if not text:
        if not args.marker_prefix:
            raise SystemExit("Provide --text or --marker-prefix.")
        marker = _build_marker(args.marker_prefix)
        text = marker
    else:
        if args.append_marker or args.marker_prefix:
            marker = _build_marker(args.marker_prefix or "LC-MARKER")
            text = f"{text} [{marker}]"

    sent_at = datetime.now(timezone.utc).isoformat()
    status = "dry_run"
    response_status = None
    response_body = None
    if not args.dry_run:
        response_status, response_body = _send_chatflow_message(
            args.api_url, token, instance_id, jid, text, timeout
        )
        status = "sent" if response_status == 200 else "error"

    result = {
        "instance_id": instance_id,
        "jid": jid,
        "marker": marker,
        "text": text,
        "sent_at": sent_at,
        "status": status,
        "http_status": response_status,
        "response": (response_body or "")[:200] if response_body else None,
    }
    print(json.dumps({"chatflow_send": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
