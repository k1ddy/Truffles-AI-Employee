#!/usr/bin/env python3
import json, os, sys, uuid, subprocess
from pathlib import Path

def safe_read(p: Path, limit_chars: int = 8000) -> str:
    if not p.exists():
        return f"[missing] {p}"
    s = p.read_text(encoding="utf-8", errors="replace")
    return s[:limit_chars]

def sh(cmd: list[str], cwd: str) -> str:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
        return (r.stdout or "").strip()
    except Exception:
        return ""

def main():
    inp = json.load(sys.stdin)
    project_dir = os.environ.get("FACTORY_PROJECT_DIR") or inp.get("cwd") or os.getcwd()

    token = f"HOOK_OK_{uuid.uuid4().hex}"

    branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], project_dir)
    head = sh(["git", "rev-parse", "--short", "HEAD"], project_dir)

    state = safe_read(Path(project_dir) / "STATE.md", limit_chars=9000)

    additional = (
        "SESSIONSTART CONTEXT (auto)\n"
        f"HOOK_SMOKE_TOKEN: {token}\n"
        f"REPO: {project_dir}\n"
        f"GIT_BRANCH: {branch}\n"
        f"GIT_HEAD: {head}\n"
        "\nSTATE_MD_SNIPPET:\n"
        "-----------------\n"
        f"{state}\n"
    )

    # Вариант 1: JSON формат (по документации)
    # out = {
    #     "hookSpecificOutput": {
    #         "hookEventName": "SessionStart",
    #         "additionalContext": additional
    #     }
    # }
    # sys.stdout.write(json.dumps(out, ensure_ascii=True))
    
    # Вариант 2: Plaintext (по документации для SessionStart exit 0 + stdout -> context)
    # Заменяем Unicode символы на ASCII для Windows
    additional_safe = additional.encode('ascii', 'replace').decode('ascii')
    sys.stdout.write(additional_safe)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"hook failed: {e}", file=sys.stderr)
        sys.exit(1)