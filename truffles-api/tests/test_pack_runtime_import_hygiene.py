from pathlib import Path

CORE_WEBHOOK_FILES = [
    "truffles-api/app/routers/webhook/policy.py",
    "truffles-api/app/routers/webhook/booking.py",
    "truffles-api/app/routers/webhook/info.py",
    "truffles-api/app/routers/webhook/response.py",
]

CORE_RUNTIME_FILES = [
    *CORE_WEBHOOK_FILES,
    "truffles-api/app/routers/webhook/pending.py",
    "truffles-api/app/services/tool_registry_service.py",
    "truffles-api/app/services/ai_service.py",
]


def test_core_webhook_modules_do_not_use_demo_decision_symbols() -> None:
    forbidden_symbols = (
        "DemoSalonDecision",
        "get_demo_salon_decision",
        "get_demo_salon_service_decision",
    )
    repo_root = Path(__file__).resolve().parents[2]
    for relative_path in CORE_WEBHOOK_FILES:
        content = (repo_root / relative_path).read_text(encoding="utf-8")
        for symbol in forbidden_symbols:
            assert symbol not in content, f"{relative_path} contains forbidden symbol: {symbol}"


def test_core_runtime_modules_do_not_import_demo_knowledge_module() -> None:
    forbidden_imports = (
        "from app.services.demo_salon_knowledge import",
        "import app.services.demo_salon_knowledge",
    )
    repo_root = Path(__file__).resolve().parents[2]
    for relative_path in CORE_RUNTIME_FILES:
        content = (repo_root / relative_path).read_text(encoding="utf-8")
        for pattern in forbidden_imports:
            assert pattern not in content, f"{relative_path} contains forbidden import: {pattern}"
