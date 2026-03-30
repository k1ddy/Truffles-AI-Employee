from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


def _resolve_prompts_dir() -> Path:
    module_path = Path(__file__).resolve()
    for parent in module_path.parents:
        candidate = parent / "prompts"
        if candidate.is_dir():
            return candidate
    return module_path.parents[2] / "prompts"


_PROMPTS_DIR = _resolve_prompts_dir()
_CONTROLLER_PROMPT_PATH = _PROMPTS_DIR / "intent_classifier.md"
_PLAN_PROMPT_PATH = _PROMPTS_DIR / "llm_plan.md"

_CONTROLLER_PROMPT_FALLBACK = """# Dialogue Controller Prompt (pack-ref-only)

Ты Dialogue Controller для сервисного бизнеса. Вход всегда JSON. Верни ТОЛЬКО JSON.
Не придумывай факты о бизнесе и не используй внешний контекст: только текст клиента и входные поля.
service_query должен быть словом/фразой только из сообщения клиента (1-6 слов), иначе пустая строка.

Вход (JSON):
```json
{"task":"controller","message":"...","carryover":{"class":"...","intents":["..."],"info_sections":["..."],"ttl_remaining":0},"expected_reply_type":"..."}
```

или
```json
{"task":"answer_interpreter","message":"...","expected_reply_type":"service_choice|time|name","carryover":{"class":"...","intents":["..."],"info_sections":["..."],"ttl_remaining":0},"question_context":{"prompt_hint":"..."}}
```

Режимы:

1) task="controller" (или task отсутствует) → строго такой вид:
```json
{"class":"...","goal":"...","intents":["..."],"slots":{"service_query":""},"followups":[],"safety_flags":[],"confidence":0.0,"reason":"...","carryover":{}}
```

2) task="answer_interpreter" → строго такой вид:
```json
{"slot":"service|datetime|name","value":"...","confidence":0.0,"reason":"..."}
```

## CLASS (одно значение)
- booking — запись/перенос/отмена/окошко/время записи.
- info_bundle — адрес/как добраться/график/время работы/парковка/гости/ранний приход/цены/длительность.
- consult — совет/подбор/рекомендации по услугам без цены/адреса/записи.
- greeting — привет/спасибо/ок.
- out_of_domain — не по теме (погода, код, рецепты).
- other — остальное/неуверенность.

## GOAL (одно значение)
- booking, info, consult, greeting, out_of_domain, other — выбери наиболее точную цель диалога.

## INTENTS (список)
Разрешённые: booking, pricing, duration, location, hours, consult, greeting, out_of_domain, other.
- Для info_bundle перечисляй info-интенты из текста (pricing/duration/location/hours).
- Для booking/consult/greeting/out_of_domain ставь одноимённый интент.
- Если не уверен — other.

## SLOTS
- service_query: 1–6 слов, только из текста клиента, если услуга названа явно. Иначе пустая строка.

## FOLLOWUPS
- Список коротких подсказок (строки), что спросить дальше. Пустой список, если не нужно.

## SAFETY_FLAGS
- Список коротких меток рисков (например, "payment", "medical", "complaint") если они видны. Иначе пусто.

## CONFIDENCE
- 0.0–1.0. Если сомневаешься — 0.0.

## REASON
- Короткая причина (1–6 слов).

## ANSWER INTERPRETER (task="answer_interpreter")
- slot: service|datetime|name. expected_reply_type: service_choice→service, time→datetime, name→name.
- value: краткий ответ из сообщения клиента (для service 1–6 слов). Если ответа нет — пустая строка.
- confidence: 0.0–1.0. Если сомневаешься — 0.0.
"""

_PLAN_PROMPT_FALLBACK = """# Hybrid LLM Plan Prompt
Return JSON only (no markdown). Required fields: outcome, tool_action, confidence.
Optional fields: pack_refs, language, reason, goal, slot_state, open_questions.
Use tool_action and pack_refs only from the allowed lists provided in the input.
slot_state and open_questions may only use: service, datetime, name.
If missing required args, set outcome=collect and list open_questions accordingly.
"""

_CONTROLLER_PROMPT_CACHE: "ControllerPromptSnapshotV1 | None" = None
_PLAN_PROMPT_CACHE: "PlanPromptSnapshotV1 | None" = None


class ControllerPromptSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "controller_prompt_snapshot.v1"
    asset_version: str = "v1"
    prompt_text: str
    source: str
    fallback_used: bool = False


class PlanPromptSnapshotV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "plan_prompt_snapshot.v1"
    asset_version: str = "v1"
    prompt_text: str
    source: str
    fallback_used: bool = False


def load_controller_prompt_snapshot() -> ControllerPromptSnapshotV1:
    global _CONTROLLER_PROMPT_CACHE
    if _CONTROLLER_PROMPT_CACHE is not None:
        return _CONTROLLER_PROMPT_CACHE
    prompt_text = ""
    source = str(_CONTROLLER_PROMPT_PATH)
    fallback_used = False
    try:
        prompt_text = _CONTROLLER_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        prompt_text = ""
    if not prompt_text:
        prompt_text = _CONTROLLER_PROMPT_FALLBACK.strip()
        source = "controller_prompt_fallback.v1"
        fallback_used = True
    _CONTROLLER_PROMPT_CACHE = ControllerPromptSnapshotV1(
        prompt_text=prompt_text,
        source=source,
        fallback_used=fallback_used,
    )
    return _CONTROLLER_PROMPT_CACHE


def load_plan_prompt_snapshot() -> PlanPromptSnapshotV1:
    global _PLAN_PROMPT_CACHE
    if _PLAN_PROMPT_CACHE is not None:
        return _PLAN_PROMPT_CACHE
    prompt_text = ""
    source = str(_PLAN_PROMPT_PATH)
    fallback_used = False
    try:
        prompt_text = _PLAN_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        prompt_text = ""
    if not prompt_text:
        prompt_text = _PLAN_PROMPT_FALLBACK.strip()
        source = "plan_prompt_fallback.v1"
        fallback_used = True
    _PLAN_PROMPT_CACHE = PlanPromptSnapshotV1(
        prompt_text=prompt_text,
        source=source,
        fallback_used=fallback_used,
    )
    return _PLAN_PROMPT_CACHE


__all__ = [
    "ControllerPromptSnapshotV1",
    "PlanPromptSnapshotV1",
    "load_controller_prompt_snapshot",
    "load_plan_prompt_snapshot",
]
