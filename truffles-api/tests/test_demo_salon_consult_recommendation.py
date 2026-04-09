from app.services.demo_salon_knowledge_compat import get_demo_salon_service_decision


def test_consult_haircut_recommendation_returns_consult_reply():
    decision = get_demo_salon_service_decision(
        "Какую именно стрижку вы рекомендуете?",
        client_slug="demo_salon",
        intent_decomp={"consult_intent": True},
    )

    assert decision is not None
    assert decision.intent in {"consult_reply", "service_match"}
    assert isinstance(decision.response, str)
    assert "стриж" in decision.response.lower()
    assert "рекоменд" in decision.response.lower() or "выбирают" in decision.response.lower()
    meta = decision.meta or {}
    assert meta.get("consult_recommendation") is True
