#!/usr/bin/env python3
import json, re, sys

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(1)

    tool = (data.get("tool_name") or "").strip()
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or tool_input.get("cmd") or ""

    if tool.lower() != "execute" or not isinstance(command, str) or not command.strip():
        sys.exit(1)

    cmd = command.strip()
    issues = []

    if re.search(r'(?i)\bdir\b', cmd) and re.search(r'(?i)\s/b\b', cmd):
        issues.append("PowerShell: `dir /b` — это синтаксис cmd.exe. Используй `cmd /c dir /b ...` или `Get-ChildItem ...`.")

    if "&&" in cmd:
        issues.append("PowerShell: `&&` может не работать. Либо запускай команды отдельно, либо оберни в `cmd /c \"cmd1 && cmd2\"`.")

    if re.search(r'(?i)(^|\s)curl(\s|$)', cmd) and not re.search(r'(?i)curl\.exe', cmd):
        issues.append("PowerShell: `curl` = алиас `Invoke-WebRequest`. Используй `curl.exe` (пример: `curl.exe -sS -X POST ...`).")

    if "`" in cmd:
        issues.append("PowerShell: обратные кавычки `` ` `` ломают строки/JSON. Используй одинарные кавычки или вынеси в .sh/.ps1 файл и запускай его.")

    if re.search(r'(?i)\bssh\b', cmd) and ('"' in cmd or "'" in cmd):
        issues.append("SSH+кавычки: если команда сложная — вынеси на сервер в .sh и вызывай `ssh host bash -lc ./script.sh`.")

    if issues:
        for m in issues:
            print("• " + m, file=sys.stderr)
        print("Решение по умолчанию для Windows: предпочитай `cmd /c ...` или серверные bash-скрипты.", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
