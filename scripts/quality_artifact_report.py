#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone, timedelta


def _parse_iso(text):
    if not text:
        return None
    value = str(text)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _load_manifest(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _collect_from_index(index_root, cutoff, mode):
    manifests = []
    by_hour_root = os.path.join(index_root, "by_hour")
    if not os.path.isdir(by_hour_root):
        return manifests
    for date_dir in sorted(os.listdir(by_hour_root)):
        date_path = os.path.join(by_hour_root, date_dir)
        if not os.path.isdir(date_path):
            continue
        for hour_dir in sorted(os.listdir(date_path)):
            hour_path = os.path.join(date_path, hour_dir)
            if not os.path.isdir(hour_path):
                continue
            hour_key = f"{date_dir}T{hour_dir}"
            hour_dt = _parse_iso(f"{date_dir}T{hour_dir}:00:00+00:00")
            if hour_dt and hour_dt < cutoff:
                continue
            for filename in sorted(os.listdir(hour_path)):
                if not filename.endswith(".json"):
                    continue
                manifest = _load_manifest(os.path.join(hour_path, filename))
                if not manifest:
                    continue
                if mode and manifest.get("mode") != mode:
                    continue
                finished_at = _parse_iso(manifest.get("finished_at") or manifest.get("started_at"))
                if finished_at and finished_at < cutoff:
                    continue
                manifest["_hour_key"] = hour_key
                manifests.append(manifest)
    return manifests


def _collect_fallback(output_root, cutoff, mode):
    manifests = []
    for root, _, files in os.walk(output_root):
        if "run_manifest.json" not in files:
            continue
        manifest_path = os.path.join(root, "run_manifest.json")
        mtime = datetime.fromtimestamp(os.path.getmtime(manifest_path), tz=timezone.utc)
        if mtime < cutoff:
            continue
        manifest = _load_manifest(manifest_path)
        if not manifest:
            continue
        if mode and manifest.get("mode") != mode:
            continue
        finished_at = _parse_iso(manifest.get("finished_at") or manifest.get("started_at"))
        if finished_at and finished_at < cutoff:
            continue
        manifest["_hour_key"] = finished_at.strftime("%Y-%m-%dT%H") if finished_at else "unknown"
        manifests.append(manifest)
    return manifests


def _format_row(manifest):
    artifacts = manifest.get("artifacts") or {}
    return [
        str(manifest.get("finished_at") or manifest.get("started_at") or ""),
        str(manifest.get("mode") or ""),
        str(manifest.get("run_id") or ""),
        str(manifest.get("status") or ""),
        str(manifest.get("infra_valid") or ""),
        str(manifest.get("semantic_valid") or ""),
        str(manifest.get("run_integrity_valid") or ""),
        str(manifest.get("manual_audit_status") or ""),
        str(manifest.get("artifact_integrity_valid") or ""),
        str(manifest.get("output_dir") or ""),
        str(artifacts.get("summary") or ""),
    ]


def main():
    parser = argparse.ArgumentParser(description="Report llm-quality run artifacts by hour/mode.")
    parser.add_argument("--hours", type=int, default=24, help="Look back window in hours.")
    parser.add_argument("--mode", choices=["lock", "replay", "full"], default=None)
    parser.add_argument("--index-root", default="/tmp/booking_quality/_index")
    parser.add_argument("--output-root", default="/tmp/booking_quality")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--group-by-hour", action="store_true", default=True)
    parser.add_argument("--no-group-by-hour", action="store_false", dest="group_by_hour")
    parser.add_argument("--show-commands", action="store_true", help="Show command/resume lines.")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(args.hours, 1))
    manifests = _collect_from_index(args.index_root, cutoff, args.mode)
    if not manifests:
        manifests = _collect_fallback(args.output_root, cutoff, args.mode)

    manifests.sort(
        key=lambda m: _parse_iso(m.get("finished_at") or m.get("started_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    manifests = manifests[: max(args.limit, 1)]

    header = [
        "finished_at",
        "mode",
        "run_id",
        "status",
        "infra_valid",
        "semantic_valid",
        "run_integrity_valid",
        "manual_audit",
        "artifacts_valid",
        "output_dir",
        "summary_path",
    ]
    print("\t".join(header))
    last_hour = None
    for manifest in manifests:
        hour_key = manifest.get("_hour_key")
        if args.group_by_hour and hour_key and hour_key != last_hour:
            print(f"== {hour_key}")
            last_hour = hour_key
        print("\t".join(_format_row(manifest)))
        if args.show_commands:
            command = manifest.get("command") or ""
            resume = manifest.get("resume_command") or ""
            if command:
                print(f"command\t{command}")
            if resume:
                print(f"resume\t{resume}")


if __name__ == "__main__":
    main()
