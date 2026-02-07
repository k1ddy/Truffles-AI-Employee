from pathlib import Path

CORE_WEBHOOK_FILES = [
    "truffles-api/app/routers/webhook/policy.py",
    "truffles-api/app/routers/webhook/booking.py",
    "truffles-api/app/routers/webhook/info.py",
    "truffles-api/app/routers/webhook/response.py",
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
