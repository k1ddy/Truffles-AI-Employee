#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

def read_latest(project_dir: Path) -> str:
    pointer = project_dir / ".factory" / "context_pack_latest_path.txt"
    if pointer.exists():
        p = Path(pointer.read_text(encoding="utf-8").strip())
        if p.exists():
            return str(p)

    packs = sorted((project_dir / ".factory").glob("context_pack_*.txt"), key=lambda x: x.stat().st_mtime, reverse=True)
    return str(packs[0]) if packs else ""

def main():
    project_dir = os.environ.get("FACTORY_PROJECT_DIR")
    base = Path(project_dir) if project_dir else Path.cwd()

    latest = read_latest(base)
    lines = ["AUTOCONTEXT (SessionStart):"]
    if latest:
        lines.append(f"- latest_context_pack: {latest}")
        try:
            txt = Path(latest).read_text(encoding="utf-8", errors="replace")
            snippet = "\n".join(txt.splitlines()[:60])
            lines.append("- context_pack_snippet (first 60 lines):")
            lines.append(snippet)
        except Exception as e:
            lines.append(f"- context_pack_read_error: {e}")
    else:
        lines.append("- latest_context_pack: NOT FOUND")

    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}}
    json.dump(out, sys.stdout)

if __name__ == "__main__":
    main()
