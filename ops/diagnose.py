#!/usr/bin/env python3
"""
БЫСТРАЯ ДИАГНОСТИКА
Запуск: python3 ~/truffles-main/ops/diagnose.py

Показывает:
- Состояние conversations
- Состояние handovers
"""
import argparse
import base64
import glob
import json
import os
import random
import re
import signal
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

LIVECHECK_SUITES = {
    "ca01-core": [
        {
            "case_id": "CA01_REFUND",
            "expected_policy_section": "refund",
            "messages": [
                "хочу вернуть деньги за услугу",
                "верните оплату пожалуйста",
                "нужен возврат денег",
            ],
        },
        {
            "case_id": "CA01_PAYMENT",
            "expected_policy_section": "payment_info",
            "messages": [
                "можно оплатить картой?",
                "есть оплата каспи?",
                "можно оплатить переводом?",
            ],
        },
        {
            "case_id": "CA01_RESCHEDULE",
            "expected_policy_section": "reschedule",
            "messages": [
                "перенесите запись на завтра",
                "поменять дату записи",
                "переписать на другой день",
            ],
        },
        {
            "case_id": "CA01_MEDICAL",
            "expected_policy_section": "medical",
            "messages": [
                "у меня аллергия на гель-лак",
                "жжет после окрашивания",
                "можно беременным на процедуру?",
            ],
        },
    ],
    "ca01-extended": [
        {
            "case_id": "CA01_CANCEL",
            "expected_policy_section": "cancel",
            "messages": [
                "отмените запись пожалуйста",
                "я не приду, отмените",
            ],
        },
        {
            "case_id": "CA01_LEGAL",
            "expected_policy_section": "legal",
            "messages": [
                "хочу договор и оферту",
                "у меня юридическая претензия",
            ],
        },
        {
            "case_id": "CA01_COMPLAINT",
            "expected_policy_section": "complaint",
            "messages": [
                "жалоба: плохо сделали",
                "недоволен качеством услуги",
            ],
        },
    ],
    "ca02-policy": [
        {
            "case_id": "CA02_DISCOUNT",
            "expected_policy_section": "discounts",
            "messages": [
                "есть скидка на услуги?",
                "можно скидку?",
                "какие акции сейчас есть?",
            ],
        },
        {
            "case_id": "CA02_PAYMENT",
            "expected_policy_section": "payment_info",
            "messages": [
                "можно оплатить картой?",
                "есть оплата каспи?",
                "можно оплатить переводом?",
            ],
        },
    ],
    "ca03-info": [
        {
            "case_id": "CA03_ADDRESS_HOURS",
            "expected_info_sections": ["address", "hours"],
            "expected_fact_intents": ["location", "hours"],
            "expected_info_combined": True,
            "messages": [
                "где вы и когда работаете?",
                "где находитесь и во сколько открыты?",
            ],
        },
        {
            "case_id": "CA03_GUEST_POLICY",
            "expected_info_sections": ["guest_policy"],
            "expected_fact_intents": ["guest_policy"],
            "messages": [
                "можно с ребенком?",
                "детям можно приходить?",
            ],
        },
    ],
    "ca04-service": [
        {
            "case_id": "CA04_SERVICE_MATCH",
            "expected_intent": "service_match",
            "expected_fact_intents": ["service_match"],
            "messages": [
                "делаете маникюр?",
                "маникюр делаете?",
            ],
        },
        {
            "case_id": "CA04_SERVICE_NOT_FOUND",
            "expected_intent": "service_not_found",
            "expected_fact_intents": ["service_not_found"],
            "messages": [
                "делаете массаж?",
                "делаете стрижку?",
            ],
        },
    ],
    "ca05-booking": [
        {
            "case_id": "CA05_BOOKING_FLOW",
            "expected_policy_section": None,
            "messages": [
                "хочу записаться",
                "маникюр",
                "сколько стоит маникюр?",
            ],
            "steps": [
                {
                    "message": "хочу записаться",
                    "expect_expected_reply_type": "service_choice",
                    "expect_llm_used": False,
                },
                {
                    "message": "маникюр",
                    "expect_expected_reply_type": "time",
                    "expect_booking_service": "маникюр",
                    "expect_llm_used": False,
                },
                {
                    "message": "сколько стоит маникюр?",
                    "expect_booking_interrupt": True,
                },
            ],
        }
    ],
    "ca05-booking-commit": [
        {
            "case_id": "CA05_BOOKING_COMMIT",
            "steps": [
                {
                    "message": "хочу записаться",
                    "expect_expected_reply_type": "service_choice",
                    "expect_llm_used": False,
                },
                {
                    "message": "маникюр",
                    "expect_expected_reply_type": "time",
                    "expect_booking_service": "маникюр",
                    "expect_llm_used": False,
                },
                {
                    "message": "__BOOKING_TIME__",
                    "expect_expected_reply_type": "name",
                    "suppress_marker": True,
                },
                {
                    "message": "__BOOKING_NAME__",
                    "expect_booking_commit": True,
                    "suppress_marker": True,
                },
            ],
        }
    ],
    "ca06-consult": [
        {
            "case_id": "CA06_PACK_ONLY",
            "expected_consult_playbook_id": "hair_damage",
            "expected_meta_consult_playbook_id": "hair_damage",
            "expected_consult_decision": "consult_reply",
            "expected_source": "pack",
            "expected_llm_used": False,
            "messages": [
                "сухие волосы, что посоветуете?",
            ],
        },
        {
            "case_id": "CA06_SHORT_CIRCUIT",
            "expected_consult_playbook_id": "nails_care",
            "expected_consult_decision": "short_circuit",
            "expected_fact_source_any": ["truth", "service_matcher"],
            "expected_llm_used": False,
            "messages": [
                "уход за ногтями, сколько стоит маникюр?",
            ],
        },
    ],
    "ca07-ood": [
        {
            "case_id": "CA07_OOD",
            "expected_action": "out_of_domain",
            "expected_intent": "out_of_domain",
            "expected_source_any": [
                "domain_router",
                "domain_anchor",
                "router_low_confidence",
                "service_semantic_guard",
                "no_response_guard",
                "question_contract",
            ],
            "expected_trace_stage_any": ["out_of_domain"],
            "expected_trace_decision_any": [
                "early_block",
                "fallback",
                "domain_anchor",
                "router_low_confidence",
                "service_semantic_guard",
                "no_response_guard",
                "expected_reply_off_topic",
            ],
            "expected_llm_used": False,
            "messages": [
                "какая погода?",
            ],
        },
        {
            "case_id": "CA07_LOW_SIGNAL",
            "expected_action": "out_of_domain",
            "expected_intent": "out_of_domain",
            "expected_source_any": [
                "service_semantic_guard",
                "no_response_guard",
                "router_low_confidence",
                "domain_router",
                "question_contract",
                "domain_anchor",
            ],
            "expected_trace_stage_any": ["out_of_domain"],
            "expected_trace_decision_any": [
                "service_semantic_guard",
                "no_response_guard",
                "router_low_confidence",
                "early_block",
            ],
            "expected_llm_used": False,
            "messages": [
                "мм...",
                "...",
            ],
        },
        {
            "case_id": "CA07_SMALLTALK",
            "expected_action": "smalltalk",
            "expected_intent": "greeting",
            "expected_source_any": ["fast_intent"],
            "expected_trace_stage_any": ["fast_intent", "smalltalk"],
            "expected_trace_decision_any": ["smalltalk", "greeting"],
            "expected_llm_used": False,
            "marker_in_text": False,
            "reset_before_case": True,
            "messages": [
                "привет",
            ],
        },
    ],
    "ca08-state": [
        {
            "case_id": "CA08_PENDING",
            "expected_policy_section": "refund",
            "messages": [
                "верните оплату пожалуйста",
                "хочу вернуть деньги",
            ],
        }
    ],
    "ca09-manager": [
        {
            "case_id": "CA09_MANAGER",
            "expected_policy_section": "payment_info",
            "messages": [
                "можно оплатить картой?",
                "есть оплата каспи?",
            ],
        }
    ],
    "ca10-outbox": [
        {
            "case_id": "CA10_DEDUP",
            "expected_policy_section": "reschedule",
            "messages": [
                "перенесите запись на завтра",
                "поменять дату записи",
            ],
        }
    ],
}

WEBHOOK_FUZZ_CASES = [
    {
        "case_id": "LAW_REFUND",
        "expected_policy_section": "refund",
        "messages": [
            "хочу вернуть деньги за услугу",
            "нужен возврат денег",
        ],
    },
    {
        "case_id": "LAW_PAYMENT",
        "expected_policy_section": "payment_info",
        "messages": [
            "можно оплатить картой?",
            "есть оплата каспи?",
        ],
    },
    {
        "case_id": "LAW_RESCHEDULE",
        "expected_policy_section": "reschedule",
        "messages": [
            "перенесите запись на завтра",
            "поменять дату записи",
        ],
    },
    {
        "case_id": "LAW_MEDICAL",
        "expected_policy_section": "medical",
        "messages": [
            "у меня аллергия на гель-лак",
            "жжет после окрашивания",
        ],
    },
    {
        "case_id": "LAW_LEGAL",
        "expected_policy_section": "legal",
        "messages": [
            "хочу договор и оферту",
            "у меня юридическая претензия",
        ],
    },
    {
        "case_id": "LAW_COMPLAINT",
        "expected_policy_section": "complaint",
        "messages": [
            "жалоба: плохо сделали",
            "недоволен качеством услуги",
        ],
    },
    {
        "case_id": "INFO_HOURS",
        "expected_policy_section": None,
        "messages": [
            "до скольки работаете?",
            "какой график работы?",
        ],
    },
    {
        "case_id": "INFO_LOCATION",
        "expected_policy_section": None,
        "messages": [
            "где вы находитесь?",
            "как до вас добраться?",
        ],
    },
    {
        "case_id": "INFO_PRICE",
        "expected_policy_section": None,
        "messages": [
            "сколько стоит маникюр?",
            "какая цена на стрижку?",
        ],
    },
    {
        "case_id": "BOOK_TIME",
        "expected_policy_section": None,
        "messages": [
            "хочу записаться на завтра вечером",
            "запишите на понедельник",
        ],
    },
    {
        "case_id": "CONSULT_AFTERCOLOR",
        "expected_policy_section": None,
        "messages": [
            "посоветуйте уход после окрашивания",
            "как ухаживать после окраски?",
        ],
    },
    {
        "case_id": "CHAOS_RU_KZ_MIXED",
        "expected_policy_section": None,
        "turns": [
            "салем, қандай қызметтер бар?",
            "маникюр бағасы қанша?",
            "қанша уақыт алады?",
            "ертеңге жазылғым келеді",
            "кешке 7-8 болады ма",
            "адрес қайда?",
            "жұмыс уақыты нешеге дейін?",
            "жеңілдік бар ма?",
            "жазып қойыңыз, имя Алия",
            "номер 87770001122",
            "спс",
        ],
    },
]

NOISE_SUFFIXES = ["плз", "пжл", "плиз", "срочно", "спс", "pls"]
PENDING_ACK_PHRASES = ["ок", "да", "жду", "ага", "можно"]
SAFE_ALLOWLIST_JID = "77015705555@s.whatsapp.net"
SAFE_ALLOWLIST_CLIENT_SLUG = "demo_salon"

CHAOS_LANG_MODES = ("ru", "kk", "mixed")
CHAOS_FILLERS = ["слушай", "короче", "ээ", "ну", "если честно"]
CHAOS_INTERJECTIONS = ["блин", "капец", "ахаха", "мм", "ппц"]
CHAOS_SERVICE_PATTERNS = [
    "{service}",
    "мне бы {service}",
    "хочу {service}",
    "{service} надо",
    "нужен {service}",
]
CHAOS_TIME_PATTERNS = [
    "{time}",
    "на {time}",
    "в {time}",
    "после обеда",
    "к вечеру",
    "часов в {hour}",
    "к {hour}",
]
CHAOS_TIME_HOURS = ["5", "6", "7", "8", "9", "10", "11"]
CHAOS_NAME_PATTERNS = [
    "{name}",
    "меня зовут {name}",
    "я {name}",
    "это {name}",
]
CHAOS_CORRECTIONS = ["ой нет", "не, лучше", "передумал, давайте", "ой, не так"]
CHAOS_SERVICES = [
    "маникюр",
    "педикюр",
    "окрашивание",
    "стрижка",
    "брови",
    "ресницы",
]
CHAOS_NAMES = ["Алия", "Айгерим", "Дина", "Нуржан", "Мадина", "Азиз", "Арман"]
CHAOS_TIMES = [
    "завтра в 7",
    "в пятницу утром",
    "сегодня после обеда",
    "ертең кешке",
    "сенбі түсте",
    "жұма күні кешке",
    "после обеда",
    "к вечеру",
    "часов в 7",
]
CHAOS_CONNECTORS = {
    "ru": ["и", "а еще", "также", "плюс"],
    "kk": ["және", "тағы", "сонымен қатар"],
}
CHAOS_INTENT_PHRASES = {
    "greeting": {
        "ru": ["привет", "добрый день", "здравствуйте"],
        "kk": ["салем", "сәлем", "ассалаумағалейкум"],
    },
    "thanks": {
        "ru": ["спасибо", "благодарю", "спс"],
        "kk": ["рахмет", "үлкен рахмет"],
    },
    "booking": {
        "ru": ["хочу записаться", "запишите меня", "нужна запись", "можно записаться?", "нужно срочно записаться"],
        "kk": ["жазылғым келеді", "жазып қойыңыз", "жазылуға бола ма"],
    },
    "pricing": {
        "ru": ["сколько стоит {service}", "какая цена на {service}", "че по цене {service}"],
        "kk": ["{service} бағасы қанша", "{service} қанша тұрады"],
    },
    "address": {
        "ru": ["где вы находитесь", "адрес где", "как до вас добраться", "скиньте адрес"],
        "kk": ["мекенжай қайда", "қайда орналасқансыз"],
    },
    "hours": {
        "ru": ["до скольки работаете", "график работы какой", "во сколько открываетесь"],
        "kk": ["жұмыс уақыты нешеге дейін", "қашанға дейін ашық"],
    },
    "duration": {
        "ru": ["сколько по времени", "длительность какая"],
        "kk": ["қанша уақыт алады", "уақыты қанша"],
    },
    "discount": {
        "ru": ["есть скидка", "какие акции сейчас", "можно скидку", "скидос есть?"],
        "kk": ["жеңілдік бар ма", "акция бар ма"],
    },
    "payment": {
        "ru": ["можно оплатить картой", "есть каспи", "можно переводом", "каспи ред есть?"],
        "kk": ["картамен төлеуге бола ма", "каспи бар ма"],
    },
    "refund": {
        "ru": ["хочу вернуть деньги", "нужен возврат денег"],
        "kk": ["ақшаны қайтару керек", "қайтарым жасайсыздар ма"],
    },
    "medical": {
        "ru": ["у меня аллергия", "после процедуры жжет", "можно беременным"],
        "kk": ["аллергия бар", "жанып тұр", "жүкті болса бола ма"],
    },
    "complaint": {
        "ru": ["жалоба на услугу", "я недоволен качеством"],
        "kk": ["шағым бар", "қызметке наразымын"],
    },
    "reschedule": {
        "ru": ["перенесите запись", "поменять дату записи"],
        "kk": ["жазбаны ауыстыру", "күні өзгерту керек"],
    },
    "human": {
        "ru": ["хочу менеджера", "свяжите с администратором"],
        "kk": ["менеджер керек", "администратормен байланыс"],
    },
    "opt_out": {
        "ru": ["не пишите", "стоп", "отстаньте"],
        "kk": ["жазбаңыз", "тоқта", "кедергі жасамаңыз"],
    },
    "ood": {
        "ru": ["какая погода", "курс доллара", "закажите пиццу", "а вы бот?", "что по пробкам"],
        "kk": ["ауа райы қандай", "доллар бағамы", "пицца заказ"],
    },
}
CHAOS_CONSULT_TRIGGERS = [
    ("hair_aftercolor", "уход после окрашивания"),
    ("hair_aftercolor", "бояудан кейін күтім"),
    ("hair_damage", "сухие волосы"),
    ("hair_damage", "волосы ломаются"),
    ("hair_color_choice", "какой оттенок мне подойдет"),
    ("nails_care", "ломкие ногти"),
    ("nails_care", "уход за ногтями"),
    ("brows_lashes_care", "уход за ресницами"),
    ("sensitive_skin", "чувствительная кожа"),
]
CHAOS_INTENT_PRIORITY = [
    "hard_law",
    "policy",
    "opt_out",
    "human",
    "booking",
    "consult",
    "info",
    "greeting",
    "thanks",
    "ood",
]
CHAOS_POLICY_MAP = {
    "discount": "discounts",
    "payment": "payment_info",
}
CHAOS_HARD_LAW = {"refund", "medical", "complaint", "reschedule"}
CHAOS_INFO = {"pricing", "address", "hours", "duration"}
CHAOS_RAG_TOP_N = 10
CHAOS_IN_DOMAIN_INTENTS = (
    set(CHAOS_INFO)
    | set(CHAOS_POLICY_MAP.keys())
    | set(CHAOS_HARD_LAW)
    | {"booking", "consult", "service", "time", "name", "greeting", "thanks"}
)
CHAOS_PENDING_STATUS = [
    "когда ответит менеджер?",
    "когда будет ответ?",
    "менеджер жауап бере ме?",
]
CHAOS_PENDING_ACK = PENDING_ACK_PHRASES
CHAOS_PENDING_WAIT = ["спасибо", "рахмет", "понял", "ждете", "окей"]


def _chaos_pick(rng, items):
    return rng.choice(items)


def _chaos_pick_lang_mode(rng):
    return rng.choices(CHAOS_LANG_MODES, weights=[0.5, 0.2, 0.3], k=1)[0]


def _chaos_pick_phrase(rng, intent_key, lang_mode):
    phrases = CHAOS_INTENT_PHRASES.get(intent_key, {})
    if lang_mode == "mixed":
        if rng.random() < 0.5 and phrases.get("kk"):
            return _chaos_pick(rng, phrases.get("kk"))
        if phrases.get("ru"):
            return _chaos_pick(rng, phrases.get("ru"))
        if phrases.get("kk"):
            return _chaos_pick(rng, phrases.get("kk"))
    if lang_mode == "kk" and phrases.get("kk"):
        return _chaos_pick(rng, phrases.get("kk"))
    if phrases.get("ru"):
        return _chaos_pick(rng, phrases.get("ru"))
    if phrases.get("kk"):
        return _chaos_pick(rng, phrases.get("kk"))
    return ""


def _chaos_join_parts(rng, parts, lang_mode):
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    connector_lang = "ru" if lang_mode == "ru" else "kk"
    connector = _chaos_pick(rng, CHAOS_CONNECTORS.get(connector_lang, ["и"]))
    text = parts[0]
    for part in parts[1:]:
        text = f"{text}, {connector} {part}"
        if lang_mode == "mixed" and rng.random() < 0.4:
            connector = _chaos_pick(
                rng,
                CHAOS_CONNECTORS.get("kk" if connector_lang == "ru" else "ru", ["и"]),
            )
    return text


def _chaos_apply_noise(rng, text, level):
    if level == "none":
        return text
    noisy = text
    if rng.random() < 0.35:
        noisy = f"{noisy} {_chaos_pick(rng, NOISE_SUFFIXES)}"
    if level == "low":
        return noisy
    if noisy and rng.random() < 0.3:
        idx = rng.randrange(0, len(noisy))
        noisy = noisy[:idx] + noisy[idx + 1 :]
    if noisy and rng.random() < 0.25:
        idx = rng.randrange(0, len(noisy))
        noisy = noisy[:idx] + noisy[idx] + noisy[idx:]
    return noisy


def _chaos_humanize_message(rng, text, lang_mode):
    if not text:
        return text
    if rng.random() < 0.35:
        text = f"{_chaos_pick(rng, CHAOS_FILLERS)} {text}"
    if rng.random() < 0.25:
        text = f"{text} {_chaos_pick(rng, CHAOS_INTERJECTIONS)}"
    if lang_mode == "mixed" and rng.random() < 0.2:
        text = f"{text} {_chaos_pick(rng, NOISE_SUFFIXES)}"
    return text


def _chaos_render_intent(
    rng,
    intent_key,
    *,
    lang_mode,
    service=None,
    name=None,
    time_value=None,
    include_service=True,
):
    if intent_key == "service":
        value = service or _chaos_pick(rng, CHAOS_SERVICES)
        pattern = _chaos_pick(rng, CHAOS_SERVICE_PATTERNS)
        return pattern.format(service=value)
    if intent_key == "time":
        value = time_value or _chaos_pick(rng, CHAOS_TIMES)
        pattern = _chaos_pick(rng, CHAOS_TIME_PATTERNS)
        if "{hour}" in pattern:
            return pattern.format(hour=_chaos_pick(rng, CHAOS_TIME_HOURS))
        return pattern.format(time=value)
    if intent_key == "name":
        value = name or _chaos_pick(rng, CHAOS_NAMES)
        pattern = _chaos_pick(rng, CHAOS_NAME_PATTERNS)
        return pattern.format(name=value)
    phrase = _chaos_pick_phrase(rng, intent_key, lang_mode)
    if "{service}" in phrase:
        if include_service and service:
            return phrase.format(service=service)
        return phrase.replace("{service}", "").strip()
    return phrase


def _chaos_build_message(
    rng,
    intents,
    *,
    lang_mode,
    service=None,
    name=None,
    time_value=None,
    include_service=True,
    noise="low",
):
    parts = []
    for intent_key in intents:
        parts.append(
            _chaos_render_intent(
                rng,
                intent_key,
                lang_mode=lang_mode,
                service=service,
                name=name,
                time_value=time_value,
                include_service=include_service,
            )
        )
    text = _chaos_join_parts(rng, [part for part in parts if part], lang_mode)
    text = _chaos_humanize_message(rng, text, lang_mode)
    return _chaos_apply_noise(rng, text, noise)


def _chaos_make_turn(text, intents, expected):
    return {
        "type": "user",
        "text": text,
        "intents": list(intents),
        "expected": expected,
    }


def _chaos_make_pending_turn(rng, action):
    if action == "pending_ack":
        text = _chaos_pick(rng, CHAOS_PENDING_ACK)
    elif action == "pending_wait":
        text = _chaos_pick(rng, CHAOS_PENDING_WAIT)
    else:
        text = _chaos_pick(rng, CHAOS_PENDING_STATUS)
    forbid_actions = ["booking_prompt"] + _chaos_booking_completion_actions()
    return _chaos_make_turn(
        text,
        [action],
        {
            "pending_action": action,
            "state": "pending",
            "forbid": {"action_any": forbid_actions},
        },
    )


def _chaos_make_manager_turn(action, channel):
    return {"type": "manager", "action": action, "channel": channel}


def _chaos_spread_extra(extra, slots, rng):
    if extra <= 0 or slots <= 0:
        return [0] * max(slots, 0)
    counts = [0] * slots
    for _ in range(extra):
        counts[rng.randrange(0, slots)] += 1
    return counts


def _chaos_pick_handoff_channel(rng):
    return rng.choices(["telegram", "console"], weights=[0.6, 0.4], k=1)[0]


def _chaos_booking_completion_actions():
    return [
        "booking_escalated",
        "booking_captured_pending",
        "booking_reuse_handover",
    ]


def _chaos_build_booking_case(rng, case_id, min_turns, max_turns, noise):
    lang_mode = _chaos_pick_lang_mode(rng)
    service = _chaos_pick(rng, CHAOS_SERVICES)
    name = _chaos_pick(rng, CHAOS_NAMES)
    time_value = _chaos_pick(rng, CHAOS_TIMES)
    target_turns = rng.randint(min_turns, max_turns)
    base_turns = 6
    extra_turns = max(target_turns - base_turns, 0)
    interrupt_counts = _chaos_spread_extra(extra_turns, 5, rng)
    turns = []
    expected_reply_type = None

    intents = ["booking"]
    if rng.random() < 0.6:
        intents.append("greeting")
    if rng.random() < 0.5:
        primary_info = _chaos_pick(rng, list(CHAOS_INFO))
        intents.append(primary_info)
        if rng.random() < 0.35:
            extra_pool = [item for item in CHAOS_INFO if item != primary_info]
            if extra_pool:
                intents.append(_chaos_pick(rng, extra_pool))
    include_service = rng.random() < 0.4
    if any(item in {"pricing", "duration"} for item in intents):
        include_service = True
    text = _chaos_build_message(
        rng,
        intents,
        lang_mode=lang_mode,
        service=service,
        include_service=include_service,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            text,
            intents,
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "service_choice",
                "state": "bot_active",
            },
        )
    )
    expected_reply_type = "service_choice"

    for _ in range(interrupt_counts[0]):
        info_intent = _chaos_pick(rng, list(CHAOS_INFO))
        text = _chaos_build_message(
            rng,
            [info_intent],
            lang_mode=lang_mode,
            service=service,
            noise=noise,
        )
        turns.append(
            _chaos_make_turn(
                text,
                [info_intent],
                {
                    "action_any": ["reply"],
                    "booking_interrupt": True,
                    "expected_reply_type": expected_reply_type,
                    "state": "bot_active",
                },
            )
        )

    text = _chaos_build_message(
        rng,
        ["service"],
        lang_mode=lang_mode,
        service=service,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            text,
            ["service"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "time",
                "state": "bot_active",
            },
        )
    )
    expected_reply_type = "time"

    for _ in range(interrupt_counts[1]):
        info_intent = _chaos_pick(rng, list(CHAOS_INFO))
        text = _chaos_build_message(
            rng,
            [info_intent],
            lang_mode=lang_mode,
            service=service,
            noise=noise,
        )
        turns.append(
            _chaos_make_turn(
                text,
                [info_intent],
                {
                    "action_any": ["reply"],
                    "booking_interrupt": True,
                    "expected_reply_type": expected_reply_type,
                    "state": "bot_active",
                },
            )
        )

    text = _chaos_build_message(
        rng,
        ["time"],
        lang_mode=lang_mode,
        time_value=time_value,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            text,
            ["time"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "name",
                "state": "bot_active",
            },
        )
    )
    expected_reply_type = "name"

    for _ in range(interrupt_counts[2]):
        info_intent = _chaos_pick(rng, list(CHAOS_INFO))
        text = _chaos_build_message(
            rng,
            [info_intent],
            lang_mode=lang_mode,
            service=service,
            noise=noise,
        )
        turns.append(
            _chaos_make_turn(
                text,
                [info_intent],
                {
                    "action_any": ["reply"],
                    "booking_interrupt": True,
                    "expected_reply_type": expected_reply_type,
                    "state": "bot_active",
                },
            )
        )

    if rng.random() < 0.45:
        correction_prefix = _chaos_pick(rng, CHAOS_CORRECTIONS)
        correction_time = _chaos_build_message(
            rng,
            ["time"],
            lang_mode=lang_mode,
            time_value=time_value,
            noise=noise,
        )
        turns.append(
            _chaos_make_turn(
                f"{correction_prefix}, {correction_time}",
                ["time"],
                {
                    "action_any": ["booking_prompt"],
                    "expected_reply_type": expected_reply_type,
                    "state": "bot_active",
                },
            )
        )

    text = _chaos_build_message(
        rng,
        ["name"],
        lang_mode=lang_mode,
        name=name,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            text,
            ["name"],
            {
                "action_any": _chaos_booking_completion_actions(),
                "expected_reply_type": None,
                "state": "pending",
                "handover_status": "pending",
            },
        )
    )
    expected_reply_type = None

    for _ in range(interrupt_counts[3]):
        turns.append(_chaos_make_pending_turn(rng, "pending_status"))

    turns.append(
        _chaos_make_pending_turn(rng, "pending_status")
    )

    for _ in range(interrupt_counts[4]):
        action = "pending_ack" if rng.random() < 0.6 else "pending_wait"
        turns.append(_chaos_make_pending_turn(rng, action))

    handoff_channel = _chaos_pick_handoff_channel(rng)
    turns.append(_chaos_make_manager_turn("take", handoff_channel))
    turns.append(_chaos_make_manager_turn("resolve", handoff_channel))

    turns.append(
        _chaos_make_turn(
            _chaos_build_message(
                rng,
                ["thanks"],
                lang_mode=lang_mode,
                noise=noise,
            ),
            ["thanks"],
            {
                "action_any": ["smalltalk", "reply"],
                "state": "bot_active",
            },
        )
    )

    return {
        "case_id": case_id,
        "kind": "booking",
        "lang_mode": lang_mode,
        "turns": turns,
    }


def _chaos_build_policy_case(rng, case_id, min_turns, max_turns, noise):
    lang_mode = _chaos_pick_lang_mode(rng)
    service = _chaos_pick(rng, CHAOS_SERVICES)
    target_turns = rng.randint(min_turns, max_turns)
    base_turns = 5
    extra_turns = max(target_turns - base_turns, 0)
    interrupt_counts = _chaos_spread_extra(extra_turns, 3, rng)
    turns = []

    is_hard_law = rng.random() < 0.6
    if is_hard_law:
        intent = _chaos_pick(rng, list(CHAOS_HARD_LAW))
        policy_gate = "hard_law"
    else:
        intent = _chaos_pick(rng, list(CHAOS_POLICY_MAP.keys()))
        policy_gate = CHAOS_POLICY_MAP.get(intent)

    intents = [intent]
    if rng.random() < 0.5:
        intents.append("booking")
    if rng.random() < 0.4:
        primary_info = _chaos_pick(rng, list(CHAOS_INFO))
        intents.append(primary_info)
        if rng.random() < 0.35:
            extra_pool = [item for item in CHAOS_INFO if item != primary_info]
            if extra_pool:
                intents.append(_chaos_pick(rng, extra_pool))

    text = _chaos_build_message(
        rng,
        intents,
        lang_mode=lang_mode,
        service=service,
        include_service=True,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            text,
            intents,
            {
                "policy_gate": policy_gate,
                "state": "pending",
                "handover_status": "pending",
            },
        )
    )

    for _ in range(interrupt_counts[0]):
        turns.append(_chaos_make_pending_turn(rng, "pending_status"))

    turns.append(
        _chaos_make_pending_turn(rng, "pending_status")
    )

    for _ in range(interrupt_counts[1]):
        action = "pending_ack" if rng.random() < 0.6 else "pending_wait"
        turns.append(_chaos_make_pending_turn(rng, action))

    handoff_channel = _chaos_pick_handoff_channel(rng)
    turns.append(_chaos_make_manager_turn("take", handoff_channel))
    turns.append(_chaos_make_manager_turn("resolve", handoff_channel))

    for _ in range(interrupt_counts[2]):
        text = _chaos_build_message(
            rng,
            ["booking"],
            lang_mode=lang_mode,
            service=service,
            include_service=False,
            noise=noise,
        )
        turns.append(
            _chaos_make_turn(
                text,
                ["booking"],
                {
                    "action_any": ["booking_prompt"],
                    "expected_reply_type": "service_choice",
                    "state": "bot_active",
                },
            )
        )

    return {
        "case_id": case_id,
        "kind": "policy",
        "lang_mode": lang_mode,
        "turns": turns,
    }


def _chaos_build_consult_case(rng, case_id, min_turns, max_turns, noise):
    lang_mode = _chaos_pick_lang_mode(rng)
    service = _chaos_pick(rng, CHAOS_SERVICES)
    name = _chaos_pick(rng, CHAOS_NAMES)
    time_value = _chaos_pick(rng, CHAOS_TIMES)
    target_turns = rng.randint(min_turns, max_turns)
    base_turns = 5
    extra_turns = max(target_turns - base_turns, 0)
    interrupt_counts = _chaos_spread_extra(extra_turns, 2, rng)
    turns = []

    consult_id, consult_phrase = _chaos_pick(rng, CHAOS_CONSULT_TRIGGERS)
    text = _chaos_apply_noise(rng, consult_phrase, noise)
    turns.append(
        _chaos_make_turn(
            text,
            ["consult"],
            {
                "action_any": ["reply"],
                "consult_playbook_id": consult_id,
                "state": "bot_active",
            },
        )
    )

    for _ in range(interrupt_counts[0]):
        info_intent = _chaos_pick(rng, list(CHAOS_INFO))
        info_text = _chaos_build_message(
            rng,
            [info_intent],
            lang_mode=lang_mode,
            service=service,
            noise=noise,
        )
        turns.append(
            _chaos_make_turn(
                info_text,
                [info_intent],
                {
                    "action_any": ["reply"],
                    "state": "bot_active",
                },
            )
        )

    booking_text = _chaos_build_message(
        rng,
        ["booking"],
        lang_mode=lang_mode,
        service=service,
        include_service=False,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            booking_text,
            ["booking"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "service_choice",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["service"], lang_mode=lang_mode, service=service, noise=noise),
            ["service"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "time",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["time"], lang_mode=lang_mode, time_value=time_value, noise=noise),
            ["time"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "name",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["name"], lang_mode=lang_mode, name=name, noise=noise),
            ["name"],
            {
                "action_any": _chaos_booking_completion_actions(),
                "expected_reply_type": None,
                "state": "pending",
                "handover_status": "pending",
            },
        )
    )

    handoff_channel = _chaos_pick_handoff_channel(rng)
    turns.append(_chaos_make_manager_turn("resolve", handoff_channel))

    for _ in range(interrupt_counts[1]):
        turns.append(
            _chaos_make_turn(
                _chaos_build_message(rng, ["thanks"], lang_mode=lang_mode, noise=noise),
                ["thanks"],
                {"action_any": ["smalltalk", "reply"], "state": "bot_active"},
            )
        )

    return {
        "case_id": case_id,
        "kind": "consult",
        "lang_mode": lang_mode,
        "turns": turns,
    }


def _chaos_build_info_case(rng, case_id, min_turns, max_turns, noise):
    lang_mode = _chaos_pick_lang_mode(rng)
    service = _chaos_pick(rng, CHAOS_SERVICES)
    name = _chaos_pick(rng, CHAOS_NAMES)
    time_value = _chaos_pick(rng, CHAOS_TIMES)
    target_turns = rng.randint(min_turns, max_turns)
    base_turns = 5
    extra_turns = max(target_turns - base_turns, 0)
    interrupt_counts = _chaos_spread_extra(extra_turns, 2, rng)
    turns = []

    info_intents = ["address", "hours"]
    if rng.random() < 0.4:
        extra_pool = [item for item in CHAOS_INFO if item not in info_intents]
        if extra_pool:
            info_intents.append(_chaos_pick(rng, extra_pool))
    info_text = _chaos_build_message(
        rng,
        info_intents,
        lang_mode=lang_mode,
        service=service,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            info_text,
            info_intents,
            {
                "action_any": ["reply"],
                "info_sections": list(info_intents),
                "state": "bot_active",
            },
        )
    )

    for _ in range(interrupt_counts[0]):
        info_intent = _chaos_pick(rng, list(CHAOS_INFO))
        text = _chaos_build_message(
            rng,
            [info_intent],
            lang_mode=lang_mode,
            service=service,
            noise=noise,
        )
        turns.append(
            _chaos_make_turn(
                text,
                [info_intent],
                {"action_any": ["reply"], "state": "bot_active"},
            )
        )

    booking_text = _chaos_build_message(
        rng,
        ["booking"],
        lang_mode=lang_mode,
        service=service,
        include_service=False,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            booking_text,
            ["booking"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "service_choice",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["service"], lang_mode=lang_mode, service=service, noise=noise),
            ["service"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "time",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["time"], lang_mode=lang_mode, time_value=time_value, noise=noise),
            ["time"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "name",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["name"], lang_mode=lang_mode, name=name, noise=noise),
            ["name"],
            {
                "action_any": _chaos_booking_completion_actions(),
                "expected_reply_type": None,
                "state": "pending",
                "handover_status": "pending",
            },
        )
    )
    handoff_channel = _chaos_pick_handoff_channel(rng)
    turns.append(_chaos_make_manager_turn("resolve", handoff_channel))

    for _ in range(interrupt_counts[1]):
        turns.append(
            _chaos_make_turn(
                _chaos_build_message(rng, ["thanks"], lang_mode=lang_mode, noise=noise),
                ["thanks"],
                {"action_any": ["smalltalk", "reply"], "state": "bot_active"},
            )
        )

    return {
        "case_id": case_id,
        "kind": "info",
        "lang_mode": lang_mode,
        "turns": turns,
    }


def _chaos_build_ood_case(rng, case_id, min_turns, max_turns, noise):
    lang_mode = _chaos_pick_lang_mode(rng)
    service = _chaos_pick(rng, CHAOS_SERVICES)
    name = _chaos_pick(rng, CHAOS_NAMES)
    time_value = _chaos_pick(rng, CHAOS_TIMES)
    target_turns = rng.randint(min_turns, max_turns)
    base_turns = 5
    extra_turns = max(target_turns - base_turns, 0)
    interrupt_counts = _chaos_spread_extra(extra_turns, 2, rng)
    turns = []

    ood_text = _chaos_build_message(
        rng,
        ["ood"],
        lang_mode=lang_mode,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            ood_text,
            ["ood"],
            {"action_any": ["out_of_domain"], "state": "bot_active"},
        )
    )

    for _ in range(interrupt_counts[0]):
        turns.append(
            _chaos_make_turn(
                _chaos_build_message(rng, ["greeting"], lang_mode=lang_mode, noise=noise),
                ["greeting"],
                {"action_any": ["smalltalk", "reply"], "state": "bot_active"},
            )
        )

    booking_text = _chaos_build_message(
        rng,
        ["booking"],
        lang_mode=lang_mode,
        service=service,
        include_service=False,
        noise=noise,
    )
    turns.append(
        _chaos_make_turn(
            booking_text,
            ["booking"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "service_choice",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["service"], lang_mode=lang_mode, service=service, noise=noise),
            ["service"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "time",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["time"], lang_mode=lang_mode, time_value=time_value, noise=noise),
            ["time"],
            {
                "action_any": ["booking_prompt"],
                "expected_reply_type": "name",
                "state": "bot_active",
            },
        )
    )
    turns.append(
        _chaos_make_turn(
            _chaos_build_message(rng, ["name"], lang_mode=lang_mode, name=name, noise=noise),
            ["name"],
            {
                "action_any": _chaos_booking_completion_actions(),
                "expected_reply_type": None,
                "state": "pending",
                "handover_status": "pending",
            },
        )
    )
    handoff_channel = _chaos_pick_handoff_channel(rng)
    turns.append(_chaos_make_manager_turn("resolve", handoff_channel))

    for _ in range(interrupt_counts[1]):
        turns.append(
            _chaos_make_turn(
                _chaos_build_message(rng, ["thanks"], lang_mode=lang_mode, noise=noise),
                ["thanks"],
                {"action_any": ["smalltalk", "reply"], "state": "bot_active"},
            )
        )

    return {
        "case_id": case_id,
        "kind": "ood",
        "lang_mode": lang_mode,
        "turns": turns,
    }


def _chaos_generate_cases(count, rng, min_turns, max_turns, noise):
    cases = []
    builders = [
        ("booking", _chaos_build_booking_case, 0.45),
        ("policy", _chaos_build_policy_case, 0.25),
        ("consult", _chaos_build_consult_case, 0.15),
        ("info", _chaos_build_info_case, 0.1),
        ("ood", _chaos_build_ood_case, 0.05),
    ]
    weights = [item[2] for item in builders]
    for idx in range(1, count + 1):
        kind, builder, _ = rng.choices(builders, weights=weights, k=1)[0]
        case_id = f"CHAOS_{kind.upper()}_{idx:04d}"
        cases.append(builder(rng, case_id, min_turns, max_turns, noise))
    return cases


def _chaos_matches_action(meta, expected_actions):
    if not expected_actions:
        return True
    action = (meta or {}).get("action")
    pending_action = (meta or {}).get("pending_action")
    return action in expected_actions or pending_action in expected_actions


def _chaos_trace_has_stage_with_reason(trace_entries, stage, reason=None):
    for entry in trace_entries or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("stage") != stage:
            continue
        if reason is None or entry.get("reason") == reason:
            return True
    return False


def _chaos_info_sections_match(meta, expected_sections):
    if not expected_sections:
        return True
    info_sections = (meta or {}).get("info_sections")
    if not isinstance(info_sections, list):
        return False
    return all(section in info_sections for section in expected_sections)


def _chaos_action_fallback_ok(expected, meta, conv_meta, trace_entries, info_sections_ok):
    expected_actions = expected.get("action_any") or []
    meta_action = (meta or {}).get("action")
    if "reply" in expected_actions and expected.get("info_sections") and info_sections_ok:
        if meta_action in _chaos_booking_completion_actions() or meta_action == "booking_prompt":
            return True
    if "booking_prompt" in expected_actions and meta_action == "reply":
        expected_reply_type = expected.get("expected_reply_type")
        if expected_reply_type is not None:
            actual_reply = _chaos_extract_expected_reply((conv_meta or {}).get("context"))
            if actual_reply == expected_reply_type:
                return True
        if _chaos_trace_has_stage_with_reason(trace_entries, "question_contract", "booking_prompt"):
            return True
    return False


def _chaos_extract_expected_reply(context):
    if not isinstance(context, dict):
        return None
    value = context.get("expected_reply_type")
    if isinstance(value, str):
        return value.strip()
    return value


def _chaos_intent_set(turn):
    intents = set()
    for item in turn.get("intents") or []:
        if isinstance(item, str):
            intents.add(item)
    return intents


def _chaos_trace_has_stage(trace_entries, stage):
    for entry in trace_entries or []:
        if isinstance(entry, dict) and entry.get("stage") == stage:
            return True
    return False


def _chaos_rag_status(rag_confident, rag_reason):
    if rag_confident is True:
        return "confident"
    if rag_confident is False:
        if isinstance(rag_reason, str) and rag_reason.strip():
            return rag_reason.strip()
        if rag_reason is None:
            return "not_confident"
        return str(rag_reason)
    return "missing"


def _chaos_extract_rag_scores(trace_entries):
    for entry in trace_entries or []:
        if isinstance(entry, dict):
            rag_scores = entry.get("rag_scores")
            if isinstance(rag_scores, dict):
                return rag_scores
    return None


def _chaos_extract_rag_filter(trace_entries):
    for entry in trace_entries or []:
        if isinstance(entry, dict):
            rag_filter = entry.get("rag_filter")
            if isinstance(rag_filter, dict):
                return rag_filter
    return None


def _chaos_best_rag_score(rag_scores):
    if not isinstance(rag_scores, dict):
        return None
    best = None
    for key in ("hybrid_max", "vector_max", "bm25_max"):
        value = rag_scores.get(key)
        if isinstance(value, (int, float)):
            best = value if best is None else max(best, value)
    return best


def _chaos_build_rag_record(
    *,
    case,
    turn,
    turn_idx,
    message_id,
    conversation_id,
    meta,
    trace_entries,
    noise_level,
    response_status,
):
    intent_set = _chaos_intent_set(turn)
    intent_bucket = (
        "in_domain" if intent_set.intersection(CHAOS_IN_DOMAIN_INTENTS) else "out_of_domain"
    )
    rag_confident = (meta or {}).get("rag_confident")
    rag_reason = (meta or {}).get("rag_reason")
    rag_scores = (meta or {}).get("rag_scores") if isinstance(meta, dict) else None
    if not isinstance(rag_scores, dict):
        rag_scores = _chaos_extract_rag_scores(trace_entries)
    rag_best_score = _chaos_best_rag_score(rag_scores)
    rag_filter = _chaos_extract_rag_filter(trace_entries)
    rag_filter_reason = rag_filter.get("filter_reason") if isinstance(rag_filter, dict) else None
    rag_status = _chaos_rag_status(rag_confident, rag_reason)
    record = {
        "case_id": case.get("case_id"),
        "kind": case.get("kind"),
        "lang_mode": case.get("lang_mode"),
        "noise": noise_level,
        "turn": turn_idx,
        "message_id": message_id,
        "conversation_id": conversation_id,
        "text": turn.get("text"),
        "intents": sorted(intent_set),
        "intent_bucket": intent_bucket,
        "rag_status": rag_status,
        "rag_confident": rag_confident,
        "rag_reason": rag_reason,
        "rag_best_score": rag_best_score,
        "rag_scores": rag_scores,
        "rag_filter": rag_filter,
        "rag_filter_reason": rag_filter_reason,
        "action": (meta or {}).get("action"),
        "policy_gate": (meta or {}).get("policy_gate"),
        "response_status": response_status,
    }
    pattern = (
        f"{case.get('lang_mode')}|{noise_level}|{intent_bucket}|{rag_status}|"
        f"{rag_filter_reason or 'missing'}"
    )
    flags = {
        "low_score_in_domain": intent_bucket == "in_domain"
        and rag_status in {"low_score", "empty"},
        "high_score_out_of_domain": intent_bucket == "out_of_domain" and rag_confident is True,
        "branch_filter_missing": rag_filter_reason == "branch_missing",
        "branch_filter_empty": rag_filter_reason == "branch_filter_empty",
    }
    return record, pattern, flags


def _chaos_update_rag_summary(summary, record, pattern, flags):
    summary["total_turns"] += 1
    rag_status = record.get("rag_status") or "missing"
    status_counts = summary.setdefault("rag_status_counts", {})
    status_counts[rag_status] = status_counts.get(rag_status, 0) + 1
    if rag_status == "confident":
        summary["rag_confident"] += 1
    elif rag_status == "low_score":
        summary["rag_low_score"] += 1
    elif rag_status == "empty":
        summary["rag_empty"] += 1
    elif rag_status == "overridden_by_gate":
        summary["rag_overridden_by_gate"] += 1
    elif rag_status == "missing":
        summary["rag_missing"] += 1
    if flags.get("low_score_in_domain"):
        summary["low_score_in_domain"] += 1
    if flags.get("high_score_out_of_domain"):
        summary["high_score_out_of_domain"] += 1
    if flags.get("branch_filter_missing"):
        summary["branch_filter_missing"] += 1
    if flags.get("branch_filter_empty"):
        summary["branch_filter_empty"] += 1
    lang_counts = summary.setdefault("lang_mode_counts", {})
    lang_mode = record.get("lang_mode") or "unknown"
    lang_counts[lang_mode] = lang_counts.get(lang_mode, 0) + 1
    noise_counts = summary.setdefault("noise_counts", {})
    noise_level = record.get("noise") or "unknown"
    noise_counts[noise_level] = noise_counts.get(noise_level, 0) + 1
    intent_counts = summary.setdefault("intent_bucket_counts", {})
    intent_bucket = record.get("intent_bucket") or "unknown"
    intent_counts[intent_bucket] = intent_counts.get(intent_bucket, 0) + 1
    patterns = summary.setdefault("patterns", {})
    patterns[pattern] = patterns.get(pattern, 0) + 1


def _chaos_evaluate_turn(
    *,
    turn,
    meta,
    conv_meta,
    handover_meta,
    trace_entries,
):
    failures = []
    expected = turn.get("expected") or {}
    intent_set = _chaos_intent_set(turn)
    meta_action = (meta or {}).get("action")
    meta_intent = (meta or {}).get("intent")
    meta_policy_gate = (meta or {}).get("policy_gate")
    if meta is None:
        failures.append("missing_decision_meta")
    if expected.get("policy_gate") and (meta or {}).get("policy_gate") != expected.get("policy_gate"):
        failures.append("policy_gate_mismatch")
    if expected.get("consult_playbook_id") and (
        (meta or {}).get("consult_playbook_id") != expected.get("consult_playbook_id")
    ):
        failures.append("consult_playbook_mismatch")
    expected_sections = expected.get("info_sections") or []
    info_sections_ok = _chaos_info_sections_match(meta, expected_sections)
    if expected_sections and not info_sections_ok:
        failures.append("info_sections_mismatch")
    if expected.get("booking_interrupt") and not (meta or {}).get("booking_info_interrupt"):
        failures.append("booking_interrupt_missing")
    if expected.get("action_any") and not _chaos_matches_action(meta, expected.get("action_any")):
        if not _chaos_action_fallback_ok(expected, meta, conv_meta, trace_entries, info_sections_ok):
            failures.append("action_mismatch")
    forbid = expected.get("forbid") if isinstance(expected.get("forbid"), dict) else {}
    if forbid:
        forbidden_actions = forbid.get("action_any") or []
        if forbidden_actions and _chaos_matches_action(meta, forbidden_actions):
            failures.append("forbidden_action")
        forbidden_policies = forbid.get("policy_gate_any") or []
        if forbidden_policies and meta_policy_gate in forbidden_policies:
            failures.append("forbidden_policy_gate")
        forbidden_sources = forbid.get("fact_source_any") or []
        if forbidden_sources and (meta or {}).get("fact_source") in forbidden_sources:
            failures.append("forbidden_fact_source")
        forbidden_intents = forbid.get("intent_any") or []
        if forbidden_intents and meta_intent in forbidden_intents:
            failures.append("forbidden_intent")
        forbidden_stages = forbid.get("trace_stage_any") or []
        if forbidden_stages and any(
            _chaos_trace_has_stage(trace_entries, stage) for stage in forbidden_stages
        ):
            failures.append("forbidden_trace_stage")
    if expected.get("pending_action") and (meta or {}).get("pending_action") != expected.get("pending_action"):
        failures.append("pending_action_mismatch")
    expected_state = expected.get("state")
    if expected_state and (conv_meta or {}).get("state") != expected_state:
        failures.append("state_mismatch")
    expected_reply_type = expected.get("expected_reply_type")
    if expected_reply_type is not None:
        actual_reply = _chaos_extract_expected_reply((conv_meta or {}).get("context"))
        if actual_reply != expected_reply_type:
            failures.append("expected_reply_type_mismatch")
    expected_handover_status = expected.get("handover_status")
    if expected_handover_status and (handover_meta or {}).get("status") != expected_handover_status:
        failures.append("handover_status_mismatch")
    if not trace_entries:
        failures.append("missing_decision_trace")
    if meta_policy_gate and not (
        intent_set.intersection(set(CHAOS_POLICY_MAP.keys())) or intent_set.intersection(CHAOS_HARD_LAW)
    ):
        failures.append("policy_gate_false_positive")
    if _chaos_trace_has_stage(trace_entries, "out_of_domain") and intent_set.intersection(
        CHAOS_IN_DOMAIN_INTENTS
    ):
        failures.append("ood_false_positive")
    return failures


def _chaos_build_failure_patterns(failures, meta, conv_meta):
    patterns = []
    action = (meta or {}).get("action") or "none"
    intent = (meta or {}).get("intent") or (meta or {}).get("controller_goal") or "none"
    policy_gate = (meta or {}).get("policy_gate") or "none"
    expected_reply_type = _chaos_extract_expected_reply((conv_meta or {}).get("context")) or "none"
    for failure in failures:
        patterns.append(
            " | ".join(
                [
                    failure,
                    f"action={action}",
                    f"intent={intent}",
                    f"expected_reply_type={expected_reply_type}",
                    f"policy_gate={policy_gate}",
                ]
            )
        )
    return patterns


def _resolve_chaos_jid_base(simulation_id: str, seed: int | None) -> int:
    env_base = os.environ.get("CHAOS_JID_BASE")
    if env_base and env_base.isdigit():
        return int(env_base)
    digits = "".join(ch for ch in simulation_id if ch.isdigit())
    offset = int(digits[-6:]) if digits else int(seed or 0) % 1000000
    offset = (offset + int(seed or 0)) % 1000000
    return 79990000000 + (offset * 1000)

def _parse_livecheck_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py livecheck",
        description="Run live-check runner via ChatFlow send-text.",
    )
    parser.add_argument("--suite", default="ca01-core", choices=sorted(LIVECHECK_SUITES.keys()))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-wait", type=float, default=5.0)
    parser.add_argument("--max-wait", type=float, default=15.0)
    parser.add_argument("--noise", choices=["none", "low"], default="low")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)

def _parse_livecheck_auto_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py livecheck-auto",
        description="Run webhook live-check with auto-ACK and DB polling.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRUFFLES_API_BASE_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--client-slug",
        default=os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon"),
    )
    parser.add_argument("--suite", default="ca01-core", choices=sorted(LIVECHECK_SUITES.keys()))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-wait", type=float, default=1.0)
    parser.add_argument("--max-wait", type=float, default=3.0)
    parser.add_argument("--noise", choices=["none", "low"], default="low")
    parser.add_argument("--case-ids", default=None)
    parser.add_argument("--jid-mode", choices=["unique", "allowlist"], default="allowlist")
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--allowlist-jids", default=None)
    parser.add_argument("--allow-non-allowlist", action="store_true")
    parser.add_argument("--webhook-secret", default=None)
    parser.add_argument("--admin-token", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--ack-text", default="ок")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--poll-timeout", type=float, default=20.0)
    parser.add_argument("--fail-fast-after", type=float, default=8.0)
    parser.add_argument("--reset-before-suite", action="store_true")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)

def _parse_send_text_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py send-text",
        description="Send one ChatFlow message.",
    )
    parser.add_argument("--text", default=None)
    parser.add_argument("--marker-prefix", default=None)
    parser.add_argument("--append-marker", action="store_true")
    parser.add_argument("--token", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--jid", default=None)
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)

def _parse_send_and_explain_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py send-and-explain",
        description="Send one ChatFlow message and run explain.",
    )
    parser.add_argument("--text", default=None)
    parser.add_argument("--marker-prefix", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--jid", default=None)
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--receiver-phone", default=None)
    parser.add_argument("--client-slug", default=None)
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--minutes", type=int, default=120)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--traefik", action="store_true")
    parser.add_argument("--wait-seconds", type=float, default=5.0)
    return parser.parse_args(argv)

def _apply_noise(text, rng, level):
    if level == "none":
        return text
    suffix = rng.choice(NOISE_SUFFIXES)
    return f"{text} {suffix}"

def _build_marker(prefix):
    normalized = (prefix or "").strip().replace(" ", "_")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{normalized}-{timestamp}"

def _send_chatflow_message(api_url, token, instance_id, jid, message, timeout):
    params = {
        "token": token,
        "instance_id": instance_id,
        "jid": jid,
        "msg": message,
    }
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{api_url}?{query}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body

def _resolve_send_text_config(args):
    token = args.token or os.environ.get("CHATFLOW_TOKEN")
    instance_id = args.instance_id or os.environ.get("CHATFLOW_INSTANCE_ID")
    jid = args.jid or os.environ.get("CHATFLOW_JID")
    api_url = args.api_url or os.environ.get("CHATFLOW_API_URL", "https://app.chatflow.kz/api/v1/send-text")
    timeout = args.timeout
    if timeout is None:
        timeout = float(os.environ.get("CHATFLOW_TIMEOUT_SECONDS", "30"))
    if not token or not instance_id or not jid:
        raise SystemExit("send-text: missing token/instance-id/jid (use args or env)")

    marker = None
    text = args.text
    if not text:
        if not args.marker_prefix:
            raise SystemExit("send-text: provide --text or --marker-prefix")
        marker = _build_marker(args.marker_prefix)
        text = marker
    else:
        if args.append_marker or args.marker_prefix:
            marker = _build_marker(args.marker_prefix or "LC-MARKER")
            text = f"{text} [{marker}]"

    return token, instance_id, jid, api_url, timeout, text, marker

def _run_send_text(args, *, return_result=False):
    token, instance_id, jid, api_url, timeout, text, marker = _resolve_send_text_config(args)
    sent_at = datetime.now(timezone.utc).isoformat()
    status = "dry_run"
    response_status = None
    response_body = None
    if not args.dry_run:
        response_status, response_body = _send_chatflow_message(
            api_url, token, instance_id, jid, text, timeout
        )
        status = "sent" if response_status == 200 else "error"
    result = {
        "instance_id": instance_id,
        "jid": jid,
        "marker": marker,
        "text": text,
        "sent_at": sent_at,
        "status": status,
        "http_status": response_status,
        "response": (response_body or "")[:200] if response_body else None,
    }
    print(json.dumps({"send_text": result}, ensure_ascii=False))
    if return_result:
        return result
    return None

def _run_send_and_explain(args):
    if not args.receiver_phone and not args.client_slug:
        raise SystemExit("send-and-explain: provide --receiver-phone or --client-slug")
    if not args.marker_prefix:
        args.marker_prefix = "LC-EXPLAIN"
    args.append_marker = True
    send_result = _run_send_text(args, return_result=True)
    marker = send_result.get("marker")
    search_text = marker or args.text
    if not search_text:
        raise SystemExit("send-and-explain: missing marker/text for explain")
    wait_seconds = float(args.wait_seconds or 0)
    if wait_seconds > 0:
        time.sleep(wait_seconds)
    explain_argv = []
    if args.client_slug:
        explain_argv += ["--client-slug", args.client_slug]
    if args.receiver_phone:
        explain_argv += ["--receiver-phone", args.receiver_phone]
    if args.remote_jid:
        explain_argv += ["--remote-jid", args.remote_jid]
    explain_argv += [
        "--text",
        search_text,
        "--minutes",
        str(int(args.minutes)),
        "--limit",
        str(int(args.limit)),
    ]
    if args.traefik:
        explain_argv.append("--traefik")
    _run_explain(_parse_explain_args(explain_argv))

def _parse_webhook_fuzz_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py webhook-fuzz",
        description="Send webhook fuzz batch directly to /webhook/{client_slug}.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRUFFLES_API_BASE_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--client-slug",
        default=os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon"),
    )
    parser.add_argument("--mode", choices=["logic", "state"], default="logic")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-wait", type=float, default=0.5)
    parser.add_argument("--max-wait", type=float, default=2.0)
    parser.add_argument("--noise", choices=["none", "low"], default="low")
    parser.add_argument("--case-ids", default=None)
    parser.add_argument("--allowlist-jids", default=None)
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--webhook-secret", default=None)
    parser.add_argument("--admin-token", default=None)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--skip-outbox", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def _parse_chaos_sim_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py chaos-sim",
        description="Run chaos simulation against /webhook with decision_meta/trace evaluation.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRUFFLES_API_BASE_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--client-slug",
        default=os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon"),
    )
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-turns", type=int, default=10)
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--noise", choices=["none", "low", "high"], default="low")
    parser.add_argument("--mode", choices=["logic", "llm"], default="logic")
    parser.add_argument("--webhook-secret", default=None)
    parser.add_argument("--admin-token", default=None)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--poll-timeout", type=float, default=20.0)
    parser.add_argument("--poll-interval", type=float, default=0.6)
    parser.add_argument("--min-wait", type=float, default=0.3)
    parser.add_argument("--max-wait", type=float, default=1.2)
    parser.add_argument("--outbox-wait", type=float, default=None)
    parser.add_argument("--skip-outbox", action="store_true")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--simulation-id", default=None)
    parser.add_argument("--dump-cases", action="store_true")
    parser.add_argument("--console-base-url", default=os.environ.get("CONSOLE_API_BASE_URL"))
    parser.add_argument("--console-token", default=None)
    parser.add_argument("--console-env", default="/home/zhan/secrets/console-contract.env")
    parser.add_argument("--console-client-id", default=None)
    parser.add_argument("--console-mode", choices=["real", "skip"], default="real")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug-all", action="store_true")
    parser.add_argument("--rag-audit", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)

def _parse_explain_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py explain",
        description="Explain inbound processing by message marker/id.",
    )
    parser.add_argument(
        "--client-slug",
        default=None,
    )
    parser.add_argument(
        "--receiver-phone",
        default=None,
        help="Receiver phone (branches.phone) to auto-resolve client_slug.",
    )
    parser.add_argument("--text", default=None, help="Substring of inbound message text.")
    parser.add_argument("--message-id", default=None, help="ChatFlow metadata.messageId value.")
    parser.add_argument("--message-uuid", default=None, help="messages.id UUID.")
    parser.add_argument("--conversation-id", default=None)
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--minutes", type=int, default=120)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--traefik", action="store_true")
    parser.add_argument("--traefik-minutes", type=int, default=120)
    args = parser.parse_args(argv)
    if not args.client_slug and not args.receiver_phone:
        args.client_slug = os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon")
    return args


def _load_env_file(path):
    if not path:
        return {}
    if not os.path.exists(path):
        return {}
    env = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        return {}
    return env


def _fetch_keycloak_token(env_map):
    token_url = env_map.get("KEYCLOAK_TOKEN_URL") or env_map.get(
        "CONSOLE_KEYCLOAK_TOKEN_URL"
    ) or "https://auth.truffles.kz/realms/truffles/protocol/openid-connect/token"
    client_id = env_map.get("CONSOLE_KEYCLOAK_CLIENT_ID") or env_map.get(
        "KEYCLOAK_CLIENT_ID"
    ) or "console-web"
    client_secret = env_map.get("CONSOLE_KEYCLOAK_CLIENT_SECRET") or env_map.get(
        "KEYCLOAK_CLIENT_SECRET"
    )
    username = env_map.get("CONSOLE_KEYCLOAK_USERNAME") or env_map.get("KEYCLOAK_USERNAME")
    password = env_map.get("CONSOLE_KEYCLOAK_PASSWORD") or env_map.get("KEYCLOAK_PASSWORD")
    if not client_secret or not username or not password:
        return None, "missing_keycloak_credentials"
    payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "password",
            "username": username,
            "password": password,
        }
    ).encode("utf-8")
    req = urllib.request.Request(token_url, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(data) if data else {}
            token = payload.get("access_token")
            if token:
                return token, None
            return None, "token_missing"
    except Exception as exc:
        return None, str(exc)


def _resolve_console_token(args):
    if args.console_mode == "skip":
        return None, None
    token = args.console_token or os.environ.get("CONSOLE_API_TOKEN")
    env_map = {}
    if not token and args.console_env:
        env_map = _load_env_file(args.console_env)
        token = env_map.get("CONSOLE_API_TOKEN")
    if token:
        return token, None
    if not env_map and args.console_env:
        env_map = _load_env_file(args.console_env)
    token, error = _fetch_keycloak_token(env_map)
    return token, error


def _console_request(method, url, token, headers=None, payload=None, timeout=15.0):
    headers = dict(headers or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        data = b""
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, body, str(exc)
    except Exception as exc:
        return None, "", str(exc)

def _parse_trace_bundle_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py trace-bundle",
        description="Collect decision_meta/trace + outbox timing for a message.",
    )
    parser.add_argument("--client-slug", default=None)
    parser.add_argument(
        "--receiver-phone",
        default=None,
        help="Receiver phone (branches.phone) to auto-resolve client_slug.",
    )
    parser.add_argument("--text", default=None, help="Substring of inbound message text.")
    parser.add_argument("--message-id", default=None, help="ChatFlow metadata.messageId value.")
    parser.add_argument("--message-uuid", default=None, help="messages.id UUID.")
    parser.add_argument("--conversation-id", default=None)
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--minutes", type=int, default=120)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--outbox-limit", type=int, default=3)
    parser.add_argument("--output", default="-", help="Output path (use '-' for stdout).")
    args = parser.parse_args(argv)
    if not args.client_slug and not args.receiver_phone:
        args.client_slug = os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon")
    return args

def _pick_fuzz_cases(cases, count, rng):
    if count <= 0:
        return []
    shuffled = list(cases)
    rng.shuffle(shuffled)
    if count <= len(shuffled):
        return shuffled[:count]
    selected = list(shuffled)
    while len(selected) < count:
        selected.append(rng.choice(cases))
    return selected

def _parse_csv_values(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]

def _resolve_allowlist_jids(explicit, container_name):
    for value in (
        explicit,
        os.environ.get("FUZZ_ALLOWLIST_JIDS"),
        os.environ.get("OUTBOUND_ALLOWLIST_JIDS"),
        os.environ.get("CHATFLOW_JID"),
    ):
        jids = _parse_csv_values(value)
        if jids:
            return jids
    if container_name:
        for env_name in ("OUTBOUND_ALLOWLIST_JIDS", "CHATFLOW_JID"):
            jids = _parse_csv_values(_resolve_env_from_container(container_name, env_name))
            if jids:
                return jids
    return []

def _select_allowlist_jid(allowlist_jids, suite_name, seed):
    if not allowlist_jids:
        return None
    if len(allowlist_jids) == 1:
        return allowlist_jids[0]
    seed_value = f"{suite_name}:{seed or 0}"
    digest = uuid.uuid5(uuid.NAMESPACE_DNS, seed_value).int
    idx = digest % len(allowlist_jids)
    return allowlist_jids[idx]

def _select_cases(cases, case_ids):
    if not case_ids:
        return None, []
    requested = _parse_csv_values(case_ids)
    case_map = {case["case_id"]: case for case in cases}
    missing = [case_id for case_id in requested if case_id not in case_map]
    if missing:
        raise SystemExit(f"webhook-fuzz: unknown case_ids: {', '.join(missing)}")
    return [case_map[case_id] for case_id in requested], requested

def _resolve_test_mode(container_name):
    value = os.environ.get("TEST_MODE")
    if (value is None or value == "") and container_name:
        value = _resolve_env_from_container(container_name, "TEST_MODE")
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

def _resolve_db_user_simple():
    env_user = os.environ.get("DB_USER")
    if env_user:
        return env_user
    result = run_command(
        ["docker", "exec", "-i", "truffles_postgres_1", "/bin/sh", "-lc", "printf '%s' \"${POSTGRES_USER:-}\""]
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "postgres"

def _escape_sql_literal(value):
    return str(value).replace("'", "''")

def _normalize_phone_digits(value):
    if not value:
        return ""
    return re.sub(r"\D", "", str(value))

def _resolve_webhook_secret(client_slug, explicit):
    if explicit:
        return explicit
    for env_name in ("WEBHOOK_SECRET", "TRUFFLES_WEBHOOK_SECRET"):
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value
    if not client_slug:
        return None
    db_user = _resolve_db_user_simple()
    safe_slug = _escape_sql_literal(client_slug)
    query = (
        "SELECT cs.webhook_secret "
        "FROM client_settings cs "
        "JOIN clients c ON c.id = cs.client_id "
        f"WHERE c.name = '{safe_slug}' LIMIT 1;"
    )
    result = run_command(
        [
            "docker",
            "exec",
            "-i",
            "truffles_postgres_1",
            "psql",
            "-U",
            db_user,
            "-d",
            "chatbot",
            "-t",
            "-A",
            "-c",
            query,
        ]
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None

def _run_psql_query(db_user, query):
    result = run_command(
        [
            "docker",
            "exec",
            "-i",
            "truffles_postgres_1",
            "psql",
            "-U",
            db_user,
            "-d",
            "chatbot",
            "-t",
            "-A",
            "-F",
            "\t",
            "-c",
            query,
        ]
    )
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout.strip(), None

def _parse_iso_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None

def _fetch_client_meta(db_user, client_slug):
    safe_slug = _escape_sql_literal(client_slug)
    query = (
        "SELECT c.id, c.config->>'instance_id', b.id, b.instance_id, "
        "cs.telegram_chat_id, cs.owner_telegram_id "
        "FROM clients c "
        "LEFT JOIN branches b ON b.client_id = c.id AND b.is_active = TRUE "
        "LEFT JOIN client_settings cs ON cs.client_id = c.id "
        f"WHERE c.name = '{safe_slug}' "
        "ORDER BY b.created_at DESC NULLS LAST "
        "LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t")
    return {
        "client_id": parts[0] if len(parts) > 0 else None,
        "client_instance_id": parts[1] if len(parts) > 1 and parts[1] else None,
        "branch_id": parts[2] if len(parts) > 2 else None,
        "branch_instance_id": parts[3] if len(parts) > 3 and parts[3] else None,
        "telegram_chat_id": parts[4] if len(parts) > 4 and parts[4] else None,
        "owner_telegram_id": parts[5] if len(parts) > 5 and parts[5] else None,
    }, None

def _fetch_client_by_branch_phone(db_user, phone):
    digits = _normalize_phone_digits(phone)
    if not digits:
        return None, "receiver phone has no digits"
    safe_phone = _escape_sql_literal(phone or "")
    safe_digits = _escape_sql_literal(digits)
    query = (
        "SELECT json_build_object("
        "'client_slug', c.name, "
        "'client_id', c.id, "
        "'branch_id', b.id, "
        "'branch_phone', b.phone, "
        "'instance_id', b.instance_id"
        ") "
        "FROM branches b "
        "JOIN clients c ON c.id = b.client_id "
        "WHERE b.is_active = TRUE AND ("
        f"b.phone = '{safe_phone}' "
        f"OR regexp_replace(b.phone, '\\\\D', '', 'g') = '{safe_digits}') "
        "ORDER BY b.updated_at DESC NULLS LAST, b.created_at DESC NULLS LAST "
        "LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    try:
        return json.loads(row), None
    except Exception:
        return None, None

def _fetch_conversation_meta(db_user, conversation_id):
    safe_id = _escape_sql_literal(conversation_id)
    query = (
        "SELECT state, telegram_topic_id, context::text "
        f"FROM conversations WHERE id = '{safe_id}' LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t", 2)
    state = parts[0] if len(parts) > 0 else None
    topic_raw = parts[1] if len(parts) > 1 else None
    context_raw = parts[2] if len(parts) > 2 else None
    topic_id = None
    if topic_raw:
        try:
            topic_id = int(topic_raw)
        except ValueError:
            topic_id = None
    context = None
    if context_raw:
        try:
            context = json.loads(context_raw)
        except Exception:
            context = None
    return {
        "state": state,
        "telegram_topic_id": topic_id,
        "context": context,
    }, None

def _fetch_latest_conversation_state(db_user, client_id, remote_jid):
    if not client_id or not remote_jid:
        return None, None, "missing client_id or remote_jid"
    safe_client = _escape_sql_literal(client_id)
    safe_jid = _escape_sql_literal(remote_jid)
    query = (
        "SELECT c.id, c.state "
        "FROM conversations c "
        "JOIN users u ON u.id = c.user_id "
        f"WHERE c.client_id = '{safe_client}' AND u.remote_jid = '{safe_jid}' "
        "ORDER BY c.last_message_at DESC NULLS LAST, c.started_at DESC "
        "LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, None, error
    if not row:
        return None, None, None
    parts = row.split("\t", 1)
    return parts[0] if parts else None, parts[1] if len(parts) > 1 else None, None

def _fetch_handover_meta(db_user, conversation_id):
    safe_id = _escape_sql_literal(conversation_id)
    query = (
        "SELECT id, status, assigned_to, assigned_to_name, first_response_at, "
        "manager_response, resolved_at, added_to_knowledge, knowledge_doc_id "
        f"FROM handovers WHERE conversation_id = '{safe_id}' "
        "ORDER BY created_at DESC LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t", 8)
    return {
        "handover_id": parts[0] if len(parts) > 0 else None,
        "status": parts[1] if len(parts) > 1 else None,
        "assigned_to": parts[2] if len(parts) > 2 and parts[2] else None,
        "assigned_to_name": parts[3] if len(parts) > 3 and parts[3] else None,
        "first_response_at": parts[4] if len(parts) > 4 and parts[4] else None,
        "manager_response": parts[5] if len(parts) > 5 and parts[5] else None,
        "resolved_at": parts[6] if len(parts) > 6 and parts[6] else None,
        "added_to_knowledge": parts[7] if len(parts) > 7 and parts[7] else None,
        "knowledge_doc_id": parts[8] if len(parts) > 8 and parts[8] else None,
    }, None

def _fetch_message_count(db_user, message_id):
    safe_id = _escape_sql_literal(message_id)
    query = f"SELECT COUNT(*) FROM messages WHERE metadata->>'messageId' = '{safe_id}';"
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return 0, None
    try:
        return int(row.strip()), None
    except ValueError:
        return None, None

def _fetch_message_dedup_count(db_user, client_id, message_id):
    safe_client = _escape_sql_literal(client_id)
    safe_id = _escape_sql_literal(message_id)
    query = (
        "SELECT COUNT(*) FROM message_dedup "
        f"WHERE client_id = '{safe_client}' AND message_id = '{safe_id}';"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return 0, None
    try:
        return int(row.strip()), None
    except ValueError:
        return None, None

def _fetch_outbox_summary(db_user, client_id, inbound_message_id):
    safe_client = _escape_sql_literal(client_id)
    safe_id = _escape_sql_literal(inbound_message_id)
    query = (
        "SELECT COUNT(*), MAX(status) "
        "FROM outbox_messages "
        f"WHERE client_id = '{safe_client}' AND inbound_message_id = '{safe_id}';"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return {"count": 0, "status": None}, None
    parts = row.split("\t", 1)
    count = None
    try:
        count = int(parts[0]) if parts and parts[0] else 0
    except ValueError:
        count = None
    status = parts[1] if len(parts) > 1 and parts[1] else None
    return {"count": count, "status": status}, None

def _fetch_outbox_rows(db_user, client_id, inbound_message_id, limit=5):
    safe_client = _escape_sql_literal(client_id)
    safe_id = _escape_sql_literal(inbound_message_id)
    query = (
        "SELECT json_build_object("
        "'id', id, "
        "'status', status, "
        "'attempts', attempts, "
        "'created_at', created_at, "
        "'updated_at', updated_at, "
        "'last_error', last_error, "
        "'meta', meta, "
        "'payload_json', payload_json"
        ") "
        "FROM outbox_messages "
        f"WHERE client_id = '{safe_client}' AND inbound_message_id = '{safe_id}' "
        "ORDER BY created_at DESC "
        f"LIMIT {int(max(limit, 1))};"
    )
    rows_raw, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not rows_raw:
        return [], None
    rows = []
    for line in rows_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        payload_meta = _extract_outbox_payload_meta(row.get("payload_json"))
        row["payload_meta"] = payload_meta
        row.pop("payload_json", None)
        rows.append(row)
    return rows, None


def _fetch_appointment_row(db_user, appointment_id):
    if not appointment_id:
        return None, None
    safe_id = _escape_sql_literal(appointment_id)
    query = (
        "SELECT json_build_object("
        "'id', id, "
        "'status', status, "
        "'source', source, "
        "'start_at', start_at, "
        "'end_at', end_at, "
        "'customer_name', customer_name, "
        "'customer_phone', customer_phone, "
        "'branch_id', branch_id, "
        "'client_id', client_id, "
        "'conversation_id', conversation_id"
        ") "
        "FROM appointments "
        f"WHERE id = '{safe_id}';"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    try:
        return json.loads(row), None
    except Exception:
        return None, "appointment row parse failed"


def _fetch_appointment_audit_rows(db_user, appointment_id, limit=5):
    if not appointment_id:
        return [], None
    safe_id = _escape_sql_literal(appointment_id)
    query = (
        "SELECT json_build_object("
        "'id', id, "
        "'action', action, "
        "'actor_type', actor_type, "
        "'channel', channel, "
        "'created_at', created_at, "
        "'trace_id', trace_id, "
        "'correlation_id', correlation_id, "
        "'payload', payload"
        ") "
        "FROM appointment_audit "
        f"WHERE appointment_id = '{safe_id}' "
        "ORDER BY created_at DESC "
        f"LIMIT {int(max(limit, 1))};"
    )
    rows_raw, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not rows_raw:
        return [], None
    rows = []
    for line in rows_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows, None

def _fetch_branch_meta(db_user, branch_id):
    if not branch_id:
        return None, None
    safe_id = _escape_sql_literal(branch_id)
    query = (
        "SELECT json_build_object("
        "'branch_id', b.id, "
        "'phone', b.phone, "
        "'instance_id', b.instance_id, "
        "'name', b.name, "
        "'slug', b.slug"
        ") "
        "FROM branches b "
        f"WHERE b.id = '{safe_id}' LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    try:
        return json.loads(row), None
    except Exception:
        return None, None

def _fetch_message_rows(db_user, where_clause, limit):
    query = (
        "SELECT json_build_object("
        "'message_uuid', m.id, "
        "'content', m.content, "
        "'created_at', m.created_at, "
        "'remote_jid', u.remote_jid, "
        "'instance_id', m.metadata->>'instanceId', "
        "'message_id', m.metadata->>'messageId', "
        "'conversation_id', c.id, "
        "'branch_id', c.branch_id, "
        "'conversation_state', c.state, "
        "'client_slug', cl.name, "
        "'decision_meta', m.metadata->'decision_meta'"
        ") "
        "FROM messages m "
        "JOIN conversations c ON c.id = m.conversation_id "
        "JOIN users u ON u.id = c.user_id "
        "JOIN clients cl ON cl.id = c.client_id "
        f"WHERE {where_clause} "
        "ORDER BY m.created_at DESC "
        f"LIMIT {int(max(limit, 1))};"
    )
    rows_raw, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not rows_raw:
        return [], None
    rows = []
    for line in rows_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows, None

def _fetch_message_bundle_rows(db_user, where_clause, limit):
    query = (
        "SELECT json_build_object("
        "'message_uuid', m.id, "
        "'content', m.content, "
        "'created_at', m.created_at, "
        "'remote_jid', u.remote_jid, "
        "'instance_id', m.metadata->>'instanceId', "
        "'message_id', m.metadata->>'messageId', "
        "'conversation_id', c.id, "
        "'branch_id', c.branch_id, "
        "'conversation_state', c.state, "
        "'client_slug', cl.name, "
        "'decision_meta', m.metadata->'decision_meta', "
        "'metadata', m.metadata"
        ") "
        "FROM messages m "
        "JOIN conversations c ON c.id = m.conversation_id "
        "JOIN users u ON u.id = c.user_id "
        "JOIN clients cl ON cl.id = c.client_id "
        f"WHERE {where_clause} "
        "ORDER BY m.created_at DESC "
        f"LIMIT {int(max(limit, 1))};"
    )
    rows_raw, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not rows_raw:
        return [], None
    rows = []
    for line in rows_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows, None

def _fetch_latest_outbox_for_conversation(db_user, conversation_id):
    safe_id = _escape_sql_literal(conversation_id)
    query = (
        "SELECT inbound_message_id, status, payload_json::text, meta::text "
        f"FROM outbox_messages WHERE conversation_id = '{safe_id}' "
        "ORDER BY created_at DESC LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t", 3)
    payload = None
    if len(parts) > 2 and parts[2]:
        try:
            payload = json.loads(parts[2])
        except Exception:
            payload = None
    meta = None
    if len(parts) > 3 and parts[3]:
        try:
            meta = json.loads(parts[3])
        except Exception:
            meta = None
    return {
        "inbound_message_id": parts[0] if len(parts) > 0 else None,
        "status": parts[1] if len(parts) > 1 else None,
        "payload_json": payload,
        "meta": meta,
    }, None

def _compute_outbox_latency(message_created_at, outbox_rows):
    if not message_created_at or not outbox_rows:
        return {}
    message_ts = _parse_iso_datetime(message_created_at)
    if not message_ts:
        return {}
    first_row = outbox_rows[0] if outbox_rows else None
    if not isinstance(first_row, dict):
        return {}
    created_at = _parse_iso_datetime(first_row.get("created_at"))
    updated_at = _parse_iso_datetime(first_row.get("updated_at"))
    if not created_at:
        return {}
    inbound_to_outbox_ms = (created_at - message_ts).total_seconds() * 1000
    outbox_total_ms = None
    if updated_at:
        outbox_total_ms = (updated_at - created_at).total_seconds() * 1000
    return {
        "inbound_to_outbox_ms": round(inbound_to_outbox_ms, 2),
        "outbox_total_ms": round(outbox_total_ms, 2) if outbox_total_ms is not None else None,
    }

def _summarize_decision_meta(meta):
    if not isinstance(meta, dict):
        return {}
    keys = [
        "action",
        "intent",
        "source",
        "pending_action",
        "shield_reason",
        "policy_gate",
        "policy_section",
        "rag_reason",
        "llm_used",
        "llm_timeout",
    ]
    summary = {}
    for key in keys:
        value = meta.get(key)
        if value is not None:
            summary[key] = value
    return summary

def _summarize_trace(context, limit=12):
    if not isinstance(context, dict):
        return []
    trace = context.get("decision_trace")
    if not trace:
        return []
    items = []
    for entry in _trace_as_list(trace):
        stage = entry.get("stage")
        decision = entry.get("decision")
        if not stage:
            continue
        if decision:
            items.append(f"{stage}:{decision}")
        else:
            items.append(stage)
    if len(items) > limit:
        return items[-limit:]
    return items

def _extract_outbox_payload_meta(payload):
    if not isinstance(payload, dict):
        return {}
    body = payload.get("body")
    if not isinstance(body, dict):
        return {}
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    return {
        "instance_id": metadata.get("instanceId"),
        "remote_jid": metadata.get("remoteJid"),
        "message_id": metadata.get("messageId"),
    }

def _fetch_traefik_hits(client_slug, minutes, limit):
    if not client_slug:
        return [], "missing client_slug"
    since_value = f"{int(max(minutes, 1))}m"
    result = run_command(["docker", "logs", "truffles-traefik", "--since", since_value])
    if result.returncode != 0:
        return [], result.stderr.strip()
    target = f"/webhook/{client_slug}"
    lines = [line for line in result.stdout.splitlines() if target in line]
    return lines[-int(max(limit, 1)) :], None

def _parse_owner_identity(raw_value):
    if not raw_value:
        return None, None
    tokens = [token for token in re.split(r"[\\s,]+", raw_value.strip()) if token]
    for token in tokens:
        cleaned = token.strip().lstrip("@")
        if not cleaned:
            continue
        if cleaned.lstrip("-").isdigit():
            try:
                return int(cleaned), None
            except ValueError:
                continue
        return None, cleaned
    return None, None

def _resolve_learning_env(container_name):
    learning_mode = os.environ.get("LEARNING_MODE") or ""
    qdrant_collection = os.environ.get("QDRANT_COLLECTION") or ""
    if container_name:
        learning_mode = _resolve_env_from_container(container_name, "LEARNING_MODE") or learning_mode
        qdrant_collection = _resolve_env_from_container(container_name, "QDRANT_COLLECTION") or qdrant_collection
    return {
        "learning_mode": learning_mode.strip().lower(),
        "qdrant_collection": qdrant_collection.strip(),
    }

def _resolve_qdrant_env(container_name):
    host = os.environ.get("QDRANT_HOST", "") or ""
    api_key = os.environ.get("QDRANT_API_KEY", "") or ""
    if container_name:
        host = _resolve_env_from_container(container_name, "QDRANT_HOST") or host
        api_key = _resolve_env_from_container(container_name, "QDRANT_API_KEY") or api_key
    host = host.strip() or "http://qdrant:6333"
    return {"host": host, "api_key": api_key.strip()}

def _qdrant_find_handover(
    *,
    container_name,
    host,
    api_key,
    collection,
    handover_id,
    client_slug,
    timeout,
):
    if not container_name:
        return None, "qdrant: container not found"
    if not collection:
        return None, "qdrant: collection missing"
    payload = {
        "filter": {
            "must": [
                {"key": "metadata.handover_id", "match": {"value": handover_id}},
                {"key": "metadata.client_slug", "match": {"value": client_slug}},
            ]
        },
        "limit": 1,
        "with_payload": True,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    url = f"{host.rstrip('/')}/collections/{collection}/points/scroll"
    max_time = int(max(timeout, 1))
    curl_check = run_docker_exec(container_name, "command -v curl >/dev/null 2>&1 && echo curl_ok")
    use_curl = curl_check.returncode == 0 and "curl_ok" in (curl_check.stdout or "")
    if use_curl:
        headers = "-H 'Content-Type: application/json'"
        if api_key:
            headers += f" -H 'api-key: {api_key}'"
        cmd = (
            f"printf %s {shlex.quote(payload_json)} | "
            f"curl -sS -X POST {headers} --data-binary @- --max-time {max_time} {shlex.quote(url)}"
        )
        result = run_docker_exec(container_name, cmd)
        if result.returncode != 0:
            return None, (result.stderr.strip() or "qdrant: curl failed")
    else:
        payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
        env_parts = [
            f"PAYLOAD_B64={shlex.quote(payload_b64)}",
            f"QDRANT_URL={shlex.quote(url)}",
        ]
        if api_key:
            env_parts.append(f"QDRANT_API_KEY={shlex.quote(api_key)}")
        env_prefix = " ".join(env_parts)
        python_script = (
            "import base64, json, os, sys, urllib.request\n"
            "payload = json.loads(base64.b64decode(os.environ['PAYLOAD_B64']).decode('utf-8'))\n"
            "url = os.environ.get('QDRANT_URL')\n"
            "api_key = os.environ.get('QDRANT_API_KEY')\n"
            "req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), method='POST')\n"
            "req.add_header('Content-Type', 'application/json')\n"
            "if api_key:\n"
            "    req.add_header('api-key', api_key)\n"
            "try:\n"
            f"    with urllib.request.urlopen(req, timeout={max_time}) as resp:\n"
            "        body = resp.read().decode('utf-8', 'replace')\n"
            "        print(body)\n"
            "except Exception as exc:\n"
            "    print('ERROR:' + str(exc))\n"
            "    sys.exit(1)\n"
        )
        cmd = f"{env_prefix} python3 - <<'PY'\n{python_script}PY"
        result = run_docker_exec(container_name, cmd)
        if result.returncode != 0:
            return None, (result.stderr.strip() or "qdrant: python request failed")
    try:
        data = json.loads(result.stdout or "")
    except Exception:
        return None, "qdrant: invalid json response"
    points = (data.get("result") or {}).get("points") or []
    return bool(points), None

def _trace_has_entry(trace_list, stage, decision=None):
    if not isinstance(trace_list, list):
        return False
    for entry in trace_list:
        if not isinstance(entry, dict):
            continue
        if entry.get("stage") != stage:
            continue
        if decision is not None and entry.get("decision") != decision:
            continue
        return True
    return False


def _trace_as_list(trace_list):
    if isinstance(trace_list, dict):
        return [trace_list]
    if isinstance(trace_list, list):
        return [entry for entry in trace_list if isinstance(entry, dict)]
    return []


def _find_trace_entry(trace_list, *, stage, policy_gate=None, policy_section=None):
    for entry in _trace_as_list(trace_list):
        if entry.get("stage") != stage:
            continue
        if policy_gate and entry.get("policy_gate") != policy_gate:
            continue
        if policy_section and entry.get("policy_section") != policy_section:
            continue
        return entry
    return None

def _send_json_payload(url, payload, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, body, str(exc)
    except urllib.error.URLError as exc:
        return None, "", str(exc)

def _build_livecheck_message(rng, case, marker_prefix, timestamp, idx, noise):
    base_text = rng.choice(case["messages"])
    text = _apply_noise(base_text, rng, noise)
    marker = f"{marker_prefix}:{case['case_id']}:{timestamp}:{idx:02d}"
    marker_in_text = case.get("marker_in_text", True)
    if marker_in_text:
        message = f"{text} [{marker}]"
    else:
        message = text
    return text, marker, message

def _fetch_message_meta(db_user, message_id):
    query = (
        "SELECT conversation_id, metadata->'decision_meta' AS decision_meta "
        "FROM messages WHERE role='user' "
        f"AND metadata->>'messageId' = '{message_id}' "
        "ORDER BY created_at DESC LIMIT 1;"
    )
    result = run_command(
        [
            "docker",
            "exec",
            "-i",
            "truffles_postgres_1",
            "psql",
            "-U",
            db_user,
            "-d",
            "chatbot",
            "-t",
            "-A",
            "-F",
            "\t",
            "-c",
            query,
        ]
    )
    if result.returncode != 0:
        return None, None, result.stderr.strip()
    row = result.stdout.strip()
    if not row:
        return None, None, None
    parts = row.split("\t", 1)
    conversation_id = parts[0] if parts else None
    meta_raw = parts[1] if len(parts) > 1 else None
    if meta_raw:
        try:
            meta = json.loads(meta_raw)
        except Exception:
            meta = None
    else:
        meta = None
    return conversation_id, meta, None

def _poll_decision_meta(
    db_user,
    message_id,
    timeout,
    interval,
    require_action=True,
    fail_fast_after=None,
):
    deadline = time.time() + max(timeout, 0)
    last_meta = None
    last_conv_id = None
    last_error = None
    missing_action_since = None
    while time.time() <= deadline:
        conversation_id, meta, error = _fetch_message_meta(db_user, message_id)
        if error:
            last_error = error
        if conversation_id:
            last_conv_id = conversation_id
        if meta:
            last_meta = meta
            if not require_action:
                return last_conv_id, last_meta, None
            action = meta.get("action") or meta.get("pending_action")
            policy_gate = meta.get("policy_gate")
            if action or policy_gate:
                return last_conv_id, last_meta, None
            if fail_fast_after is not None:
                if missing_action_since is None:
                    missing_action_since = time.time()
                elif time.time() - missing_action_since >= fail_fast_after:
                    meta_keys = sorted(k for k in meta.keys() if isinstance(k, str))
                    return (
                        last_conv_id,
                        last_meta,
                        (
                            "missing_action (message_id="
                            f"{message_id}, conv_id={last_conv_id}, meta_keys={meta_keys})"
                        ),
                    )
        time.sleep(max(interval, 0.2))
    return last_conv_id, last_meta, last_error or "timeout"

def _poll_decision_trace(db_user, conversation_id, timeout, interval):
    if not conversation_id:
        return None, [], "missing conversation_id"
    deadline = time.time() + max(timeout, 0)
    last_meta = None
    last_error = None
    last_trace = []
    while time.time() <= deadline:
        conv_meta, conv_error = _fetch_conversation_meta(db_user, conversation_id)
        if conv_error:
            last_error = conv_error
        elif conv_meta:
            last_meta = conv_meta
            context = conv_meta.get("context") if isinstance(conv_meta, dict) else None
            trace_list = context.get("decision_trace") if isinstance(context, dict) else None
            trace_entries = _trace_as_list(trace_list)
            if trace_entries:
                return conv_meta, trace_entries, None
            last_trace = trace_entries
        time.sleep(max(interval, 0.2))
    return last_meta, last_trace, last_error or "trace timeout"

def _resolve_env_from_container(container_name, var_name):
    if not container_name:
        return ""
    result = run_docker_exec(container_name, f'printf "%s" "${{{var_name}:-}}"')
    if result.returncode != 0:
        return ""
    return result.stdout.strip()

def _resolve_outbox_coalesce_seconds(container_name):
    value = os.environ.get("OUTBOX_COALESCE_SECONDS") or ""
    if container_name:
        container_value = _resolve_env_from_container(container_name, "OUTBOX_COALESCE_SECONDS")
        if container_value:
            value = container_value
    if not value:
        return 8.0
    try:
        return max(0.0, float(value))
    except ValueError:
        return 8.0

def _resolve_outbox_wait_seconds(container_name, extra_seconds=1.0):
    return max(0.0, _resolve_outbox_coalesce_seconds(container_name) + extra_seconds)

def _resolve_fail_fast_after(args, outbox_wait_seconds):
    if args.fail_fast_after <= 0:
        return None
    min_after = max(outbox_wait_seconds + 10.0, min(30.0, args.poll_timeout * 0.5))
    fail_fast_after = max(args.fail_fast_after, min_after)
    if fail_fast_after >= args.poll_timeout:
        return None
    return fail_fast_after

def _resolve_remote_jid(explicit, rng, container_name=None):
    if explicit:
        return explicit
    env_value = (
        os.environ.get("FUZZ_REMOTE_JID")
        or os.environ.get("CHATFLOW_JID")
        or os.environ.get("OUTBOUND_ALLOWLIST_JIDS")
    )
    if not env_value and container_name:
        env_value = _resolve_env_from_container(container_name, "OUTBOUND_ALLOWLIST_JIDS")
    if not env_value and container_name:
        env_value = _resolve_env_from_container(container_name, "CHATFLOW_JID")
    jids = [jid.strip() for jid in (env_value or "").split(",") if jid.strip()]
    if jids:
        return rng.choice(jids) if len(jids) > 1 else jids[0]
    return "77015705555@s.whatsapp.net"

def _logic_jid_for_index(idx):
    base = int(os.environ.get("FUZZ_LOGIC_JID_BASE", "99900000000"))
    return f"{base + idx}@s.whatsapp.net"

def _send_webhook_payload(url, payload, secret, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Webhook-Secret"] = secret
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, body, str(exc)
    except urllib.error.URLError as exc:
        return None, "", str(exc)

def _post_admin_outbox(url, admin_token, timeout):
    headers = {"X-Admin-Token": admin_token} if admin_token else {}
    req = urllib.request.Request(url, data=b"", method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, body, str(exc)
    except urllib.error.URLError as exc:
        return None, "", str(exc)
    except (TimeoutError, socket.timeout) as exc:
        return None, "", f"timeout: {exc}"
    except Exception as exc:
        return None, "", str(exc)

def _post_admin_outbox_with_wait(url, admin_token, timeout, wait_seconds):
    if wait_seconds and wait_seconds > 0:
        time.sleep(wait_seconds)
    return _post_admin_outbox(url, admin_token, timeout)

def _ensure_bot_active_before_suite(args, context):
    if args.dry_run:
        return
    remote_jid = context.get("remote_jid")
    client_meta = context.get("client_meta") or {}
    client_id = client_meta.get("client_id")
    db_user = context.get("db_user")
    webhook_url = context.get("webhook_url")
    webhook_secret = context.get("webhook_secret")
    admin_token = context.get("admin_token")
    instance_id = context.get("instance_id")
    timestamp = context.get("timestamp")
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0
    if not remote_jid or not client_id or not db_user:
        return
    conv_id, state, error = _fetch_latest_conversation_state(db_user, client_id, remote_jid)
    if error:
        print(json.dumps({"stage": "preflight_state", "error": error}, ensure_ascii=False))
        return
    state_before = state
    if state not in ("pending", "manager_active"):
        return
    if state == "manager_active":
        handover_meta, _ = _fetch_handover_meta(db_user, conv_id)
        handover_id = (handover_meta or {}).get("handover_id")
        conv_meta, _ = _fetch_conversation_meta(db_user, conv_id)
        topic_id = (conv_meta or {}).get("telegram_topic_id")
        chat_id_raw = client_meta.get("telegram_chat_id")
        if not handover_id or not chat_id_raw:
            raise SystemExit("livecheck-auto: preflight missing handover or telegram_chat_id")
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            raise SystemExit(f"livecheck-auto: invalid telegram_chat_id {chat_id_raw}")
        owner_id, owner_username = _parse_owner_identity(client_meta.get("owner_telegram_id"))
        manager_id = owner_id if owner_id is not None else 10001
        manager_username = owner_username or "ci_manager"
        preflight_action = "resolve_manager"
        preflight_message_id = f"LC-PREFLIGHT-{timestamp}-{uuid.uuid4().hex[:8]}"
        callback_message = {
            "message_id": int(time.time() * 1000) % 1000000,
            "date": int(time.time()),
            "chat": {"id": chat_id, "type": "supergroup", "title": "CI"},
        }
        if topic_id:
            callback_message["message_thread_id"] = topic_id
        callback_payload = {
            "update_id": int(time.time()),
            "callback_query": {
                "id": preflight_message_id,
                "from": {
                    "id": manager_id,
                    "is_bot": False,
                    "first_name": "CI",
                    "last_name": "Runner",
                    "username": manager_username,
                },
                "message": callback_message,
                "data": f"resolve_{handover_id}",
            },
        }
        preflight_status, preflight_body, preflight_error = _send_json_payload(
            f"{context.get('base_url')}/telegram-webhook", callback_payload, args.timeout
        )
    else:
        preflight_text = args.ack_text or "ок"
        preflight_action = "ack_pending"
        preflight_message_id = f"LC-PREFLIGHT-{timestamp}-{uuid.uuid4().hex[:8]}"
        preflight_payload = {
            "body": {
                "messageType": "text",
                "message": preflight_text,
                "metadata": {
                    "sender": "LivecheckAuto",
                    "timestamp": int(time.time()),
                    "messageId": preflight_message_id,
                    "remoteJid": remote_jid,
                },
            }
        }
        if instance_id:
            preflight_payload["body"]["metadata"]["instanceId"] = instance_id
        preflight_status, preflight_body, preflight_error = _send_webhook_payload(
            webhook_url, preflight_payload, webhook_secret, args.timeout
        )
        _post_admin_outbox_with_wait(
            f"{context.get('base_url')}/admin/outbox/process",
            admin_token,
            args.timeout,
            outbox_wait_seconds,
        )
    if preflight_error:
        raise SystemExit(f"livecheck-auto: preflight message failed ({preflight_error})")
    cleared = False
    clear_wait_seconds = 30
    for _ in range(clear_wait_seconds):
        time.sleep(1.0)
        conv_id, state, _ = _fetch_latest_conversation_state(db_user, client_id, remote_jid)
        if state == "bot_active":
            cleared = True
            break
    print(
        json.dumps(
            {
                "stage": "preflight_clear_pending",
                "state_before": state_before,
                "action": preflight_action,
                "conversation_id": conv_id,
                "message_id": preflight_message_id,
                "status": preflight_status,
                "response": (preflight_body or "")[:200] if preflight_body else None,
                "state_after": state,
                "cleared": cleared,
            },
            ensure_ascii=False,
        )
    )
    if not cleared:
        raise SystemExit(
            f"livecheck-auto: pending state not cleared before {args.suite} (state_after={state})"
        )

def _run_webhook_fuzz(args):
    if args.count < 1:
        raise SystemExit("webhook-fuzz: --count must be >= 1")
    rng = random.Random(args.seed or int(time.time()))
    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_url = args.base_url.rstrip("/")
    client_slug = args.client_slug
    webhook_url = f"{base_url}/webhook/{client_slug}"
    mode = args.mode
    skip_outbox = args.skip_outbox or mode == "logic"

    container_name, _ = resolve_container_name()

    webhook_secret = (
        args.webhook_secret
        or os.environ.get("WEBHOOK_SECRET")
        or os.environ.get("TRUFFLES_WEBHOOK_SECRET")
    )
    admin_token = args.admin_token or os.environ.get("ALERTS_ADMIN_TOKEN")
    if not admin_token and container_name:
        admin_token = _resolve_env_from_container(container_name, "ALERTS_ADMIN_TOKEN")

    instance_id = (
        args.instance_id
        or os.environ.get("CHATFLOW_INSTANCE_ID")
        or os.environ.get("INSTANCE_ID")
    )
    test_mode_enabled = _resolve_test_mode(container_name)
    allowlist_jids = _resolve_allowlist_jids(args.allowlist_jids, container_name)
    selected_cases, requested_case_ids = _select_cases(WEBHOOK_FUZZ_CASES, args.case_ids)
    if selected_cases is None:
        selected_cases = _pick_fuzz_cases(WEBHOOK_FUZZ_CASES, args.count, rng)
        requested_case_ids = []

    if mode == "logic" and not test_mode_enabled:
        raise SystemExit("webhook-fuzz: TEST_MODE disabled; logic mode is blocked for safety")

    remote_jid = None
    if mode == "state":
        if not allowlist_jids:
            raise SystemExit("webhook-fuzz: allowlist-jids required for state mode")
        remote_jid = args.remote_jid or allowlist_jids[0]
        if remote_jid not in allowlist_jids:
            raise SystemExit(
                f"webhook-fuzz: remote-jid {remote_jid} not in allowlist; refusing to send"
            )

    markers = []
    message_ids = []
    remote_jids = []

    for idx, case in enumerate(selected_cases, start=1):
        case_turns = case.get("turns")
        if case_turns is None:
            case_messages = case.get("messages") or []
            if not case_messages:
                raise SystemExit("webhook-fuzz: case missing messages")
            case_turns = [rng.choice(case_messages)]
        elif not isinstance(case_turns, list) or not case_turns:
            raise SystemExit("webhook-fuzz: case turns must be non-empty list")

        if mode == "logic":
            remote_jid = _logic_jid_for_index(idx)
            if not skip_outbox and allowlist_jids and remote_jid not in allowlist_jids:
                raise SystemExit(
                    f"webhook-fuzz: remote-jid {remote_jid} not in allowlist; refusing to send"
                )

        for turn_idx, base_text in enumerate(case_turns, start=1):
            text = _apply_noise(base_text, rng, args.noise)
            if len(case_turns) > 1:
                marker = f"FZ:{case['case_id']}:{timestamp}:{idx:02d}:{turn_idx:02d}"
                message_id = f"FZ-{timestamp}-{idx:02d}-{turn_idx:02d}-{uuid.uuid4().hex[:8]}"
            else:
                marker = f"FZ:{case['case_id']}:{timestamp}:{idx:02d}"
                message_id = f"FZ-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
            message = f"{text} [{marker}]"
            sent_at = datetime.now(timezone.utc).isoformat()
            remote_jids.append(remote_jid)
            metadata = {
                "sender": "FuzzRunner",
                "timestamp": int(time.time()),
                "messageId": message_id,
                "remoteJid": remote_jid,
            }
            if instance_id:
                metadata["instanceId"] = instance_id
            payload = {
                "body": {
                    "messageType": "text",
                    "message": message,
                    "metadata": metadata,
                }
            }

            status = "dry_run"
            response_status = None
            response_body = None
            response_error = None
            if not args.dry_run:
                response_status, response_body, response_error = _send_webhook_payload(
                    webhook_url, payload, webhook_secret, args.timeout
                )
                if response_status and 200 <= response_status < 300:
                    status = "sent"
                else:
                    status = "error"

            log = {
                "case_id": case["case_id"],
                "marker": marker,
                "message_id": message_id,
                "remote_jid": remote_jid,
                "text": message,
                "sent_at": sent_at,
                "expected_policy_section": case["expected_policy_section"],
                "status": status,
                "http_status": response_status,
                "turn": turn_idx if len(case_turns) > 1 else None,
            }
            if response_error:
                log["error"] = response_error
            if response_body:
                log["response"] = response_body[:200]
            print(json.dumps(log, ensure_ascii=False))

            markers.append(marker)
            message_ids.append(message_id)

            if turn_idx < len(case_turns):
                time.sleep(rng.uniform(min_wait, max_wait))

        if idx < len(selected_cases):
            time.sleep(rng.uniform(min_wait, max_wait))

    outbox_status = None
    outbox_error = None
    outbox_body = None
    if not skip_outbox:
        if not allowlist_jids:
            raise SystemExit("webhook-fuzz: allowlist-jids required when outbox enabled")
        unique_jids = sorted(set(remote_jids))
        not_allowed = [jid for jid in unique_jids if jid not in allowlist_jids]
        if not_allowed:
            raise SystemExit(
                "webhook-fuzz: outbox enabled for non-allowlist JID(s): "
                + ", ".join(not_allowed)
            )
        if not admin_token and not args.dry_run:
            raise SystemExit("webhook-fuzz: missing admin token for outbox/process")
        if not args.dry_run:
            outbox_url = f"{base_url}/admin/outbox/process"
            outbox_status, outbox_body, outbox_error = _post_admin_outbox(
                outbox_url, admin_token, args.timeout
            )
            outbox_log = {
                "outbox_url": outbox_url,
                "status": outbox_status,
                "error": outbox_error,
            }
            if outbox_body:
                outbox_log["response"] = outbox_body[:200]
            print(json.dumps(outbox_log, ensure_ascii=False))
            if outbox_status and outbox_status >= 400:
                raise SystemExit(f"webhook-fuzz: outbox/process failed (status {outbox_status})")

    summary = {
        "count": len(selected_cases),
        "message_count": len(message_ids),
        "base_url": base_url,
        "client_slug": client_slug,
        "seed": args.seed,
        "mode": mode,
        "skip_outbox": skip_outbox,
        "allowlist_jids": allowlist_jids,
        "case_ids": requested_case_ids,
        "remote_jid": remote_jid,
        "remote_jids": remote_jids,
        "instance_id": instance_id,
        "test_mode": test_mode_enabled,
        "markers": markers,
        "message_ids": message_ids,
        "outbox_status": outbox_status,
    }
    print(json.dumps({"summary": summary}, ensure_ascii=False))


def _run_chaos_sim(args):
    if args.count < 1:
        raise SystemExit("chaos-sim: --count must be >= 1")
    if args.min_turns < 4 or args.min_turns > args.max_turns:
        raise SystemExit("chaos-sim: invalid --min-turns/--max-turns range")

    stop_requested = False
    stop_reason = None
    interrupted = False

    def _handle_stop(signum, _frame):
        nonlocal stop_requested, stop_reason, interrupted
        if stop_requested:
            return
        stop_requested = True
        interrupted = True
        stop_reason = f"signal_{signum}"
        print("chaos-sim: stop requested, finishing current turn...", file=sys.stderr)

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    seed = args.seed or int(time.time())
    rng = random.Random(seed)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_url = args.base_url.rstrip("/")
    client_slug = args.client_slug
    webhook_url = f"{base_url}/webhook/{client_slug}"
    webhook_secret = _resolve_webhook_secret(client_slug, args.webhook_secret)
    simulation_id = args.simulation_id or f"SIM-{timestamp}-{seed}"
    jid_base = _resolve_chaos_jid_base(simulation_id, seed)

    output_dir = args.output_dir or os.path.join(
        os.getcwd(),
        "ops",
        "artifacts",
        "chaos_sim",
        timestamp,
    )
    os.makedirs(output_dir, exist_ok=True)
    turns_path = None
    turns_handle = None
    if args.debug_all:
        turns_path = os.path.join(output_dir, "turns.jsonl")
        turns_handle = open(turns_path, "w", encoding="utf-8")
    rag_audit = bool(getattr(args, "rag_audit", False))
    rag_debug_path = None
    rag_debug_handle = None
    rag_summary = None
    if rag_audit:
        rag_debug_path = os.path.join(output_dir, "rag_debug.jsonl")
        rag_debug_handle = open(rag_debug_path, "w", encoding="utf-8")
        rag_summary = {
            "total_turns": 0,
            "rag_confident": 0,
            "rag_low_score": 0,
            "rag_empty": 0,
            "rag_overridden_by_gate": 0,
            "rag_missing": 0,
            "low_score_in_domain": 0,
            "high_score_out_of_domain": 0,
            "branch_filter_missing": 0,
            "branch_filter_empty": 0,
            "rag_status_counts": {},
            "lang_mode_counts": {},
            "noise_counts": {},
            "intent_bucket_counts": {},
            "patterns": {},
        }

    container_name, _ = resolve_container_name()
    admin_token = args.admin_token or os.environ.get("ALERTS_ADMIN_TOKEN")
    if not admin_token and container_name:
        admin_token = _resolve_env_from_container(container_name, "ALERTS_ADMIN_TOKEN")

    skip_outbox = args.skip_outbox
    outbox_wait_seconds = (
        args.outbox_wait
        if args.outbox_wait is not None
        else _resolve_outbox_wait_seconds(container_name)
    )
    if not skip_outbox and not args.dry_run and not admin_token:
        raise SystemExit("chaos-sim: missing admin token for outbox/process")

    db_user = _resolve_db_user_simple()
    client_meta, client_error = _fetch_client_meta(db_user, client_slug)
    if client_error:
        raise SystemExit(f"chaos-sim: client meta lookup failed ({client_error})")
    instance_id = None
    if client_meta:
        instance_id = client_meta.get("branch_instance_id") or client_meta.get("client_instance_id")
    telegram_chat_id = None
    if client_meta and client_meta.get("telegram_chat_id"):
        try:
            telegram_chat_id = int(client_meta.get("telegram_chat_id"))
        except ValueError:
            telegram_chat_id = None

    console_token, console_error = _resolve_console_token(args)
    if console_error and args.console_mode == "real":
        raise SystemExit(f"chaos-sim: console token error ({console_error})")
    console_base_url = (args.console_base_url or base_url).rstrip("/")
    console_headers = {}
    if args.console_client_id:
        console_headers["X-Client-Id"] = args.console_client_id
    elif client_meta and client_meta.get("client_id"):
        console_headers["X-Client-Id"] = client_meta.get("client_id")

    cases = _chaos_generate_cases(args.count, rng, args.min_turns, args.max_turns, args.noise)
    if args.dump_cases:
        cases_path = os.path.join(output_dir, "cases.jsonl")
        with open(cases_path, "w", encoding="utf-8") as handle:
            for case in cases:
                handle.write(json.dumps(case, ensure_ascii=False) + "\n")
    failures = []
    failure_counts = {}
    pattern_counts = {}
    stats = {
        "cases": len(cases),
        "turns": 0,
        "failures": 0,
        "escalations": 0,
        "lead_captured": 0,
        "booking_failed": 0,
        "manager_resolved": 0,
        "console_resolved": 0,
    }
    processed_cases = 0

    def _bump_failure_counts(labels):
        for label in labels:
            failure_counts[label] = failure_counts.get(label, 0) + 1

    def _bump_pattern_counts(patterns):
        for pattern in patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    def _build_remote_jid(idx):
        return f"{jid_base + idx}@s.whatsapp.net"

    def _send_telegram_callback(action, handover_id):
        if not telegram_chat_id:
            return None, "", "telegram_chat_id_missing"
        payload = {
            "update_id": rng.randint(100000, 999999),
            "callback_query": {
                "id": f"sim-{uuid.uuid4().hex[:10]}",
                "from": {"id": 10101, "is_bot": False, "first_name": "Sim"},
                "data": f"{action}_{handover_id}",
                "message": {
                    "message_id": rng.randint(1, 99999),
                    "date": int(time.time()),
                    "chat": {"id": telegram_chat_id, "type": "group"},
                },
            },
        }
        return _send_webhook_payload(
            f"{base_url}/telegram-webhook", payload, None, args.timeout
        )

    def _send_console_action(action, handover_id):
        if args.console_mode == "skip":
            return None, "", "console_skipped"
        if not console_token:
            return None, "", "console_token_missing"
        url = f"{console_base_url}/console/v1/cases/{handover_id}/{action}"
        return _console_request(
            "POST",
            url,
            console_token,
            headers=console_headers,
            payload={},
            timeout=args.timeout,
        )

    for case_idx, case in enumerate(cases, start=1):
        if stop_requested:
            break
        remote_jid = _build_remote_jid(case_idx)
        conversation_id = None
        for turn_idx, turn in enumerate(case["turns"], start=1):
            if stop_requested:
                break
            if turn.get("type") == "manager":
                if not conversation_id:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "type": "manager",
                            "failure": ["missing_conversation_id"],
                        }
                    )
                    _bump_failure_counts(["missing_conversation_id"])
                    stats["failures"] += 1
                    continue
                handover_meta, _ = _fetch_handover_meta(db_user, conversation_id)
                handover_id = (handover_meta or {}).get("handover_id")
                if not handover_id:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "type": "manager",
                            "failure": ["handover_missing"],
                        }
                    )
                    _bump_failure_counts(["handover_missing"])
                    stats["failures"] += 1
                    continue
                channel = turn.get("channel")
                action = turn.get("action")
                if channel == "console":
                    status, body, error = _send_console_action(action, handover_id)
                else:
                    status, body, error = _send_telegram_callback(action, handover_id)

                if error and error not in {"console_skipped"}:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "type": "manager",
                            "handover_id": handover_id,
                            "failure": ["manager_action_failed"],
                            "error": error,
                        }
                    )
                    _bump_failure_counts(["manager_action_failed"])
                    stats["failures"] += 1
                if error == "console_skipped":
                    if turns_handle:
                        turns_handle.write(
                            json.dumps(
                                {
                                    "case_id": case["case_id"],
                                    "turn": turn_idx,
                                    "type": "manager",
                                    "action": action,
                                    "channel": channel,
                                    "handover_id": handover_id,
                                    "conversation_id": conversation_id,
                                    "request_status": status,
                                    "request_error": error,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                    continue

                conv_meta, _ = _fetch_conversation_meta(db_user, conversation_id)
                handover_meta, _ = _fetch_handover_meta(db_user, conversation_id)
                expected_state = "manager_active" if action == "take" else "bot_active"
                expected_status = "active" if action == "take" else "resolved"
                if (conv_meta or {}).get("state") != expected_state:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "type": "manager",
                            "handover_id": handover_id,
                            "failure": ["state_mismatch"],
                            "expected_state": expected_state,
                            "actual_state": (conv_meta or {}).get("state"),
                        }
                    )
                    _bump_failure_counts(["state_mismatch"])
                    stats["failures"] += 1
                if (handover_meta or {}).get("status") != expected_status:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "type": "manager",
                            "handover_id": handover_id,
                            "failure": ["handover_status_mismatch"],
                            "expected_status": expected_status,
                            "actual_status": (handover_meta or {}).get("status"),
                        }
                    )
                    _bump_failure_counts(["handover_status_mismatch"])
                    stats["failures"] += 1

                if action == "resolve":
                    if channel == "console":
                        stats["console_resolved"] += 1
                    else:
                        stats["manager_resolved"] += 1
                if turns_handle:
                    turns_handle.write(
                        json.dumps(
                            {
                                "case_id": case["case_id"],
                                "turn": turn_idx,
                                "type": "manager",
                                "action": action,
                                "channel": channel,
                                "handover_id": handover_id,
                                "conversation_id": conversation_id,
                                "request_status": status,
                                "request_error": error,
                                "expected_state": expected_state,
                                "actual_state": (conv_meta or {}).get("state"),
                                "expected_handover_status": expected_status,
                                "actual_handover_status": (handover_meta or {}).get("status"),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                continue

            stats["turns"] += 1
            message_id = f"SIM-{timestamp}-{case_idx:04d}-{turn_idx:02d}-{uuid.uuid4().hex[:8]}"
            metadata = {
                "sender": "ChaosSim",
                "timestamp": int(time.time()),
                "messageId": message_id,
                "remoteJid": remote_jid,
                "simulation_mode": True,
                "simulation_id": simulation_id,
            }
            if args.mode == "llm":
                metadata["simulation_llm"] = True
            elif args.mode == "logic":
                metadata["simulation_llm"] = False
            if instance_id:
                metadata["instanceId"] = instance_id
            payload = {
                "body": {
                    "messageType": "text",
                    "message": turn.get("text"),
                    "metadata": metadata,
                }
            }

            response_status = None
            response_body = None
            response_error = None
            if not args.dry_run:
                response_status, response_body, response_error = _send_webhook_payload(
                    webhook_url, payload, webhook_secret, args.timeout
                )
                if not skip_outbox:
                    outbox_url = f"{base_url}/admin/outbox/process"
                    _post_admin_outbox_with_wait(
                        outbox_url,
                        admin_token,
                        args.timeout,
                        outbox_wait_seconds,
                    )

            conv_id = None
            meta = None
            trace_entries = []
            conv_meta = None
            handover_meta = None
            if not args.dry_run:
                conv_id, meta, poll_error = _poll_decision_meta(
                    db_user,
                    message_id,
                    args.poll_timeout,
                    args.poll_interval,
                )
                if poll_error:
                    failures.append(
                        {
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "type": "user",
                            "text": turn.get("text"),
                            "message_id": message_id,
                            "failure": ["decision_meta_poll_failed"],
                            "error": poll_error,
                        }
                    )
                    _bump_failure_counts(["decision_meta_poll_failed"])
                    stats["failures"] += 1
                if conv_id:
                    conversation_id = conv_id
                    conv_meta, _ = _fetch_conversation_meta(db_user, conv_id)
                    trace_entries = _trace_as_list(
                        (conv_meta or {}).get("context", {}).get("decision_trace")
                    )
                    expected = turn.get("expected") or {}
                    if expected.get("handover_status") or expected.get("state") == "pending":
                        handover_meta, _ = _fetch_handover_meta(db_user, conv_id)

            expected = turn.get("expected") or {}
            failures_for_turn = []
            if not args.dry_run:
                failures_for_turn = _chaos_evaluate_turn(
                    turn=turn,
                    meta=meta,
                    conv_meta=conv_meta,
                    handover_meta=handover_meta,
                    trace_entries=trace_entries,
                )
                if failures_for_turn:
                    pattern_keys = _chaos_build_failure_patterns(failures_for_turn, meta, conv_meta)
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "user",
                        "message_id": message_id,
                        "conversation_id": conv_id,
                        "text": turn.get("text"),
                        "expected": expected,
                        "failure": failures_for_turn,
                        "patterns": pattern_keys,
                        "decision_meta": meta if args.debug or args.debug_all else None,
                        "decision_trace": trace_entries if args.debug or args.debug_all else None,
                        "conversation_context": (conv_meta or {}).get("context")
                        if args.debug or args.debug_all
                        else None,
                    }
                    failures.append(record)
                    _bump_failure_counts(failures_for_turn)
                    _bump_pattern_counts(pattern_keys)
                    stats["failures"] += 1

            if rag_audit:
                rag_record, rag_pattern, rag_flags = _chaos_build_rag_record(
                    case=case,
                    turn=turn,
                    turn_idx=turn_idx,
                    message_id=message_id,
                    conversation_id=conv_id,
                    meta=meta,
                    trace_entries=trace_entries,
                    noise_level=args.noise,
                    response_status=response_status,
                )
                if rag_debug_handle:
                    rag_debug_handle.write(json.dumps(rag_record, ensure_ascii=False) + "\n")
                if rag_summary is not None:
                    _chaos_update_rag_summary(rag_summary, rag_record, rag_pattern, rag_flags)

            if meta and meta.get("policy_gate"):
                stats["escalations"] += 1
            if meta and meta.get("action") in _chaos_booking_completion_actions():
                stats["lead_captured"] += 1
            if meta and meta.get("action") == "booking_escalation_failed":
                stats["booking_failed"] += 1

            if turns_handle:
                turns_handle.write(
                    json.dumps(
                        {
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "type": "user",
                            "message_id": message_id,
                            "conversation_id": conv_id,
                            "text": turn.get("text"),
                            "expected": expected,
                            "decision_meta": meta,
                            "decision_trace": trace_entries,
                            "conversation_context": (conv_meta or {}).get("context"),
                            "handover": handover_meta,
                            "failures": failures_for_turn,
                            "response_status": response_status,
                            "response_error": response_error,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            log = {
                "case_id": case["case_id"],
                "turn": turn_idx,
                "message_id": message_id,
                "remote_jid": remote_jid,
                "status": "sent" if response_status and 200 <= response_status < 300 else "error",
                "failures": failures_for_turn,
            }
            if response_error:
                log["error"] = response_error
            if response_body:
                log["response"] = response_body[:200]
            print(json.dumps(log, ensure_ascii=False))

            time.sleep(rng.uniform(args.min_wait, args.max_wait))

        if stop_requested:
            break
        processed_cases += 1

    if turns_handle:
        turns_handle.close()
    if rag_debug_handle:
        rag_debug_handle.close()

    failure_path = os.path.join(output_dir, "failures.jsonl")
    with open(failure_path, "w", encoding="utf-8") as handle:
        for item in failures:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    stats_path = os.path.join(output_dir, "stats.json")
    summary_path = os.path.join(output_dir, "summary.json")
    report_path = os.path.join(output_dir, "report.md")
    rag_summary_path = None
    if rag_audit and rag_summary is not None:
        rag_summary_path = os.path.join(output_dir, "rag_summary.json")
        rag_summary["rag_audit"] = True
        rag_summary["top_patterns"] = sorted(
            (
                {"pattern": key, "count": count}
                for key, count in (rag_summary.get("patterns") or {}).items()
            ),
            key=lambda item: -item["count"],
        )[:CHAOS_RAG_TOP_N]
        with open(rag_summary_path, "w", encoding="utf-8") as handle:
            json.dump(rag_summary, handle, ensure_ascii=False, indent=2)

    summary = {
        "simulation_id": simulation_id,
        "seed": seed,
        "cases": stats["cases"],
        "cases_processed": processed_cases,
        "turns": stats["turns"],
        "failures": stats["failures"],
        "failure_types": failure_counts,
        "failure_patterns": pattern_counts,
        "output_dir": output_dir,
        "jid_base": jid_base,
        "client_slug": client_slug,
        "console_mode": args.console_mode,
        "llm_mode": args.mode,
        "turns_path": turns_path,
        "rag_audit": rag_audit,
        "rag_debug_path": rag_debug_path,
        "rag_summary_path": rag_summary_path,
        "interrupted": interrupted,
        "stop_reason": stop_reason,
    }
    with open(stats_path, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write("# Chaos Simulation Report\n\n")
        handle.write(f"- simulation_id: {simulation_id}\n")
        handle.write(f"- cases: {stats['cases']}\n")
        handle.write(f"- cases_processed: {processed_cases}\n")
        handle.write(f"- turns: {stats['turns']}\n")
        handle.write(f"- failures: {stats['failures']}\n")
        handle.write(f"- jid_base: {jid_base}\n")
        handle.write(f"- interrupted: {str(interrupted).lower()}\n")
        if stop_reason:
            handle.write(f"- stop_reason: {stop_reason}\n")
        handle.write(f"- escalations: {stats['escalations']}\n")
        handle.write(f"- lead_captured: {stats['lead_captured']}\n")
        handle.write(f"- booking_failed: {stats['booking_failed']}\n")
        handle.write(f"- manager_resolved: {stats['manager_resolved']}\n")
        handle.write(f"- console_resolved: {stats['console_resolved']}\n\n")
        if turns_path:
            handle.write(f"- turns_path: {turns_path}\n\n")
        if failure_counts:
            handle.write("## Failure Types\n")
            for key, count in sorted(failure_counts.items(), key=lambda item: -item[1]):
                handle.write(f"- {key}: {count}\n")
            handle.write("\n")
        if pattern_counts:
            handle.write("## Failure Patterns\n")
            for key, count in sorted(pattern_counts.items(), key=lambda item: -item[1]):
                handle.write(f"- {key}: {count}\n")
            handle.write("\n")
        if rag_audit and rag_summary:
            handle.write("## RAG Quality Findings\n")
            handle.write(f"- rag_audit: {str(rag_audit).lower()}\n")
            handle.write(f"- total_turns: {rag_summary.get('total_turns', 0)}\n")
            handle.write(f"- rag_confident: {rag_summary.get('rag_confident', 0)}\n")
            handle.write(f"- rag_low_score: {rag_summary.get('rag_low_score', 0)}\n")
            handle.write(f"- rag_empty: {rag_summary.get('rag_empty', 0)}\n")
            handle.write(
                f"- rag_overridden_by_gate: {rag_summary.get('rag_overridden_by_gate', 0)}\n"
            )
            handle.write(f"- rag_missing: {rag_summary.get('rag_missing', 0)}\n")
            handle.write(f"- low_score_in_domain: {rag_summary.get('low_score_in_domain', 0)}\n")
            handle.write(
                f"- high_score_out_of_domain: {rag_summary.get('high_score_out_of_domain', 0)}\n"
            )
            handle.write(
                f"- branch_filter_missing: {rag_summary.get('branch_filter_missing', 0)}\n"
            )
            handle.write(
                f"- branch_filter_empty: {rag_summary.get('branch_filter_empty', 0)}\n"
            )
            if rag_summary.get("top_patterns"):
                handle.write("\n### Top Patterns\n")
                for item in rag_summary["top_patterns"]:
                    handle.write(f"- {item['pattern']}: {item['count']}\n")

    print(json.dumps({"summary": summary}, ensure_ascii=False))

def _run_explain(args):
    db_user = _resolve_db_user_simple()
    client_slug = args.client_slug
    branch_id = None
    if not client_slug and args.receiver_phone:
        resolved_branch, error = _fetch_client_by_branch_phone(db_user, args.receiver_phone)
        if error:
            raise SystemExit(f"explain: receiver phone lookup failed ({error})")
        if not resolved_branch:
            raise SystemExit("explain: receiver phone not found; provide --client-slug")
        client_slug = resolved_branch.get("client_slug")
        branch_id = resolved_branch.get("branch_id")
        print(f"resolved_client_slug={client_slug}")
        if branch_id:
            print(f"resolved_branch_id={branch_id}")
        if resolved_branch.get("instance_id"):
            print(f"resolved_instance_id={resolved_branch.get('instance_id')}")
    clauses = ["m.role = 'user'"]
    safe_slug = None
    if client_slug:
        safe_slug = _escape_sql_literal(client_slug)
        clauses.append(f"cl.name = '{safe_slug}'")
    if branch_id:
        safe_branch = _escape_sql_literal(branch_id)
        clauses.append(f"c.branch_id = '{safe_branch}'")
    if args.remote_jid:
        safe_jid = _escape_sql_literal(args.remote_jid)
        clauses.append(f"u.remote_jid = '{safe_jid}'")

    if args.message_uuid:
        safe_uuid = _escape_sql_literal(args.message_uuid)
        clauses.append(f"m.id = '{safe_uuid}'")
    elif args.message_id:
        safe_message = _escape_sql_literal(args.message_id)
        clauses.append(f"m.metadata->>'messageId' = '{safe_message}'")
    elif args.conversation_id:
        safe_conv = _escape_sql_literal(args.conversation_id)
        clauses.append(f"m.conversation_id = '{safe_conv}'")
    elif args.text:
        safe_text = _escape_sql_literal(args.text)
        minutes = int(max(args.minutes, 1))
        clauses.append(f"m.content ILIKE '%{safe_text}%'")
        clauses.append(f"m.created_at > now() - interval '{minutes} minutes'")
    else:
        raise SystemExit("explain: provide --text, --message-id, --message-uuid, or --conversation-id")

    where_clause = " AND ".join(clauses)
    rows, error = _fetch_message_rows(db_user, where_clause, args.limit)
    if error:
        raise SystemExit(f"explain: db error ({error})")

    if not rows:
        print("explain: no inbound messages found.")
        if args.traefik and client_slug:
            hits, hit_error = _fetch_traefik_hits(client_slug, args.traefik_minutes, 10)
            if hit_error:
                print(f"traefik_error: {hit_error}")
            if hits:
                print("traefik_hits:")
                for line in hits:
                    print(line)
        else:
            print("hint: check ChatFlow webhook delivery and Traefik logs.")
        return

    client_meta = None
    if client_slug:
        client_meta, _ = _fetch_client_meta(db_user, client_slug)

    for idx, row in enumerate(rows, start=1):
        print("-" * 60)
        print(f"match[{idx}] message_uuid={row.get('message_uuid')}")
        print(f"message_id={row.get('message_id')}")
        print(f"created_at={row.get('created_at')}")
        print(f"client_slug={row.get('client_slug')}")
        print(f"remote_jid={row.get('remote_jid')}")
        print(f"instance_id={row.get('instance_id')}")
        print(f"conversation_id={row.get('conversation_id')}")
        print(f"branch_id={row.get('branch_id')}")
        print(f"conversation_state={row.get('conversation_state')}")
        content = row.get("content")
        if content is not None:
            print(f"content={content}")

        decision_meta = row.get("decision_meta")
        summary = _summarize_decision_meta(decision_meta)
        if summary:
            print(f"decision_meta={json.dumps(summary, ensure_ascii=False)}")

        branch_meta, _ = _fetch_branch_meta(db_user, row.get("branch_id"))
        if branch_meta:
            print(
                "branch_meta="
                + json.dumps(
                    {
                        "phone": branch_meta.get("phone"),
                        "slug": branch_meta.get("slug"),
                        "instance_id": branch_meta.get("instance_id"),
                    },
                    ensure_ascii=False,
                )
            )
            if row.get("instance_id") and branch_meta.get("instance_id"):
                mismatch = row["instance_id"] != branch_meta["instance_id"]
                print(f"instance_id_mismatch={str(mismatch).lower()}")

        conversation_meta, _ = _fetch_conversation_meta(db_user, row.get("conversation_id"))
        if conversation_meta:
            trace = _summarize_trace(conversation_meta.get("context"))
            if trace:
                print(f"decision_trace={json.dumps(trace, ensure_ascii=False)}")

        if client_meta and row.get("message_id"):
            outbox_summary, _ = _fetch_outbox_summary(
                db_user,
                client_meta.get("client_id"),
                row.get("message_id"),
            )
            print(f"outbox_summary={json.dumps(outbox_summary, ensure_ascii=False)}")

        latest_outbox, _ = _fetch_latest_outbox_for_conversation(
            db_user,
            row.get("conversation_id"),
        )
        if latest_outbox:
            payload_meta = _extract_outbox_payload_meta(latest_outbox.get("payload_json"))
            print(
                "outbox_latest="
                + json.dumps(
                    {
                        "status": latest_outbox.get("status"),
                        "inbound_message_id": latest_outbox.get("inbound_message_id"),
                        "payload_meta": payload_meta,
                    },
                    ensure_ascii=False,
                )
            )

    if args.traefik and client_slug:
        hits, hit_error = _fetch_traefik_hits(client_slug, args.traefik_minutes, 10)
        if hit_error:
            print(f"traefik_error: {hit_error}")
        if hits:
            print("traefik_hits:")
            for line in hits:
                print(line)

def _run_trace_bundle(args):
    db_user = _resolve_db_user_simple()
    client_slug = args.client_slug
    branch_id = None
    if not client_slug and args.receiver_phone:
        resolved_branch, error = _fetch_client_by_branch_phone(db_user, args.receiver_phone)
        if error:
            raise SystemExit(f"trace-bundle: receiver phone lookup failed ({error})")
        if not resolved_branch:
            raise SystemExit("trace-bundle: receiver phone not found; provide --client-slug")
        client_slug = resolved_branch.get("client_slug")
        branch_id = resolved_branch.get("branch_id")

    clauses = ["m.role = 'user'"]
    safe_slug = None
    if client_slug:
        safe_slug = _escape_sql_literal(client_slug)
        clauses.append(f"cl.name = '{safe_slug}'")
    if branch_id:
        safe_branch = _escape_sql_literal(branch_id)
        clauses.append(f"c.branch_id = '{safe_branch}'")
    if args.remote_jid:
        safe_jid = _escape_sql_literal(args.remote_jid)
        clauses.append(f"u.remote_jid = '{safe_jid}'")

    if args.message_uuid:
        safe_uuid = _escape_sql_literal(args.message_uuid)
        clauses.append(f"m.id = '{safe_uuid}'")
    elif args.message_id:
        safe_message = _escape_sql_literal(args.message_id)
        clauses.append(f"m.metadata->>'messageId' = '{safe_message}'")
    elif args.conversation_id:
        safe_conv = _escape_sql_literal(args.conversation_id)
        clauses.append(f"m.conversation_id = '{safe_conv}'")
    elif args.text:
        safe_text = _escape_sql_literal(args.text)
        minutes = int(max(args.minutes, 1))
        clauses.append(f"m.content ILIKE '%{safe_text}%'")
        clauses.append(f"m.created_at > now() - interval '{minutes} minutes'")
    else:
        raise SystemExit(
            "trace-bundle: provide --text, --message-id, --message-uuid, or --conversation-id"
        )

    where_clause = " AND ".join(clauses)
    rows, error = _fetch_message_bundle_rows(db_user, where_clause, args.limit)
    if error:
        raise SystemExit(f"trace-bundle: db error ({error})")
    if not rows:
        print("trace-bundle: no inbound messages found.")
        return

    client_meta = None
    if client_slug:
        client_meta, _ = _fetch_client_meta(db_user, client_slug)

    bundles = []
    for row in rows:
        conv_id = row.get("conversation_id")
        decision_meta = row.get("decision_meta") if isinstance(row.get("decision_meta"), dict) else {}
        timing_meta = decision_meta.get("timing") if isinstance(decision_meta, dict) else None
        timing_snapshot = timing_meta if isinstance(timing_meta, dict) else {}
        conversation_meta, _ = _fetch_conversation_meta(db_user, conv_id)
        context = conversation_meta.get("context") if isinstance(conversation_meta, dict) else None
        decision_trace = _trace_as_list(context.get("decision_trace")) if isinstance(context, dict) else []

        outbox_summary = None
        outbox_rows = []
        outbox_latest = None
        if client_meta and row.get("message_id"):
            outbox_summary, _ = _fetch_outbox_summary(
                db_user,
                client_meta.get("client_id"),
                row.get("message_id"),
            )
            outbox_rows, _ = _fetch_outbox_rows(
                db_user,
                client_meta.get("client_id"),
                row.get("message_id"),
                limit=args.outbox_limit,
            )
        if not outbox_rows and conv_id:
            outbox_latest, _ = _fetch_latest_outbox_for_conversation(db_user, conv_id)
            if outbox_latest:
                outbox_latest["payload_meta"] = _extract_outbox_payload_meta(
                    outbox_latest.get("payload_json")
                )
                outbox_latest.pop("payload_json", None)

        latency = _compute_outbox_latency(row.get("created_at"), outbox_rows)

        bundles.append(
            {
                "message": {
                    "message_uuid": row.get("message_uuid"),
                    "message_id": row.get("message_id"),
                    "created_at": row.get("created_at"),
                    "remote_jid": row.get("remote_jid"),
                    "instance_id": row.get("instance_id"),
                    "conversation_id": conv_id,
                    "branch_id": row.get("branch_id"),
                    "client_slug": row.get("client_slug"),
                    "conversation_state": row.get("conversation_state"),
                    "content": row.get("content"),
                },
                "decision_meta": decision_meta,
                "timing": {
                    "stages": timing_snapshot.get("stages"),
                    "outbox": timing_snapshot.get("outbox"),
                    "pipeline_ms": timing_snapshot.get("pipeline_ms"),
                    "pipeline_started_at": timing_snapshot.get("pipeline_started_at"),
                    "pipeline_finished_at": timing_snapshot.get("pipeline_finished_at"),
                },
                "decision_trace": decision_trace,
                "conversation": {
                    "state": conversation_meta.get("state") if isinstance(conversation_meta, dict) else None,
                    "telegram_topic_id": conversation_meta.get("telegram_topic_id")
                    if isinstance(conversation_meta, dict)
                    else None,
                },
                "outbox": {
                    "summary": outbox_summary,
                    "rows": outbox_rows,
                    "latest": outbox_latest,
                    "latency_ms": latency,
                },
            }
        )

    payload = {
        "query": {
            "client_slug": client_slug,
            "receiver_phone": args.receiver_phone,
            "remote_jid": args.remote_jid,
            "message_id": args.message_id,
            "message_uuid": args.message_uuid,
            "conversation_id": args.conversation_id,
            "text": args.text,
            "minutes": args.minutes,
        },
        "bundles": bundles,
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(output)
        return
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(output + "\n")
    print(json.dumps({"output": args.output, "count": len(bundles)}, ensure_ascii=False))


def _resolve_booking_commit_steps(case):
    now = datetime.now(timezone.utc) + timedelta(days=2)
    now = now.replace(minute=0, second=0, microsecond=0)
    booking_time = now.strftime("%Y-%m-%d %H:%M")
    booking_name = "Алия"
    steps = []
    for step in case.get("steps") or []:
        message = step.get("message") or ""
        if message == "__BOOKING_TIME__":
            message = booking_time
        elif message == "__BOOKING_NAME__":
            message = booking_name
        steps.append({**step, "message": message})
    return steps, {"booking_time": booking_time, "booking_name": booking_name}


def _run_livecheck_ca05_booking(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    steps = case.get("steps") or []
    if not steps:
        raise SystemExit("livecheck-auto: CA05 missing steps")
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    allowlist_jids = context["allowlist_jids"]
    allow_non_allowlist = context.get("allow_non_allowlist")
    fail_fast_after = context.get("fail_fast_after")
    outbox_url = f"{base_url}/admin/outbox/process"
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0
    min_wait = max(min(args.min_wait, args.max_wait), outbox_wait_seconds)
    max_wait = max(max(args.min_wait, args.max_wait), outbox_wait_seconds)

    if not remote_jid or (remote_jid not in allowlist_jids and not allow_non_allowlist):
        raise SystemExit("livecheck-auto: CA05 remote_jid not in allowlist")

    results = []
    conv_id = None
    reset_summary = None

    if not args.dry_run:
        reset_text = "начнем сначала"
        reset_marker = f"LC:AUTO:CA05:RESET:{timestamp}"
        reset_message_id = f"LC-AUTO-{timestamp}-CA05-RESET-{uuid.uuid4().hex[:8]}"
        reset_payload = {
            "body": {
                "messageType": "text",
                "message": f"{reset_text} [{reset_marker}]",
                "metadata": {
                    "sender": "LivecheckAuto",
                    "timestamp": int(time.time()),
                    "messageId": reset_message_id,
                    "remoteJid": remote_jid,
                },
            }
        }
        if instance_id:
            reset_payload["body"]["metadata"]["instanceId"] = instance_id
        reset_status, reset_body, reset_error = _send_webhook_payload(
            webhook_url, reset_payload, webhook_secret, args.timeout
        )
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "step": "reset",
                    "marker": reset_marker,
                    "message_id": reset_message_id,
                    "remote_jid": remote_jid,
                    "text": reset_payload["body"]["message"],
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "status": "sent" if reset_status and 200 <= reset_status < 300 else "error",
                    "http_status": reset_status,
                    "error": reset_error,
                    "response": (reset_body or "")[:200] if reset_body else None,
                },
                ensure_ascii=False,
            )
        )
        _post_admin_outbox_with_wait(
            outbox_url,
            admin_token,
            args.timeout,
            outbox_wait_seconds,
        )
        conv_id, reset_meta, reset_meta_error = _poll_decision_meta(
            db_user,
            reset_message_id,
            args.poll_timeout,
            args.poll_interval,
            require_action=False,
        )
        if reset_meta_error:
            raise SystemExit(f"livecheck-auto: CA05 reset poll failed ({reset_meta_error})")
        reset_conv_meta, reset_conv_error = _fetch_conversation_meta(db_user, conv_id)
        reset_context = reset_conv_meta.get("context") if isinstance(reset_conv_meta, dict) else None
        reset_expected = (
            reset_context.get("expected_reply_type") if isinstance(reset_context, dict) else None
        )
        reset_booking = reset_context.get("booking") if isinstance(reset_context, dict) else None
        booking_active = False
        booking_service = None
        if isinstance(reset_booking, dict):
            booking_active = bool(reset_booking.get("active"))
            booking_service = reset_booking.get("service")
        if reset_expected:
            raise SystemExit("livecheck-auto: CA05 reset did not clear expected_reply_type")
        if booking_active:
            raise SystemExit("livecheck-auto: CA05 reset did not clear booking active")
        reset_summary = {
            "reset_message_id": reset_message_id,
            "reset_action": (reset_meta or {}).get("action"),
            "reset_intent": (reset_meta or {}).get("intent"),
            "reset_expected_reply_type": reset_expected,
            "reset_booking_active": booking_active,
            "reset_booking_service": booking_service,
            "reset_error": reset_conv_error,
        }

    for idx, step in enumerate(steps, start=1):
        base_text = step.get("message") or ""
        if not base_text:
            raise SystemExit("livecheck-auto: CA05 empty step message")
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"LC:AUTO:CA05:{case['case_id']}:{timestamp}:{idx:02d}"
        message = f"{text} [{marker}]"
        message_id = f"LC-AUTO-{timestamp}-CA05-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()

        metadata = {
            "sender": "LivecheckAuto",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {"body": {"messageType": "text", "message": message, "metadata": metadata}}

        status = "dry_run"
        response_status = None
        response_body = None
        response_error = None
        if not args.dry_run:
            response_status, response_body, response_error = _send_webhook_payload(
                webhook_url, payload, webhook_secret, args.timeout
            )
            status = "sent" if response_status and 200 <= response_status < 300 else "error"
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "step": idx,
                    "marker": marker,
                    "message_id": message_id,
                    "remote_jid": remote_jid,
                    "text": message,
                    "sent_at": sent_at,
                    "status": status,
                    "http_status": response_status,
                    "error": response_error,
                    "response": (response_body or "")[:200] if response_body else None,
                },
                ensure_ascii=False,
            )
        )

        meta = None
        conv_meta = None
        conv_error = None
        if not args.dry_run:
            _post_admin_outbox_with_wait(
                outbox_url,
                admin_token,
                args.timeout,
                outbox_wait_seconds,
            )
            conv_id, meta, error = _poll_decision_meta(
                db_user,
                message_id,
                args.poll_timeout,
                args.poll_interval,
                fail_fast_after=fail_fast_after,
            )
            if error:
                raise SystemExit(f"livecheck-auto: CA05 decision_meta poll failed ({error})")
            conv_meta, conv_error = _fetch_conversation_meta(db_user, conv_id)

        conv_context = conv_meta.get("context") if isinstance(conv_meta, dict) else None
        expected_reply_type = conv_context.get("expected_reply_type") if isinstance(conv_context, dict) else None
        booking_state = conv_context.get("booking") if isinstance(conv_context, dict) else None
        trace_list = conv_context.get("decision_trace") if isinstance(conv_context, dict) else None
        interrupt_trace = None
        for entry in reversed(_trace_as_list(trace_list)):
            if entry.get("stage") == "booking_interrupt":
                interrupt_trace = entry
                break

        if not args.dry_run:
            expected_reply = step.get("expect_expected_reply_type")
            if expected_reply and expected_reply_type != expected_reply:
                raise SystemExit(
                    f"livecheck-auto: CA05 expected_reply_type mismatch ({expected_reply_type})"
                )
            expected_llm = step.get("expect_llm_used")
            if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                raise SystemExit("livecheck-auto: CA05 llm_used mismatch")
            expected_service = step.get("expect_booking_service")
            if expected_service:
                service = None
                if isinstance(booking_state, dict):
                    service = booking_state.get("service")
                if not service or expected_service not in str(service).lower():
                    raise SystemExit("livecheck-auto: CA05 booking.service mismatch")
            if step.get("expect_booking_interrupt"):
                if (meta or {}).get("booking_info_interrupt") is not True:
                    raise SystemExit("livecheck-auto: CA05 booking_info_interrupt mismatch")
                info_intents = (meta or {}).get("booking_info_intents")
                if not isinstance(info_intents, list) or not info_intents:
                    raise SystemExit("livecheck-auto: CA05 booking_info_intents empty")
                if not interrupt_trace:
                    raise SystemExit("livecheck-auto: CA05 missing booking_interrupt trace")
                trace_intents = interrupt_trace.get("info_intents")
                if not isinstance(trace_intents, list) or not trace_intents:
                    raise SystemExit("livecheck-auto: CA05 trace info_intents empty")

        results.append(
            {
                "step": idx,
                "message_id": message_id,
                "conversation_id": conv_id,
                "expected_reply_type": expected_reply_type,
                "booking_service": booking_state.get("service") if isinstance(booking_state, dict) else None,
                "booking_info_interrupt": (meta or {}).get("booking_info_interrupt"),
                "booking_info_intents": (meta or {}).get("booking_info_intents"),
                "trace_booking_interrupt": bool(interrupt_trace),
                "trace_info_intents": interrupt_trace.get("info_intents") if interrupt_trace else None,
                "llm_used": (meta or {}).get("llm_used"),
                "error": conv_error,
            }
        )

        if idx < len(steps):
            time.sleep(rng.uniform(min_wait, max_wait))

    summary = {
        "suite": "ca05-booking",
        "case_id": case["case_id"],
        "conversation_id": conv_id,
        "results": results,
        "reset": reset_summary,
    }
    return summary


def _run_livecheck_ca05_booking_commit(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    steps, booking_values = _resolve_booking_commit_steps(case)
    if not steps:
        raise SystemExit("livecheck-auto: CA05 booking-commit missing steps")
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    client_meta = context.get("client_meta") or {}
    client_id = client_meta.get("client_id")
    allowlist_jids = context["allowlist_jids"]
    allow_non_allowlist = context.get("allow_non_allowlist")
    fail_fast_after = context.get("fail_fast_after")
    outbox_url = f"{base_url}/admin/outbox/process"
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0
    min_wait = max(min(args.min_wait, args.max_wait), outbox_wait_seconds)
    max_wait = max(max(args.min_wait, args.max_wait), outbox_wait_seconds)

    if not remote_jid or (remote_jid not in allowlist_jids and not allow_non_allowlist):
        raise SystemExit("livecheck-auto: CA05 booking-commit remote_jid not in allowlist")

    results = []
    conv_id = None
    appointment_id = None
    appointment_row = None
    audit_rows = None
    booking_commit_trace = None
    outbox_summary = None
    outbox_rows = None

    for idx, step in enumerate(steps, start=1):
        base_text = step.get("message") or ""
        if not base_text:
            raise SystemExit("livecheck-auto: CA05 booking-commit empty step message")
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"LC:AUTO:CA05-COMMIT:{timestamp}:{idx:02d}"
        include_marker = not step.get("suppress_marker")
        message = f"{text} [{marker}]" if include_marker else text
        message_id = f"LC-AUTO-{timestamp}-CA05C-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()

        metadata = {
            "sender": "LivecheckAuto",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {"body": {"messageType": "text", "message": message, "metadata": metadata}}

        status = "dry_run"
        response_status = None
        response_body = None
        response_error = None
        if not args.dry_run:
            response_status, response_body, response_error = _send_webhook_payload(
                webhook_url, payload, webhook_secret, args.timeout
            )
            status = "sent" if response_status and 200 <= response_status < 300 else "error"
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "step": idx,
                    "marker": marker,
                    "message_id": message_id,
                    "remote_jid": remote_jid,
                    "text": message,
                    "sent_at": sent_at,
                    "status": status,
                    "http_status": response_status,
                    "error": response_error,
                    "response": (response_body or "")[:200] if response_body else None,
                },
                ensure_ascii=False,
            )
        )

        meta = None
        conv_meta = None
        conv_error = None
        if not args.dry_run:
            _post_admin_outbox_with_wait(
                outbox_url,
                admin_token,
                args.timeout,
                outbox_wait_seconds,
            )
            conv_id, meta, error = _poll_decision_meta(
                db_user,
                message_id,
                args.poll_timeout,
                args.poll_interval,
                fail_fast_after=fail_fast_after,
            )
            if error:
                raise SystemExit(f"livecheck-auto: CA05 booking-commit decision_meta poll failed ({error})")
            conv_meta, conv_error = _fetch_conversation_meta(db_user, conv_id)

        conv_context = conv_meta.get("context") if isinstance(conv_meta, dict) else None
        expected_reply_type = conv_context.get("expected_reply_type") if isinstance(conv_context, dict) else None
        booking_state = conv_context.get("booking") if isinstance(conv_context, dict) else None
        trace_list = conv_context.get("decision_trace") if isinstance(conv_context, dict) else None
        booking_commit_trace = None
        for entry in reversed(_trace_as_list(trace_list)):
            if entry.get("stage") == "booking_commit":
                booking_commit_trace = entry
                break

        if not args.dry_run:
            expected_reply = step.get("expect_expected_reply_type")
            if expected_reply and expected_reply_type != expected_reply:
                raise SystemExit(
                    "livecheck-auto: CA05 booking-commit expected_reply_type mismatch "
                    f"({expected_reply_type})"
                )
            expected_llm = step.get("expect_llm_used")
            if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                raise SystemExit("livecheck-auto: CA05 booking-commit llm_used mismatch")
            expected_service = step.get("expect_booking_service")
            if expected_service:
                service = None
                if isinstance(booking_state, dict):
                    service = booking_state.get("service")
                if not service or expected_service not in str(service).lower():
                    raise SystemExit("livecheck-auto: CA05 booking-commit booking.service mismatch")
            if step.get("expect_booking_commit"):
                appointment_id = (meta or {}).get("appointment_id") or (
                    booking_commit_trace or {}
                ).get("appointment_id")
                if not appointment_id:
                    raise SystemExit("livecheck-auto: CA05 booking-commit appointment_id missing")
                appointment_row, appointment_error = _fetch_appointment_row(db_user, appointment_id)
                if appointment_error:
                    raise SystemExit(
                        f"livecheck-auto: CA05 booking-commit appointment fetch failed ({appointment_error})"
                    )
                if not appointment_row:
                    raise SystemExit("livecheck-auto: CA05 booking-commit appointment row missing")
                audit_rows, audit_error = _fetch_appointment_audit_rows(
                    db_user, appointment_id, limit=3
                )
                if audit_error:
                    raise SystemExit(
                        f"livecheck-auto: CA05 booking-commit appointment_audit fetch failed ({audit_error})"
                    )
                if not audit_rows:
                    raise SystemExit("livecheck-auto: CA05 booking-commit appointment_audit missing")
                outbox_summary, outbox_error = _fetch_outbox_summary(
                    db_user, client_id, message_id
                )
                if outbox_error:
                    raise SystemExit(
                        f"livecheck-auto: CA05 booking-commit outbox summary failed ({outbox_error})"
                    )
                if not outbox_summary or not outbox_summary.get("count"):
                    raise SystemExit("livecheck-auto: CA05 booking-commit outbox missing")
                outbox_rows, outbox_rows_error = _fetch_outbox_rows(
                    db_user, client_id, message_id, limit=3
                )
                if outbox_rows_error:
                    raise SystemExit(
                        f"livecheck-auto: CA05 booking-commit outbox rows failed ({outbox_rows_error})"
                    )
                if outbox_summary.get("status") == "FAILED":
                    raise SystemExit("livecheck-auto: CA05 booking-commit outbox status FAILED")
                if not booking_commit_trace:
                    raise SystemExit("livecheck-auto: CA05 booking-commit trace missing")

        results.append(
            {
                "step": idx,
                "message_id": message_id,
                "conversation_id": conv_id,
                "expected_reply_type": expected_reply_type,
                "booking_service": booking_state.get("service") if isinstance(booking_state, dict) else None,
                "appointment_id": appointment_id,
                "appointment_status": appointment_row.get("status") if isinstance(appointment_row, dict) else None,
                "appointment_audit_action": audit_rows[0].get("action")
                if isinstance(audit_rows, list) and audit_rows
                else None,
                "trace_booking_commit": bool(booking_commit_trace),
                "outbox_status": outbox_summary.get("status") if isinstance(outbox_summary, dict) else None,
                "llm_used": (meta or {}).get("llm_used"),
                "error": conv_error,
            }
        )

        if idx < len(steps):
            time.sleep(rng.uniform(min_wait, max_wait))

    summary = {
        "suite": "ca05-booking-commit",
        "case_id": case["case_id"],
        "conversation_id": conv_id,
        "booking_time": booking_values.get("booking_time"),
        "booking_name": booking_values.get("booking_name"),
        "results": results,
    }
    return summary

def _run_livecheck_ca06_reset(args, context, *, suite_label="CA06"):
    if args.dry_run:
        return None
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    allowlist_jids = context["allowlist_jids"]
    allow_non_allowlist = context.get("allow_non_allowlist")
    fail_fast_after = context.get("fail_fast_after")
    outbox_url = f"{base_url}/admin/outbox/process"
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0

    if not remote_jid or (remote_jid not in allowlist_jids and not allow_non_allowlist):
        raise SystemExit(f"livecheck-auto: {suite_label} remote_jid not in allowlist")

    reset_text = "начнем сначала"
    reset_marker = f"LC:AUTO:{suite_label}:RESET:{timestamp}"
    reset_message_id = f"LC-AUTO-{timestamp}-{suite_label}-RESET-{uuid.uuid4().hex[:8]}"
    reset_payload = {
        "body": {
            "messageType": "text",
            "message": f"{reset_text} [{reset_marker}]",
            "metadata": {
                "sender": "LivecheckAuto",
                "timestamp": int(time.time()),
                "messageId": reset_message_id,
                "remoteJid": remote_jid,
            },
        }
    }
    if instance_id:
        reset_payload["body"]["metadata"]["instanceId"] = instance_id
    reset_status, reset_body, reset_error = _send_webhook_payload(
        webhook_url, reset_payload, webhook_secret, args.timeout
    )
    print(
        json.dumps(
            {
                "case_id": f"{suite_label}_RESET",
                "step": "reset",
                "marker": reset_marker,
                "message_id": reset_message_id,
                "remote_jid": remote_jid,
                "text": reset_payload["body"]["message"],
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "status": "sent" if reset_status and 200 <= reset_status < 300 else "error",
                "http_status": reset_status,
                "error": reset_error,
                "response": (reset_body or "")[:200] if reset_body else None,
            },
            ensure_ascii=False,
        )
    )
    _post_admin_outbox_with_wait(
        outbox_url,
        admin_token,
        args.timeout,
        outbox_wait_seconds,
    )
    conv_id, reset_meta, reset_meta_error = _poll_decision_meta(
        db_user,
        reset_message_id,
        args.poll_timeout,
        args.poll_interval,
        require_action=False,
        fail_fast_after=fail_fast_after,
    )
    if reset_meta_error:
        raise SystemExit(f"livecheck-auto: CA06 reset meta poll failed ({reset_meta_error})")
    reset_conv_meta, reset_trace, reset_trace_error = _poll_decision_trace(
        db_user, conv_id, args.poll_timeout, args.poll_interval
    )
    if reset_trace_error:
        raise SystemExit(f"livecheck-auto: CA06 reset trace poll failed ({reset_trace_error})")
    last_trace = reset_trace[-1] if reset_trace else None
    reset_state = reset_conv_meta.get("state") if isinstance(reset_conv_meta, dict) else None
    return {
        "reset_suite": suite_label,
        "reset_message_id": reset_message_id,
        "reset_action": (reset_meta or {}).get("action"),
        "reset_intent": (reset_meta or {}).get("intent"),
        "reset_state": reset_state,
        "reset_trace_stage": (last_trace or {}).get("stage"),
        "reset_trace_decision": (last_trace or {}).get("decision"),
    }

def _run_livecheck_ca08_state(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    outbox_url = f"{base_url}/admin/outbox/process"
    allowlist_jids = context["allowlist_jids"]
    allow_non_allowlist = context.get("allow_non_allowlist")
    fail_fast_after = context.get("fail_fast_after")
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0

    if not remote_jid or (remote_jid not in allowlist_jids and not allow_non_allowlist):
        raise SystemExit("livecheck-auto: CA08 remote_jid not in allowlist")

    text, marker, message = _build_livecheck_message(
        rng, case, "LC:AUTO:CA08", timestamp, 1, args.noise
    )
    message_id = f"LC-AUTO-{timestamp}-CA08-{uuid.uuid4().hex[:8]}"
    sent_at = datetime.now(timezone.utc).isoformat()

    metadata = {
        "sender": "LivecheckAuto",
        "timestamp": int(time.time()),
        "messageId": message_id,
        "remoteJid": remote_jid,
    }
    if instance_id:
        metadata["instanceId"] = instance_id
    payload = {"body": {"messageType": "text", "message": message, "metadata": metadata}}

    status = "dry_run"
    response_status = None
    response_body = None
    response_error = None
    if not args.dry_run:
        response_status, response_body, response_error = _send_webhook_payload(
            webhook_url, payload, webhook_secret, args.timeout
        )
        status = "sent" if response_status and 200 <= response_status < 300 else "error"
    print(
        json.dumps(
            {
                "case_id": case["case_id"],
                "marker": marker,
                "message_id": message_id,
                "remote_jid": remote_jid,
                "text": message,
                "sent_at": sent_at,
                "expected_policy_section": case["expected_policy_section"],
                "status": status,
                "http_status": response_status,
                "error": response_error,
                "response": (response_body or "")[:200] if response_body else None,
            },
            ensure_ascii=False,
        )
    )

    conv_id = None
    meta = None
    outbox_status = None
    outbox_body = None
    outbox_error = None
    if not args.dry_run:
        outbox_status, outbox_body, outbox_error = _post_admin_outbox_with_wait(
            outbox_url,
            admin_token,
            args.timeout,
            outbox_wait_seconds,
        )
        conv_id, meta, error = _poll_decision_meta(
            db_user,
            message_id,
            args.poll_timeout,
            args.poll_interval,
            fail_fast_after=fail_fast_after,
        )
        if error:
            raise SystemExit(f"livecheck-auto: CA08 decision_meta poll failed ({error})")

    conv_before, conv_before_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_before, handover_before_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)

    ack_text = args.ack_text or "ок"
    ack_marker = f"LC:ACK:CA08:{timestamp}:01"
    ack_message_id = f"LC-ACK-{timestamp}-CA08-{uuid.uuid4().hex[:8]}"
    ack_payload = {
        "body": {
            "messageType": "text",
            "message": ack_text,
            "metadata": {
                "sender": "LivecheckAuto",
                "timestamp": int(time.time()),
                "messageId": ack_message_id,
                "remoteJid": remote_jid,
            },
        }
    }
    if instance_id:
        ack_payload["body"]["metadata"]["instanceId"] = instance_id

    ack_status = None
    ack_body = None
    ack_error = None
    ack_meta = None
    ack_outbox_status = None
    ack_outbox_body = None
    ack_outbox_error = None
    if not args.dry_run:
        ack_status, ack_body, ack_error = _send_webhook_payload(
            webhook_url, ack_payload, webhook_secret, args.timeout
        )
        ack_outbox_status, ack_outbox_body, ack_outbox_error = _post_admin_outbox_with_wait(
            outbox_url,
            admin_token,
            args.timeout,
            outbox_wait_seconds,
        )
        _, ack_meta, ack_meta_error = _poll_decision_meta(
            db_user,
            ack_message_id,
            args.poll_timeout,
            args.poll_interval,
            fail_fast_after=fail_fast_after,
        )
        if ack_meta_error:
            raise SystemExit(f"livecheck-auto: CA08 ACK poll failed ({ack_meta_error})")

    conv_after, conv_after_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_after, handover_after_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)

    trace_list = None
    if conv_after and isinstance(conv_after.get("context"), dict):
        trace_list = conv_after.get("context", {}).get("decision_trace")

    summary = {
        "suite": "ca08-state",
        "message_id": message_id,
        "ack_message_id": ack_message_id,
        "ack_marker": ack_marker,
        "conversation_id": conv_id,
        "policy_gate": (meta or {}).get("policy_gate"),
        "action": (meta or {}).get("action"),
        "pending_action": (ack_meta or {}).get("pending_action"),
        "ack_text": ack_text,
        "conversation_state_before": (conv_before or {}).get("state"),
        "conversation_state_after": (conv_after or {}).get("state"),
        "handover_status_before": (handover_before or {}).get("status"),
        "handover_status_after": (handover_after or {}).get("status"),
        "handover_added_to_knowledge": (handover_after or {}).get("added_to_knowledge"),
        "pending_sla_trace": _trace_has_entry(trace_list, "pending_sla", "pending_ack"),
        "pending_resume_trace": _trace_has_entry(trace_list, "pending_resume"),
        "errors": {
            "conversation_before": conv_before_error,
            "handover_before": handover_before_error,
            "conversation_after": conv_after_error,
            "handover_after": handover_after_error,
            "ack_error": ack_error,
            "outbox_error": outbox_error,
            "ack_outbox_error": ack_outbox_error,
        },
        "ack_http_status": ack_status,
        "ack_http_response": (ack_body or "")[:200] if ack_body else None,
        "outbox_status": outbox_status,
        "outbox_response": (outbox_body or "")[:200] if outbox_body else None,
        "ack_outbox_status": ack_outbox_status,
        "ack_outbox_response": (ack_outbox_body or "")[:200] if ack_outbox_body else None,
    }
    return summary

def _run_livecheck_ca09_manager(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    client_slug = context["client_slug"]
    client_meta = context["client_meta"]
    learning_env = context["learning_env"]
    outbox_url = f"{base_url}/admin/outbox/process"
    allowlist_jids = context["allowlist_jids"]
    allow_non_allowlist = context.get("allow_non_allowlist")
    fail_fast_after = context.get("fail_fast_after")
    qdrant_env = context["qdrant_env"]
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0

    if not remote_jid or (remote_jid not in allowlist_jids and not allow_non_allowlist):
        raise SystemExit("livecheck-auto: CA09 remote_jid not in allowlist")

    text, marker, message = _build_livecheck_message(
        rng, case, "LC:AUTO:CA09", timestamp, 1, args.noise
    )
    message_id = f"LC-AUTO-{timestamp}-CA09-{uuid.uuid4().hex[:8]}"
    metadata = {
        "sender": "LivecheckAuto",
        "timestamp": int(time.time()),
        "messageId": message_id,
        "remoteJid": remote_jid,
    }
    if instance_id:
        metadata["instanceId"] = instance_id
    payload = {"body": {"messageType": "text", "message": message, "metadata": metadata}}

    status = "dry_run"
    response_status = None
    response_body = None
    response_error = None
    if not args.dry_run:
        response_status, response_body, response_error = _send_webhook_payload(
            webhook_url, payload, webhook_secret, args.timeout
        )
        status = "sent" if response_status and 200 <= response_status < 300 else "error"
    print(
        json.dumps(
            {
                "case_id": case["case_id"],
                "marker": marker,
                "message_id": message_id,
                "remote_jid": remote_jid,
                "text": message,
                "expected_policy_section": case["expected_policy_section"],
                "status": status,
                "http_status": response_status,
                "error": response_error,
                "response": (response_body or "")[:200] if response_body else None,
            },
            ensure_ascii=False,
        )
    )

    conv_id = None
    meta = None
    if not args.dry_run:
        _post_admin_outbox_with_wait(
            outbox_url,
            admin_token,
            args.timeout,
            outbox_wait_seconds,
        )
        conv_id, meta, error = _poll_decision_meta(
            db_user,
            message_id,
            args.poll_timeout,
            args.poll_interval,
            fail_fast_after=fail_fast_after,
        )
        if error:
            raise SystemExit(f"livecheck-auto: CA09 decision_meta poll failed ({error})")

    conv_before, conv_before_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_before, handover_before_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)

    chat_id_raw = client_meta.get("telegram_chat_id") if client_meta else None
    topic_id = (conv_before or {}).get("telegram_topic_id")
    if not chat_id_raw:
        raise SystemExit("livecheck-auto: CA09 missing telegram_chat_id for client")
    if not topic_id:
        raise SystemExit("livecheck-auto: CA09 missing telegram_topic_id for conversation")
    try:
        chat_id = int(chat_id_raw)
    except ValueError:
        raise SystemExit(f"livecheck-auto: CA09 invalid telegram_chat_id {chat_id_raw}")

    owner_id, owner_username = _parse_owner_identity(client_meta.get("owner_telegram_id"))
    manager_id = owner_id if owner_id is not None else 10001
    manager_username = owner_username or "ci_manager"

    qdrant_collection = learning_env.get("qdrant_collection_effective") or ""
    if not qdrant_collection.endswith("_ci"):
        raise SystemExit("livecheck-auto: CA09 requires _ci Qdrant collection")

    manager_text = "Менеджер: уточнили детали, вернемся с ответом."
    telegram_payload = {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time() * 1000) % 1000000,
            "date": int(time.time()),
            "chat": {"id": chat_id, "type": "supergroup", "title": "CI"},
            "from": {
                "id": manager_id,
                "is_bot": False,
                "first_name": "CI",
                "last_name": "Runner",
                "username": manager_username,
            },
            "text": manager_text,
            "message_thread_id": topic_id,
        },
    }

    manager_status = None
    manager_body = None
    manager_error = None
    if not args.dry_run:
        manager_status, manager_body, manager_error = _send_json_payload(
            f"{base_url}/telegram-webhook", telegram_payload, args.timeout
        )
        _post_admin_outbox_with_wait(
            outbox_url,
            admin_token,
            args.timeout,
            outbox_wait_seconds,
        )

    conv_after, conv_after_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_after, handover_after_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)
    outbox_latest, outbox_error = _fetch_latest_outbox_for_conversation(db_user, conv_id) if conv_id else (None, None)
    outbox_remote_jid = None
    if outbox_latest and isinstance(outbox_latest.get("payload_json"), dict):
        payload_meta = outbox_latest["payload_json"].get("body", {}).get("metadata", {})
        outbox_remote_jid = payload_meta.get("remoteJid")

    qdrant_found = None
    qdrant_error = None
    if not args.dry_run:
        handover_id = (handover_after or {}).get("handover_id")
        if not handover_id:
            qdrant_error = "qdrant: handover_id missing"
        else:
            qdrant_found, qdrant_error = _qdrant_find_handover(
                container_name=context.get("container_name"),
                host=qdrant_env.get("host"),
                api_key=qdrant_env.get("api_key"),
                collection=qdrant_collection,
                handover_id=handover_id,
                client_slug=client_slug,
                timeout=args.timeout,
            )

    summary = {
        "suite": "ca09-manager",
        "message_id": message_id,
        "conversation_id": conv_id,
        "policy_gate": (meta or {}).get("policy_gate"),
        "action": (meta or {}).get("action"),
        "manager_message": manager_text,
        "manager_identity": {
            "manager_id": manager_id,
            "manager_username": manager_username,
            "owner_used": owner_id is not None or owner_username is not None,
        },
        "telegram_chat_id": chat_id,
        "telegram_topic_id": topic_id,
        "conversation_state_before": (conv_before or {}).get("state"),
        "conversation_state_after": (conv_after or {}).get("state"),
        "handover_status_before": (handover_before or {}).get("status"),
        "handover_status_after": (handover_after or {}).get("status"),
        "assigned_to": (handover_after or {}).get("assigned_to"),
        "first_response_at": (handover_after or {}).get("first_response_at"),
        "manager_response": (handover_after or {}).get("manager_response"),
        "learning_mode": learning_env.get("learning_mode"),
        "qdrant_collection": qdrant_collection,
        "added_to_knowledge": (handover_after or {}).get("added_to_knowledge"),
        "knowledge_doc_id": (handover_after or {}).get("knowledge_doc_id"),
        "qdrant_found": qdrant_found,
        "qdrant_error": qdrant_error,
        "outbox_status": (outbox_latest or {}).get("status"),
        "outbox_remote_jid": outbox_remote_jid,
        "telegram_status": manager_status,
        "errors": {
            "conversation_before": conv_before_error,
            "handover_before": handover_before_error,
            "conversation_after": conv_after_error,
            "handover_after": handover_after_error,
            "outbox": outbox_error,
            "telegram": manager_error,
        },
        "telegram_response": (manager_body or "")[:200] if manager_body else None,
    }
    return summary

def _run_livecheck_ca10_outbox(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0
    db_user = context["db_user"]
    client_id = context["client_meta"].get("client_id") if context.get("client_meta") else None
    allowlist_jids = context["allowlist_jids"]
    allow_non_allowlist = context.get("allow_non_allowlist")

    if not client_id:
        raise SystemExit("livecheck-auto: CA10 missing client_id")
    if not remote_jid or (remote_jid not in allowlist_jids and not allow_non_allowlist):
        raise SystemExit("livecheck-auto: CA10 remote_jid not in allowlist")

    text, marker, message = _build_livecheck_message(
        rng, case, "LC:AUTO:CA10", timestamp, 1, args.noise
    )
    message_id = f"LC-DEDUP-{timestamp}-{uuid.uuid4().hex[:8]}"
    outbox_url = f"{base_url}/admin/outbox/process"

    def _send_once(seq):
        sent_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "body": {
                "messageType": "text",
                "message": f"{message} [SEQ:{seq:02d}]",
                "metadata": {
                    "sender": "LivecheckAuto",
                    "timestamp": int(time.time()),
                    "messageId": message_id,
                    "remoteJid": remote_jid,
                },
            }
        }
        if instance_id:
            payload["body"]["metadata"]["instanceId"] = instance_id
        response_status, response_body, response_error = _send_webhook_payload(
            webhook_url, payload, webhook_secret, args.timeout
        )
        status = "sent" if response_status and 200 <= response_status < 300 else "error"
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "marker": marker,
                    "message_id": message_id,
                    "remote_jid": remote_jid,
                    "text": payload["body"]["message"],
                    "sent_at": sent_at,
                    "status": status,
                    "http_status": response_status,
                    "error": response_error,
                    "response": (response_body or "")[:200] if response_body else None,
                },
                ensure_ascii=False,
            )
        )

    if not args.dry_run:
        _send_once(1)
        _send_once(2)
        if outbox_wait_seconds > 0:
            time.sleep(outbox_wait_seconds)
        _post_admin_outbox(outbox_url, admin_token, args.timeout)

    message_count, message_error = _fetch_message_count(db_user, message_id)
    dedup_count, dedup_error = _fetch_message_dedup_count(db_user, client_id, message_id)
    outbox_summary, outbox_error = _fetch_outbox_summary(db_user, client_id, message_id)
    if (
        not args.dry_run
        and outbox_summary
        and outbox_summary.get("status") == "PENDING"
    ):
        time.sleep(2.0)
        _post_admin_outbox(outbox_url, admin_token, args.timeout)
        outbox_summary, outbox_error = _fetch_outbox_summary(db_user, client_id, message_id)

    summary = {
        "suite": "ca10-outbox",
        "message_id": message_id,
        "message_count": message_count,
        "message_dedup_count": dedup_count,
        "outbox_count": (outbox_summary or {}).get("count"),
        "outbox_status": (outbox_summary or {}).get("status"),
        "errors": {
            "message_count": message_error,
            "dedup_count": dedup_error,
            "outbox": outbox_error,
        },
    }
    return summary

def _run_livecheck_auto(args):
    suite_cases = LIVECHECK_SUITES.get(args.suite)
    if not suite_cases:
        raise SystemExit(f"Unknown suite: {args.suite}")
    rng = random.Random(args.seed or int(time.time()))
    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_url = args.base_url.rstrip("/")
    client_slug = args.client_slug
    webhook_url = f"{base_url}/webhook/{client_slug}"

    container_name, _ = resolve_container_name()
    if client_slug != SAFE_ALLOWLIST_CLIENT_SLUG:
        raise SystemExit(
            f"livecheck-auto: client_slug {client_slug} not allowed; expected {SAFE_ALLOWLIST_CLIENT_SLUG}"
        )
    test_mode_enabled = _resolve_test_mode(container_name)
    allowlist_jids = _resolve_allowlist_jids(args.allowlist_jids, container_name)
    if not allowlist_jids:
        raise SystemExit("livecheck-auto: allowlist-jids is empty")
    if not test_mode_enabled:
        raise SystemExit("livecheck-auto: TEST_MODE disabled; refusing to run")
    allow_non_allowlist = bool(args.allow_non_allowlist)

    webhook_secret = _resolve_webhook_secret(client_slug, args.webhook_secret)
    if not webhook_secret:
        raise SystemExit("livecheck-auto: missing webhook secret")

    admin_token = args.admin_token or os.environ.get("ALERTS_ADMIN_TOKEN")
    if not admin_token and container_name:
        admin_token = _resolve_env_from_container(container_name, "ALERTS_ADMIN_TOKEN")
    if not admin_token and not args.dry_run:
        raise SystemExit("livecheck-auto: missing admin token")

    db_user = _resolve_db_user_simple()
    client_meta, client_error = _fetch_client_meta(db_user, client_slug)
    if client_error:
        raise SystemExit(f"livecheck-auto: client meta lookup failed ({client_error})")
    if not client_meta or not client_meta.get("client_id"):
        raise SystemExit(f"livecheck-auto: client {client_slug} not found in DB")

    branch_instance_id = client_meta.get("branch_instance_id")
    if not branch_instance_id:
        raise SystemExit("livecheck-auto: branch.instance_id missing for client")

    instance_id = (
        args.instance_id
        or os.environ.get("CHATFLOW_INSTANCE_ID")
        or os.environ.get("INSTANCE_ID")
        or branch_instance_id
    )
    if instance_id != branch_instance_id:
        raise SystemExit(
            f"livecheck-auto: instance_id mismatch (payload {instance_id} vs branch {branch_instance_id})"
        )
    instance_drift = bool(
        client_meta.get("client_instance_id")
        and client_meta.get("client_instance_id") != branch_instance_id
    )

    learning_env = _resolve_learning_env(container_name)
    qdrant_collection = learning_env.get("qdrant_collection") or ""
    if not qdrant_collection and test_mode_enabled:
        qdrant_collection = "truffles_knowledge_ci"
    learning_env["qdrant_collection_effective"] = qdrant_collection
    qdrant_env = _resolve_qdrant_env(container_name)

    selected_cases, requested_case_ids = _select_cases(suite_cases, args.case_ids)
    if selected_cases is None:
        selected_cases = suite_cases
        requested_case_ids = [case["case_id"] for case in suite_cases]

    if args.jid_mode == "allowlist":
        remote_jid = args.remote_jid or _select_allowlist_jid(
            allowlist_jids, args.suite, args.seed
        )
        if remote_jid not in allowlist_jids and not allow_non_allowlist:
            raise SystemExit(
                f"livecheck-auto: remote-jid {remote_jid} not in allowlist; refusing to send"
            )
    else:
        remote_jid = None

    common = {
        "suite": args.suite,
        "case_ids": requested_case_ids,
        "client_slug": client_slug,
        "instance_id": instance_id,
        "branch_instance_id": branch_instance_id,
        "client_instance_id": client_meta.get("client_instance_id"),
        "instance_drift": instance_drift,
        "jid_mode": args.jid_mode,
        "remote_jid": remote_jid,
        "allowlist_jids": allowlist_jids,
        "allow_non_allowlist": allow_non_allowlist,
        "test_mode": test_mode_enabled,
        "learning_mode": learning_env.get("learning_mode"),
        "qdrant_collection": learning_env.get("qdrant_collection_effective"),
    }

    outbox_wait_seconds = _resolve_outbox_wait_seconds(container_name)
    fail_fast_after = _resolve_fail_fast_after(args, outbox_wait_seconds)
    context = {
        "rng": rng,
        "cases": selected_cases,
        "timestamp": timestamp,
        "base_url": base_url,
        "webhook_url": webhook_url,
        "webhook_secret": webhook_secret,
        "admin_token": admin_token,
        "instance_id": instance_id,
        "allowlist_jids": allowlist_jids,
        "remote_jid": remote_jid,
        "allow_non_allowlist": allow_non_allowlist,
        "db_user": db_user,
        "client_slug": client_slug,
        "client_meta": client_meta,
        "learning_env": learning_env,
        "qdrant_env": qdrant_env,
        "container_name": container_name,
        "outbox_wait_seconds": outbox_wait_seconds,
        "fail_fast_after": fail_fast_after,
    }
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0
    fail_fast_after = context.get("fail_fast_after")
    sleep_min = max(min_wait, outbox_wait_seconds)
    sleep_max = max(max_wait, outbox_wait_seconds)

    if args.suite in {
        "ca01-core",
        "ca02-policy",
        "ca03-info",
        "ca04-service",
        "ca05-booking",
        "ca05-booking-commit",
        "ca06-consult",
        "ca07-ood",
        "ca08-state",
        "ca09-manager",
        "ca10-outbox",
    }:
        _ensure_bot_active_before_suite(args, context)

    reset_summary = None
    if args.reset_before_suite and args.suite not in {"ca06-consult", "ca07-ood"}:
        reset_summary = _run_livecheck_ca06_reset(
            args, context, suite_label=f"PRE-{args.suite.upper()}"
        )
    elif args.suite == "ca06-consult":
        reset_summary = _run_livecheck_ca06_reset(args, context, suite_label="CA06")
    elif args.suite == "ca07-ood":
        reset_summary = _run_livecheck_ca06_reset(args, context, suite_label="CA07")
    if reset_summary and not args.dry_run and outbox_wait_seconds > 0:
        time.sleep(outbox_wait_seconds)

    if args.suite == "ca08-state":
        summary = _run_livecheck_ca08_state(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        return
    if args.suite == "ca05-booking":
        summary = _run_livecheck_ca05_booking(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        return
    if args.suite == "ca05-booking-commit":
        summary = _run_livecheck_ca05_booking_commit(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        return
    if args.suite == "ca09-manager":
        summary = _run_livecheck_ca09_manager(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        if not args.dry_run and summary.get("qdrant_found") is not True:
            error_note = summary.get("qdrant_error") or "qdrant evidence missing"
            raise SystemExit(f"livecheck-auto: CA09 {error_note}")
        return
    if args.suite == "ca10-outbox":
        summary = _run_livecheck_ca10_outbox(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        return

    results = []

    for idx, case in enumerate(selected_cases, start=1):
        if args.suite == "ca07-ood" and case.get("reset_before_case"):
            _run_livecheck_ca06_reset(args, context, suite_label="CA07")
            if not args.dry_run and outbox_wait_seconds > 0:
                time.sleep(outbox_wait_seconds)
        text, marker, message = _build_livecheck_message(
            rng, case, f"LC:AUTO:{args.suite}", timestamp, idx, args.noise
        )
        message_id = f"LC-AUTO-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()
        if args.jid_mode == "unique":
            remote_jid = _logic_jid_for_index(idx)
        if remote_jid not in allowlist_jids and not allow_non_allowlist:
            raise SystemExit(
                f"livecheck-auto: remote-jid {remote_jid} not in allowlist; refusing to send"
            )
        metadata = {
            "sender": "LivecheckAuto",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {
            "body": {
                "messageType": "text",
                "message": message,
                "metadata": metadata,
            }
        }
        status = "dry_run"
        response_status = None
        response_body = None
        response_error = None
        if not args.dry_run:
            response_status, response_body, response_error = _send_webhook_payload(
                webhook_url, payload, webhook_secret, args.timeout
            )
            status = "sent" if response_status and 200 <= response_status < 300 else "error"
        log = {
            "case_id": case["case_id"],
            "marker": marker,
            "message_id": message_id,
            "remote_jid": remote_jid,
            "text": message,
            "sent_at": sent_at,
            "expected_policy_section": case.get("expected_policy_section"),
            "status": status,
            "http_status": response_status,
        }
        if case.get("expected_info_sections"):
            log["expected_info_sections"] = case.get("expected_info_sections")
        if case.get("expected_fact_intents"):
            log["expected_fact_intents"] = case.get("expected_fact_intents")
        if case.get("expected_info_combined") is not None:
            log["expected_info_combined"] = case.get("expected_info_combined")
        if case.get("expected_action"):
            log["expected_action"] = case.get("expected_action")
        if case.get("expected_intent"):
            log["expected_intent"] = case.get("expected_intent")
        if case.get("expected_source_any"):
            log["expected_source_any"] = case.get("expected_source_any")
        if case.get("expected_trace_stage_any"):
            log["expected_trace_stage_any"] = case.get("expected_trace_stage_any")
        if case.get("expected_trace_decision_any"):
            log["expected_trace_decision_any"] = case.get("expected_trace_decision_any")
        if case.get("expected_llm_used") is not None:
            log["expected_llm_used"] = case.get("expected_llm_used")
        if response_error:
            log["error"] = response_error
        if response_body:
            log["response"] = response_body[:200]
        print(json.dumps(log, ensure_ascii=False))

        if not args.dry_run:
            outbox_url = f"{base_url}/admin/outbox/process"
            _post_admin_outbox_with_wait(
                outbox_url,
                admin_token,
                args.timeout,
                outbox_wait_seconds,
            )
            conv_id, meta, error = _poll_decision_meta(
                db_user,
                message_id,
                args.poll_timeout,
                args.poll_interval,
                fail_fast_after=fail_fast_after,
            )
            if error:
                raise SystemExit(f"livecheck-auto: decision_meta poll failed ({error})")

            ack_marker = None
            ack_message_id = None
            ack_text = None
            ack_status = None
            # Skip ACK for CA07 to avoid overwriting the OOD trace with fast_intent.
            if args.suite != "ca07-ood":
                ack_marker = f"LC:ACK:{case['case_id']}:{timestamp}:{idx:02d}"
                ack_message_id = f"LC-ACK-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
                ack_text = args.ack_text or "ок"
                ack_payload = {
                    "body": {
                        "messageType": "text",
                        "message": ack_text,
                        "metadata": {
                            "sender": "LivecheckAuto",
                            "timestamp": int(time.time()),
                            "messageId": ack_message_id,
                            "remoteJid": remote_jid,
                        },
                    }
                }
                if instance_id:
                    ack_payload["body"]["metadata"]["instanceId"] = instance_id
                ack_status, _, ack_error = _send_webhook_payload(
                    webhook_url, ack_payload, webhook_secret, args.timeout
                )
                if ack_error:
                    raise SystemExit(f"livecheck-auto: ACK failed ({ack_error})")
                _post_admin_outbox_with_wait(
                    outbox_url,
                    admin_token,
                    args.timeout,
                    outbox_wait_seconds,
                )

            policy_pack_missing = (meta or {}).get("policy_pack_missing")
            if policy_pack_missing:
                raise SystemExit("livecheck-auto: policy_pack_missing=true")

            expected_sections = case.get("expected_info_sections") or []
            expected_fact_intents = case.get("expected_fact_intents") or []
            expected_info_combined = case.get("expected_info_combined")
            if args.suite == "ca03-info":
                fact_source = (meta or {}).get("fact_source")
                if fact_source != "truth":
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} fact_source mismatch ({fact_source})"
                    )
                if (meta or {}).get("llm_used") is not False:
                    raise SystemExit(f"livecheck-auto: CA03 {case['case_id']} llm_used not false")
                if (meta or {}).get("source") not in {"truth_gate", "class_router"}:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} source mismatch"
                    )
                info_sections = (meta or {}).get("info_sections")
                if expected_sections:
                    if not isinstance(info_sections, list) or any(
                        item not in info_sections for item in expected_sections
                    ):
                        raise SystemExit(
                            f"livecheck-auto: CA03 {case['case_id']} info_sections mismatch"
                        )
                fact_intents = (meta or {}).get("fact_intents")
                if expected_fact_intents:
                    if not isinstance(fact_intents, list) or any(
                        item not in fact_intents for item in expected_fact_intents
                    ):
                        raise SystemExit(
                            f"livecheck-auto: CA03 {case['case_id']} fact_intents mismatch"
                        )
                if expected_info_combined is True and (meta or {}).get("info_combined") is not True:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} info_combined mismatch"
                    )

            if args.suite == "ca04-service":
                expected_intent = case.get("expected_intent")
                if (meta or {}).get("action") != "reply":
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} action mismatch")
                if (meta or {}).get("intent") != expected_intent:
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} intent mismatch")
                if (meta or {}).get("fact_source") != "service_matcher":
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} fact_source mismatch")
                if (meta or {}).get("source") != "service_matcher":
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} source mismatch")
                if (meta or {}).get("llm_used") is not False:
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} llm_used not false")
                fact_intents = (meta or {}).get("fact_intents")
                if expected_fact_intents:
                    if not isinstance(fact_intents, list) or any(
                        item not in fact_intents for item in expected_fact_intents
                    ):
                        raise SystemExit(
                            f"livecheck-auto: CA04 {case['case_id']} fact_intents mismatch"
                        )

            if args.suite == "ca06-consult":
                expected_source = case.get("expected_source")
                if expected_source and (meta or {}).get("source") != expected_source:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} source mismatch"
                    )
                expected_meta_playbook = case.get("expected_meta_consult_playbook_id")
                if expected_meta_playbook and (
                    (meta or {}).get("consult_playbook_id") != expected_meta_playbook
                ):
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} consult_playbook_id mismatch"
                    )
                expected_fact_sources = case.get("expected_fact_source_any") or []
                if expected_fact_sources:
                    fact_source = (meta or {}).get("fact_source")
                    if fact_source not in expected_fact_sources:
                        raise SystemExit(
                            f"livecheck-auto: CA06 {case['case_id']} fact_source mismatch"
                        )
                expected_llm = case.get("expected_llm_used")
                if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} llm_used mismatch"
                    )

            if args.suite == "ca07-ood":
                expected_action = case.get("expected_action")
                actual_action = (meta or {}).get("action")
                if expected_action and actual_action != expected_action:
                    raise SystemExit(
                        "livecheck-auto: CA07 "
                        f"{case['case_id']} action mismatch "
                        f"(expected {expected_action}, got {actual_action})"
                    )
                expected_intent = case.get("expected_intent")
                actual_intent = (meta or {}).get("intent")
                if expected_intent and actual_intent != expected_intent:
                    raise SystemExit(
                        "livecheck-auto: CA07 "
                        f"{case['case_id']} intent mismatch "
                        f"(expected {expected_intent}, got {actual_intent})"
                    )
                expected_sources = case.get("expected_source_any") or []
                actual_source = (meta or {}).get("source")
                if expected_sources and actual_source not in expected_sources:
                    raise SystemExit(
                        "livecheck-auto: CA07 "
                        f"{case['case_id']} source mismatch "
                        f"(expected one of {expected_sources}, got {actual_source})"
                    )
                expected_llm = case.get("expected_llm_used")
                if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} llm_used mismatch"
                    )

            conv_meta = None
            conv_error = None
            trace_entry = None
            info_trace = None
            consult_trace = None
            trace_source = None
            if conv_id:
                conv_meta, conv_error = _fetch_conversation_meta(db_user, conv_id)
                trace_list = None
                if conv_meta and isinstance(conv_meta.get("context"), dict):
                    trace_list = conv_meta.get("context", {}).get("decision_trace")
                if (meta or {}).get("policy_gate") or case.get("expected_policy_section"):
                    trace_entry = _find_trace_entry(
                        trace_list,
                        stage="policy_gate",
                        policy_gate=(meta or {}).get("policy_gate"),
                        policy_section=(meta or {}).get("policy_section")
                        or case.get("expected_policy_section"),
                    )
                if args.suite == "ca03-info":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") in {"truth_gate", "info_class"}:
                            info_trace = entry
                            break
                if args.suite == "ca04-service":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") == "service_matcher":
                            info_trace = entry
                            break
                if args.suite == "ca06-consult":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") == "consult_flow":
                            consult_trace = entry
                            break
                if args.suite == "ca07-ood":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") in {"out_of_domain", "fast_intent", "smalltalk"}:
                            info_trace = entry
                            break

            if args.suite == "ca03-info":
                if not info_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} missing truth_gate/info_class trace"
                    )
                if info_trace.get("stage") == "truth_gate":
                    trace_source = "truth_gate"
                else:
                    trace_source = "class_router"
                if trace_source not in {"truth_gate", "class_router"}:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} trace_source mismatch"
                    )
                if info_trace.get("fact_source") != "truth":
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} trace fact_source mismatch"
                    )

            if args.suite == "ca04-service":
                if not info_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA04 {case['case_id']} missing service_matcher trace"
                    )
                if info_trace.get("decision") != case.get("expected_intent"):
                    raise SystemExit(
                        f"livecheck-auto: CA04 {case['case_id']} trace decision mismatch"
                    )
                if info_trace.get("fact_source") != "service_matcher":
                    raise SystemExit(
                        f"livecheck-auto: CA04 {case['case_id']} trace fact_source mismatch"
                    )

            if args.suite == "ca06-consult":
                if not consult_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} missing consult_flow trace"
                    )
                expected_decision = case.get("expected_consult_decision")
                if expected_decision and consult_trace.get("decision") != expected_decision:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} consult_flow decision mismatch"
                    )
                expected_trace_playbook = case.get("expected_consult_playbook_id")
                if expected_trace_playbook and (
                    consult_trace.get("consult_playbook_id") != expected_trace_playbook
                ):
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} consult_flow playbook mismatch"
                    )

            if args.suite == "ca07-ood":
                if not info_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} missing guard trace"
                    )
                expected_stages = case.get("expected_trace_stage_any") or []
                if expected_stages and info_trace.get("stage") not in expected_stages:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} trace stage mismatch"
                    )
                expected_decisions = case.get("expected_trace_decision_any") or []
                if expected_decisions and info_trace.get("decision") not in expected_decisions:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} trace decision mismatch"
                    )

            results.append(
                {
                    "case_id": case["case_id"],
                    "message_id": message_id,
                    "conversation_id": conv_id,
                    "remote_jid": remote_jid,
                    "action": (meta or {}).get("action"),
                    "intent": (meta or {}).get("intent"),
                    "policy_gate": (meta or {}).get("policy_gate"),
                    "policy_section": (meta or {}).get("policy_section"),
                    "policy_source": (meta or {}).get("source"),
                    "risk_level": (meta or {}).get("risk_level"),
                    "policy_pack_missing": policy_pack_missing,
                    "llm_used": (meta or {}).get("llm_used"),
                    "fact_source": (meta or {}).get("fact_source"),
                    "info_sections": (meta or {}).get("info_sections"),
                    "info_combined": (meta or {}).get("info_combined"),
                    "fact_intents": (meta or {}).get("fact_intents"),
                    "service_query": (meta or {}).get("service_query"),
                    "consult_playbook_id": (meta or {}).get("consult_playbook_id"),
                    "consult_topic": (meta or {}).get("consult_topic"),
                    "consult_variant_id": (meta or {}).get("consult_variant_id"),
                    "source": (meta or {}).get("source"),
                    "ack_message_id": ack_message_id,
                    "ack_marker": ack_marker,
                    "ack_text": ack_text,
                    "ack_status": ack_status,
                    "trace_policy_type": (trace_entry or {}).get("policy_type") if trace_entry else None,
                    "trace_source": (trace_entry or {}).get("source") if trace_entry else None,
                    "trace_policy_gate": (trace_entry or {}).get("policy_gate") if trace_entry else None,
                    "trace_policy_section": (trace_entry or {}).get("policy_section") if trace_entry else None,
                    "trace_risk_level": (trace_entry or {}).get("risk_level") if trace_entry else None,
                    "trace_stage": (info_trace or {}).get("stage") if info_trace else None,
                    "trace_decision": (info_trace or {}).get("decision") if info_trace else None,
                    "trace_source": trace_source,
                    "trace_fact_source": (info_trace or {}).get("fact_source") if info_trace else None,
                    "trace_info_sections": (info_trace or {}).get("info_sections") if info_trace else None,
                    "trace_intents": (info_trace or {}).get("intents") if info_trace else None,
                    "trace_consult_decision": (consult_trace or {}).get("decision") if consult_trace else None,
                    "trace_consult_playbook_id": (consult_trace or {}).get("consult_playbook_id")
                    if consult_trace
                    else None,
                    "trace_error": conv_error,
                }
            )

        if idx < len(selected_cases):
            time.sleep(rng.uniform(sleep_min, sleep_max))

    summary = dict(common)
    summary["results"] = results
    if reset_summary:
        summary["reset"] = reset_summary
    print(json.dumps({"summary": summary}, ensure_ascii=False))

def _run_livecheck(args):
    suite = LIVECHECK_SUITES.get(args.suite)
    if not suite:
        raise SystemExit(f"Unknown suite: {args.suite}")
    token = os.environ.get("CHATFLOW_TOKEN")
    instance_id = os.environ.get("CHATFLOW_INSTANCE_ID")
    jid = os.environ.get("CHATFLOW_JID")
    api_url = os.environ.get("CHATFLOW_API_URL", "https://app.chatflow.kz/api/v1/send-text")
    timeout = float(os.environ.get("CHATFLOW_TIMEOUT_SECONDS", "30"))
    if not token or not instance_id or not jid:
        raise SystemExit("Missing CHATFLOW_TOKEN/CHATFLOW_INSTANCE_ID/CHATFLOW_JID in env.")

    rng = random.Random(args.seed or int(time.time()))
    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    for idx, case in enumerate(suite, start=1):
        base_text = rng.choice(case["messages"])
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"LC:{args.suite}:{case['case_id']}:{timestamp}:{idx:02d}"
        message = f"{text} [{marker}]"
        sent_at = datetime.now(timezone.utc).isoformat()
        status = "dry_run"
        response_body = None
        response_status = None
        if not args.dry_run:
            response_status, response_body = _send_chatflow_message(
                api_url, token, instance_id, jid, message, timeout
            )
            status = "sent" if response_status == 200 else "error"
        log = {
            "case_id": case["case_id"],
            "marker": marker,
            "text": message,
            "sent_at": sent_at,
            "expected_policy_section": case["expected_policy_section"],
            "status": status,
            "http_status": response_status,
        }
        if response_body:
            log["response"] = response_body[:200]
        print(json.dumps(log, ensure_ascii=False))
        if idx < len(suite):
            time.sleep(rng.uniform(min_wait, max_wait))


def _parse_deploy_verify_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py deploy-verify",
        description="Verify deployed build via /admin/version.",
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--expected-commit", default=None)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=1.0)
    return parser.parse_args(argv)


def _fetch_json(url, timeout):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)


def _run_deploy_verify(args):
    url = args.base_url.rstrip("/") + "/admin/version"
    last_error = None
    payload = None
    for _ in range(max(args.retries, 1)):
        try:
            payload = _fetch_json(url, args.timeout)
            break
        except Exception as exc:
            last_error = str(exc)
            time.sleep(max(args.sleep, 0))

    if not isinstance(payload, dict):
        raise SystemExit(f"deploy-verify failed: no response from {url}. last_error={last_error}")

    version = payload.get("version") or ""
    git_commit = payload.get("git_commit") or ""

    if not version or version == "unknown":
        raise SystemExit("deploy-verify failed: version unknown")
    if args.expected_commit and git_commit != args.expected_commit:
        raise SystemExit(
            f"deploy-verify failed: git_commit mismatch (expected {args.expected_commit}, got {git_commit})"
        )
    if args.expected_version and version != args.expected_version:
        raise SystemExit(
            f"deploy-verify failed: version mismatch (expected {args.expected_version}, got {version})"
        )

    print(
        json.dumps(
            {"ok": True, "version": version, "git_commit": git_commit, "url": url},
            ensure_ascii=False,
        )
    )

def _parse_emit_evidence_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py emit-evidence",
        description="Generate markdown evidence from livecheck jsonl artifacts.",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Path/glob to livecheck jsonl file (repeatable).",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing livecheck-*.jsonl artifacts.",
    )
    parser.add_argument("--gate", default=None, help="Path to livecheck-gate.txt.")
    parser.add_argument(
        "--output",
        default="livecheck-evidence.md",
        help="Markdown output path (use '-' for stdout).",
    )
    parser.add_argument("--title", default="Livecheck Evidence")
    parser.add_argument(
        "--suite-order",
        default=None,
        help="Comma-separated suite order (default: alphabetical).",
    )
    return parser.parse_args(argv)

def _resolve_emit_inputs(inputs, input_dir):
    paths = []
    if input_dir:
        paths.extend(sorted(glob.glob(os.path.join(input_dir, "livecheck-*.jsonl"))))
    for raw in inputs or []:
        if not raw:
            continue
        if os.path.isdir(raw):
            paths.extend(sorted(glob.glob(os.path.join(raw, "livecheck-*.jsonl"))))
            continue
        expanded = glob.glob(raw)
        if expanded:
            paths.extend(sorted(expanded))
        else:
            paths.append(raw)
    seen = set()
    resolved = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        resolved.append(path)
    if not resolved:
        raise SystemExit("emit-evidence: no jsonl inputs found")
    return resolved

def _resolve_gate_path(gate_path, input_dir):
    if gate_path:
        return gate_path
    if input_dir:
        direct = os.path.join(input_dir, "livecheck-gate.txt")
        if os.path.isfile(direct):
            return direct
        matches = sorted(glob.glob(os.path.join(input_dir, "livecheck-gate-*.txt")))
        if matches:
            return matches[0]
    return None

def _read_gate_file(path):
    if not path or not os.path.isfile(path):
        return None
    values = {}
    flags = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value
            else:
                flags.append(line)
    return {"path": path, "values": values, "flags": flags}

def _load_jsonl_entries(path):
    entries = []
    errors = []
    with open(path, "r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except Exception as exc:
                errors.append({"line": idx, "error": str(exc), "raw": raw[:200]})
    return entries, errors

def _extract_summary(entries):
    summary = None
    for entry in entries:
        if isinstance(entry, dict) and "summary" in entry:
            summary = entry.get("summary")
    return summary

def _extract_case_logs(entries):
    logs = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if "summary" in entry:
            continue
        if entry.get("case_id"):
            logs.append(entry)
    return logs

def _suite_name_from_path(path, summary):
    if isinstance(summary, dict):
        suite = summary.get("suite")
        if suite:
            return suite
    base = os.path.basename(path)
    if base.startswith("livecheck-") and base.endswith(".jsonl"):
        return base[len("livecheck-") : -len(".jsonl")]
    return os.path.splitext(base)[0]

def _format_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

def _escape_table(value):
    return _format_cell(value).replace("|", "\\|").replace("\n", " ").strip()

def _render_table(columns, rows):
    lines = []
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines.append(header)
    lines.append(sep)
    for row in rows:
        values = []
        for _, key in columns:
            values.append(_escape_table(row.get(key)))
        lines.append("| " + " | ".join(values) + " |")
    return lines

def _compact_errors(errors):
    if not isinstance(errors, dict):
        return None
    present = {key: value for key, value in errors.items() if value}
    if not present:
        return None
    return json.dumps(present, ensure_ascii=False)

def _render_suite_summary(lines, summary):
    if not isinstance(summary, dict):
        lines.append("- summary: missing")
        return
    case_ids = summary.get("case_ids")
    if case_ids:
        lines.append(f"- case_ids: {', '.join(case_ids)}")
    for key in (
        "client_slug",
        "instance_id",
        "branch_instance_id",
        "client_instance_id",
        "instance_drift",
        "jid_mode",
        "remote_jid",
        "test_mode",
        "learning_mode",
        "qdrant_collection",
    ):
        value = summary.get(key)
        if value is None or value == "":
            continue
        lines.append(f"- {key}: `{_format_cell(value)}`")
    error_note = _compact_errors(summary.get("errors"))
    if error_note:
        lines.append(f"- errors: `{error_note}`")

def _render_suite_lines(suite):
    lines = [f"## Suite {suite['name']}", f"- input: `{suite['input']}`"]
    summary = suite.get("summary")
    _render_suite_summary(lines, summary)
    if not isinstance(summary, dict):
        if suite.get("case_logs"):
            lines.append("")
            columns = [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("marker", "marker"),
                ("status", "status"),
                ("http_status", "http_status"),
            ]
            lines.extend(_render_table(columns, suite["case_logs"]))
        return lines

    suite_name = suite["name"]
    results = summary.get("results")
    if suite_name == "ca05-booking" and isinstance(results, list):
        reset = summary.get("reset") or {}
        if reset:
            reset_parts = []
            for key in (
                "reset_message_id",
                "reset_action",
                "reset_intent",
                "reset_expected_reply_type",
                "reset_booking_active",
                "reset_booking_service",
            ):
                if key in reset and reset.get(key) is not None:
                    reset_parts.append(f"{key}={_format_cell(reset.get(key))}")
            if reset_parts:
                lines.append(f"- reset: {'; '.join(reset_parts)}")
        lines.append("")
        columns = [
            ("step", "step"),
            ("message_id", "message_id"),
            ("conversation_id", "conversation_id"),
            ("expected_reply_type", "expected_reply_type"),
            ("booking_service", "booking_service"),
            ("booking_info_interrupt", "booking_info_interrupt"),
            ("booking_info_intents", "booking_info_intents"),
            ("trace_booking_interrupt", "trace_booking_interrupt"),
            ("llm_used", "llm_used"),
        ]
        lines.extend(_render_table(columns, results))
        return lines

    if suite_name == "ca05-booking-commit" and isinstance(results, list):
        booking_time = summary.get("booking_time")
        booking_name = summary.get("booking_name")
        if booking_time:
            lines.append(f"- booking_time: `{_format_cell(booking_time)}`")
        if booking_name:
            lines.append(f"- booking_name: `{_format_cell(booking_name)}`")
        lines.append("")
        columns = [
            ("step", "step"),
            ("message_id", "message_id"),
            ("conversation_id", "conversation_id"),
            ("expected_reply_type", "expected_reply_type"),
            ("booking_service", "booking_service"),
            ("appointment_id", "appointment_id"),
            ("appointment_status", "appointment_status"),
            ("appointment_audit_action", "appointment_audit_action"),
            ("trace_booking_commit", "trace_booking_commit"),
            ("outbox_status", "outbox_status"),
            ("llm_used", "llm_used"),
        ]
        lines.extend(_render_table(columns, results))
        return lines

    if suite_name == "ca08-state":
        for key in ("message_id", "ack_message_id", "conversation_id"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(
            f"- conversation_state: `{summary.get('conversation_state_before')}` → `{summary.get('conversation_state_after')}`"
        )
        lines.append(
            f"- handover_status: `{summary.get('handover_status_before')}` → `{summary.get('handover_status_after')}`"
        )
        for key in ("policy_gate", "action", "pending_action"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(f"- pending_sla_trace: `{_format_cell(summary.get('pending_sla_trace'))}`")
        lines.append(f"- pending_resume_trace: `{_format_cell(summary.get('pending_resume_trace'))}`")
        return lines

    if suite_name == "ca09-manager":
        for key in ("message_id", "conversation_id"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(
            f"- conversation_state: `{summary.get('conversation_state_before')}` → `{summary.get('conversation_state_after')}`"
        )
        lines.append(
            f"- handover_status: `{summary.get('handover_status_before')}` → `{summary.get('handover_status_after')}`"
        )
        for key in ("assigned_to", "first_response_at"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(f"- qdrant_found: `{_format_cell(summary.get('qdrant_found'))}`")
        for key in ("outbox_status", "telegram_status"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        return lines

    if suite_name == "ca10-outbox":
        for key in (
            "message_id",
            "message_count",
            "message_dedup_count",
            "outbox_count",
            "outbox_status",
        ):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        return lines

    if isinstance(results, list):
        suite_columns = {
            "ca01-core": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("policy_gate", "policy_gate"),
                ("policy_section", "policy_section"),
                ("risk_level", "risk_level"),
                ("llm_used", "llm_used"),
                ("trace_policy_gate", "trace_policy_gate"),
                ("trace_policy_section", "trace_policy_section"),
            ],
            "ca02-policy": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("policy_gate", "policy_gate"),
                ("policy_section", "policy_section"),
                ("risk_level", "risk_level"),
                ("llm_used", "llm_used"),
                ("trace_policy_type", "trace_policy_type"),
                ("trace_policy_gate", "trace_policy_gate"),
                ("trace_policy_section", "trace_policy_section"),
            ],
            "ca03-info": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("fact_source", "fact_source"),
                ("info_sections", "info_sections"),
                ("fact_intents", "fact_intents"),
                ("info_combined", "info_combined"),
                ("llm_used", "llm_used"),
                ("source", "source"),
                ("trace_stage", "trace_stage"),
                ("trace_fact_source", "trace_fact_source"),
                ("trace_info_sections", "trace_info_sections"),
            ],
            "ca04-service": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("fact_source", "fact_source"),
                ("fact_intents", "fact_intents"),
                ("service_query", "service_query"),
                ("llm_used", "llm_used"),
                ("trace_stage", "trace_stage"),
                ("trace_decision", "trace_decision"),
                ("trace_fact_source", "trace_fact_source"),
            ],
            "ca06-consult": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("consult_playbook_id", "consult_playbook_id"),
                ("source", "source"),
                ("fact_source", "fact_source"),
                ("llm_used", "llm_used"),
                ("trace_consult_decision", "trace_consult_decision"),
                ("trace_consult_playbook_id", "trace_consult_playbook_id"),
            ],
            "ca07-ood": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("source", "source"),
                ("llm_used", "llm_used"),
                ("trace_stage", "trace_stage"),
                ("trace_decision", "trace_decision"),
            ],
        }
        columns = suite_columns.get(
            suite_name,
            [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
            ],
        )
        lines.append("")
        lines.extend(_render_table(columns, results))
    return lines

def _run_emit_evidence(args):
    inputs = _resolve_emit_inputs(args.input, args.input_dir)
    gate_path = _resolve_gate_path(args.gate, args.input_dir)
    gate = _read_gate_file(gate_path)

    suites = []
    for path in inputs:
        entries, parse_errors = _load_jsonl_entries(path)
        summary = _extract_summary(entries)
        suite_name = _suite_name_from_path(path, summary)
        suites.append(
            {
                "name": suite_name,
                "input": os.path.basename(path),
                "summary": summary,
                "case_logs": _extract_case_logs(entries),
                "parse_errors": parse_errors,
            }
        )

    if args.suite_order:
        ordered = []
        suite_map = {suite["name"]: suite for suite in suites}
        for name in _parse_csv_values(args.suite_order):
            suite = suite_map.pop(name, None)
            if suite:
                ordered.append(suite)
        for name in sorted(suite_map.keys()):
            ordered.append(suite_map[name])
        suites = ordered
    else:
        suites = sorted(suites, key=lambda item: item["name"])

    lines = [f"# {args.title}"]
    generated_at = datetime.now(timezone.utc).isoformat()
    lines.append(f"- generated_at: `{generated_at}`")
    lines.append(
        "- inputs: " + ", ".join(f"`{os.path.basename(path)}`" for path in inputs)
    )
    if gate:
        lines.append("")
        lines.append("## Gate")
        for key in sorted(gate.get("values", {}).keys()):
            value = gate["values"].get(key, "")
            lines.append(f"- {key}={value}")
        if gate.get("flags"):
            lines.append(f"- flags: {', '.join(gate['flags'])}")
        lines.append(f"- gate_file: `{os.path.basename(gate['path'])}`")
    else:
        lines.append("")
        lines.append("## Gate")
        lines.append("- gate_file: missing")

    for suite in suites:
        lines.append("")
        lines.extend(_render_suite_lines(suite))
        if suite.get("parse_errors"):
            lines.append(f"- parse_errors: `{json.dumps(suite['parse_errors'], ensure_ascii=False)}`")

    output = "\n".join(lines).rstrip() + "\n"
    if args.output == "-":
        print(output)
        return
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(output)
    print(json.dumps({"output": args.output, "suites": [s['name'] for s in suites]}, ensure_ascii=False))

def run_command(command):
    return subprocess.run(command, capture_output=True, text=True)

API_CONTAINER_HINT = "truffles-api"

def resolve_container_name():
    result = run_command(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name={API_CONTAINER_HINT}",
            "--format",
            "{{.Names}}",
        ]
    )
    if result.returncode != 0:
        return None, result.stderr.strip()
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not names:
        return None, ""
    if API_CONTAINER_HINT in names:
        return API_CONTAINER_HINT, ""
    return names[0], ""

def run_docker_exec(container_name, command):
    return run_command(["docker", "exec", "-i", container_name, "/bin/sh", "-lc", command])

def run_curl(url, headers=None):
    cmd = ["curl", "-s"]
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    cmd.append(url)
    return run_command(cmd)

if len(sys.argv) > 1 and sys.argv[1] == "webhook-fuzz":
    _run_webhook_fuzz(_parse_webhook_fuzz_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "chaos-sim":
    _run_chaos_sim(_parse_chaos_sim_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "send-text":
    _run_send_text(_parse_send_text_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "send-and-explain":
    _run_send_and_explain(_parse_send_and_explain_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "explain":
    _run_explain(_parse_explain_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "trace-bundle":
    _run_trace_bundle(_parse_trace_bundle_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "emit-evidence":
    _run_emit_evidence(_parse_emit_evidence_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "livecheck-auto":
    _run_livecheck_auto(_parse_livecheck_auto_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "livecheck":
    _run_livecheck(_parse_livecheck_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "deploy-verify":
    _run_deploy_verify(_parse_deploy_verify_args(sys.argv[2:]))
    raise SystemExit(0)

print("=" * 60)
print("ДИАГНОСТИКА TRUFFLES")
print("=" * 60)

print("\n🔎 PRE-FLIGHT:")
print("-" * 40)
container_name, docker_error = resolve_container_name()
status = ""
if docker_error:
    print(f"docker error: {docker_error}")
    print("Skipping docker checks (no access).")
else:
    if container_name:
        print(f"truffles-api container: {container_name}")
        status_result = run_command(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name]
        )
        status = status_result.stdout.strip() if status_result.returncode == 0 else ""
        if status:
            print(f"truffles-api status: {status}")
        else:
            print("truffles-api status: UNKNOWN")
    else:
        print("truffles-api container: NOT FOUND (container missing?)")

if container_name:
    image_result = run_command(
        ["docker", "inspect", "--format", "{{.Config.Image}}", container_name]
    )
    if image_result.returncode == 0 and image_result.stdout.strip():
        print(f"truffles-api image: {image_result.stdout.strip()}")
    else:
        print("truffles-api image: UNKNOWN")
else:
    print("truffles-api image: UNKNOWN")

if status == "running":
    env_checks = [
        ("TEST_MODE", True),
        ("OUTBOUND_ALLOWLIST_JIDS", True),
        ("OUTBOX_WORKER_ENABLED", True),
        ("PUBLIC_BASE_URL", True),
        ("MEDIA_SIGNING_SECRET", False),
        ("MEDIA_URL_TTL_SECONDS", True),
        ("MEDIA_CLEANUP_TTL_DAYS", True),
        ("CHATFLOW_MEDIA_TIMEOUT_SECONDS", True),
        ("ALERTS_ADMIN_TOKEN", False),
    ]
    for name, show_value in env_checks:
        if show_value:
            cmd = (
                f'if [ -n "${name}" ]; then echo "{name}=${{{name}}}"; '
                f'else echo "{name}=MISSING"; fi'
            )
        else:
            cmd = (
                f'if [ -n "${name}" ]; then echo "{name}=SET"; '
                f'else echo "{name}=MISSING"; fi'
            )
        result = run_docker_exec(container_name, cmd)
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(f"{name}=UNKNOWN (env check failed)")
else:
    print("Skipping env checks (truffles-api not running).")

# 1. Database state
print("\n📁 БАЗА ДАННЫХ:")
print("-" * 40)

# Conversations
def resolve_db_user():
    env_user = os.environ.get("DB_USER")
    if env_user:
        return env_user
    result = run_command(
        ["docker", "exec", "-i", "truffles_postgres_1", "/bin/sh", "-lc", "printf '%s' \"${POSTGRES_USER:-}\""]
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "postgres"

db_user = resolve_db_user()
print(f"DB_USER={db_user}")

result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', db_user, '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN bot_status='muted' THEN 1 END) as muted, COUNT(telegram_topic_id) as with_topic FROM conversations;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Conversations: {parts[0].strip()} total, {parts[1].strip()} muted, {parts[2].strip()} with topic")

# Handovers
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', db_user, '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN status='pending' THEN 1 END) as pending, COUNT(CASE WHEN status='active' THEN 1 END) as active FROM handovers;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Handovers: {parts[0].strip()} total, {parts[1].strip()} pending, {parts[2].strip()} active")

print("\n📮 OUTBOX STATUS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT status, COUNT(*) FROM outbox_messages GROUP BY status;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🧩 DECISION_META (last 3):")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT metadata->'decision_meta' FROM messages ORDER BY created_at DESC LIMIT 3;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🧾 ПОСЛЕДНИЕ HANDOVERS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT created_at, status, conversation_id, channel_ref, telegram_message_id "
        "FROM handovers ORDER BY created_at DESC LIMIT 10;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🟡 PENDING/MANAGER_ACTIVE CONVERSATIONS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT id, state, telegram_topic_id, last_message_at "
        "FROM conversations WHERE state IN ('pending','manager_active') "
        "ORDER BY last_message_at DESC LIMIT 10;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🌐 ADMIN ENDPOINTS:")
print("-" * 40)
version_result = run_curl("http://localhost:8000/admin/version")
if version_result.returncode == 0 and version_result.stdout.strip():
    print(f"/admin/version: {version_result.stdout.strip()}")
else:
    print("/admin/version: FAILED")

health_result = run_curl("http://localhost:8000/admin/health")
if health_result.returncode == 0 and health_result.stdout.strip():
    print(f"/admin/health: {health_result.stdout.strip()}")
else:
    print("/admin/health: FAILED")

admin_token = ""
if container_name:
    token_result = run_docker_exec(
        container_name, 'printf "%s" "${ALERTS_ADMIN_TOKEN:-}"'
    )
    if token_result.returncode == 0:
        admin_token = token_result.stdout.strip()

if admin_token:
    metric_date = datetime.now(timezone.utc).date().isoformat()
    metrics_result = run_curl(
        f"http://localhost:8000/admin/metrics?client_slug=demo_salon&metric_date={metric_date}",
        headers={"X-Admin-Token": admin_token},
    )
    if metrics_result.returncode == 0 and metrics_result.stdout.strip():
        print(f"/admin/metrics: {metrics_result.stdout.strip()}")
    else:
        print("/admin/metrics: FAILED")
else:
    print("/admin/metrics: SKIPPED (ALERTS_ADMIN_TOKEN missing)")

print("\n" + "=" * 60)
