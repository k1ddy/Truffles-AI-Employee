from __future__ import annotations

import pytest

from app.services import pack_runtime_service as runtime

_TARGET_SERVICES = ("Маникюр", "Стрижка")
_CYR_TO_LAT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def _load_service_alias_cases(client_slug: str) -> list[tuple[str, str]]:
    truth = runtime.load_yaml_truth(client_slug)
    catalog = truth.get("services_catalog") if isinstance(truth, dict) else None
    services = catalog.get("services") if isinstance(catalog, dict) else None
    if not isinstance(services, list):
        return []
    rows: list[tuple[str, str]] = []
    for service in services:
        if not isinstance(service, dict):
            continue
        name = service.get("name")
        if not isinstance(name, str) or name not in _TARGET_SERVICES:
            continue
        aliases = service.get("aliases")
        alias = None
        if isinstance(aliases, list):
            for raw_alias in aliases:
                if isinstance(raw_alias, str) and raw_alias.strip():
                    alias = raw_alias.strip()
                    break
        if not alias:
            alias = name.strip()
        rows.append((name.strip(), alias))
    return rows


def _translit(value: str) -> str:
    return value.casefold().translate(_CYR_TO_LAT)


def _with_typo(value: str) -> str:
    token = value.strip()
    if len(token) <= 4:
        return token
    midpoint = len(token) // 2
    return f"{token[:midpoint]}{token[midpoint + 1 :]}"


def _resolve_variant(message_text: str, *, client_slug: str):
    decision = runtime.get_pack_service_decision(message_text, client_slug=client_slug)
    if decision is None:
        decision = runtime.get_pack_decision(message_text, client_slug=client_slug)
    assert decision is not None
    assert isinstance(decision.meta, dict)
    return decision


@pytest.mark.parametrize("service_name,alias", _load_service_alias_cases("demo_salon"))
def test_pack_grounding_exact_alias_matches_service(service_name: str, alias: str) -> None:
    decision = _resolve_variant(
        f"Делаете {alias}?",
        client_slug="demo_salon",
    )
    meta = decision.meta or {}
    assert meta.get("resolver_id")
    assert meta.get("resolver_version")
    assert decision.intent == "service_match"
    service_query = str(meta.get("service_query") or "")
    assert service_query
    assert service_name.casefold() in service_query.casefold()


@pytest.mark.parametrize("service_name,alias", _load_service_alias_cases("demo_salon"))
@pytest.mark.parametrize(
    "variant_builder",
    (
        lambda alias: _translit(alias),
        lambda alias: _with_typo(alias),
        lambda alias: f"{alias} bagasy qancha",
    ),
)
def test_pack_grounding_variant_respects_no_guess_policy(
    service_name: str,
    alias: str,
    variant_builder,
) -> None:
    decision = _resolve_variant(
        f"Сколько стоит {variant_builder(alias)}?",
        client_slug="demo_salon",
    )
    meta = decision.meta or {}
    action_class = meta.get("action_class")
    if decision.intent == "service_match":
        assert action_class == "FACT"
        candidates = meta.get("resolver_candidates") or []
        assert isinstance(candidates, list)
        assert any("service:" in str(item.get("id") or "") for item in candidates if isinstance(item, dict))
        return
    assert action_class in {"COLLECT", "HANDOFF"}
    assert isinstance(meta.get("abstain_reason"), str) and meta.get("abstain_reason")
