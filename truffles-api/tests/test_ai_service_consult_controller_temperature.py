from types import SimpleNamespace

from app.schemas.consult import ConsultTopic
from app.services import ai_service


def _topic() -> ConsultTopic:
    return ConsultTopic.model_validate(
        {
            "id": "nails",
            "title": "Ногтевой сервис",
            "summary": "Вопросы по маникюру и связанным услугам.",
            "allowed_advice": ["Базовые разъяснения по услугам салона."],
            "required_questions": [],
            "optional_questions": [],
            "disallowed_claims": [],
            "fact_requirements": [],
            "risk_tags": ["none"],
            "clarify_limit": 1,
            "escalate_when": ["unknown_topic"],
            "next_step": "Предложить запись.",
        }
    )


def _controller_json() -> str:
    return (
        '{"intent":"consult","topic_id":"nails","confidence":0.9,'
        '"risk_class":"low","actions":["answer"],"slots":{},"notes":"ok"}'
    )


def test_consult_controller_uses_supported_temperature_for_gpt5(monkeypatch):
    captured: dict[str, float] = {}

    class _LLM:
        def generate(self, _messages, **kwargs):
            captured["temperature"] = kwargs.get("temperature")
            return SimpleNamespace(content=_controller_json())

    monkeypatch.setattr(ai_service, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_service, "FAST_MODEL", "gpt-5-mini")
    monkeypatch.setattr(ai_service, "_should_attempt_llm", lambda *_a, **_k: True)
    monkeypatch.setattr(ai_service, "get_llm_provider", lambda: _LLM())

    result = ai_service.generate_consult_controller_output(
        message_text="Подскажите по маникюру",
        topics=[_topic()],
        candidates=[{"topic_id": "nails", "score": 0.9}],
        consult_question=None,
        timing_context={},
    )

    assert result.ok is True
    assert captured["temperature"] in (0.0, 1.0)


def test_consult_controller_keeps_zero_temperature_for_non_gpt5(monkeypatch):
    captured: dict[str, float] = {}

    class _LLM:
        def generate(self, _messages, **kwargs):
            captured["temperature"] = kwargs.get("temperature")
            return SimpleNamespace(content=_controller_json())

    monkeypatch.setattr(ai_service, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_service, "FAST_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(ai_service, "_should_attempt_llm", lambda *_a, **_k: True)
    monkeypatch.setattr(ai_service, "get_llm_provider", lambda: _LLM())

    result = ai_service.generate_consult_controller_output(
        message_text="Подскажите по маникюру",
        topics=[_topic()],
        candidates=[{"topic_id": "nails", "score": 0.9}],
        consult_question=None,
        timing_context={},
    )

    assert result.ok is True
    assert captured["temperature"] == 0.0
