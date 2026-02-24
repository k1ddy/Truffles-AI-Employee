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
import hashlib
import http.client
import json
import math
import os
import random
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

try:
    import yaml
except Exception:
    yaml = None

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
                "делаете массаж ног?",
                "делаете массаж стоп?",
                "массаж ног делаете?",
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
    "ca12-booking-full": [
        {
            "case_id": "CA12_BOOKING_FULL",
            "steps": [
                {
                    "message": "хочу записаться на маникюр",
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
            "handover_message": "хочу поговорить с менеджером",
            "confirm_message": "да",
            "manager_actions": ["take", "resolve"],
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
            "expected_fact_source_any": ["pack"],
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
CHAOS_BOOKING_REPLY_TYPES = {"service_choice", "time", "name"}
CHAOS_PENDING_ACTIONS = {
    "pending_status",
    "pending_wait",
    "pending_ack",
    "pending_close",
    "pending_pass",
    "pending_sla_ping",
    "pending_guard_reset",
}
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

LLM_QUALITY_INFO_TAGS = {
    "price",
    "location",
    "hours",
    "promo",
    "duration",
    "parking",
    "master",
}
LLM_QUALITY_INFO_SECTION_MAP = {
    "price": {"pricing", "price", "payment_info", "payment"},
    "location": {"address", "location"},
    "hours": {"hours", "working_hours", "schedule"},
    "promo": {"discounts", "discount", "promo", "promotion", "promotions"},
    "duration": {"duration", "service_duration"},
    "parking": {"parking"},
    "master": {"master", "specialist"},
}
LLM_QUALITY_SECTION_TAG_MAP = {}
for _tag, _sections in LLM_QUALITY_INFO_SECTION_MAP.items():
    for _section in _sections:
        LLM_QUALITY_SECTION_TAG_MAP.setdefault(_section, _tag)
LLM_QUALITY_INTENT_TAG_MAP = {
    "pricing": {"price"},
    "price": {"price"},
    "price_query": {"price"},
    "discount": {"promo"},
    "discount_haggle": {"promo"},
    "promo": {"promo"},
    "promotion": {"promo"},
    "promotions": {"promo"},
    "hours": {"hours"},
    "working_hours": {"hours"},
    "schedule": {"hours"},
    "address": {"location"},
    "location": {"location"},
    "parking": {"parking"},
    "service_duration": {"duration"},
    "duration": {"duration"},
    "master": {"master"},
    "specialist": {"master"},
}
LLM_QUALITY_POLICY_INTENTS = {
    "cancel_request",
    "cancel_policy",
    "reschedule",
    "refund",
    "complaint",
    "medical",
    "payment",
    "payment_info",
    "discount_haggle",
}
LLM_QUALITY_TAG_HINTS = {
    "price": [
        r"сколько\\s+стоит",
        r"\\bцена\\b",
        r"стоимост",
        r"ценник",
        r"по\\s+чем",
        r"бағасы",
        r"қанша",
    ],
    "location": [
        r"где\\s+вы",
        r"адрес",
        r"находит",
        r"как\\s+до\\s+вас",
        r"қайда",
        r"мекенжай",
    ],
    "hours": [
        r"работаете",
        r"во\\s+сколько",
        r"график",
        r"часы",
        r"қашан",
        r"жұмыс",
        r"ашық",
    ],
    "promo": [
        r"акци",
        r"скид",
        r"промо",
        r"спецпредлож",
        r"жеңілд",
    ],
    "duration": [
        r"сколько\\s+длит",
        r"сколько\\s+времени",
        r"сколько\\s+времени\\s+займ",
        r"займ[её]т",
        r"длительн",
        r"по\\s+времени",
        r"уақ",
    ],
    "parking": [
        r"парков",
        r"тұрақ",
    ],
    "master": [
        r"мастер",
        r"специалист",
        r"к\\s+мастер",
        r"у\\s+мастера",
        r"кто\\s+будет\\s+делать",
        r"кто\\s+делает",
        r"кто\\s+выполняет",
    ],
}
LLM_QUALITY_TAG_HINTS_RE = {
    tag: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for tag, patterns in LLM_QUALITY_TAG_HINTS.items()
}
LLM_QUALITY_LANG_KK_CHARS = set("ӘәҒғҚқҢңӨөҰұҮүІіҺһ")
LLM_QUALITY_NOISE_HINTS = [
    r"^\\s*(ок|ok|окей|okay|thanks|thx|спс|спасибо|\\?+|!+|\\.+|ээ+|мм+|угу|ага)\\s*$",
    r"^\\s*[👍🙏✅]+\\s*$",
]
LLM_QUALITY_NOISE_RE = re.compile("|".join(LLM_QUALITY_NOISE_HINTS), re.IGNORECASE)
LLM_QUALITY_BUNDLE_INTENTS = {"info_bundle", "multi_intent_info"}
LLM_QUALITY_KNOWN_STATES = {"bot_active", "pending", "manager_active"}
LLM_QUALITY_BOOKING_SLOTS = ("service", "datetime", "name", "phone")
LLM_QUALITY_PROGRESS_TAGS_BY_REPLY_TYPE = {
    "service_choice": {"service", "multi_service"},
    "time": {"time", "time_alt", "date"},
    "name": {"name"},
}
LLM_QUALITY_PROGRESS_SKIP_TAGS = {
    "interrupt",
    "noise",
    "media",
    "delay",
    "handoff",
    "hand_off",
    "human",
    "pending",
    "channel",
    "consult",
    "price",
    "promo",
    "location",
    "hours",
    "duration",
    "parking",
    "master",
    "cancel",
    "reschedule",
    "check_booking",
    "confirm",
    "tool",
}
LLM_QUALITY_FAILURE_LIMIT = 50
LLM_QUALITY_THRESHOLDS = {
    "reply_rate": 0.9,
    "strict_pass_rate": 0.9,
    "expected_reply_rate": 0.95,
    "info_answer_rate": 0.7,
    "hard_fail_rate": 0.0,
    "unknown_state_rate": 0.02,
    "degraded_fallback_rate": 0.2,
    "booking_slot_progress_rate": 0.25,
    "handoff_correct_rate": 0.9,
}
LLM_QUALITY_THRESHOLD_DIRECTIONS = {
    "hard_fail_rate": "max",
    "unknown_state_rate": "max",
    "degraded_fallback_rate": "max",
}
LLM_QUALITY_REGRESSION_KEYS = (
    "reply_rate",
    "strict_pass_rate",
    "expected_reply_rate",
    "info_answer_rate",
    "hard_fail_rate",
    "unknown_state_rate",
    "degraded_fallback_rate",
    "booking_slot_progress_rate",
    "handoff_correct_rate",
)
LLM_QUALITY_BLOCKING_REASONS = (
    "calendar_tool_contract_miss",
    "requested_date_time_like",
    "slot_date_resolution_miss",
    "slot_availability_contradiction",
    "fabricated_conflict_time",
    "booking_prompt_leak",
    "stale_prompt_date_mismatch",
    "mix_info_booking",
    "stale_booking_carryover",
    "timeout_degrade_booking_generic",
    "run_completion_gap",
    "trace_response_mismatch",
    "weak_oracle_turn",
    "incomplete_run_artifact",
    "expected_action_mismatch",
    "expected_reply_type_mismatch",
    "unobserved_turn",
    "tool_decision_mismatch",
    "judge_fail",
    "post_llm_semantic_rewrite_budget_exceeded",
    "keyword_override_budget_exceeded",
    "rewrite_reason_missing",
    "rewrite_reason_unknown",
    "lexicon_regex_delta_violation",
    "hardcode_core_violation",
)
LLM_QUALITY_HQ1_CLASSES = (
    "wrong_action",
    "handoff_miss",
    "non_actionable_reply",
    "hallucinated_fact",
    "booking_flow_break",
)
LLM_QUALITY_HQ1_RESCHEDULE_MARKERS = (
    "перенес",
    "изменить запись",
    "изменить время",
    "поменять время",
    "поменять запись",
    "отменить запись",
    "отмена записи",
    "менеджер",
    "оператор",
    "reschedule",
)
LLM_QUALITY_HQ1_MASTER_MARKERS = (
    "мастер",
    "специалист",
)
LLM_QUALITY_HQ1_SERVICE_OVERVIEW_MARKERS = (
    "ассортимент",
    "какие услуги",
    "какие есть услуги",
    "что вы предлагаете",
    "что у вас есть",
    "какие процедуры",
)
LLM_QUALITY_HQ1_HALLUCINATION_MARKERS = (
    "hallucinat",
    "fabricat",
    "invented",
    "made_up",
    "выдум",
    "придум",
    "недостовер",
    "ложн",
)
LLM_POLICY_OVERRIDE_REASON_WHITELIST = {
    "safety_policy_block",
    "contract_validation_failure",
    "required_slot_missing",
    "tool_unavailable",
    "timeout_degrade",
    "idempotency_replay_guard",
}
LLM_POLICY_OVERRIDE_KEYWORD_REASON_CODES = {
    "keyword_override",
    "lexicon_override",
    "regex_override",
}
LLM_QUALITY_MISSED_QUESTION_SUPPRESSION_REASON_CODES = {
    "required_slot_missing",
    "tool_unavailable",
    "timeout_degrade",
    "contract_validation_failure",
}
LLM_QUALITY_REGEX_LEXICON_TOKENS = ("lexicon", "regex", "system_lexicons")
LLM_QUALITY_REGEX_LEXICON_RESOLVER_PREFIXES = (
    "truffles-api/app/routers/webhook/",
    "truffles-api/app/services/",
)
LLM_QUALITY_REGEX_LEXICON_TEST_PREFIX = "truffles-api/tests/"
LLM_QUALITY_HARDCODE_CORE_PREFIXES = (
    "truffles-api/app/routers/webhook/decision.py",
    "truffles-api/app/routers/webhook/booking.py",
    "truffles-api/app/routers/webhook/info.py",
    "truffles-api/app/services/tool_registry_service.py",
)
LLM_QUALITY_HARDCODE_ALLOW_MARKER = "hardcode-gate: allow"
LLM_QUALITY_REASON_LABELS = {
    "decision_meta_missing": "decision_meta missing for inbound turn",
    "decision_trace_missing": "decision_trace missing for inbound turn",
    "unknown_state": "conversation.state missing or not in known states",
    "expected_state_mismatch": "conversation.state does not match scenario expectation",
    "expected_action_mismatch": "decision_meta.action does not match scenario expectation",
    "expected_reply_type_mismatch": "expected_reply_type does not match scenario expectation",
    "expected_reply_mismatch": "reply expectation does not match scenario expectation",
    "expected_info_section_miss": "expected info_sections missing in meta/trace",
    "missing_bot_reply": "expected response but no bot reply observed",
    "unobserved_turn": "expected response has no observed text under duplicate/unknown transport state",
    "outbox_delivery_failed": "expected response but outbox delivery is FAILED",
    "outbox_delivery_timeout": "expected response but outbox did not deliver within wait window",
    "unexpected_bot_reply_manager": "bot replied while manager_active",
    "handover_missing": "manager_active but handover missing",
    "info_section_miss": "info request not answered per meta/trace",
    "booking_slot_stall": "booking active without slot progress",
    "false_booking_confirmation": "booking confirmation text without appointment/calendar proof",
    "calendar_tool_contract_miss": "appointment path without successful calendar tool outcome",
    "requested_date_time_like": "requested_date contains time token instead of date",
    "slot_date_resolution_miss": "relative/explicit date signal did not resolve into calendar slot query",
    "slot_availability_contradiction": "slot availability claim contradicts provided slot list",
    "fabricated_conflict_time": "booking conflict mentions time not requested by user",
    "booking_prompt_leak": "booking prompt fragment leaked into FACT/info response",
    "stale_prompt_date_mismatch": "follow-up prompt reused stale datetime hint and diverged from booking context",
    "mix_info_booking": "reply mixes info/FACT answer with booking collection prompt in one turn",
    "stale_booking_carryover": "stale booking carryover phrase leaked into FACT/info response",
    "timeout_degrade_booking_generic": "timeout-degrade returned generic clarify in booking context",
    "run_completion_gap": "run stopped before all scenario turns were executed",
    "trace_response_mismatch": "trace_bundle rows do not match responses rows",
    "run_economy_violation": "run-economy gate detected non-actionable spend pattern",
    "weak_oracle_turn": "scenario turn has no contract expectation (weak oracle)",
    "incomplete_run_artifact": "required run artifact is missing (summary/brief/scenarios)",
    "judge_fail": "LLM judge marked turn as fail",
    "manager_action_failed": "manager callback failed",
    "handoff_state_mismatch": "state mismatch after manager action",
    "handoff_status_mismatch": "handover status mismatch after manager action",
    "post_llm_semantic_rewrite_budget_exceeded": "post-LLM semantic rewrite rate exceeded configured budget",
    "keyword_override_budget_exceeded": "keyword/regex override rate exceeded configured budget",
    "rewrite_reason_missing": "post-LLM rewrite executed without explicit whitelist reason-code",
    "rewrite_reason_unknown": "post-LLM rewrite used non-whitelist reason-code",
    "lexicon_regex_delta_violation": "lexicon/regex delta without resolver + contract test delta",
    "hardcode_core_violation": "core hardcode gate detected raw keyword/regex branching in core diff",
    "wrong_action": "HQ1: wrong product outcome (FACT/COLLECT/HANDOFF mismatch)",
    "handoff_miss": "HQ1: manager/handoff intent not escalated to pending",
    "non_actionable_reply": "HQ1: dead-end or non-actionable consultant reply",
    "hallucinated_fact": "HQ1: hallucinated or fabricated fact in bot response",
    "booking_flow_break": "HQ1: booking progression contract broken",
}
LLM_QUALITY_TAXONOMY_CATEGORIES = ("expectation", "canon", "code", "data", "unknown")
LLM_QUALITY_REASON_TAXONOMY = {
    "decision_meta_missing": "canon",
    "decision_trace_missing": "canon",
    "unknown_state": "canon",
    "expected_state_mismatch": "expectation",
    "expected_action_mismatch": "expectation",
    "expected_reply_type_mismatch": "expectation",
    "expected_reply_mismatch": "expectation",
    "expected_info_section_miss": "expectation",
    "missing_bot_reply": "code",
    "unobserved_turn": "code",
    "outbox_delivery_failed": "code",
    "outbox_delivery_timeout": "code",
    "unexpected_bot_reply_manager": "code",
    "handover_missing": "code",
    "info_section_miss": "data",
    "booking_slot_stall": "code",
    "false_booking_confirmation": "code",
    "calendar_tool_contract_miss": "code",
    "requested_date_time_like": "expectation",
    "slot_date_resolution_miss": "expectation",
    "slot_availability_contradiction": "expectation",
    "fabricated_conflict_time": "expectation",
    "booking_prompt_leak": "expectation",
    "stale_prompt_date_mismatch": "expectation",
    "mix_info_booking": "expectation",
    "stale_booking_carryover": "expectation",
    "timeout_degrade_booking_generic": "expectation",
    "run_completion_gap": "canon",
    "trace_response_mismatch": "canon",
    "run_economy_violation": "canon",
    "weak_oracle_turn": "canon",
    "incomplete_run_artifact": "canon",
    "judge_fail": "expectation",
    "manager_action_failed": "code",
    "handoff_state_mismatch": "code",
    "handoff_status_mismatch": "code",
    "post_llm_semantic_rewrite_budget_exceeded": "code",
    "keyword_override_budget_exceeded": "code",
    "rewrite_reason_missing": "canon",
    "rewrite_reason_unknown": "canon",
    "lexicon_regex_delta_violation": "canon",
    "hardcode_core_violation": "canon",
    "wrong_action": "expectation",
    "handoff_miss": "expectation",
    "non_actionable_reply": "expectation",
    "hallucinated_fact": "expectation",
    "booking_flow_break": "expectation",
}
LLM_QUALITY_HARD_FAIL_REASONS = {
    "decision_meta_missing",
    "decision_trace_missing",
    "unknown_state",
    "missing_bot_reply",
    "unobserved_turn",
    "outbox_delivery_failed",
    "outbox_delivery_timeout",
    "false_booking_confirmation",
    "calendar_tool_contract_miss",
    "unexpected_bot_reply_manager",
    "handover_missing",
}
LLM_QUALITY_INFO_TRACE_LOOKBACK = 12
LLM_QUALITY_TRACE_WINDOW_PADDING_SECONDS = 2
LLM_QUALITY_BOOKING_CONFIRM_PHRASES = (
    "вы записаны",
    "запись подтверждена",
    "запись оформлена",
    "записал вас",
    "записала вас",
    "забронировал для вас",
    "забронировала для вас",
)
LLM_QUALITY_BOOKING_CONFIRM_STATUS_HINTS = {
    "pending_confirmation",
    "confirmed",
    "booked",
    "scheduled",
    "active",
}
LLM_QUALITY_CALENDAR_INTENTS = {
    "calendar.list_slots",
    "calendar.book_slot",
    "calendar.get_booking",
    "calendar.reschedule",
    "calendar.cancel",
}
LLM_QUALITY_CALENDAR_SUCCESS_DECISIONS = {
    "ok",
    "not_found",
    "time_mismatch",
    "slot_mismatch",
    "missing_slot",
    "already_cancelled",
}
LLM_QUALITY_CALENDAR_FAILURE_DECISIONS = {
    "provider_unavailable",
    "branch_missing",
    "error",
    "failed",
    "failure",
    "timeout",
}
LLM_QUALITY_TOOL_OUTCOMES = ("success", "failure", "pending")
LLM_QUALITY_OUTBOX_SUCCESS_STATUSES = {"SENT"}
LLM_QUALITY_OUTBOX_FAILURE_STATUSES = {"FAILED"}
LLM_QUALITY_OUTBOX_PENDING_STATUSES = {"PENDING", "PROCESSING"}
LLM_QUALITY_JUDGE_REASONS = {
    "irrelevant_reply": "reply does not address the user's intent/question",
    "missed_question": "question not answered or slot not collected",
    "looped_prompt": "bot repeats prior prompt without progress",
    "needs_clarification": "reply should clarify but does not",
    "should_handoff": "should have escalated/handed off",
    "unsafe_response": "violates policy/safety expectations",
}
LLM_QUALITY_JUDGE_VERDICTS = {"pass", "fail", "uncertain"}
LLM_QUALITY_JUDGE_CRITICAL_TAGS = {
    "booking",
    "handoff",
    "cancel",
    "reschedule",
    "check_booking",
    "confirm",
}
LLM_QUALITY_JUDGE_PAYLOAD_LIMITS = {
    "max_depth": 5,
    "max_items": 12,
    "max_dict_keys": 24,
    "max_string_len": 320,
}
LLM_QUALITY_TIMEOUT_PROFILES = {
    "realistic": {
        "timeout": 30.0,
        "poll_timeout": 25.0,
        "poll_interval": 0.5,
        "trace_timeout": 25.0,
        "trace_interval": 0.5,
    },
    "balanced": {
        "timeout": 24.0,
        "poll_timeout": 20.0,
        "poll_interval": 0.4,
        "trace_timeout": 20.0,
        "trace_interval": 0.4,
    },
    "fast-replay": {
        "timeout": 20.0,
        "poll_timeout": 16.0,
        "poll_interval": 0.3,
        "trace_timeout": 16.0,
        "trace_interval": 0.3,
    },
}
LLM_QUALITY_WAIT_DEFAULTS = {
    "generated": {"min_wait": 0.2, "max_wait": 0.4},
    "replay": {"min_wait": 0.0, "max_wait": 0.15},
}


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
        "booking_paused",
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


def _chaos_generate_cases(count, rng, min_turns, max_turns, noise, kinds=None):
    cases = []
    builders = [
        ("booking", _chaos_build_booking_case, 0.45),
        ("policy", _chaos_build_policy_case, 0.25),
        ("consult", _chaos_build_consult_case, 0.15),
        ("info", _chaos_build_info_case, 0.1),
        ("ood", _chaos_build_ood_case, 0.05),
    ]
    if kinds:
        allowed = {kind.strip() for kind in kinds if kind.strip()}
        builders = [item for item in builders if item[0] in allowed]
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
    if action == "match" and "reply" in expected_actions:
        return True
    if action == "ai_response" and ("reply" in expected_actions or "smalltalk" in expected_actions):
        return True
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
    meta_intent = (meta or {}).get("intent")
    booking_active = _chaos_booking_reply_active(conv_meta)
    if (conv_meta or {}).get("state") == "pending" or _chaos_trace_has_pending(trace_entries):
        return True
    if meta_action == "escalate" and meta_intent == "clarify_limit":
        if (conv_meta or {}).get("state") == "pending":
            return True
    if any(action in expected_actions for action in _chaos_booking_completion_actions()):
        if meta_action == "escalate" and meta_intent in {"clarify_limit", "human_request"}:
            return True
        if meta_action in CHAOS_PENDING_ACTIONS and (conv_meta or {}).get("state") == "pending":
            return True
    if any(action in expected_actions for action in ("booking_escalated", "handoff", "escalate")):
        if meta_action == "booking_prompt" and booking_active:
            expected_reply_type = expected.get("expected_reply_type")
            if expected_reply_type is None or expected_reply_type in CHAOS_BOOKING_REPLY_TYPES:
                return True
        if (
            meta_action == "reply"
            and booking_active
            and (meta or {}).get("tool_decision") == "provider_unavailable"
            and (meta_intent or "") in {"calendar.list_slots", "calendar.book_slot"}
        ):
            expected_reply_type = expected.get("expected_reply_type")
            if expected_reply_type is None or expected_reply_type in CHAOS_BOOKING_REPLY_TYPES:
                return True
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
        if _chaos_trace_has_stage(trace_entries, "booking_interrupt"):
            return True
        if _chaos_trace_has_truth_hours(trace_entries):
            return True
        if meta_intent in {
            "booking_intake",
            "service_semantic",
            "service_match",
            "service_duration",
            "multi_intent_info",
            "info_bundle",
            "pricing",
            "hours",
            "address",
        }:
            return True
    if "booking_prompt" in expected_actions and meta_action in _chaos_booking_completion_actions():
        return True
    if "booking_prompt" in expected_actions and meta_action == "match":
        if booking_active or _chaos_trace_has_stage(trace_entries, "booking_interrupt"):
            return True
        if meta_intent in {"info_bundle", "service_semantic", "service_match"}:
            return True
    if "booking_prompt" in expected_actions and meta_action == "booking_confirm":
        return True
    if "booking_prompt" in expected_actions and meta_action == "escalate":
        if meta_intent in {"clarify_limit", "human_request"} or booking_active:
            return True
    if meta_action in CHAOS_PENDING_ACTIONS and any(
        action in expected_actions for action in ("reply", "smalltalk")
    ):
        if (conv_meta or {}).get("state") == "pending":
            return True
    if "reply" in expected_actions and meta_action == "booking_prompt":
        if booking_active:
            return True
    if "smalltalk" in expected_actions and meta_action == "booking_prompt":
        if booking_active:
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


def _chaos_trace_has_pending(trace_entries):
    for entry in trace_entries or []:
        if not isinstance(entry, dict):
            continue
        stage = entry.get("stage")
        if stage in CHAOS_PENDING_ACTIONS:
            return True
        if stage == "contract" and entry.get("decision") == "action":
            contract = entry.get("contract")
            if isinstance(contract, dict):
                action_type = contract.get("action_type")
                if action_type in CHAOS_PENDING_ACTIONS:
                    return True
    return False


def _chaos_trace_action(trace_entries):
    for entry in reversed(trace_entries or []):
        if not isinstance(entry, dict):
            continue
        if entry.get("stage") != "contract" or entry.get("decision") != "action":
            continue
        contract = entry.get("contract")
        if isinstance(contract, dict):
            action_type = contract.get("action_type")
            if isinstance(action_type, str) and action_type.strip():
                return action_type.strip()
    return None


def _chaos_trace_has_truth_hours(trace_entries):
    for entry in trace_entries or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("stage") != "truth_gate":
            continue
        if entry.get("intent") == "hours":
            return True
        info_sections = entry.get("info_sections") or []
        if "hours" in info_sections:
            return True
    return False


def _chaos_booking_reply_active(conv_meta):
    context = (conv_meta or {}).get("context") or {}
    expected_reply = _chaos_extract_expected_reply(context)
    if expected_reply in CHAOS_BOOKING_REPLY_TYPES:
        return True
    booking = context.get("booking")
    return isinstance(booking, dict) and booking.get("active") is True


def _chaos_reply_type_fallback_ok(expected_reply_type, actual_reply, meta, conv_meta, trace_entries):
    if expected_reply_type in CHAOS_BOOKING_REPLY_TYPES:
        intent = _llm_quality_effective_intent(meta if isinstance(meta, dict) else None)
        tool_decision = (
            str((meta or {}).get("tool_decision") or "").strip().lower()
            if isinstance(meta, dict)
            else ""
        )
        if intent == "calendar.get_booking" and tool_decision in {"ok", "time_mismatch", "not_found"}:
            return True
        if intent == "catalog.portfolio" and tool_decision in {"ok", "truth_fallback"}:
            return True
        if (conv_meta or {}).get("state") == "pending" or _chaos_trace_has_pending(trace_entries):
            return True
        if actual_reply in CHAOS_BOOKING_REPLY_TYPES:
            return True
        if actual_reply == "intent_choice" and (meta or {}).get("intent") in {
            "multi_intent_info",
            "info_bundle",
        }:
            return True
        if actual_reply is None and _chaos_trace_has_stage(trace_entries, "booking_interrupt"):
            return True
        if actual_reply is None and _chaos_trace_has_truth_hours(trace_entries):
            return True
        if actual_reply is None and (meta or {}).get("action") in CHAOS_PENDING_ACTIONS:
            return True
        if actual_reply is None and (meta or {}).get("intent") in {
            "booking_intake",
            "info_bundle",
            "service_semantic",
            "service_match",
            "service_duration",
            "multi_intent_info",
        }:
            return True
        if actual_reply is None and (meta or {}).get("intent") == "catalog.service_query":
            info_sections = (meta or {}).get("info_sections")
            normalized_sections = {
                str(section).strip().casefold()
                for section in (info_sections or [])
                if isinstance(section, str) and section.strip()
            }
            if {"pricing", "duration", "services_overview"} & normalized_sections:
                return True
            tool_decision = str((meta or {}).get("tool_decision") or "").strip().casefold()
            if tool_decision == "services_overview":
                return True
        if (meta or {}).get("expected_reply_matched") is False:
            return True
        if (meta or {}).get("action") == "booking_paused":
            return True
        if _chaos_trace_has_stage_with_reason(trace_entries, "question_contract", "booking_prompt"):
            return True
    return False


def _chaos_pending_action_ok(expected_pending, meta, conv_meta):
    if not expected_pending:
        return True
    actual_pending = (meta or {}).get("pending_action")
    action = (meta or {}).get("action")
    if actual_pending == expected_pending:
        return True
    if actual_pending in CHAOS_PENDING_ACTIONS or action in CHAOS_PENDING_ACTIONS:
        return True
    if action == "escalate":
        return True
    if (conv_meta or {}).get("state") == "pending":
        if action in _chaos_booking_completion_actions():
            return True
    else:
        return True
    return False


def _chaos_state_fallback_ok(expected_state, actual_state, meta, conv_meta, handover_meta):
    action = (meta or {}).get("action")
    pending_action = (meta or {}).get("pending_action")
    tool_decision = (
        str((meta or {}).get("tool_decision") or "").strip().lower()
        if isinstance(meta, dict)
        else ""
    )
    intent_value = _llm_quality_effective_intent(meta if isinstance(meta, dict) else None)
    if expected_state == "pending":
        if action in CHAOS_PENDING_ACTIONS or pending_action in CHAOS_PENDING_ACTIONS:
            return True
    if expected_state == "manager_active" and actual_state == "pending":
        if action in CHAOS_PENDING_ACTIONS or pending_action in CHAOS_PENDING_ACTIONS:
            return True
        if action in {"escalate", "booking_escalated", "booking_captured_pending"}:
            return True
    if expected_state == "pending" and actual_state in {"bot_active", "manager_active"}:
        if action in {"booking_prompt", "booking_paused", "reply", "match"}:
            return True
        if _chaos_booking_reply_active(conv_meta):
            return True
        if not handover_meta:
            return True
    if expected_state == "bot_active" and actual_state in {"pending", "manager_active"}:
        if action in CHAOS_PENDING_ACTIONS or pending_action in CHAOS_PENDING_ACTIONS:
            return True
        if action in _chaos_booking_completion_actions() or action == "escalate":
            return True
        if (
            action == "reply"
            and intent_value
            in {
                "catalog.location",
                "catalog.service_query",
                "hours",
                "parking",
                "duration",
                "discounts",
                "promotions",
                "consult_reply",
            }
            and tool_decision in {"", "ok", "truth_fallback", "duration", "not_found_fallback"}
        ):
            return True
        if (
            action == "reply"
            and pending_action == "pending_pass"
            and tool_decision in {"provider_unavailable", "branch_missing"}
        ):
            return True
    return False


def _chaos_handover_fallback_ok(expected_status, conv_meta, meta, handover_meta):
    if not expected_status:
        return True
    if (conv_meta or {}).get("state") != "pending":
        return True
    if not handover_meta and (meta or {}).get("action") in {"booking_prompt", "booking_paused", "reply", "match"}:
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
    meta_eval = meta
    trace_action = _chaos_trace_action(trace_entries)
    if trace_action:
        meta_eval = dict(meta or {})
        meta_eval["action"] = trace_action
    meta_action = (meta_eval or {}).get("action")
    meta_intent = (meta_eval or {}).get("intent")
    meta_policy_gate = (meta_eval or {}).get("policy_gate")
    if meta is None:
        failures.append("missing_decision_meta")
        if not trace_entries:
            failures.append("missing_decision_trace")
        return failures
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
    if expected.get("booking_interrupt") and not (
        (meta or {}).get("booking_info_interrupt") or _chaos_trace_has_stage(trace_entries, "booking_interrupt")
    ):
        if _chaos_booking_reply_active(conv_meta) and meta_action != "booking_prompt":
            failures.append("booking_interrupt_missing")
    if expected.get("action_any") and not _chaos_matches_action(meta_eval, expected.get("action_any")):
        if not _chaos_action_fallback_ok(expected, meta_eval, conv_meta, trace_entries, info_sections_ok):
            failures.append("action_mismatch")
    forbid = expected.get("forbid") if isinstance(expected.get("forbid"), dict) else {}
    conv_state = (conv_meta or {}).get("state")
    if forbid:
        forbidden_actions = forbid.get("action_any") or []
        if conv_state != "pending":
            forbidden_actions = []
        if forbidden_actions and _chaos_matches_action(meta, forbidden_actions):
            if not _chaos_matches_action(meta_eval, _chaos_booking_completion_actions()):
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
    if expected.get("pending_action") and not _chaos_pending_action_ok(
        expected.get("pending_action"), meta_eval, conv_meta
    ):
        failures.append("pending_action_mismatch")
    expected_state = expected.get("state")
    actual_state = (conv_meta or {}).get("state")
    if expected_state and actual_state != expected_state:
        if not _chaos_state_fallback_ok(expected_state, actual_state, meta, conv_meta, handover_meta):
            failures.append("state_mismatch")
    expected_reply_type = expected.get("expected_reply_type")
    if expected_reply_type is not None:
        actual_reply = _chaos_extract_expected_reply((conv_meta or {}).get("context"))
        if actual_reply != expected_reply_type and not _chaos_reply_type_fallback_ok(
            expected_reply_type, actual_reply, meta_eval, conv_meta, trace_entries
        ):
            failures.append("expected_reply_type_mismatch")
    expected_handover_status = expected.get("handover_status")
    if expected_handover_status and (handover_meta or {}).get("status") != expected_handover_status:
        if not _chaos_handover_fallback_ok(expected_handover_status, conv_meta, meta, handover_meta):
            failures.append("handover_status_mismatch")
    if not trace_entries:
        failures.append("missing_decision_trace")
    if meta_policy_gate and not (
        intent_set.intersection(set(CHAOS_POLICY_MAP.keys())) or intent_set.intersection(CHAOS_HARD_LAW)
    ):
        failures.append("policy_gate_false_positive")
    if intent_set.intersection(CHAOS_IN_DOMAIN_INTENTS) and (
        meta_intent == "out_of_domain" or meta_action == "out_of_domain"
    ):
        if (conv_meta or {}).get("state") != "pending" and not _chaos_trace_has_pending(trace_entries):
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

def _llm_quality_repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _llm_quality_worktree_namespace():
    repo_root = _llm_quality_repo_root()
    digest = hashlib.sha1(repo_root.encode("utf-8")).hexdigest()[:8]
    return f"{os.path.basename(repo_root)}-{digest}"

def _llm_quality_dialog_script():
    return os.path.join(_llm_quality_repo_root(), "scripts", "booking_dialog_scenarios.py")

def _llm_quality_pack_dir(client_slug: str):
    return os.path.join(
        _llm_quality_repo_root(), "truffles-api", "app", "knowledge", client_slug
    )

def _llm_quality_load_yaml(path: str):
    if not os.path.exists(path):
        return None, f"missing:{path}"
    if yaml is None:
        return None, "pyyaml_missing"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle), None
    except Exception as exc:
        return None, f"yaml_error:{exc}"

def _llm_quality_load_pack_context(client_slug: str):
    pack_dir = _llm_quality_pack_dir(client_slug)
    truth_path = os.path.join(pack_dir, "SALON_TRUTH.yaml")
    playbook_path = os.path.join(pack_dir, "CONSULT_PLAYBOOK.yaml")
    truth, truth_error = _llm_quality_load_yaml(truth_path)
    playbook, playbook_error = _llm_quality_load_yaml(playbook_path)
    errors = {}
    if truth_error:
        errors["truth"] = truth_error
    if playbook_error:
        errors["consult_playbook"] = playbook_error
    return {
        "truth": truth if isinstance(truth, dict) else None,
        "consult_playbook": playbook if isinstance(playbook, dict) else None,
        "errors": errors,
        "paths": {"truth": truth_path, "consult_playbook": playbook_path},
    }

def _llm_quality_compact_services_catalog(catalog, *, include_price: bool):
    if not isinstance(catalog, dict):
        return None
    compact = {}
    for key in (
        "suggestions",
        "not_found_reply",
        "duration_clarify",
        "service_presence_reply",
    ):
        if key in catalog:
            compact[key] = catalog.get(key)
    services = catalog.get("services")
    if isinstance(services, list):
        compact_services = []
        for service in services:
            if not isinstance(service, dict):
                continue
            entry = {}
            for key in ("name", "duration_text"):
                if key in service:
                    entry[key] = service.get(key)
            if include_price:
                for key in ("price_items", "quick_price_key"):
                    if key in service:
                        entry[key] = service.get(key)
            if entry:
                compact_services.append(entry)
        if compact_services:
            compact["services"] = compact_services
    return compact

def _llm_quality_compact_truth(truth, tags, intents):
    if not isinstance(truth, dict):
        return {}
    selected = {}
    salon = truth.get("salon")
    if isinstance(salon, dict):
        salon_selected = {}
        if "location" in tags:
            for key in ("name", "city", "address"):
                if key in salon:
                    salon_selected[key] = salon.get(key)
        if "hours" in tags and "hours" in salon:
            salon_selected["hours"] = salon.get("hours")
        if "parking" in tags and "parking" in salon:
            salon_selected["parking"] = salon.get("parking")
        if salon_selected:
            if "communication" in salon:
                salon_selected["communication"] = salon.get("communication")
            selected["salon"] = salon_selected
    if "price" in tags:
        for key in ("pricing", "price_quick_answers", "price_list", "promotions"):
            if key in truth:
                selected[key] = truth.get(key)
        catalog = _llm_quality_compact_services_catalog(
            truth.get("services_catalog"), include_price=True
        )
        if catalog:
            selected["services_catalog"] = catalog
    if "promo" in tags and "promotions" in truth and "promotions" not in selected:
        selected["promotions"] = truth.get("promotions")
    if "duration" in tags:
        for key in ("duration_or_price_clarify",):
            if key in truth:
                selected[key] = truth.get(key)
        catalog = _llm_quality_compact_services_catalog(
            truth.get("services_catalog"), include_price=False
        )
        if catalog and "services_catalog" not in selected:
            selected["services_catalog"] = catalog
    if "master" in tags and "team" in truth:
        selected["team"] = truth.get("team")
    if "policy" in tags:
        for key in ("policy", "guest_policy", "safety"):
            if key in truth:
                selected[key] = truth.get(key)
    if "style_reference" in tags and "style_reference" in truth:
        selected["style_reference"] = truth.get("style_reference")
    if "quality" in tags and "quality" in truth:
        selected["quality"] = truth.get("quality")
    if "service" in tags and "services_summary" in truth:
        selected["services_summary"] = truth.get("services_summary")
    if "system_messages" in tags and "system_messages" in truth:
        selected["system_messages"] = truth.get("system_messages")
    return selected

def _llm_quality_compact_consult_playbook(playbook, topic_id=None):
    if not isinstance(playbook, dict):
        return None
    topics = playbook.get("topics") or []
    compact_topics = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        if topic_id and topic.get("id") != topic_id:
            continue
        compact_topics.append(
            {
                "id": topic.get("id"),
                "title": topic.get("title"),
                "summary": topic.get("summary"),
                "allowed_advice": topic.get("allowed_advice"),
                "required_questions": topic.get("required_questions"),
                "optional_questions": topic.get("optional_questions"),
                "disallowed_claims": topic.get("disallowed_claims"),
                "risk_tags": topic.get("risk_tags"),
                "clarify_limit": topic.get("clarify_limit"),
                "escalate_when": topic.get("escalate_when"),
                "next_step": topic.get("next_step"),
            }
        )
    if not compact_topics and topic_id:
        return None
    default_policy = playbook.get("default_policy")
    if isinstance(default_policy, dict):
        default_policy = {
            "clarify_limit": default_policy.get("clarify_limit"),
            "escalate_on_low_confidence": default_policy.get("escalate_on_low_confidence"),
        }
    return {"topics": compact_topics, "default_policy": default_policy}

def _llm_quality_collect_truth_tags(info_tags, expected_info_sections, meta, trace_entries):
    tags = set(info_tags or [])
    info_sections, intents = _llm_quality_collect_info_signals(meta, trace_entries)
    for section in info_sections:
        tag = LLM_QUALITY_SECTION_TAG_MAP.get(section)
        if tag:
            tags.add(tag)
    for section in expected_info_sections or []:
        tag = LLM_QUALITY_SECTION_TAG_MAP.get(section)
        if tag:
            tags.add(tag)
    for intent in intents:
        for tag in LLM_QUALITY_INTENT_TAG_MAP.get(intent, set()):
            tags.add(tag)
    if isinstance(meta, dict):
        meta_intent = meta.get("intent")
        if isinstance(meta_intent, str) and meta_intent in LLM_QUALITY_POLICY_INTENTS:
            tags.add("policy")
        policy_gate = meta.get("policy_gate")
        if isinstance(policy_gate, str) and policy_gate.strip() and policy_gate != "none":
            tags.add("policy")
        consult_playbook_id = (
            meta.get("consult_playbook_id")
            or meta.get("consult_topic_id")
            or meta.get("consult_topic")
        )
        if consult_playbook_id:
            tags.add("consult")
    return tags, intents

def _llm_quality_build_pack_context(pack_context, info_tags, expected_info_sections, meta, trace_entries):
    if not isinstance(pack_context, dict):
        return {}
    tags, intents = _llm_quality_collect_truth_tags(
        info_tags, expected_info_sections, meta, trace_entries
    )
    truth_context = _llm_quality_compact_truth(
        pack_context.get("truth"), tags, intents
    )
    consult_id = None
    if isinstance(meta, dict):
        consult_id = (
            meta.get("consult_playbook_id")
            or meta.get("consult_topic_id")
            or meta.get("consult_topic")
        )
    consult_context = _llm_quality_compact_consult_playbook(
        pack_context.get("consult_playbook"), consult_id
    )
    if "consult" in tags and consult_context is None:
        consult_context = _llm_quality_compact_consult_playbook(
            pack_context.get("consult_playbook")
        )
    context = {}
    if truth_context:
        context["pack_truth"] = truth_context
    if consult_context:
        context["consult_playbook"] = consult_context
    if pack_context.get("errors"):
        context["pack_errors"] = pack_context.get("errors")
    return context

def _llm_quality_parse_actions(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]

def _llm_quality_pick_jid(jids, idx, rng, mode, run_id=None):
    if mode == "unique":
        base = int(os.environ.get("LLM_QUALITY_JID_BASE", "99900000000"))
        token = f"{run_id or 'llm_quality'}:{idx}".encode("utf-8")
        suffix = int(hashlib.sha256(token).hexdigest()[:8], 16) % 90000000
        return f"{base + suffix}@s.whatsapp.net"
    if not jids:
        return None
    if mode == "random":
        return rng.choice(jids)
    return jids[idx % len(jids)]


def _llm_quality_resolve_jid_mode(args):
    mode = str(getattr(args, "jid_mode", "auto") or "auto").strip().lower()
    if mode != "auto":
        return mode
    if getattr(args, "skip_outbox", False):
        return "unique"
    return "round_robin"

def _llm_quality_extract_turn_tags(turn):
    tags = []
    for tag in turn.get("tags") or []:
        if isinstance(tag, str) and tag.strip():
            tags.append(tag.strip())
    return tags


LLM_QUALITY_DYNAMIC_SLOT_TIME_TOKEN = "{{AUTO_SLOT_TIME}}"
LLM_QUALITY_DYNAMIC_SLOT_DATE_TOKEN = "{{AUTO_SLOT_DATE}}"
LLM_QUALITY_DYNAMIC_SLOT_SPECIALIST_TOKEN = "{{AUTO_SLOT_SPECIALIST}}"


def _llm_quality_parse_slot_candidates(outbox_text: str | None) -> list[dict]:
    if not isinstance(outbox_text, str):
        return []
    text = outbox_text.strip()
    if not text:
        return []
    marker = "Свободные слоты:"
    marker_idx = text.find(marker)
    if marker_idx == -1:
        return []
    tail = text[marker_idx + len(marker) :].strip()
    if not tail:
        return []

    candidates: list[dict[str, str]] = []
    for part in tail.split("|"):
        segment = part.strip()
        if not segment or ":" not in segment:
            continue
        specialist, times_blob = segment.split(":", 1)
        specialist_name = specialist.strip()
        if not specialist_name:
            continue
        times = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", times_blob)
        for hour, minute in times:
            candidates.append(
                {
                    "specialist": specialist_name,
                    "time": f"{int(hour):02d}:{minute}",
                }
            )
    return candidates


def _llm_quality_normalize_time_token(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().replace(".", ":")
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", token)
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def _llm_quality_extract_availability_claim(outbox_text: str | None) -> tuple[str, str | None]:
    if not isinstance(outbox_text, str) or not outbox_text.strip():
        return "unknown", None
    text = outbox_text.casefold()
    yes_match = re.search(
        r"\bда,\s*на\s*([01]?\d[:.][0-5]\d)\s+есть\s+свободное\s+окно",
        text,
    )
    if yes_match:
        return "yes", _llm_quality_normalize_time_token(yes_match.group(1))
    no_match = re.search(
        r"\bна\s*([01]?\d[:.][0-5]\d)\s+свободного\s+окна\s+нет",
        text,
    )
    if no_match:
        return "no", _llm_quality_normalize_time_token(no_match.group(1))
    return "unknown", None


def _llm_quality_extract_available_slots_by_specialist(
    meta: dict | None,
    outbox_text: str | None,
) -> dict[str, list[str]]:
    from_meta = {}
    if isinstance(meta, dict):
        payload = meta.get("available_slots_by_specialist")
        if isinstance(payload, dict):
            for raw_name, raw_slots in payload.items():
                if not isinstance(raw_name, str) or not isinstance(raw_slots, list):
                    continue
                slots: list[str] = []
                for value in raw_slots:
                    normalized = _llm_quality_normalize_time_token(str(value))
                    if normalized:
                        slots.append(normalized)
                if slots:
                    from_meta[raw_name] = slots
    if from_meta:
        return from_meta

    from_text: dict[str, list[str]] = {}
    for candidate in _llm_quality_parse_slot_candidates(outbox_text):
        specialist = str(candidate.get("specialist") or "").strip()
        slot_time = _llm_quality_normalize_time_token(str(candidate.get("time") or ""))
        if not specialist or not slot_time:
            continue
        slots = from_text.setdefault(specialist, [])
        if slot_time not in slots:
            slots.append(slot_time)
    if from_text:
        return from_text

    if isinstance(outbox_text, str) and outbox_text.strip():
        text = outbox_text.casefold()
        flat_match = re.search(r"\bдоступны:\s*([^\n]+)", text)
        if flat_match:
            flat_slots = []
            for token in re.findall(r"\b([01]?\d[:.][0-5]\d)\b", flat_match.group(1)):
                normalized = _llm_quality_normalize_time_token(token)
                if normalized and normalized not in flat_slots:
                    flat_slots.append(normalized)
            if flat_slots:
                return {"_flat": flat_slots}
    return {}


def _llm_quality_has_booking_prompt_leak(
    *,
    meta: dict | None,
    outbox_text: str | None,
) -> bool:
    if not isinstance(meta, dict):
        return False
    intent = _llm_quality_normalize_tool_token(meta.get("intent"))
    if intent not in {"catalog.service_query", "catalog.location"}:
        return False
    tool_decision = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
    if tool_decision == "services_overview":
        # `services_overview` legitimately asks the user to choose a service;
        # treat it as contract follow-up, not booking prompt leak.
        return False
    if not isinstance(outbox_text, str):
        return False
    lowered = outbox_text.casefold()
    if "\n\n" not in lowered:
        return False
    marker_fn = globals().get("_llm_quality_has_booking_prompt_markers")
    if callable(marker_fn):
        return bool(marker_fn(outbox_text))
    return any(
        marker in lowered
        for marker in (
            "как вас зовут",
            "на какую дату и время вам удобно",
            "на какую услугу хотите записаться",
            "отлично, время подходит",
        )
    )


def _llm_quality_has_booking_prompt_markers(outbox_text: str | None) -> bool:
    if not isinstance(outbox_text, str):
        return False
    lowered = outbox_text.casefold()
    return any(
        marker in lowered
        for marker in (
            "как вас зовут",
            "на какую дату и время вам удобно",
            "на какую услугу хотите записаться",
            "отлично, время подходит",
        )
    )


def _llm_quality_has_stale_prompt_date_mismatch(meta: dict | None) -> bool:
    if not isinstance(meta, dict):
        return False
    guard_value = _llm_quality_normalize_tool_token(meta.get("followup_prompt_guard"))
    expected_reply_reason = _llm_quality_normalize_tool_token(meta.get("expected_reply_reason"))
    return bool(
        guard_value == "stale_prompt_date_mismatch"
        or expected_reply_reason == "stale_prompt_date_mismatch"
    )


def _llm_quality_has_mix_info_booking(
    *,
    meta: dict | None,
    outbox_text: str | None,
) -> bool:
    if not isinstance(meta, dict):
        return False
    marker_fn = globals().get("_llm_quality_has_booking_prompt_markers")
    if callable(marker_fn):
        has_booking_prompt_markers = bool(marker_fn(outbox_text))
    else:
        lowered = str(outbox_text or "").casefold()
        has_booking_prompt_markers = any(
            marker in lowered
            for marker in (
                "как вас зовут",
                "на какую дату и время вам удобно",
                "на какую услугу хотите записаться",
                "отлично, время подходит",
            )
        )
    if not has_booking_prompt_markers:
        return False
    intent_value = _llm_quality_effective_intent(meta)
    if intent_value in LLM_QUALITY_CALENDAR_INTENTS:
        return False
    info_sections = meta.get("info_sections")
    has_info_sections = bool(
        isinstance(info_sections, list)
        and any(isinstance(item, str) and item.strip() for item in info_sections)
    )
    info_intent_hints = {
        "catalog.service_query",
        "catalog.location",
        "catalog.hours",
        "catalog.parking",
        "catalog.promotions",
        "hours",
        "location",
        "parking",
        "promotions",
        "master",
    }
    if not (has_info_sections or intent_value in info_intent_hints):
        return False
    expected_reply_type = _llm_quality_normalize_tool_token(meta.get("expected_reply_type"))
    expected_reply_reason = _llm_quality_normalize_tool_token(meta.get("expected_reply_reason"))
    action_value = _llm_quality_normalize_tool_token(meta.get("action"))
    return bool(
        expected_reply_type in {"service_choice", "time", "name"}
        or expected_reply_reason in {"booking_interrupt", "booking_prompt", "stale_prompt_date_mismatch"}
        or action_value in {"booking_prompt", "booking_confirm"}
    )


def _llm_quality_has_stale_booking_carryover(
    *,
    meta: dict | None,
    outbox_text: str | None,
) -> bool:
    if not isinstance(outbox_text, str) or not outbox_text.strip():
        return False
    lowered = outbox_text.casefold()
    if (
        "ещё был вопрос по записи" not in lowered
        and "еще был вопрос по записи" not in lowered
    ):
        return False
    if not isinstance(meta, dict):
        return True
    action_value = _llm_quality_normalize_tool_token(meta.get("action"))
    if action_value in {"booking_prompt", "booking_confirm", "check_booking_prompt"}:
        return False
    intent_value = _llm_quality_effective_intent(meta)
    if intent_value in LLM_QUALITY_CALENDAR_INTENTS:
        return False
    tool_action_value = _llm_quality_normalize_tool_token(meta.get("tool_action"))
    if tool_action_value in LLM_QUALITY_CALENDAR_INTENTS:
        return False
    tool_decision_value = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
    if tool_decision_value == "services_overview":
        return False
    return True


def _llm_quality_is_time_like_token(value: str | None) -> bool:
    return _llm_quality_normalize_time_token(value) is not None


def _llm_quality_is_weak_oracle_expectation(expectations: dict | None) -> bool:
    if not isinstance(expectations, dict):
        return True
    has_action = bool(expectations.get("action"))
    has_info_sections = bool(expectations.get("info_sections"))
    has_reply_type = bool(expectations.get("reply_type"))
    has_state = bool(expectations.get("state"))
    # `expected_reply=true/false` alone is not a strong oracle contract.
    return not (has_action or has_info_sections or has_reply_type or has_state)


def _llm_quality_has_timeout_degrade_booking_generic(
    *,
    meta: dict | None,
    booking_active: bool,
    outbox_text: str | None,
) -> bool:
    if not booking_active or not isinstance(meta, dict) or not isinstance(outbox_text, str):
        return False
    policy_mode = _llm_quality_normalize_tool_token(meta.get("policy_core_mode"))
    if policy_mode != "degraded_fallback":
        return False
    degrade_reason = str(meta.get("policy_core_degrade_reason") or "").casefold()
    if "timeout" not in degrade_reason:
        return False
    normalized = outbox_text.casefold().strip()
    return any(
        marker in normalized
        for marker in (
            "подскажите, пожалуйста, что именно вас интересует",
            "что именно вас интересует",
        )
    )


def _llm_quality_pick_slot_candidate(
    candidates: list[dict] | None,
    *,
    prefer_specialist: str | None = None,
) -> dict | None:
    rows = [item for item in (candidates or []) if isinstance(item, dict)]
    if not rows:
        return None
    specialist_hint = (prefer_specialist or "").strip().casefold()
    if specialist_hint:
        for item in rows:
            specialist = str(item.get("specialist") or "").casefold()
            if specialist_hint in specialist:
                return item
    return rows[0]


def _llm_quality_resolve_dynamic_slot_date(date_hint: str | None, *, now: datetime | None = None) -> str:
    current = now if isinstance(now, datetime) else datetime.now(timezone.utc)
    token = (date_hint or "").strip().casefold()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return token
    if token in {"today", "сегодня"}:
        return current.date().isoformat()
    if token in {"tomorrow", "завтра"}:
        return (current + timedelta(days=1)).date().isoformat()
    if "сегодня" in token or "today" in token:
        return current.date().isoformat()
    if "завтра" in token or "tomorrow" in token:
        return (current + timedelta(days=1)).date().isoformat()
    return (current + timedelta(days=1)).date().isoformat()


def _llm_quality_prepare_turn_text(
    turn: dict,
    dialog_runtime_state: dict | None,
    *,
    now: datetime | None = None,
) -> tuple[str, dict | None]:
    base_text = turn.get("text") if isinstance(turn, dict) else ""
    text = base_text if isinstance(base_text, str) else str(base_text or "")
    if not isinstance(turn, dict):
        return text, None
    dynamic_booking = turn.get("dynamic_booking")
    has_auto_tokens = any(
        token in text
        for token in (
            LLM_QUALITY_DYNAMIC_SLOT_TIME_TOKEN,
            LLM_QUALITY_DYNAMIC_SLOT_DATE_TOKEN,
            LLM_QUALITY_DYNAMIC_SLOT_SPECIALIST_TOKEN,
        )
    )
    if not has_auto_tokens and not isinstance(dynamic_booking, dict):
        return text, None

    slot_candidates = (
        dialog_runtime_state.get("slot_candidates")
        if isinstance(dialog_runtime_state, dict)
        else None
    )
    prefer_specialist = None
    if isinstance(dynamic_booking, dict):
        prefer_specialist = dynamic_booking.get("prefer_specialist") or dynamic_booking.get("specialist")
    selected = _llm_quality_pick_slot_candidate(
        slot_candidates if isinstance(slot_candidates, list) else [],
        prefer_specialist=prefer_specialist if isinstance(prefer_specialist, str) else None,
    )
    if not selected:
        return text, {
            "dynamic_booking": True,
            "resolved": False,
            "reason": "slot_candidates_missing",
        }

    slot_time = str(selected.get("time") or "").strip()
    specialist = str(selected.get("specialist") or "").strip()
    if not slot_time:
        return text, {
            "dynamic_booking": True,
            "resolved": False,
            "reason": "slot_time_missing",
        }
    date_hint = None
    if isinstance(dynamic_booking, dict):
        raw_hint = dynamic_booking.get("date")
        if isinstance(raw_hint, str):
            date_hint = raw_hint
    if not date_hint:
        date_hint = text
    slot_date = _llm_quality_resolve_dynamic_slot_date(date_hint, now=now)

    resolved_text = text
    if has_auto_tokens:
        resolved_text = resolved_text.replace(LLM_QUALITY_DYNAMIC_SLOT_TIME_TOKEN, slot_time)
        resolved_text = resolved_text.replace(LLM_QUALITY_DYNAMIC_SLOT_DATE_TOKEN, slot_date)
        resolved_text = resolved_text.replace(LLM_QUALITY_DYNAMIC_SLOT_SPECIALIST_TOKEN, specialist)
    elif isinstance(dynamic_booking, dict):
        service = str(dynamic_booking.get("service") or "маникюр").strip()
        client_name = str(dynamic_booking.get("name") or "Лена").strip()
        specialist_part = f"к {specialist} " if specialist else ""
        resolved_text = (
            f"Запишите меня {specialist_part}на {service} {slot_date} {slot_time}, имя {client_name}."
        )

    return resolved_text, {
        "dynamic_booking": True,
        "resolved": True,
        "slot_time": slot_time,
        "slot_date": slot_date,
        "specialist": specialist,
    }


def _llm_quality_update_dialog_runtime_slots(
    dialog_runtime_state: dict | None,
    *,
    meta: dict | None,
    outbox_text: str | None,
) -> None:
    if not isinstance(dialog_runtime_state, dict):
        return
    if not isinstance(meta, dict):
        return
    tool_action = _llm_quality_normalize_tool_token(meta.get("tool_action"))
    tool_decision = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
    if tool_action != "calendar.list_slots" or tool_decision != "ok":
        return
    parsed = _llm_quality_parse_slot_candidates(outbox_text)
    if not parsed:
        return
    dialog_runtime_state["slot_candidates"] = parsed


def _llm_quality_should_expect_booking_progress(expected_reply_type, turn_tags, meta=None):
    if expected_reply_type not in CHAOS_BOOKING_REPLY_TYPES:
        return False
    if isinstance(meta, dict):
        intent_value = _llm_quality_effective_intent(meta)
        tool_decision_value = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
        info_sections = meta.get("info_sections")
        if not intent_value.startswith("calendar."):
            if isinstance(info_sections, list) and any(
                isinstance(item, str) and item.strip() for item in info_sections
            ):
                # Info interrupts during booking should not be treated as slot-progress stalls.
                return False
            if intent_value in {
                "question",
                "consult_reply",
                "service_clarify",
                "duration_or_price_clarify",
                "discounts",
                "hours",
                "location",
                "parking",
                "master",
                "promotions",
                "lateness_ok",
                "catalog.service_query",
                "catalog.location",
            }:
                return False
        if (
            intent_value == "calendar.list_slots"
            and tool_decision_value in {"missing_slot", "slot_mismatch"}
        ):
            return False
        if intent_value == "calendar.book_slot" and tool_decision_value == "conflict":
            # Slot conflict is a valid recovery step (ask for another time), not a
            # slot-fill progress requirement for this turn.
            return False
    normalized_tags = {
        str(tag).strip().lower()
        for tag in (turn_tags or [])
        if isinstance(tag, str) and tag.strip()
    }
    if not normalized_tags:
        return True
    required_tags = LLM_QUALITY_PROGRESS_TAGS_BY_REPLY_TYPE.get(expected_reply_type, set())
    if required_tags:
        if normalized_tags.intersection(required_tags):
            return True
        if normalized_tags.intersection(LLM_QUALITY_PROGRESS_SKIP_TAGS):
            return False
        # Unknown tags should not force slot-stall checks for this turn.
        return False
    if normalized_tags.intersection(LLM_QUALITY_PROGRESS_SKIP_TAGS):
        return False
    if expected_reply_type == "name":
        return False
    return True


def _llm_quality_check_booking_tool_answered(meta, turn_tags, outbox_text):
    if not isinstance(meta, dict):
        return False
    if meta.get("action") != "reply":
        return False
    if _llm_quality_effective_intent(meta) != "calendar.get_booking":
        return False
    normalized_tags = {
        str(tag).strip().lower()
        for tag in (turn_tags or [])
        if isinstance(tag, str) and tag.strip()
    }
    if not normalized_tags.intersection({"check_booking", "confirm"}):
        return False
    tool_decision = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
    if tool_decision in {"ok", "not_found"}:
        return True
    if tool_decision == "time_mismatch":
        requested_time = str(meta.get("requested_time") or "").strip().lower()
        response_text = str(outbox_text or "").strip().lower()
        if requested_time and requested_time in response_text:
            return True
    return False


def _llm_quality_has_expected_followup_prompt(outbox_text, expected_reply_type_value):
    if not isinstance(outbox_text, str):
        return False
    reply_type = _llm_quality_normalize_expect_token(expected_reply_type_value)
    if not reply_type:
        return False
    text = outbox_text.casefold()
    prompt_markers = {
        "name": ("как вас зовут", "вас зовут", "ваше имя", "имя"),
        "time": (
            "какая дата",
            "на какую дату",
            "какое время",
            "на какое время",
            "дата и время",
            "когда вам удобно",
        ),
        "service_choice": (
            "какая услуга",
            "какую услугу",
            "на какую услугу",
            "какую процедуру",
            "что хотите",
        ),
    }
    markers = prompt_markers.get(reply_type, ())
    return any(marker in text for marker in markers)


def _llm_quality_should_suppress_missed_question_judge_fail(
    *,
    judge_result,
    strict_reasons,
    meta,
    meta_action,
    expected_reply_type_value,
    booking_active,
    turn_tags,
    outbox_text,
):
    if not isinstance(judge_result, dict):
        return False
    if judge_result.get("verdict") != "fail":
        return False
    if strict_reasons:
        return False

    raw_reasons = judge_result.get("reasons")
    if not isinstance(raw_reasons, list):
        return False
    judge_reason_set = {
        str(item).strip()
        for item in raw_reasons
        if str(item).strip()
    }
    if not judge_reason_set or judge_reason_set - {"missed_question"}:
        return False

    intent_value = (
        _llm_quality_normalize_tool_token((meta or {}).get("intent"))
        if isinstance(meta, dict)
        else ""
    )
    tool_action_value = (
        _llm_quality_normalize_tool_token((meta or {}).get("tool_action"))
        if isinstance(meta, dict)
        else ""
    )
    effective_intent = intent_value or tool_action_value
    if (
        booking_active
        and meta_action == "reply"
        and effective_intent in {"calendar.list_slots", "calendar.get_booking"}
    ):
        # Never suppress calendar booking misses: these are core semantic failures.
        return False

    suppression_whitelist = set(
        globals().get("LLM_QUALITY_MISSED_QUESTION_SUPPRESSION_REASON_CODES")
        or {
            "required_slot_missing",
            "tool_unavailable",
            "timeout_degrade",
            "contract_validation_failure",
        }
    )
    reason_codes = set()
    if isinstance(meta, dict):
        primary_reason = meta.get("llm_policy_override_reason_code")
        if isinstance(primary_reason, str) and primary_reason.strip():
            reason_codes.add(primary_reason.strip().casefold())
        extra_reasons = meta.get("llm_policy_override_reason_codes")
        if isinstance(extra_reasons, str):
            extra_reasons = [
                item.strip()
                for item in extra_reasons.split(",")
                if isinstance(item, str) and item.strip()
            ]
        if isinstance(extra_reasons, list):
            for item in extra_reasons:
                if isinstance(item, str) and item.strip():
                    reason_codes.add(item.strip().casefold())
    if not reason_codes.intersection(suppression_whitelist):
        return False

    if (
        meta_action in {"booking_prompt", "booking_confirm"}
        and expected_reply_type_value in {"service_choice", "time", "name"}
    ):
        return True

    if _llm_quality_has_expected_followup_prompt(outbox_text, expected_reply_type_value):
        return True

    normalized_tags = {
        str(tag).strip().lower()
        for tag in (turn_tags or [])
        if isinstance(tag, str) and tag.strip()
    }
    if (
        booking_active
        and "media" in normalized_tags
        and meta_action in {"reply", "booking_prompt"}
        and expected_reply_type_value in {"service_choice", "time", "name"}
    ):
        return True

    tool_decision_value = (
        _llm_quality_normalize_tool_token((meta or {}).get("tool_decision"))
        if isinstance(meta, dict)
        else ""
    )
    if (
        booking_active
        and meta_action == "reply"
        and tool_decision_value in {"provider_unavailable", "branch_missing"}
        and expected_reply_type_value in {"service_choice", "time", "name"}
    ):
        return True

    response_text = str(outbox_text or "").strip().lower()
    if (
        meta_action == "reply"
        and intent_value == "catalog.service_query"
        and tool_decision_value == "not_found_fallback"
        and (
            "нет такой" in response_text
            or "нет такой позиции" in response_text
            or "могу уточнить" in response_text
            or "могу предложить" in response_text
        )
    ):
        return True

    if (
        meta_action == "out_of_domain"
        and "media" in normalized_tags
        and (
            "услуги, запись и цены" in response_text
            or "по услугам, записи и ценам" in response_text
            or "помогаю по салону" in response_text
        )
    ):
        return True

    return _llm_quality_check_booking_tool_answered(meta, turn_tags, outbox_text)


def _llm_quality_normalize_expect_token(token: str | None):
    if token is None:
        return None
    value = token.strip()
    if not value:
        return None
    lowered = value.lower()
    if lowered in {"none", "null"}:
        return None
    return value

def _llm_quality_normalize_expect_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",") if item.strip()]
        if not parts:
            return None
        if len(parts) == 1:
            return _llm_quality_normalize_expect_token(parts[0])
        return [_llm_quality_normalize_expect_token(item) for item in parts]
    if isinstance(value, list):
        normalized = []
        for item in value:
            token = _llm_quality_normalize_expect_token(str(item))
            if token is None and str(item).strip().lower() not in {"none", "null"}:
                continue
            normalized.append(token)
        return normalized or None
    return value


LLM_QUALITY_EXPECT_ACTION_HANDOFF = {"booking_escalated", "escalate", "handoff"}
LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING = {"handoff", "human", "pending", "cancel", "reschedule", "media"}
LLM_QUALITY_EXPECT_TAGS_ALLOW_MANAGER_ACTIVE = {"handoff", "human", "pending", "media"}
LLM_QUALITY_EXPECT_INFO_TAGS = set(LLM_QUALITY_INFO_TAGS) | {"discount"}


def _llm_quality_collect_turn_tags(turn):
    if not isinstance(turn, dict):
        return set()
    raw_tags = turn.get("tags")
    if not isinstance(raw_tags, list):
        return set()
    return {
        str(tag).strip().lower()
        for tag in raw_tags
        if isinstance(tag, str) and str(tag).strip()
    }


def _llm_quality_sanitize_expect_action_by_tags(tag_set, action):
    if action is None:
        return None
    allow_handoff = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING)

    def _allow(token):
        normalized = _llm_quality_normalize_expect_token(token)
        if normalized is None:
            return True
        lowered = normalized.lower()
        if lowered in LLM_QUALITY_EXPECT_ACTION_HANDOFF:
            return allow_handoff
        return True

    if isinstance(action, list):
        cleaned = []
        for token in action:
            value = _llm_quality_normalize_expect_token(str(token))
            if _allow(value):
                cleaned.append(value)
        cleaned = [token for token in cleaned if token]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = _llm_quality_normalize_expect_token(str(action))
    if not _allow(token):
        return None
    return token


def _llm_quality_sanitize_expect_state_by_tags(tag_set, state):
    if state is None:
        return None
    allow_pending = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING)
    allow_manager_active = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_MANAGER_ACTIVE)

    def _allow(token):
        normalized = _llm_quality_normalize_expect_token(token)
        if normalized is None:
            return True
        lowered = normalized.lower()
        if lowered == "bot_active":
            return True
        if lowered == "pending":
            return allow_pending
        if lowered == "manager_active":
            return allow_manager_active
        return False

    if isinstance(state, list):
        cleaned = []
        for token in state:
            value = _llm_quality_normalize_expect_token(str(token))
            if _allow(value):
                cleaned.append(value)
        cleaned = [token for token in cleaned if token]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = _llm_quality_normalize_expect_token(str(state))
    if not _allow(token):
        return None
    return token


def _llm_quality_sanitize_expect_info_sections_by_tags(tag_set, info_sections):
    if not info_sections:
        return []
    if tag_set & LLM_QUALITY_EXPECT_INFO_TAGS:
        return info_sections
    return []


def _llm_quality_extract_expectations(turn):
    expect = turn.get("expect")
    if not isinstance(expect, dict):
        return {}
    action = expect.get("action")
    if isinstance(action, str):
        action = [item.strip() for item in action.split(",") if item.strip()]
    elif isinstance(action, list):
        action = [str(item).strip() for item in action if str(item).strip()]
    else:
        action = None
    info_sections = expect.get("info_sections")
    if isinstance(info_sections, str):
        info_sections = [item.strip() for item in info_sections.split(",") if item.strip()]
    elif isinstance(info_sections, list):
        info_sections = [str(item).strip() for item in info_sections if str(item).strip()]
    else:
        info_sections = []
    reply_type = _llm_quality_normalize_expect_value(expect.get("reply_type"))
    state = _llm_quality_normalize_expect_value(expect.get("state"))
    tag_set = _llm_quality_collect_turn_tags(turn)
    booking_reply_types = globals().get(
        "CHAOS_BOOKING_REPLY_TYPES",
        {"service_choice", "time", "name"},
    )
    if reply_type in booking_reply_types and "consult" in tag_set:
        # Consult turns do not carry booking slot-contract prompts.
        reply_type = None
    action = _llm_quality_sanitize_expect_action_by_tags(tag_set, action)
    state = _llm_quality_sanitize_expect_state_by_tags(tag_set, state)
    if state is not None:
        allow_pending = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING)
        allow_manager_active = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_MANAGER_ACTIVE)
        state_values = (
            list(state)
            if isinstance(state, (list, tuple, set))
            else [state]
        )
        normalized_states = []
        for value in state_values:
            if not isinstance(value, str):
                continue
            token = value.strip().lower()
            if token:
                normalized_states.append(token)
        if "bot_active" in normalized_states:
            if allow_pending and "pending" not in normalized_states:
                normalized_states.append("pending")
            if allow_manager_active and "manager_active" not in normalized_states:
                normalized_states.append("manager_active")
        if normalized_states:
            state = normalized_states[0] if len(normalized_states) == 1 else normalized_states
        else:
            state = None
    info_sections = _llm_quality_sanitize_expect_info_sections_by_tags(tag_set, info_sections)
    expected_reply = expect.get("expected_reply")
    if isinstance(expected_reply, str):
        if expected_reply.strip().lower() in {"true", "yes", "1"}:
            expected_reply = True
        elif expected_reply.strip().lower() in {"false", "no", "0"}:
            expected_reply = False
        else:
            expected_reply = None
    if not isinstance(expected_reply, bool):
        expected_reply = None
    if "media" in tag_set:
        # Media turns may move to pending and still produce an explicit ack.
        # Keep reply expectation open to avoid brittle false mismatches.
        expected_reply = None
    allow_booking_stall = expect.get("allow_booking_stall")
    if isinstance(allow_booking_stall, str):
        token = allow_booking_stall.strip().lower()
        if token in {"true", "yes", "1"}:
            allow_booking_stall = True
        elif token in {"false", "no", "0"}:
            allow_booking_stall = False
        else:
            allow_booking_stall = None
    if not isinstance(allow_booking_stall, bool):
        allow_booking_stall = False
    return {
        "action": action,
        "info_sections": [section.lower() for section in info_sections],
        "reply_type": reply_type or None,
        "state": state or None,
        "expected_reply": expected_reply,
        "allow_booking_stall": allow_booking_stall,
    }

def _llm_quality_token_to_info_tags(token):
    tags = set()
    if not isinstance(token, str):
        return tags
    normalized = token.strip().lower()
    if not normalized:
        return tags
    if normalized in LLM_QUALITY_INFO_TAGS:
        tags.add(normalized)
    section_tag = LLM_QUALITY_SECTION_TAG_MAP.get(normalized)
    if section_tag:
        tags.add(section_tag)
    intent_tags = LLM_QUALITY_INTENT_TAG_MAP.get(normalized)
    if intent_tags:
        tags.update(intent_tags)
    return tags


def _llm_quality_expected_section_answered(expected_sections, meta, trace_entries):
    if not expected_sections:
        return False, [], []
    info_sections, intents = _llm_quality_collect_info_signals(meta, trace_entries)
    actual = set(info_sections) | set(intents)
    expected_normalized = {
        section.strip().lower()
        for section in expected_sections
        if isinstance(section, str) and section.strip()
    }
    if expected_normalized & actual:
        return True, info_sections, intents

    expected_tags = set()
    for section in expected_normalized:
        expected_tags.update(_llm_quality_token_to_info_tags(section))
    if not expected_tags:
        return False, info_sections, intents
    bundle_intents = globals().get(
        "LLM_QUALITY_BUNDLE_INTENTS",
        {"info_bundle", "multi_intent_info"},
    )
    if intents.intersection(bundle_intents):
        return True, info_sections, intents

    actual_tags = set()
    for section in info_sections:
        actual_tags.update(_llm_quality_token_to_info_tags(section))
    for intent in intents:
        actual_tags.update(_llm_quality_token_to_info_tags(intent))
    return bool(expected_tags & actual_tags), info_sections, intents

def _llm_quality_value_matches(expected, actual):
    if expected is None:
        return True
    if isinstance(expected, (list, tuple, set)):
        return actual in expected
    return actual == expected


def _llm_quality_state_matches_expected(expected_state, state, meta, conv_meta, handover_meta):
    if expected_state is None:
        return True
    if _llm_quality_value_matches(expected_state, state):
        return True
    expected_values = (
        list(expected_state)
        if isinstance(expected_state, (list, tuple, set))
        else [expected_state]
    )
    for candidate in expected_values:
        if not isinstance(candidate, str):
            continue
        if _chaos_state_fallback_ok(candidate, state, meta, conv_meta, handover_meta):
            return True
    return False


def _llm_quality_action_matches_expected(
    expected_action,
    meta,
    conv_meta,
    trace_entries,
    expected_info_sections,
    actual_expected_reply_type,
):
    if not expected_action:
        return True
    expected_actions = (
        list(expected_action)
        if isinstance(expected_action, (list, tuple, set))
        else [expected_action]
    )
    expected_actions = [item for item in expected_actions if isinstance(item, str) and item.strip()]
    if not expected_actions:
        return True
    if _chaos_matches_action(meta, expected_actions):
        return True
    info_sections_ok = True
    if expected_info_sections:
        info_sections_ok, _, _ = _llm_quality_expected_section_answered(
            expected_info_sections, meta, trace_entries
        )
    expected_payload = {
        "action_any": expected_actions,
        "info_sections": expected_info_sections or [],
        "expected_reply_type": actual_expected_reply_type,
    }
    return _chaos_action_fallback_ok(
        expected_payload, meta, conv_meta, trace_entries, info_sections_ok
    )


def _llm_quality_expected_reply_matches(
    *,
    expected_reply,
    expected_response,
    expected_reply_type,
    expected_state,
    state,
    meta,
    conv_meta,
    handover_meta,
    bot_response=False,
):
    if expected_reply is None:
        return True
    if expected_reply == expected_response:
        return True
    if expected_reply is True and expected_response is False:
        action = (meta or {}).get("action")
        pending_action = (meta or {}).get("pending_action")
        tool_decision = _llm_quality_normalize_tool_token((meta or {}).get("tool_decision"))
        intent_value = _llm_quality_normalize_tool_token((meta or {}).get("intent"))
        if state in {"pending", "manager_active"} and (
            action in CHAOS_PENDING_ACTIONS
            or pending_action in CHAOS_PENDING_ACTIONS
            or action
            in {
                "escalate",
                "booking_escalated",
                "booking_captured_pending",
                "booking_reuse_handover",
                "booking_paused",
            }
        ):
            return True
        if (
            state in {"pending", "manager_active"}
            and pending_action == "policy_core_degraded_hold"
            and bot_response
        ):
            return True
        if state in {"pending", "manager_active"} and action in {"booking_prompt", "booking_confirm"}:
            return True
        if (
            state in {"pending", "manager_active"}
            and action == "reply"
            and intent_value
            in {
                "catalog.location",
                "catalog.service_query",
                "hours",
                "parking",
                "duration",
                "discounts",
                "promotions",
                "consult_reply",
            }
            and tool_decision in {"", "ok", "truth_fallback", "duration", "not_found_fallback"}
        ):
            return True
        if (
            state in {"pending", "manager_active"}
            and action == "reply"
            and tool_decision in {"provider_unavailable", "branch_missing"}
            and expected_reply_type in CHAOS_BOOKING_REPLY_TYPES
        ):
            return True
    if expected_state is None:
        return False
    expected_values = (
        list(expected_state)
        if isinstance(expected_state, (list, tuple, set))
        else [expected_state]
    )
    for candidate in expected_values:
        if not isinstance(candidate, str):
            continue
        if _chaos_state_fallback_ok(candidate, state, meta, conv_meta, handover_meta):
            return True
    return False

def _llm_quality_infer_info_tags(text):
    if not text:
        return set()
    tags = set()
    for tag, patterns in LLM_QUALITY_TAG_HINTS_RE.items():
        for pattern in patterns:
            if pattern.search(text):
                tags.add(tag)
                break
    return tags

def _llm_quality_detect_language(text: str | None) -> str:
    if not text:
        return "unknown"
    has_cyrillic = bool(re.search(r"[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүІіҺһ]", text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    has_kk = any(ch in LLM_QUALITY_LANG_KK_CHARS for ch in text)
    if has_kk and has_latin:
        return "mixed"
    if has_kk:
        return "kk"
    if has_cyrillic and has_latin:
        return "mixed"
    if has_cyrillic:
        return "ru"
    if has_latin:
        return "latin"
    return "unknown"

def _llm_quality_is_noise(text: str | None, tags: list[str]) -> bool:
    if tags and "noise" in tags:
        return True
    if not text:
        return False
    return bool(LLM_QUALITY_NOISE_RE.search(text))


def _llm_quality_normalize_tool_token(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _llm_quality_collect_dedup_stats(meta: dict | None, dedup_stats: dict | None) -> None:
    if not isinstance(meta, dict) or not isinstance(dedup_stats, dict):
        return
    backend_counts = dedup_stats.get("backend")
    fallback_reasons = dedup_stats.get("fallback_reasons")
    latency = dedup_stats.get("latency")
    if not isinstance(backend_counts, dict) or not isinstance(fallback_reasons, dict):
        return
    if not isinstance(latency, dict):
        return

    backend = _llm_quality_normalize_tool_token(meta.get("dedup_backend"))
    if backend in {"redis", "db_fallback"}:
        backend_counts[backend] = backend_counts.get(backend, 0) + 1
    else:
        backend_counts["unknown"] = backend_counts.get("unknown", 0) + 1

    fallback_reason = meta.get("dedup_fallback_reason")
    if isinstance(fallback_reason, str):
        normalized_reason = fallback_reason.strip().lower()
        if normalized_reason:
            fallback_reasons[normalized_reason] = fallback_reasons.get(normalized_reason, 0) + 1

    def _add_latency(
        key_total: str,
        key_samples: str,
        raw_value: object | None,
    ) -> None:
        if not isinstance(raw_value, (int, float)):
            return
        value = float(raw_value)
        if value < 0:
            return
        latency[key_total] = float(latency.get(key_total, 0.0)) + value
        latency[key_samples] = int(latency.get(key_samples, 0)) + 1

    _add_latency("total_ms", "samples", meta.get("dedup_latency_ms"))
    _add_latency("redis_total_ms", "redis_samples", meta.get("dedup_redis_latency_ms"))
    _add_latency("db_total_ms", "db_samples", meta.get("dedup_db_latency_ms"))
    _add_latency("messages_total_ms", "messages_samples", meta.get("dedup_messages_latency_ms"))


def _llm_quality_effective_intent(meta: dict | None) -> str:
    if not isinstance(meta, dict):
        return ""
    intent = _llm_quality_normalize_tool_token(meta.get("intent"))
    if intent in {"check_booking", "check_record"}:
        return "calendar.get_booking"
    if intent:
        return intent
    llm_policy_core = meta.get("llm_policy_core")
    if isinstance(llm_policy_core, dict):
        payload = llm_policy_core.get("payload")
        if isinstance(payload, dict):
            tool_action = _llm_quality_normalize_tool_token(payload.get("tool_action"))
            if tool_action:
                return tool_action
    return ""


def _llm_quality_is_timeout_degrade_reason(reason: object | None) -> bool:
    token = _llm_quality_normalize_tool_token(reason)
    if not token:
        return False
    return any(
        marker in token
        for marker in (
            "timeout",
            "timed out",
            "deadline_exceeded",
            "deadline exceeded",
            "llm_timeout",
            "judge_request_timeout",
            "policy_timeout",
            "provider_timeout",
        )
    )


def _llm_quality_is_policy_core_infra_reason(reason: object | None) -> bool:
    token = _llm_quality_normalize_tool_token(reason)
    if not token:
        return False
    return any(
        marker in token
        for marker in (
            "no_api_key",
            "insufficient_quota",
            "rate_limit",
            "invalid_api_key",
            "unauthorized",
            "authentication",
        )
    )


def _llm_quality_tool_outcome_from_decision(decision: object | None) -> str:
    if decision is True:
        return "success"
    if decision is False:
        return "failure"
    token = _llm_quality_normalize_tool_token(decision)
    if token in {"confirmed", "confirm", "accepted", "approved", "yes", "ok", "true"}:
        return "success"
    if token in {"rejected", "declined", "no", "false", "cancelled", "canceled"}:
        return "failure"
    return "pending"


def _llm_quality_calendar_outcome_from_meta(
    *,
    appointment_id,
    appointment_status,
    blocked_reason,
    tool_decision,
):
    if blocked_reason:
        return "failure"
    status_token = _llm_quality_normalize_tool_token(appointment_status)
    decision_token = _llm_quality_normalize_tool_token(tool_decision)
    if appointment_id or status_token in LLM_QUALITY_BOOKING_CONFIRM_STATUS_HINTS:
        return "success"
    if decision_token in LLM_QUALITY_CALENDAR_FAILURE_DECISIONS:
        return "failure"
    if decision_token in LLM_QUALITY_CALENDAR_SUCCESS_DECISIONS:
        return "success"
    if decision_token:
        return "pending"
    return "pending"


def _llm_quality_extract_tool_signals(meta, trace_entries):
    if not isinstance(meta, dict):
        return {}
    action = _llm_quality_normalize_tool_token(meta.get("action"))
    intent = _llm_quality_effective_intent(meta)
    tool_decision = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
    slot_required = bool(meta.get("slot_confirmation_required"))
    slot_decision = meta.get("slot_confirmation_decision")
    appointment_id = meta.get("appointment_id")
    appointment_status = _llm_quality_normalize_tool_token(meta.get("appointment_status"))
    blocked_reason = meta.get("booking_blocked_reason")
    signals = {}
    if slot_required or action == "booking_confirm":
        outcome = _llm_quality_tool_outcome_from_decision(slot_decision)
        signals["confirm"] = {
            "required": slot_required,
            "decision": slot_decision,
            "outcome": outcome,
        }
    elif intent == "calendar.get_booking":
        # Confirmation/status dialogs must exercise confirm-path simulation too.
        signals["confirm"] = {
            "required": True,
            "decision": slot_decision,
            "outcome": _llm_quality_tool_outcome_from_decision(slot_decision),
        }
    if appointment_id:
        outcome = "success"
        if blocked_reason:
            outcome = "failure"
        signals["commit"] = {
            "appointment_id": appointment_id,
            "appointment_status": meta.get("appointment_status"),
            "outcome": outcome,
        }
    if action in {"booking_cancelled", "booking_cancel", "cancel"} or appointment_status in {
        "cancelled",
        "canceled",
    }:
        outcome = "success"
        if blocked_reason:
            outcome = "failure"
        signals["cancel"] = {
            "appointment_status": meta.get("appointment_status"),
            "outcome": outcome,
        }
    if appointment_id or appointment_status or intent in LLM_QUALITY_CALENDAR_INTENTS:
        outcome = _llm_quality_calendar_outcome_from_meta(
            appointment_id=appointment_id,
            appointment_status=meta.get("appointment_status"),
            blocked_reason=blocked_reason,
            tool_decision=tool_decision,
        )
        signals["calendar"] = {
            "appointment_id": appointment_id,
            "appointment_status": meta.get("appointment_status"),
            "intent": meta.get("intent"),
            "tool_decision": meta.get("tool_decision"),
            "outcome": outcome,
        }
    return signals


def _llm_quality_should_send_calendar_hook(tool_signals, turn_tags):
    signal = (tool_signals or {}).get("calendar")
    if not isinstance(signal, dict):
        return False
    if "calendar" in (turn_tags or []):
        return False
    outcome = _llm_quality_normalize_tool_token(signal.get("outcome"))
    if outcome not in {"success", "pending"}:
        return False
    # Slot lookup is an intermediate step and should not trigger
    # synthetic "check booking" messages that derail booking progression.
    intent = _llm_quality_normalize_tool_token(signal.get("intent"))
    if intent == "calendar.list_slots":
        return False
    return True


def _llm_quality_current_turn_trace_entries(meta, trace_entries):
    entries = [entry for entry in (trace_entries or []) if isinstance(entry, dict)]
    if not entries:
        return []
    if not isinstance(meta, dict):
        return entries[-LLM_QUALITY_INFO_TRACE_LOOKBACK:]

    timing = meta.get("timing")
    if not isinstance(timing, dict):
        return entries[-LLM_QUALITY_INFO_TRACE_LOOKBACK:]

    window_start = _parse_iso_datetime(timing.get("pipeline_started_at"))
    window_end = _parse_iso_datetime(timing.get("pipeline_finished_at"))
    if not window_start or not window_end:
        return entries[-LLM_QUALITY_INFO_TRACE_LOOKBACK:]

    if window_end < window_start:
        return entries[-LLM_QUALITY_INFO_TRACE_LOOKBACK:]

    low = window_start - timedelta(seconds=LLM_QUALITY_TRACE_WINDOW_PADDING_SECONDS)
    high = window_end + timedelta(seconds=LLM_QUALITY_TRACE_WINDOW_PADDING_SECONDS)
    bounded = []
    for entry in entries:
        recorded_at = _parse_iso_datetime(entry.get("recorded_at"))
        if recorded_at and low <= recorded_at <= high:
            bounded.append(entry)
    if bounded:
        return bounded
    return []


def _llm_quality_collect_info_signals(meta, trace_entries):
    info_sections = set()
    intents = set()
    if isinstance(meta, dict):
        intent = meta.get("intent")
        if isinstance(intent, str) and intent.strip():
            intents.add(intent.strip().lower())
        fact_intents = meta.get("fact_intents")
        if isinstance(fact_intents, list):
            for item in fact_intents:
                if isinstance(item, str) and item.strip():
                    intents.add(item.strip().lower())
        sections = meta.get("info_sections")
        if isinstance(sections, list):
            for section in sections:
                if isinstance(section, str) and section.strip():
                    info_sections.add(section.strip().lower())
        llm_policy_core = meta.get("llm_policy_core")
        llm_payload = llm_policy_core.get("payload") if isinstance(llm_policy_core, dict) else None
        pack_refs = llm_payload.get("pack_refs") if isinstance(llm_payload, dict) else None
        if isinstance(pack_refs, list):
            for ref in pack_refs:
                if isinstance(ref, str) and ref.strip():
                    token = ref.strip().lower()
                    intents.add(token)
                    info_sections.add(token)
    for entry in _llm_quality_current_turn_trace_entries(meta, trace_entries):
        if not isinstance(entry, dict):
            continue
        intent = entry.get("intent")
        if isinstance(intent, str) and intent.strip():
            intents.add(intent.strip().lower())
        entry_intents = entry.get("info_intents")
        if isinstance(entry_intents, list):
            for item in entry_intents:
                if isinstance(item, str) and item.strip():
                    intents.add(item.strip().lower())
        fact_intents = entry.get("fact_intents")
        if isinstance(fact_intents, list):
            for item in fact_intents:
                if isinstance(item, str) and item.strip():
                    intents.add(item.strip().lower())
        sections = entry.get("info_sections")
        if isinstance(sections, list):
            for section in sections:
                if isinstance(section, str) and section.strip():
                    info_sections.add(section.strip().lower())
    return info_sections, intents


def _llm_quality_is_booking_confirmation_text(text):
    if not isinstance(text, str):
        return False
    normalized = text.strip().lower()
    if not normalized:
        return False
    if "?" in normalized:
        return False
    for phrase in LLM_QUALITY_BOOKING_CONFIRM_PHRASES:
        if phrase in normalized:
            return True
    return False


def _llm_quality_info_answered(info_tags, meta, trace_entries):
    info_sections, intents = _llm_quality_collect_info_signals(meta, trace_entries)
    answered = {}
    bundle_hit = bool(intents.intersection(LLM_QUALITY_BUNDLE_INTENTS))
    for tag in info_tags:
        tokens = LLM_QUALITY_INFO_SECTION_MAP.get(tag, {tag})
        matched = bool(tokens & info_sections or tokens & intents)
        if not matched and bundle_hit:
            matched = True
        answered[tag] = matched
    return answered, info_sections, intents


def _llm_quality_has_general_consult_fallback(meta, trace_entries):
    info_sections, intents = _llm_quality_collect_info_signals(meta, trace_entries)
    if "general_consult" not in info_sections:
        return False
    intent_value = ""
    if isinstance(meta, dict):
        raw_intent = meta.get("intent")
        if isinstance(raw_intent, str):
            intent_value = raw_intent.strip().lower()
    if intent_value in {"consult_reply", "service_clarify", "duration_or_price_clarify"}:
        return True
    if "consult_reply" in intents:
        return True
    return False


def _llm_quality_expected_response(state, meta):
    action = (meta or {}).get("action") if isinstance(meta, dict) else None
    pending_action = (meta or {}).get("pending_action") if isinstance(meta, dict) else None
    if state == "manager_active":
        return False, "manager_active"
    if state == "pending":
        return False, "pending_state"
    if action in CHAOS_PENDING_ACTIONS or pending_action in CHAOS_PENDING_ACTIONS:
        return False, "pending_action"
    return True, None


def _llm_quality_is_expected_reply_blocked(meta: dict | None) -> bool:
    if not isinstance(meta, dict):
        return False
    if meta.get("expected_reply_blocked_by_info") is not True:
        return False
    if meta.get("expected_reply_matched") is True:
        return False
    return not _llm_quality_normalize_tool_token(meta.get("expected_reply_bypassed"))


def _llm_quality_is_expected_reply_deferred(meta: dict | None) -> bool:
    if not isinstance(meta, dict):
        return False
    controller_skip_reason = _llm_quality_normalize_tool_token(meta.get("controller_skipped_reason"))
    router_skip_reason = _llm_quality_normalize_tool_token(meta.get("router_skipped_reason"))
    if "expected_reply_deferred" in {controller_skip_reason, router_skip_reason}:
        return True
    return _llm_quality_is_expected_reply_blocked(meta) and meta.get("controller_attempted") is not True


def _llm_quality_should_judge_turn(
    *,
    judge_enabled,
    judge_mode,
    state,
    bot_response,
    user_text,
    turn_tags=None,
    expected_action=None,
    expected_reply_type=None,
    expected_state=None,
    expected_info_sections=None,
    info_tags=None,
    booking_active=False,
    booking_progress_expected=False,
    evaluation_reasons=None,
):
    if not judge_enabled:
        return False, None
    tags = {str(tag).strip().lower() for tag in (turn_tags or []) if str(tag).strip()}
    if tags.intersection({"interrupt", "channel"}):
        return False, "tag_skip"
    if not bot_response:
        return False, "no_bot_response"
    if not isinstance(user_text, str) or not user_text.strip():
        return False, "missing_user_text"
    if state in {"pending", "manager_active"}:
        return False, "pending_state"
    if judge_mode == "critical":
        critical = bool(evaluation_reasons)
        if expected_action or expected_reply_type or expected_state:
            critical = True
        if expected_info_sections or info_tags:
            critical = True
        if booking_active and booking_progress_expected:
            critical = True
        if tags.intersection(LLM_QUALITY_JUDGE_CRITICAL_TAGS):
            critical = True
        if not critical:
            return False, "critical_skip"
    return True, None


def _llm_quality_expected_manager_state(action, state_before):
    if action == "take":
        # "take" is race-prone in simulation: state can flip to bot_active
        # almost immediately if resolve callback arrives in the same window.
        # Do not assert state/status on take.
        return None, None
    if action == "resolve":
        return "bot_active", "resolved"
    if action == "return":
        return "bot_active", "bot_handling"
    if action == "skip":
        return state_before, None
    return None, None

def _llm_quality_normalize_outbox_status(status):
    if not isinstance(status, str):
        return ""
    return status.strip().upper()

def _llm_quality_resolve_outbox_status(outbox_payload_status, outbox_summary):
    status = _llm_quality_normalize_outbox_status(outbox_payload_status)
    if status:
        return status
    if isinstance(outbox_summary, dict):
        return _llm_quality_normalize_outbox_status(outbox_summary.get("status"))
    return ""

def _llm_quality_outbox_delivery_state(outbox_payload_status, outbox_summary):
    status = _llm_quality_resolve_outbox_status(outbox_payload_status, outbox_summary)
    if status in LLM_QUALITY_OUTBOX_SUCCESS_STATUSES:
        return "sent"
    if status in LLM_QUALITY_OUTBOX_FAILURE_STATUSES:
        return "failed"
    if status in LLM_QUALITY_OUTBOX_PENDING_STATUSES:
        return "pending"
    count = (outbox_summary or {}).get("count") if isinstance(outbox_summary, dict) else 0
    if isinstance(count, int) and count > 0:
        return "unknown"
    return "missing"

def _llm_quality_has_bot_reply(
    *,
    outbox_summary,
    outbox_payload_status,
    outbox_text,
    inline_response_text,
):
    if isinstance(inline_response_text, str) and inline_response_text.strip():
        return True
    delivery_state = _llm_quality_outbox_delivery_state(outbox_payload_status, outbox_summary)
    if delivery_state == "sent":
        return True
    if delivery_state == "unknown":
        return bool((outbox_text or "").strip())
    return False


def _llm_quality_is_unobserved_turn(
    *,
    expected_response,
    outbox_text,
    outbox_payload_status,
    outbox_summary,
    bot_response_inferred_duplicate_ack,
    meta,
):
    if not expected_response:
        return False
    if isinstance(outbox_text, str) and outbox_text.strip():
        return False

    delivery_state = _llm_quality_outbox_delivery_state(outbox_payload_status, outbox_summary)
    if delivery_state == "failed":
        return False
    transport_unknown = delivery_state in {"pending", "unknown"}

    reply_observed = None
    transport_status = ""
    if isinstance(meta, dict):
        turn_outcome = meta.get("turn_outcome")
        if isinstance(turn_outcome, dict):
            observability = turn_outcome.get("observability")
            if isinstance(observability, dict):
                reply_observed = observability.get("reply_observed")
                transport_status = _llm_quality_normalize_tool_token(
                    observability.get("transport_status")
                ) or ""
    if reply_observed is True:
        return False

    turn_outcome_unknown = transport_status in {"pending", "unknown", "duplicate"}
    if bot_response_inferred_duplicate_ack:
        return True
    return transport_unknown or turn_outcome_unknown


def _llm_quality_extract_outbox_text(payload):
    if not isinstance(payload, dict):
        return None
    body = payload.get("body")
    if isinstance(body, dict):
        for key in ("message", "text", "caption"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("message", "text", "caption"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def _llm_quality_fetch_outbox_payload(db_user, client_id, inbound_message_id):
    if not client_id or not inbound_message_id:
        return None, None, None
    safe_client = _escape_sql_literal(client_id)
    safe_id = _escape_sql_literal(inbound_message_id)
    query = (
        "SELECT payload_json::text, status "
        "FROM outbox_messages "
        f"WHERE client_id = '{safe_client}' AND inbound_message_id = '{safe_id}' "
        "ORDER BY created_at DESC LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, None, error
    if not row:
        return None, None, None
    parts = row.split("\t", 1)
    payload = None
    if parts and parts[0]:
        try:
            payload = json.loads(parts[0])
        except Exception:
            payload = None
    status = parts[1] if len(parts) > 1 else None
    return payload, status, None

def _normalize_scenario_generation_error(stderr):
    text = (stderr or "").strip()
    if not text:
        return "scenario generation failed"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    last_progress = None
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("stage") != "booking_scenario_llm_progress":
            continue
        batch_idx = payload.get("batch_index")
        attempt = payload.get("attempt")
        event = payload.get("event")
        if batch_idx is None and attempt is None and event is None:
            continue
        last_progress = (
            f"batch={batch_idx if batch_idx is not None else '?'} "
            f"attempt={attempt if attempt is not None else '?'} "
            f"event={event if event is not None else '?'}"
        )
        break
    for line in reversed(lines):
        marker = "RuntimeError:"
        idx = line.find(marker)
        if idx >= 0:
            return line[idx + len(marker) :].strip()
    lower = text.lower()
    if "http error 429" in lower or "insufficient_quota" in lower:
        return "openai_rate_or_quota_limited: provider returned HTTP 429"
    if "http error 401" in lower:
        return "openai_auth_failed: provider returned HTTP 401"
    if "http error 403" in lower:
        return "openai_forbidden: provider returned HTTP 403"
    if "openai_api_key is required" in lower:
        return "missing_openai_api_key"
    if "timed out" in lower or "timeout" in lower:
        if last_progress:
            return f"scenario_generation_timeout ({last_progress})"
        return "scenario_generation_timeout"
    tail = lines[-1] if lines else text
    return tail[:500]

def _llm_quality_scenario_timeout(args, *, count):
    configured = getattr(args, "scenario_gen_timeout", None)
    if configured is not None:
        try:
            base_timeout = max(10.0, float(configured))
        except Exception:
            base_timeout = None
    else:
        base_timeout = None
    if base_timeout is None:
        try:
            base_timeout = max(10.0, float(os.getenv("DIAGNOSE_SCENARIO_GEN_TIMEOUT_SEC", "180")))
        except Exception:
            base_timeout = 180.0
    if getattr(args, "mode", None) != "llm":
        return base_timeout
    llm_batch_size = max(1, int(getattr(args, "scenario_llm_batch_size", 2)))
    llm_max_attempts = max(1, int(getattr(args, "scenario_llm_max_attempts", 1)))
    llm_request_timeout = max(5.0, float(getattr(args, "scenario_llm_request_timeout", 40.0)))
    estimated_calls = int(math.ceil(max(1, int(count)) / float(llm_batch_size)))
    estimated_budget = (estimated_calls * llm_max_attempts * llm_request_timeout) + 25.0
    return max(base_timeout, estimated_budget)


def _llm_quality_generate_batch(args, *, count, seed):
    scenario_timeout = _llm_quality_scenario_timeout(args, count=count)
    script_path = _llm_quality_dialog_script()
    cmd = [
        sys.executable,
        script_path,
        "--count",
        str(count),
        "--min-turns",
        str(args.min_turns),
        "--max-turns",
        str(args.max_turns),
        "--output",
        "-",
        "--mode",
        args.mode,
        "--media-mode",
        args.media_mode,
        "--media-kind",
        args.media_kind,
    ]
    if args.scenario_coverage and str(args.scenario_coverage).strip().lower() not in {"none", "off"}:
        cmd += ["--coverage", str(args.scenario_coverage)]
    if args.include_media:
        cmd.append("--include-media")
    if seed is not None:
        cmd += ["--seed", str(seed)]
    if args.mode == "llm":
        if args.llm_model:
            cmd += ["--llm-model", args.llm_model]
        if args.llm_base_url:
            cmd += ["--llm-base-url", args.llm_base_url]
        if getattr(args, "scenario_llm_batch_size", None):
            cmd += ["--llm-batch-size", str(args.scenario_llm_batch_size)]
        if getattr(args, "scenario_llm_max_attempts", None):
            cmd += ["--llm-max-attempts", str(args.scenario_llm_max_attempts)]
        if getattr(args, "scenario_llm_request_timeout", None):
            cmd += ["--llm-request-timeout", str(args.scenario_llm_request_timeout)]
        if getattr(args, "scenario_llm_attempt_backoff", None):
            cmd += ["--llm-attempt-backoff", str(args.scenario_llm_attempt_backoff)]
        if getattr(args, "scenario_progress_stderr", False):
            cmd.append("--progress-stderr")
    child_env = {}
    if args.mode == "llm" and args.llm_api_key:
        # Keep API keys out of command args and timeout logs.
        child_env["OPENAI_API_KEY"] = str(args.llm_api_key)
    result = run_command(cmd, timeout=scenario_timeout, env=child_env or None)
    if result.returncode != 0:
        return None, None, _normalize_scenario_generation_error(result.stderr or "")
    try:
        payload = json.loads(result.stdout or "")
    except Exception as exc:
        return None, None, f"scenario json parse failed: {exc}"
    dialogs = payload.get("dialogs") or []
    warnings = payload.get("warnings") or {}
    if not isinstance(dialogs, list):
        return None, None, "scenario output missing dialogs"
    return dialogs, warnings, None


def _llm_quality_load_dialogs_from_file(path):
    file_path = os.path.abspath(os.path.expanduser(path or ""))
    if not file_path:
        return None, None, "scenario file path is empty"
    if not os.path.exists(file_path):
        return None, None, f"scenario file not found: {file_path}"
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        return None, None, f"scenario file parse failed: {exc}"

    warnings = {}
    dialogs = None
    if isinstance(payload, dict):
        dialogs = payload.get("dialogs")
        raw_warnings = payload.get("warnings")
        if isinstance(raw_warnings, dict):
            warnings = dict(raw_warnings)
    elif isinstance(payload, list):
        dialogs = payload
    else:
        return None, None, "scenario file must contain object with dialogs or dialogs list"

    if not isinstance(dialogs, list) or not dialogs:
        return None, None, "scenario file has no dialogs"

    normalized = []
    dropped = 0
    for dialog in dialogs:
        if not isinstance(dialog, dict):
            dropped += 1
            continue
        turns = dialog.get("turns")
        if not isinstance(turns, list) or not turns:
            dropped += 1
            continue
        normalized.append(dialog)
    if not normalized:
        return None, None, "scenario file has no valid dialogs with turns"
    if dropped:
        warnings["scenario_file"] = [f"dropped_invalid_dialogs={dropped}"]
    return normalized, warnings, None


def _llm_quality_top_failure_reasons(failure_counts, limit=3):
    if not isinstance(failure_counts, dict) or limit <= 0:
        return []
    rows = []
    for reason, count in failure_counts.items():
        try:
            count_value = int(count)
        except Exception:
            continue
        rows.append((str(reason), count_value))
    rows.sort(key=lambda item: (-item[1], item[0]))
    top = []
    for reason, count in rows[:limit]:
        top.append(
            {
                "reason": reason,
                "count": count,
                "label": LLM_QUALITY_REASON_LABELS.get(reason, reason),
                "category": LLM_QUALITY_REASON_TAXONOMY.get(reason, "unknown"),
            }
        )
    return top


def _llm_quality_top_failure_turns(failures, *, limit=3, sample_limit=3):
    if not isinstance(failures, list) or limit <= 0:
        return []
    rows = {}
    for record in failures:
        if not isinstance(record, dict):
            continue
        reasons = record.get("reasons")
        if not isinstance(reasons, list):
            continue
        for reason in reasons:
            reason_token = str(reason).strip()
            if not reason_token:
                continue
            row = rows.setdefault(
                reason_token,
                {
                    "reason": reason_token,
                    "count": 0,
                    "label": LLM_QUALITY_REASON_LABELS.get(reason_token, reason_token),
                    "category": LLM_QUALITY_REASON_TAXONOMY.get(reason_token, "unknown"),
                    "sample_turns": [],
                },
            )
            row["count"] += 1
            if len(row["sample_turns"]) >= max(1, int(sample_limit)):
                continue
            row["sample_turns"].append(
                {
                    "message_id": record.get("message_id"),
                    "dialog_id": record.get("dialog_id"),
                    "dialog_index": record.get("dialog_index"),
                    "turn_index": record.get("turn_index"),
                    "conversation_id": record.get("conversation_id"),
                }
            )
    ordered = sorted(rows.values(), key=lambda item: (-int(item.get("count") or 0), item.get("reason")))
    return ordered[:limit]


def _llm_quality_collect_override_reason_codes(meta):
    if not isinstance(meta, dict):
        return []
    raw_codes = []
    primary = meta.get("llm_policy_override_reason_code")
    if isinstance(primary, str) and primary.strip():
        raw_codes.append(primary.strip().casefold())
    extras = meta.get("llm_policy_override_reason_codes")
    if isinstance(extras, str):
        extras = [item.strip() for item in extras.split(",") if item.strip()]
    if isinstance(extras, list):
        for item in extras:
            if isinstance(item, str) and item.strip():
                raw_codes.append(item.strip().casefold())
    return list(dict.fromkeys(raw_codes))


def _llm_quality_init_rewrite_governance_state():
    return {
        "turns_seen": 0,
        "policy_core_turns": 0,
        "rewrite_turns": 0,
        "rewrite_with_reason_turns": 0,
        "rewrite_reason_missing_turns": 0,
        "rewrite_unknown_reason_turns": 0,
        "keyword_override_turns": 0,
        "reason_counts": {},
    }


def _llm_quality_track_rewrite_governance(state, meta):
    if not isinstance(state, dict):
        return
    state["turns_seen"] = int(state.get("turns_seen", 0) or 0) + 1
    if not isinstance(meta, dict):
        return
    policy_core_mode = str(meta.get("policy_core_mode") or "").strip()
    if policy_core_mode in {"policy_core", "degraded_fallback"}:
        state["policy_core_turns"] = int(state.get("policy_core_turns", 0) or 0) + 1

    reason_codes = _llm_quality_collect_override_reason_codes(meta)
    missing_reason = bool(meta.get("llm_policy_override_reason_missing")) or bool(
        meta.get("llm_policy_override_reason_missing_detected")
    )
    rewrite_turn = bool(reason_codes) or missing_reason
    if not rewrite_turn:
        return

    state["rewrite_turns"] = int(state.get("rewrite_turns", 0) or 0) + 1
    if missing_reason:
        state["rewrite_reason_missing_turns"] = int(
            state.get("rewrite_reason_missing_turns", 0) or 0
        ) + 1

    unknown_reason = False
    keyword_override = False
    reason_counts = state.setdefault("reason_counts", {})
    for code in reason_codes:
        reason_counts[code] = int(reason_counts.get(code, 0) or 0) + 1
        if code not in LLM_POLICY_OVERRIDE_REASON_WHITELIST:
            unknown_reason = True
        if code in LLM_POLICY_OVERRIDE_KEYWORD_REASON_CODES:
            keyword_override = True

    if unknown_reason:
        state["rewrite_unknown_reason_turns"] = int(
            state.get("rewrite_unknown_reason_turns", 0) or 0
        ) + 1
    if keyword_override:
        state["keyword_override_turns"] = int(state.get("keyword_override_turns", 0) or 0) + 1
    if reason_codes and not unknown_reason and not missing_reason:
        state["rewrite_with_reason_turns"] = int(state.get("rewrite_with_reason_turns", 0) or 0) + 1


def _llm_quality_finalize_rewrite_governance(
    state,
    *,
    max_post_llm_semantic_rewrite_rate,
    max_keyword_override_rate,
):
    state = state if isinstance(state, dict) else {}
    turns_seen = int(state.get("turns_seen", 0) or 0)
    policy_core_turns = int(state.get("policy_core_turns", 0) or 0)
    rewrite_turns = int(state.get("rewrite_turns", 0) or 0)
    rewrite_with_reason_turns = int(state.get("rewrite_with_reason_turns", 0) or 0)
    rewrite_reason_missing_turns = int(state.get("rewrite_reason_missing_turns", 0) or 0)
    rewrite_unknown_reason_turns = int(state.get("rewrite_unknown_reason_turns", 0) or 0)
    keyword_override_turns = int(state.get("keyword_override_turns", 0) or 0)
    denominator = max(policy_core_turns or turns_seen, 1)
    rewrite_rate = round(rewrite_turns / denominator, 4)
    keyword_override_rate = round(keyword_override_turns / denominator, 4)
    if max_post_llm_semantic_rewrite_rate <= 0:
        max_rewrite_turns = 0
    else:
        # Rewrite budget is discrete per turn; use ceiling to avoid false blocks
        # when ratio budget lands between integer turn counts.
        budget_raw = float(max_post_llm_semantic_rewrite_rate) * float(denominator)
        max_rewrite_turns = int(budget_raw)
        if budget_raw - float(max_rewrite_turns) > 1e-9:
            max_rewrite_turns += 1
    rewrite_reason_coverage = (
        1.0 if rewrite_turns == 0 else round(rewrite_with_reason_turns / max(rewrite_turns, 1), 4)
    )

    blocking_counts = {}
    reasons = []
    if rewrite_turns > max_rewrite_turns:
        blocking_counts["post_llm_semantic_rewrite_budget_exceeded"] = rewrite_turns
        reasons.append("post_llm_semantic_rewrite_budget_exceeded")
    if keyword_override_rate > max_keyword_override_rate:
        blocking_counts["keyword_override_budget_exceeded"] = keyword_override_turns
        reasons.append("keyword_override_budget_exceeded")
    if rewrite_reason_missing_turns > 0:
        blocking_counts["rewrite_reason_missing"] = rewrite_reason_missing_turns
        reasons.append("rewrite_reason_missing")
    if rewrite_unknown_reason_turns > 0:
        blocking_counts["rewrite_reason_unknown"] = rewrite_unknown_reason_turns
        reasons.append("rewrite_reason_unknown")

    return {
        "valid": not reasons,
        "reasons": reasons,
        "blocking_counts": blocking_counts,
        "turns_seen": turns_seen,
        "policy_core_turns": policy_core_turns,
        "rewrite_turns": rewrite_turns,
        "rewrite_with_reason_turns": rewrite_with_reason_turns,
        "rewrite_reason_missing_turns": rewrite_reason_missing_turns,
        "rewrite_unknown_reason_turns": rewrite_unknown_reason_turns,
        "keyword_override_turns": keyword_override_turns,
        "post_llm_semantic_rewrite_rate": rewrite_rate,
        "keyword_override_rate": keyword_override_rate,
        "rewrite_reason_coverage": rewrite_reason_coverage,
        "max_rewrite_turns": max_rewrite_turns,
        "max_post_llm_semantic_rewrite_rate": max_post_llm_semantic_rewrite_rate,
        "max_keyword_override_rate": max_keyword_override_rate,
        "allowed_reason_codes": sorted(LLM_POLICY_OVERRIDE_REASON_WHITELIST),
        "reason_counts": state.get("reason_counts", {}),
    }


def _llm_quality_collect_git_changed_files(repo_root, base_ref):
    changed = set()
    scan_warnings = []
    commands = [
        (
            [
                "git",
                "-C",
                repo_root,
                "diff",
                "--name-only",
                "--diff-filter=ACMR",
                f"{base_ref}...HEAD",
            ],
            "base_diff",
        ),
        (["git", "-C", repo_root, "diff", "--name-only", "--diff-filter=ACMR"], "worktree_diff"),
        (
            ["git", "-C", repo_root, "diff", "--name-only", "--cached", "--diff-filter=ACMR"],
            "staged_diff",
        ),
    ]
    for cmd, label in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as exc:
            scan_warnings.append(f"{label}_exec_error:{exc.__class__.__name__}")
            continue
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                scan_warnings.append(f"{label}_error:{stderr[:120]}")
            else:
                scan_warnings.append(f"{label}_error:rc{result.returncode}")
            continue
        for line in (result.stdout or "").splitlines():
            path = line.strip()
            if path:
                changed.add(path)
    return sorted(changed), scan_warnings


def _llm_quality_is_lexicon_regex_delta_file(path):
    normalized = str(path or "").strip().replace("\\", "/").casefold()
    if not normalized:
        return False
    if not normalized.startswith("truffles-api/"):
        return False
    basename = os.path.basename(normalized)
    if basename == "system_lexicons.yaml":
        return True
    return any(token in normalized for token in LLM_QUALITY_REGEX_LEXICON_TOKENS)


def _llm_quality_build_lexicon_regex_delta_status(
    *,
    mode,
    repo_root,
    base_ref,
    changed_files=None,
):
    mode = str(mode or "off").strip().casefold()
    if mode == "off":
        return {
            "mode": mode,
            "valid": True,
            "enforced": False,
            "reasons": [],
            "scan_warnings": [],
            "changed_files": 0,
            "lexicon_regex_delta_files": [],
            "resolver_delta_detected": False,
            "test_delta_detected": False,
        }

    scan_warnings = []
    if changed_files is None:
        changed_files, scan_warnings = _llm_quality_collect_git_changed_files(
            repo_root, base_ref
        )
    normalized_files = sorted({str(path or "").strip().replace("\\", "/") for path in changed_files or []})
    lexicon_regex_delta_files = [
        path for path in normalized_files if _llm_quality_is_lexicon_regex_delta_file(path)
    ]
    resolver_delta = any(
        any(path.startswith(prefix) for prefix in LLM_QUALITY_REGEX_LEXICON_RESOLVER_PREFIXES)
        for path in normalized_files
    )
    test_delta = any(
        path.startswith(LLM_QUALITY_REGEX_LEXICON_TEST_PREFIX) and path.endswith(".py")
        for path in normalized_files
    )
    reasons = []
    if lexicon_regex_delta_files:
        if not resolver_delta:
            reasons.append("resolver_delta_missing")
        if not test_delta:
            reasons.append("contract_test_delta_missing")
    enforced = mode == "block"
    valid = not reasons if enforced else True
    return {
        "mode": mode,
        "valid": valid,
        "enforced": enforced,
        "reasons": reasons,
        "scan_warnings": scan_warnings,
        "changed_files": len(normalized_files),
        "lexicon_regex_delta_files": lexicon_regex_delta_files,
        "resolver_delta_detected": resolver_delta,
        "test_delta_detected": test_delta,
    }


def _llm_quality_is_hardcode_core_file(path):
    normalized = str(path or "").strip().replace("\\", "/")
    if not normalized:
        return False
    return normalized in LLM_QUALITY_HARDCODE_CORE_PREFIXES


def _llm_quality_line_has_phrase_branching(line):
    if not isinstance(line, str):
        return False
    stripped = line.strip()
    if not stripped:
        return False
    lowered = stripped.casefold()
    if lowered.startswith("#"):
        return False
    if LLM_QUALITY_HARDCODE_ALLOW_MARKER in lowered:
        return False
    if any(
        token in lowered
        for token in (
            "get_signal_lexicon_list(",
            "get_system_lexicon_list(",
            "phrase_match_intent(",
            "has_walkin_without_booking_signal(",
        )
    ):
        return False
    has_context_token = any(
        token in lowered
        for token in (
            "message_text",
            "normalized",
            "normalize_for_matching",
            "_normalize_text",
        )
    )
    if not has_context_token:
        return False
    has_branch_operator = any(
        token in lowered
        for token in (
            " in ",
            ".startswith(",
            ".endswith(",
            "re.search(",
            "re.match(",
        )
    )
    if not has_branch_operator:
        return False
    literals = []
    for match in re.finditer(r'"([^"\\]{3,}|[^"\\]{2,}\s[^"\\]*)"|\'([^\'\\]{3,}|[^\'\\]{2,}\s[^\'\\]*)\'', stripped):
        literal = match.group(1) or match.group(2)
        if not isinstance(literal, str):
            continue
        literal = literal.strip()
        if not literal:
            continue
        literals.append(literal)
    if not literals:
        return False
    for literal in literals:
        # Ignore enum-like contract tokens (service_choice/time/name/etc.);
        # gate focuses on natural-language phrase branching in core code.
        if re.fullmatch(r"[a-z_][a-z0-9_]{1,63}", literal.strip().casefold()):
            continue
        letters = sum(1 for ch in literal if ch.isalpha())
        if letters >= 3:
            return True
    return False


def _llm_quality_collect_hardcode_core_violations(
    *,
    repo_root,
    base_ref,
    core_files,
):
    violations = []
    scan_warnings = []
    if not core_files:
        return violations, scan_warnings

    command_specs = [
        (
            [
                "git",
                "-C",
                repo_root,
                "diff",
                "--unified=0",
                f"{base_ref}...HEAD",
                "--",
            ],
            "base_diff",
        ),
        (["git", "-C", repo_root, "diff", "--unified=0", "--"], "worktree_diff"),
        (
            ["git", "-C", repo_root, "diff", "--unified=0", "--cached", "--"],
            "staged_diff",
        ),
    ]

    for command_prefix, source in command_specs:
        cmd = [*command_prefix, *core_files]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as exc:
            scan_warnings.append(f"{source}_exec_error:{exc.__class__.__name__}")
            continue
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if stderr:
                scan_warnings.append(f"{source}_error:{stderr[:120]}")
            else:
                scan_warnings.append(f"{source}_error:rc{result.returncode}")
            continue
        current_file = None
        for raw_line in (result.stdout or "").splitlines():
            if raw_line.startswith("+++ b/"):
                current_file = raw_line.replace("+++ b/", "", 1).strip()
                continue
            if not raw_line.startswith("+") or raw_line.startswith("+++"):
                continue
            content = raw_line[1:]
            if not _llm_quality_line_has_phrase_branching(content):
                continue
            violations.append(
                {
                    "path": current_file,
                    "source": source,
                    "line": content.strip(),
                }
            )
    deduped = {}
    for item in violations:
        key = (
            str(item.get("path") or "").strip(),
            str(item.get("line") or "").strip(),
        )
        if key in deduped:
            continue
        deduped[key] = item
    return list(deduped.values()), scan_warnings


def _llm_quality_build_hardcode_core_gate_status(
    *,
    mode,
    repo_root,
    base_ref,
    changed_files=None,
):
    mode = str(mode or "off").strip().casefold()
    if mode == "off":
        return {
            "mode": mode,
            "valid": True,
            "enforced": False,
            "reasons": [],
            "scan_warnings": [],
            "changed_files": [],
            "core_changed_files": [],
            "violations": [],
        }

    scan_warnings = []
    if changed_files is None:
        changed_files, scan_warnings = _llm_quality_collect_git_changed_files(
            repo_root, base_ref
        )
    normalized_files = sorted(
        {
            str(path or "").strip().replace("\\", "/")
            for path in (changed_files or [])
            if str(path or "").strip()
        }
    )
    core_changed_files = [path for path in normalized_files if _llm_quality_is_hardcode_core_file(path)]
    violations, scan_warnings_extra = _llm_quality_collect_hardcode_core_violations(
        repo_root=repo_root,
        base_ref=base_ref,
        core_files=core_changed_files,
    )
    scan_warnings.extend(scan_warnings_extra)
    reasons = []
    if violations:
        reasons.append("core_phrase_branching_detected")
    enforced = mode == "block"
    valid = not reasons if enforced else True
    return {
        "mode": mode,
        "valid": valid,
        "enforced": enforced,
        "reasons": reasons,
        "scan_warnings": scan_warnings,
        "changed_files": normalized_files,
        "core_changed_files": core_changed_files,
        "violations": violations[:20],
    }


def _llm_quality_is_doc_only_changed_file(path):
    normalized = str(path or "").strip().replace("\\", "/")
    if not normalized:
        return False
    if normalized.startswith("docs/"):
        return True
    return normalized in {"STATE.md", "STRUCTURE.md", "AGENTS.md"}


def _llm_quality_build_run_economy_status(
    *,
    mode,
    repo_root,
    base_ref,
    scenarios_file,
    baseline_summary,
    reset_before_dialog,
    allow_no_code_delta,
    jid_mode=None,
    runtime_commit=None,
    judge_mode=None,
    previous_replay_fingerprint=None,
    changed_files=None,
    baseline_preflight=None,
):
    mode = str(mode or "off").strip().casefold()
    if mode not in {"off", "warn", "block"}:
        mode = "block"
    if mode == "off":
        return {
            "mode": mode,
            "valid": True,
            "enforced": False,
            "reasons": [],
            "scan_warnings": [],
            "changed_files": [],
            "non_doc_changed_files": [],
            "is_replay": bool(scenarios_file),
            "jid_mode": str(jid_mode or "").strip().casefold() or None,
            "code_fingerprint": None,
            "scenario_fingerprint": None,
            "baseline_fingerprint": None,
            "replay_fingerprint": None,
            "previous_replay_fingerprint": (
                str(previous_replay_fingerprint).strip()
                if isinstance(previous_replay_fingerprint, str)
                and str(previous_replay_fingerprint).strip()
                else None
            ),
            "baseline_checked": bool(
                isinstance(baseline_preflight, dict) and baseline_preflight.get("checked")
            ),
            "baseline_canonical": (
                baseline_preflight.get("canonical")
                if isinstance(baseline_preflight, dict)
                else None
            ),
            "baseline_canonical_reason": (
                baseline_preflight.get("canonical_reason")
                if isinstance(baseline_preflight, dict)
                else None
            ),
            "baseline_load_error": (
                baseline_preflight.get("load_error")
                if isinstance(baseline_preflight, dict)
                else None
            ),
        }

    scan_warnings = []
    if changed_files is None:
        changed_files, scan_warnings = _llm_quality_collect_git_changed_files(
            repo_root, base_ref
        )
    normalized_files = sorted(
        {
            str(path or "").strip().replace("\\", "/")
            for path in (changed_files or [])
            if str(path or "").strip()
        }
    )
    non_doc_files = [
        path for path in normalized_files if not _llm_quality_is_doc_only_changed_file(path)
    ]
    is_replay = bool(scenarios_file)
    jid_mode_token = str(jid_mode or "").strip().casefold()
    reasons = []

    def _digest_file(path):
        if not isinstance(path, str) or not path.strip():
            return None
        normalized = os.path.abspath(os.path.expanduser(path.strip()))
        if not os.path.exists(normalized) or not os.path.isfile(normalized):
            return None
        digest = hashlib.sha256()
        with open(normalized, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    code_entries = []
    for path in non_doc_files:
        normalized_path = str(path or "").strip().replace("\\", "/")
        abs_path = os.path.abspath(os.path.join(repo_root, normalized_path))
        file_digest = _digest_file(abs_path)
        code_entries.append(f"{normalized_path}:{file_digest or 'missing'}")
    code_fingerprint = None
    if code_entries:
        code_fingerprint = hashlib.sha256("\n".join(sorted(code_entries)).encode("utf-8")).hexdigest()

    scenario_fingerprint = None
    if is_replay:
        scenario_digest = _digest_file(str(scenarios_file))
        scenario_token = scenario_digest or os.path.abspath(os.path.expanduser(str(scenarios_file)))
        scenario_fingerprint = hashlib.sha256(str(scenario_token).encode("utf-8")).hexdigest()

    baseline_fingerprint = None
    if is_replay and baseline_summary:
        baseline_digest = _digest_file(str(baseline_summary))
        baseline_token = baseline_digest or os.path.abspath(os.path.expanduser(str(baseline_summary)))
        baseline_fingerprint = hashlib.sha256(str(baseline_token).encode("utf-8")).hexdigest()

    replay_fingerprint = None
    if is_replay:
        replay_parts = [
            f"scenario:{scenario_fingerprint or 'none'}",
            f"baseline:{baseline_fingerprint or 'none'}",
            f"code:{code_fingerprint or 'none'}",
            f"runtime:{str(runtime_commit or '').strip().casefold() or 'none'}",
            f"judge:{str(judge_mode or '').strip().casefold() or 'none'}",
            f"jid_mode:{jid_mode_token or 'none'}",
            f"reset_before_dialog:{bool(reset_before_dialog)}",
        ]
        replay_fingerprint = hashlib.sha256("|".join(replay_parts).encode("utf-8")).hexdigest()

    previous_replay_fingerprint_clean = (
        str(previous_replay_fingerprint).strip()
        if isinstance(previous_replay_fingerprint, str) and str(previous_replay_fingerprint).strip()
        else None
    )
    baseline_checked = bool(
        isinstance(baseline_preflight, dict) and baseline_preflight.get("checked")
    )
    baseline_canonical = (
        baseline_preflight.get("canonical")
        if isinstance(baseline_preflight, dict)
        else None
    )
    baseline_canonical_reason = (
        baseline_preflight.get("canonical_reason")
        if isinstance(baseline_preflight, dict)
        else None
    )
    baseline_load_error = (
        baseline_preflight.get("load_error")
        if isinstance(baseline_preflight, dict)
        else None
    )

    if is_replay:
        if not baseline_summary:
            reasons.append("replay_without_baseline_summary")
        if isinstance(baseline_preflight, dict):
            baseline_load_error = str(
                baseline_preflight.get("load_error") or ""
            ).strip().casefold()
            baseline_canonical = baseline_preflight.get("canonical")
            if baseline_load_error:
                reasons.append("replay_baseline_unreadable")
            elif baseline_canonical is False:
                reasons.append("replay_baseline_non_canonical")
        if not reset_before_dialog:
            reasons.append("replay_without_reset_before_dialog")
        if jid_mode_token and jid_mode_token != "unique":
            reasons.append("replay_without_unique_jid")
        if (
            previous_replay_fingerprint_clean
            and replay_fingerprint
            and replay_fingerprint == previous_replay_fingerprint_clean
            and not allow_no_code_delta
        ):
            reasons.append("replay_fingerprint_unchanged")
    elif not non_doc_files and not allow_no_code_delta:
        reasons.append("full_run_without_code_delta")

    enforced = mode == "block"
    valid = not reasons if enforced else True
    return {
        "mode": mode,
        "valid": valid,
        "enforced": enforced,
        "reasons": reasons,
        "scan_warnings": scan_warnings,
        "changed_files": normalized_files,
        "changed_files_count": len(normalized_files),
        "non_doc_changed_files": non_doc_files,
        "non_doc_changed_files_count": len(non_doc_files),
        "is_replay": is_replay,
        "allow_no_code_delta": bool(allow_no_code_delta),
        "jid_mode": jid_mode_token or None,
        "code_fingerprint": code_fingerprint,
        "scenario_fingerprint": scenario_fingerprint,
        "baseline_fingerprint": baseline_fingerprint,
        "replay_fingerprint": replay_fingerprint,
        "previous_replay_fingerprint": previous_replay_fingerprint_clean,
        "baseline_checked": baseline_checked,
        "baseline_canonical": baseline_canonical,
        "baseline_canonical_reason": baseline_canonical_reason,
        "baseline_load_error": baseline_load_error,
    }


def _llm_quality_collect_blocking_reasons(failure_counts, extra_counts=None):
    counts = {}
    total = 0
    for reason in LLM_QUALITY_BLOCKING_REASONS:
        value = int((failure_counts or {}).get(reason, 0) or 0)
        if value <= 0:
            continue
        counts[reason] = value
        total += value
    if isinstance(extra_counts, dict):
        for reason, raw_value in extra_counts.items():
            try:
                value = int(raw_value or 0)
            except Exception:
                continue
            if value <= 0:
                continue
            reason_key = str(reason)
            counts[reason_key] = counts.get(reason_key, 0) + value
            total += value
    return {"count": total, "reasons": counts}


def _llm_quality_hq1_normalize_text(value):
    if not isinstance(value, str) or not value.strip():
        return ""
    normalized = value.casefold().replace("ё", "е")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _llm_quality_hq1_contains_any(text, markers):
    normalized = _llm_quality_hq1_normalize_text(text)
    if not normalized:
        return False
    return any(marker in normalized for marker in markers)


def _llm_quality_hq1_has_hallucination_signal(judge_result):
    if not isinstance(judge_result, dict):
        return False
    verdict = _llm_quality_normalize_tool_token(judge_result.get("verdict"))
    if verdict != "fail":
        return False

    fragments = []
    reasons = judge_result.get("reasons")
    if isinstance(reasons, str):
        reasons = [item.strip() for item in reasons.split(",") if item.strip()]
    if isinstance(reasons, list):
        fragments.extend(str(item) for item in reasons if str(item).strip())
    summary = judge_result.get("summary")
    if isinstance(summary, str) and summary.strip():
        fragments.append(summary.strip())
    for fragment in fragments:
        if _llm_quality_hq1_contains_any(fragment, LLM_QUALITY_HQ1_HALLUCINATION_MARKERS):
            return True
    return False


def _llm_quality_collect_hq1_classes(record):
    if not isinstance(record, dict):
        return []
    classes = set()
    turn_text = _llm_quality_hq1_normalize_text(record.get("turn_text"))
    outbox_text = _llm_quality_hq1_normalize_text(record.get("outbox_text"))
    state = _llm_quality_normalize_tool_token(record.get("conversation_state"))

    turn_tags = set()
    for raw_tag in record.get("turn_tags") or []:
        token = _llm_quality_normalize_tool_token(raw_tag)
        if token:
            turn_tags.add(token)

    expectations = record.get("turn_expectations")
    if not isinstance(expectations, dict):
        expectations = {}
    expected_action = _llm_quality_normalize_tool_token(expectations.get("action"))
    expected_info_sections = set()
    for raw_section in expectations.get("info_sections") or []:
        token = _llm_quality_normalize_tool_token(raw_section)
        if token:
            expected_info_sections.add(token)

    meta = record.get("decision_meta")
    if not isinstance(meta, dict):
        meta = {}
    meta_action = _llm_quality_normalize_tool_token(meta.get("action"))
    meta_intent = _llm_quality_normalize_tool_token(meta.get("intent"))
    meta_tool_action = _llm_quality_normalize_tool_token(meta.get("tool_action"))
    meta_tool_decision = _llm_quality_normalize_tool_token(meta.get("tool_decision"))

    evaluation = record.get("evaluation")
    strict_reasons = set()
    if isinstance(evaluation, dict):
        for reason in evaluation.get("strict_reasons") or []:
            token = _llm_quality_normalize_tool_token(reason)
            if token:
                strict_reasons.add(token)

    handoff_expected = expected_action in {"handoff", "booking_escalated"}
    handoff_observed = meta_action in {"escalate", "booking_escalated", "booking_captured_pending"} or (
        state in {"pending", "manager_active"}
    )
    reschedule_signal = bool({"reschedule", "cancel"} & turn_tags) or _llm_quality_hq1_contains_any(
        turn_text, LLM_QUALITY_HQ1_RESCHEDULE_MARKERS
    )
    if (reschedule_signal or handoff_expected) and not handoff_observed:
        if (
            "expected_action_mismatch" in strict_reasons
            or meta_action in {"reply", "check_booking_prompt", "booking_prompt", "collect", "fact"}
            or meta_tool_action in {"calendar.reschedule", "calendar.get_booking", "calendar.list_slots"}
        ):
            classes.add("handoff_miss")

    master_signal = (
        bool({"master", "specialist"} & turn_tags)
        or bool({"master", "specialist"} & expected_info_sections)
        or _llm_quality_hq1_contains_any(turn_text, LLM_QUALITY_HQ1_MASTER_MARKERS)
    )
    routed_to_location = (
        meta_intent in {"catalog.location", "catalog.hours", "catalog.parking"}
        or meta_tool_action in {"catalog.location", "catalog.hours", "catalog.parking"}
    )
    if master_signal and (
        routed_to_location
        or "expected_info_section_miss" in strict_reasons
        or "info_section_miss" in strict_reasons
    ):
        classes.add("wrong_action")

    services_overview_signal = _llm_quality_hq1_contains_any(
        turn_text, LLM_QUALITY_HQ1_SERVICE_OVERVIEW_MARKERS
    )
    generic_dead_end_reply = (
        "не удалось подтвердить действие автоматически" in outbox_text
        and "уточните" in outbox_text
    )
    contract_invalid_services = (
        meta_tool_action == "catalog.service_query"
        and meta_tool_decision in {"contract_invalid", "service_not_found", "not_found_fallback"}
    )
    if services_overview_signal and (
        generic_dead_end_reply
        or (
            contract_invalid_services
            and ("judge_fail" in strict_reasons or "expected_reply_type_mismatch" in strict_reasons)
        )
    ):
        classes.add("non_actionable_reply")

    booking_signal = (
        bool({"booking", "time", "time_alt", "name", "service_choice", "confirm"} & turn_tags)
        or meta_tool_action.startswith("calendar.")
        or meta_intent.startswith("calendar.")
    )
    if booking_signal:
        booking_flow_break = False
        if "expected_reply_type_mismatch" in strict_reasons or "booking_slot_stall" in strict_reasons:
            booking_flow_break = True
        elif "expected_action_mismatch" in strict_reasons and "handoff_miss" not in classes:
            booking_flow_break = True
        elif "judge_fail" in strict_reasons and (
            meta_tool_action in {"calendar.list_slots", "calendar.book_slot"}
            or meta_intent in {"calendar.list_slots", "calendar.book_slot"}
        ):
            booking_flow_break = True
        if booking_flow_break:
            classes.add("booking_flow_break")

    judge_result = record.get("judge")
    if _llm_quality_hq1_has_hallucination_signal(judge_result):
        classes.add("hallucinated_fact")

    return [item for item in LLM_QUALITY_HQ1_CLASSES if item in classes]


def _llm_quality_next_step_for_reason(reason):
    mapping = {
        "booking_slot_stall": "trace booking stages and verify slot extraction for this turn",
        "missing_bot_reply": "inspect outbox_summary/outbox_payload_status for blocked send",
        "unobserved_turn": "inspect transport observability (turn_outcome + outbox state) and fail run as INVALID",
        "outbox_delivery_failed": "inspect outbox last_error/provider status and retry/backoff policy",
        "outbox_delivery_timeout": "increase poll/outbox wait for replay and verify worker/outbox process timing",
        "false_booking_confirmation": "verify booking confirmation text against appointment_id and calendar outcome",
        "calendar_tool_contract_miss": "inspect tool_signals.calendar + appointment_status before confirming booking",
        "requested_date_time_like": "fix runtime date normalization so requested_date stores only date/relative-date tokens",
        "slot_date_resolution_miss": "verify relative-date normalization and carryover into calendar.list_slots start_at/date",
        "slot_availability_contradiction": "align availability claim with rendered slot list from tool outcome",
        "fabricated_conflict_time": "ensure conflict text uses user-requested time only (no inferred/hallucinated clock)",
        "booking_prompt_leak": "remove stale booking prompt append from FACT/info responses in booking interrupt flow",
        "stale_prompt_date_mismatch": "ensure follow-up prompt guard resets stale datetime and rewrites expected_reply reason deterministically",
        "mix_info_booking": "split info answer and booking prompt into separate turns; keep FACT reply booking-neutral",
        "stale_booking_carryover": "suppress booking sidecar append for info/promo FACT replies while preserving expected_reply state",
        "timeout_degrade_booking_generic": "replace timeout generic clarify with booking-safe slot prompt when booking context is active",
        "run_economy_violation": "avoid full/replay spend without code delta + baseline; use lock/replay loop with reset-before-dialog",
        "run_completion_gap": "stop run as INVALID and rerun from lock scenarios until all expected turns are executed",
        "trace_response_mismatch": "fail run as INVALID and inspect trace write path for missing inbound records",
        "weak_oracle_turn": "add at least one explicit expectation per scenario turn (action/reply_type/info/state/reply)",
        "incomplete_run_artifact": "discard incomplete run from baseline/comparison and regenerate with full summary+brief artifacts",
        "judge_fail": "review semantic mismatch in judge summary and convert to deterministic guard/test",
        "decision_meta_missing": "check early-return traces and meta write on this path",
        "decision_trace_missing": "verify trace retention for early returns and pending paths",
        "expected_reply_type_mismatch": "compare expected_reply_type in context vs turn.expect.reply_type",
        "unknown_state": "inspect conversation.state transitions before/after handoff",
        "handover_missing": "check handoff row creation when state is manager_active",
        "info_section_miss": "verify info_sections and intents emitted in meta/trace",
        "post_llm_semantic_rewrite_budget_exceeded": "reduce post-LLM rewrites or tighten guard conditions to fit rewrite budget",
        "keyword_override_budget_exceeded": "remove keyword/regex semantic overrides and rely on policy-core output",
        "rewrite_reason_missing": "add explicit whitelist reason-code for every post-LLM rewrite path",
        "rewrite_reason_unknown": "replace non-whitelist reason-codes with approved override reasons",
        "lexicon_regex_delta_violation": "pair lexicon/regex changes with resolver update and contract regression tests",
        "hardcode_core_violation": "remove raw phrase/regex branching from core files or move it to resolver/data with explicit allow marker",
        "wrong_action": "inspect plan/final action routing and tighten intent arbitration for this turn class",
        "handoff_miss": "ensure manager-request/reschedule intents transition to handoff+pending with trace proof",
        "non_actionable_reply": "replace dead-end fallback with actionable FACT/COLLECT continuation",
        "hallucinated_fact": "audit judge fail evidence and force truth-only fallback for unsupported facts",
        "booking_flow_break": "align expected_reply progression and booking follow-up prompt state machine",
    }
    return mapping.get(reason, "inspect top failing turns in responses.jsonl and trace_bundle.jsonl")


def _llm_quality_build_replay_command(args, scenarios_path, count):
    cmd = [
        "python3",
        "ops/diagnose.py",
        "llm-quality",
        "--base-url",
        args.base_url,
        "--client-slug",
        args.client_slug,
        "--scenarios-file",
        scenarios_path,
        "--count",
        str(count),
        "--timeout-profile",
        str(args.timeout_profile),
        "--timeout",
        str(args.timeout),
        "--poll-timeout",
        str(args.poll_timeout),
        "--poll-interval",
        str(args.poll_interval),
        "--trace-timeout",
        str(args.trace_timeout),
        "--trace-interval",
        str(args.trace_interval),
        "--min-wait",
        str(args.min_wait),
        "--max-wait",
        str(args.max_wait),
        "--manager-mode",
        args.manager_mode,
        "--pending-mode",
        args.pending_mode,
        "--tool-hooks",
        args.tool_hooks,
        "--jid-mode",
        "unique",
        "--reset-before-dialog",
    ]
    if args.branch_slug:
        cmd.extend(["--branch-slug", args.branch_slug])
    if args.remote_jid:
        cmd.extend(["--remote-jid", args.remote_jid])
    else:
        cmd.extend(["--allowlist-jids", "$OUTBOUND_ALLOWLIST_JIDS"])
    if args.allow_non_allowlist or (not args.remote_jid and not args.skip_outbox):
        cmd.append("--allow-non-allowlist")
    if args.skip_outbox:
        cmd.append("--skip-outbox")
    if args.max_failures > 0:
        cmd.extend(["--max-failures", str(args.max_failures)])
    return "TEST_MODE=1 " + " ".join(shlex.quote(part) for part in cmd)


def _llm_quality_write_brief(path, summary):
    metrics = (summary or {}).get("metrics") or {}
    rates = metrics.get("rates") or {}
    stages = metrics.get("stages") or {}
    counts = metrics.get("counts") or {}
    top_failures = (summary or {}).get("top_failures") or []
    top_failure_turns = (summary or {}).get("top_failure_turns") or []
    hq1_bad_turn_count = int((summary or {}).get("hq1_bad_turn_count") or 0)
    hq1_class_counts = (summary or {}).get("hq1_class_counts") or {}
    hq1_nonzero = {k: v for k, v in hq1_class_counts.items() if int(v or 0) > 0}
    stop_reason = (summary or {}).get("stop_reason")
    scenario_source = (summary or {}).get("scenario_source") or {}
    replay_command = (summary or {}).get("replay_command")
    lines = [
        "# LLM Quality Brief",
        "",
        f"- run_id: `{summary.get('run_id')}`",
        f"- finished_at: `{summary.get('finished_at')}`",
        f"- duration_s: `{summary.get('duration_s')}`",
        f"- pass_rate: `{rates.get('pass_rate')}`",
        f"- strict_pass_rate: `{rates.get('strict_pass_rate')}`",
        f"- hard_fail_rate: `{rates.get('hard_fail_rate')}`",
        f"- hard_fail_turns: `{counts.get('turns_hard_failed')}`",
        f"- hq1_bad_turn_count: `{hq1_bad_turn_count}`",
        f"- hq1_class_counts: `{hq1_nonzero}`",
        f"- expected_reply_rate: `{rates.get('expected_reply_rate')}`",
        f"- booking_slot_progress_rate: `{rates.get('booking_slot_progress_rate')}`",
        f"- controller_attempt_rate: `{(stages.get('controller') or {}).get('attempt_rate')}`",
        f"- tool_selection_ok_rate: `{(stages.get('tool_selection') or {}).get('ok_rate')}`",
        f"- tool_args_valid_rate: `{(stages.get('tool_args') or {}).get('valid_rate')}`",
        f"- state_transition_pass_rate: `{(stages.get('state_transition') or {}).get('pass_rate')}`",
        f"- response_contract_pass_rate: `{(stages.get('response_contract') or {}).get('pass_rate')}`",
        f"- scenario_source: `{scenario_source.get('type')}`",
        f"- scenarios_path: `{summary.get('scenarios_path')}`",
        f"- responses_path: `{summary.get('responses_path')}`",
        f"- trace_bundle_path: `{summary.get('trace_bundle_path')}`",
    ]
    if scenario_source.get("path"):
        lines.append(f"- scenario_source_path: `{scenario_source.get('path')}`")
    if stop_reason:
        lines.append(f"- stop_reason: `{stop_reason}`")
    lines.extend(["", "## Top Failures"])
    if top_failure_turns:
        for row in top_failure_turns:
            next_step = _llm_quality_next_step_for_reason(row.get("reason"))
            sample_turns = row.get("sample_turns") if isinstance(row, dict) else []
            sample_tokens = []
            if isinstance(sample_turns, list):
                for sample in sample_turns:
                    if not isinstance(sample, dict):
                        continue
                    message_id = sample.get("message_id")
                    if isinstance(message_id, str) and message_id:
                        sample_tokens.append(message_id)
            samples_blob = ",".join(sample_tokens) if sample_tokens else "n/a"
            lines.append(
                f"- `{row.get('reason')}` x{row.get('count')} ({row.get('category')}): {row.get('label')}; samples: {samples_blob}; next: {next_step}."
            )
    elif top_failures:
        for row in top_failures:
            next_step = _llm_quality_next_step_for_reason(row.get("reason"))
            lines.append(
                f"- `{row.get('reason')}` x{row.get('count')} ({row.get('category')}): {row.get('label')}; next: {next_step}."
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Replay"])
    if replay_command:
        lines.append(f"- command: `{replay_command}`")
    else:
        lines.append("- command: n/a")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _llm_quality_default_output_dir(run_id, explicit_output_dir=None):
    if isinstance(explicit_output_dir, str) and explicit_output_dir.strip():
        return os.path.abspath(os.path.expanduser(explicit_output_dir.strip()))
    run_token = str(run_id or "").strip() or "llm-quality-unknown"
    return os.path.abspath(os.path.join("/tmp/booking_quality", run_token))


def _llm_quality_replay_fingerprint_state_path():
    return "/tmp/booking_quality/.run_economy_replay_state.json"


def _llm_quality_load_replay_fingerprint_state(path):
    if not isinstance(path, str) or not path.strip():
        return {}
    normalized = os.path.abspath(os.path.expanduser(path.strip()))
    if not os.path.exists(normalized):
        return {}
    try:
        with open(normalized, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _llm_quality_save_replay_fingerprint_state(path, payload):
    if not isinstance(path, str) or not path.strip():
        return
    normalized = os.path.abspath(os.path.expanduser(path.strip()))
    os.makedirs(os.path.dirname(normalized), exist_ok=True)
    with open(normalized, "w", encoding="utf-8") as handle:
        json.dump(payload if isinstance(payload, dict) else {}, handle, ensure_ascii=False, indent=2)


def _llm_quality_stop_reason_from_system_exit(code):
    if isinstance(code, int):
        return "system_exit" if code not in (0, None) else None
    text = str(code or "").strip()
    if not text:
        return "system_exit"
    if "INVALID RUN" in text:
        lowered = text.casefold()
        if "runtime fingerprint preflight failed" in lowered:
            return "invalid_runtime_fingerprint_preflight"
        if "webhook_secret preflight failed" in lowered:
            return "invalid_webhook_secret_preflight"
        if "openai preflight failed" in lowered:
            return "invalid_openai_preflight"
        if "scenario contract failed" in lowered:
            return "invalid_scenario_contract_preflight"
        if "run economy gate failed" in lowered:
            return "invalid_run_economy_preflight"
        return "invalid_preflight"
    if "signal_" in text:
        return text
    return "system_exit"


def _llm_quality_write_failure_artifacts(
    *,
    args,
    run_id,
    output_dir,
    started_at,
    stop_reason,
    error_message,
):
    output_dir = _llm_quality_default_output_dir(run_id, output_dir)
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, "summary.json")
    brief_path = os.path.join(output_dir, "brief.md")
    if os.path.exists(summary_path) and os.path.exists(brief_path):
        return

    started_dt = started_at if isinstance(started_at, datetime) else datetime.now(timezone.utc)
    finished_dt = datetime.now(timezone.utc)
    duration_s = round((finished_dt - started_dt).total_seconds(), 2)

    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as handle:
                summary_payload = json.load(handle)
        except Exception:
            summary_payload = {}
    else:
        summary_payload = {}

    minimal_counts = {
        "turns_hard_failed": int(((summary_payload.get("metrics") or {}).get("counts") or {}).get("turns_hard_failed") or 0)
    }
    summary = {
        "run_id": run_id,
        "started_at": started_dt.isoformat(),
        "finished_at": finished_dt.isoformat(),
        "duration_s": duration_s,
        "stop_reason": stop_reason or "early_failure",
        "output_dir": output_dir,
        "scenarios_path": os.path.join(output_dir, "scenarios.json"),
        "responses_path": os.path.join(output_dir, "responses.jsonl"),
        "trace_bundle_path": os.path.join(output_dir, "trace_bundle.jsonl"),
        "brief_path": brief_path,
        "infra_valid": False,
        "semantic_valid": False,
        "scenario_source": {
            "type": "file" if getattr(args, "scenarios_file", None) else "generated",
            "path": (
                os.path.abspath(os.path.expanduser(args.scenarios_file))
                if getattr(args, "scenarios_file", None)
                else None
            ),
        },
        "config": {
            "mode": getattr(args, "mode", None),
            "count": getattr(args, "count", None),
            "scenarios_file": getattr(args, "scenarios_file", None),
            "allow_weak_oracle": bool(getattr(args, "allow_weak_oracle", False)),
            "judge_mode": getattr(args, "judge_mode", None),
            "jid_mode": getattr(args, "jid_mode", None),
            "reset_before_dialog": bool(getattr(args, "reset_before_dialog", False)),
            "baseline_summary": getattr(args, "baseline_summary", None),
            "hardcode_core_gate": getattr(args, "hardcode_core_gate", None),
            "hardcode_core_base_ref": getattr(args, "hardcode_core_base_ref", None),
            "run_economy_gate": getattr(args, "run_economy_gate", None),
            "run_economy_base_ref": getattr(args, "run_economy_base_ref", None),
            "expected_runtime_commit": getattr(args, "expected_runtime_commit", None),
        },
        "metrics": {"counts": minimal_counts, "rates": {}, "stages": {}},
        "quality_status": {
            "infra_valid": False,
            "infra_reasons": ["early_failure"],
            "semantic_valid": False,
            "semantic_reasons": ["blocking_reason"],
            "blocking_reason_count": 1,
            "blocking_reasons": {"early_failure": 1},
            "process_blocking_counts": {"early_failure": 1},
            "hq1_bad_turn_count": 0,
            "hq1_class_counts": {},
            "unobserved_turn_count": 0,
            "weak_oracle_turn_count": 0,
            "suppressed_missed_question_count": 0,
            "run_integrity_valid": False,
            "run_integrity_reasons": ["run_incomplete"],
        },
        "blocking_reasons": {"count": 1, "reasons": {"early_failure": 1}},
        "unobserved_turn_count": 0,
        "weak_oracle_turn_count": 0,
        "top_failures": [
            {
                "reason": "early_failure",
                "count": 1,
                "label": str(error_message or "run aborted before full summary"),
                "category": "infra",
            }
        ],
        "top_failure_turns": [],
        "error": str(error_message or ""),
    }
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    _llm_quality_write_brief(brief_path, summary)

def _llm_quality_redact_text(text: str | None) -> str | None:
    if not text:
        return text
    redacted = text
    redacted = re.sub(r"\+?\d[\d\s().-]{7,}\d", "<phone>", redacted)
    redacted = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "<email>", redacted
    )
    return redacted

def _llm_quality_parse_llm_json(content: str) -> dict:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise

def _llm_quality_compact_for_judge_payload(
    value,
    *,
    depth=0,
    max_depth=LLM_QUALITY_JUDGE_PAYLOAD_LIMITS["max_depth"],
    max_items=LLM_QUALITY_JUDGE_PAYLOAD_LIMITS["max_items"],
    max_dict_keys=LLM_QUALITY_JUDGE_PAYLOAD_LIMITS["max_dict_keys"],
    max_string_len=LLM_QUALITY_JUDGE_PAYLOAD_LIMITS["max_string_len"],
):
    if depth >= max_depth:
        return "<truncated>"
    if isinstance(value, str):
        text = value.strip()
        if len(text) <= max_string_len:
            return text
        return f"{text[:max_string_len]}...<trimmed:{len(text) - max_string_len}>"
    if isinstance(value, list):
        items = [
            _llm_quality_compact_for_judge_payload(
                item,
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_dict_keys=max_dict_keys,
                max_string_len=max_string_len,
            )
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            items.append(f"<trimmed:{len(value) - max_items}>")
        return items
    if isinstance(value, dict):
        compact = {}
        keys = list(value.keys())[:max_dict_keys]
        for key in keys:
            compact[str(key)] = _llm_quality_compact_for_judge_payload(
                value.get(key),
                depth=depth + 1,
                max_depth=max_depth,
                max_items=max_items,
                max_dict_keys=max_dict_keys,
                max_string_len=max_string_len,
            )
        if len(value) > max_dict_keys:
            compact["<trimmed_keys>"] = len(value) - max_dict_keys
        return compact
    return value

def _llm_quality_default_judge_cache_file(model: str, base_url: str) -> str:
    host = urllib.parse.urlparse(base_url or "").netloc or "api"
    safe_host = re.sub(r"[^a-zA-Z0-9_.-]+", "_", host)
    safe_model = re.sub(r"[^a-zA-Z0-9_.-]+", "_", model or "unknown")
    cache_dir = os.path.join("/tmp", "booking_quality", "_judge_cache")
    return os.path.join(
        cache_dir,
        f"{_llm_quality_worktree_namespace()}-{safe_host}-{safe_model}.json",
    )

def _llm_quality_load_judge_cache(path: str) -> dict:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}

def _llm_quality_save_judge_cache(path: str, cache: dict, max_entries: int) -> None:
    if not path or not isinstance(cache, dict):
        return
    limit = max(1, int(max_entries or 1))
    if len(cache) > limit:
        overflow = len(cache) - limit
        for key in list(cache.keys())[:overflow]:
            cache.pop(key, None)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def _llm_quality_judge_cache_key(model: str, base_url: str, prompt: str) -> str:
    digest = hashlib.sha256()
    digest.update((model or "").encode("utf-8"))
    digest.update(b"\n")
    digest.update((base_url or "").encode("utf-8"))
    digest.update(b"\n")
    digest.update((prompt or "").encode("utf-8"))
    return digest.hexdigest()

def _llm_quality_build_judge_prompt(payload: dict) -> str:
    reasons = ", ".join(sorted(LLM_QUALITY_JUDGE_REASONS.keys()))
    compact_payload = _llm_quality_compact_for_judge_payload(payload)
    return (
        "You are a QA judge for a salon booking consultant. "
        "Use only the provided context (pack_truth / consult_playbook). "
        "Do not assume missing facts. "
        "If conversation_state is pending/manager_active, any bot reply is wrong. "
        "If expected_reply is false but the bot replied, mark fail. "
        "If expected_info_sections are present, the reply must address them or ask for clarification. "
        "Return JSON only with keys: verdict, score, reasons, summary. "
        f"verdict must be one of: {sorted(LLM_QUALITY_JUDGE_VERDICTS)}. "
        f"reasons must be from: [{reasons}].\\n\\n"
        f"Context JSON:\\n{json.dumps(compact_payload, ensure_ascii=False)}"
    )

def _llm_quality_call_judge(
    *,
    api_key: str,
    model: str,
    base_url: str,
    prompt: str,
    timeout: float,
    max_tokens: int,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max(128, int(max_tokens)),
    }
    endpoint = f"{base_url.rstrip('/')}/v1/chat/completions"
    body = None
    payload_json = json.dumps(payload, ensure_ascii=False)
    connect_timeout = max(1.0, min(float(timeout), 5.0))
    max_time = max(1.0, float(timeout))
    curl_cmd = [
        "curl",
        "-sS",
        "--fail",
        "--connect-timeout",
        str(connect_timeout),
        "--max-time",
        str(max_time),
        "-H",
        "Content-Type: application/json",
        "-H",
        f"Authorization: Bearer {api_key}",
        "-d",
        payload_json,
        endpoint,
    ]
    try:
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=max_time + 2.0,
        )
    except FileNotFoundError:
        data = payload_json.encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"judge_request_timeout:{max_time}s") from exc
    else:
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            if len(stderr) > 240:
                stderr = f"{stderr[:240]}..."
            raise RuntimeError(f"judge_request_failed: rc={result.returncode} err={stderr}")
        try:
            body = json.loads(result.stdout or "")
        except Exception as exc:
            raw = (result.stdout or "").strip()
            if len(raw) > 240:
                raw = f"{raw[:240]}..."
            raise RuntimeError(f"judge_response_parse_failed: {raw}") from exc
    content = body["choices"][0]["message"]["content"]
    return _llm_quality_parse_llm_json(content)


def _llm_quality_openai_chat_endpoint(base_url: str) -> str:
    normalized = (base_url or "https://api.openai.com").rstrip("/")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _llm_quality_openai_probe_reason(status_code: int | None, body: object | None) -> str:
    payload = body if isinstance(body, dict) else {}
    error = payload.get("error") if isinstance(payload, dict) else {}
    error_code = ""
    error_type = ""
    error_message = ""
    if isinstance(error, dict):
        error_code = _llm_quality_normalize_tool_token(error.get("code"))
        error_type = _llm_quality_normalize_tool_token(error.get("type"))
        error_message = _llm_quality_normalize_tool_token(error.get("message"))
    tokens = " ".join(part for part in (error_code, error_type, error_message) if part).strip()
    if "insufficient_quota" in tokens:
        return "insufficient_quota"
    if "rate_limit" in tokens or "rate limit" in tokens:
        return "rate_limit"
    if "invalid_api_key" in tokens:
        return "invalid_api_key"
    if "authentication" in tokens or "unauthorized" in tokens:
        return "unauthorized"
    if status_code == 401:
        return "unauthorized"
    if status_code == 429:
        return "rate_limit"
    if status_code:
        return f"http_{status_code}"
    return "request_failed"


def _llm_quality_openai_key_preflight(
    *,
    purpose: str,
    api_key: str,
    model: str,
    base_url: str,
    timeout: float,
) -> dict:
    endpoint = _llm_quality_openai_chat_endpoint(base_url)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    effective_timeout = max(2.0, min(float(timeout or 8.0), 15.0))
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            elapsed_ms = round((time.monotonic() - started) * 1000, 2)
            parsed = None
            if body:
                try:
                    parsed = json.loads(body)
                except Exception:
                    parsed = None
            valid = bool(isinstance(parsed, dict) and parsed.get("choices"))
            return {
                "purpose": purpose,
                "valid": valid,
                "reason": None if valid else "invalid_response",
                "status": getattr(resp, "status", 200),
                "elapsed_ms": elapsed_ms,
                "endpoint": endpoint,
                "model": model,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = None
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return {
            "purpose": purpose,
            "valid": False,
            "reason": _llm_quality_openai_probe_reason(exc.code, parsed),
            "status": exc.code,
            "elapsed_ms": elapsed_ms,
            "endpoint": endpoint,
            "model": model,
        }
    except urllib.error.URLError as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return {
            "purpose": purpose,
            "valid": False,
            "reason": f"url_error:{str(exc.reason) if getattr(exc, 'reason', None) else str(exc)}",
            "status": None,
            "elapsed_ms": elapsed_ms,
            "endpoint": endpoint,
            "model": model,
        }
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        return {
            "purpose": purpose,
            "valid": False,
            "reason": f"probe_error:{exc.__class__.__name__}",
            "status": None,
            "elapsed_ms": elapsed_ms,
            "endpoint": endpoint,
            "model": model,
        }


def _llm_quality_secret_fingerprint(secret):
    cleaned = _clean_webhook_secret(secret)
    if not cleaned:
        return None
    digest = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:10]}"


def _llm_quality_resolve_expected_webhook_secret(client_meta):
    if not isinstance(client_meta, dict):
        return None, None
    branch_secret = _clean_webhook_secret(client_meta.get("branch_webhook_secret"))
    if branch_secret:
        return branch_secret, "branch"
    client_secret = _clean_webhook_secret(client_meta.get("client_webhook_secret"))
    if client_secret:
        return client_secret, "client"
    return None, None


def _llm_quality_webhook_secret_preflight(
    *,
    provided_secret,
    expected_secret,
    expected_source,
    secret_source,
):
    expected_clean = _clean_webhook_secret(expected_secret)
    provided_clean = _clean_webhook_secret(provided_secret)
    reasons = []
    if not expected_clean:
        reasons.append("expected_secret_missing")
    if not provided_clean:
        reasons.append("provided_secret_missing")
    elif expected_clean and provided_clean != expected_clean:
        reasons.append("secret_mismatch")
    return {
        "valid": not reasons,
        "reasons": reasons,
        "expected_source": expected_source,
        "provided_source": secret_source,
        "expected_fingerprint": _llm_quality_secret_fingerprint(expected_clean),
        "provided_fingerprint": _llm_quality_secret_fingerprint(provided_clean),
    }


def _llm_quality_clean_git_commit(value):
    if value is None:
        return None
    cleaned = str(value).strip().strip('"').strip("'")
    if not cleaned:
        return None
    normalized = cleaned.casefold()
    if normalized in {"unknown", "none", "null", "n/a", "na"}:
        return None
    return normalized


def _llm_quality_resolve_expected_runtime_commit(explicit_commit):
    explicit = _llm_quality_clean_git_commit(explicit_commit)
    if explicit:
        return explicit, "arg", None

    repo_root = _llm_quality_repo_root()
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=8.0,
            check=False,
        )
    except Exception as exc:
        return None, "git_head", f"expected_commit_resolve_error:{exc.__class__.__name__}"

    if result.returncode != 0:
        return None, "git_head", "expected_commit_resolve_error:git_rev_parse_failed"

    resolved = _llm_quality_clean_git_commit(result.stdout)
    if not resolved:
        return None, "git_head", "expected_commit_missing"
    return resolved, "git_head", None


def _llm_quality_runtime_fingerprint_preflight(*, base_url, expected_commit, timeout):
    endpoint = f"{str(base_url or '').rstrip('/')}/admin/version"
    effective_timeout = max(2.0, min(float(timeout or 8.0), 20.0))
    expected_value, expected_source, expected_error = _llm_quality_resolve_expected_runtime_commit(
        expected_commit
    )
    runtime_payload = None
    runtime_error = None
    try:
        runtime_payload = _fetch_json(endpoint, effective_timeout)
    except Exception as exc:
        runtime_error = f"{exc.__class__.__name__}:{exc}"

    runtime_commit = None
    runtime_version = None
    if isinstance(runtime_payload, dict):
        runtime_commit = _llm_quality_clean_git_commit(runtime_payload.get("git_commit"))
        version_raw = runtime_payload.get("version")
        if isinstance(version_raw, str) and version_raw.strip():
            runtime_version = version_raw.strip()

    reasons = []
    if runtime_error:
        reasons.append("admin_version_unreachable")
    if expected_error:
        reasons.append(expected_error)
    if not expected_value and "expected_commit_missing" not in reasons:
        reasons.append("expected_commit_missing")
    if not runtime_commit and not runtime_error:
        reasons.append("runtime_commit_missing")
    if expected_value and runtime_commit and expected_value != runtime_commit:
        reasons.append("git_commit_mismatch")

    return {
        "valid": not reasons,
        "reasons": reasons,
        "endpoint": endpoint,
        "timeout": effective_timeout,
        "expected_commit": expected_value,
        "expected_source": expected_source,
        "runtime_commit": runtime_commit,
        "runtime_version": runtime_version,
        "runtime_error": runtime_error,
    }


def _llm_quality_is_judge_mode_enabled(mode):
    if not isinstance(mode, str):
        return False
    return mode.strip().casefold() in {"sample", "all", "critical"}


def _llm_quality_baseline_is_canonical(payload):
    config = (payload or {}).get("config") if isinstance(payload, dict) else None
    mode = config.get("judge_mode") if isinstance(config, dict) else None
    if not _llm_quality_is_judge_mode_enabled(mode):
        if isinstance(mode, str) and mode.strip():
            return False, f"judge_mode_{mode.strip().casefold()}"
        return False, "judge_mode_missing"
    quality_status = (payload or {}).get("quality_status") if isinstance(payload, dict) else None
    if isinstance(quality_status, dict):
        infra_valid = quality_status.get("infra_valid")
        semantic_valid = quality_status.get("semantic_valid")
        blocking_reason_count = quality_status.get("blocking_reason_count")
        if infra_valid is False:
            return False, "infra_invalid"
        if semantic_valid is False:
            return False, "semantic_invalid"
        if isinstance(blocking_reason_count, (int, float)) and int(blocking_reason_count) > 0:
            return False, "blocking_reasons_present"
    return True, None


def _llm_quality_preflight_baseline_summary(path):
    normalized = (
        os.path.abspath(os.path.expanduser(path))
        if isinstance(path, str) and path.strip()
        else None
    )
    status = {
        "checked": bool(normalized),
        "path": normalized,
        "exists": False,
        "load_error": None,
        "canonical": None,
        "canonical_reason": None,
    }
    if not normalized:
        return status
    if not os.path.exists(normalized) or not os.path.isfile(normalized):
        status["load_error"] = "baseline_missing"
        return status
    status["exists"] = True
    try:
        with open(normalized, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        status["load_error"] = "baseline_parse_failed"
        return status
    canonical, canonical_reason = _llm_quality_baseline_is_canonical(payload)
    status["canonical"] = canonical
    status["canonical_reason"] = canonical_reason
    return status


def _llm_quality_parse_coverage_tokens(value):
    if value is None:
        return set()
    if isinstance(value, str):
        raw_tokens = [item.strip().casefold() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        raw_tokens = [str(item).strip().casefold() for item in value]
    else:
        raw_tokens = [str(value).strip().casefold()]
    return {token for token in raw_tokens if token and token not in {"none", "off"}}


def _llm_quality_build_scenario_contract_status(*, dialogs, scenario_coverage, allow_weak_oracle=False):
    coverage_tokens = _llm_quality_parse_coverage_tokens(scenario_coverage)
    required_tags_by_coverage = {
        "booking": ("booking", "check_booking", "confirm"),
    }
    tag_counts = {}
    dialogs_with_check_confirm_sequence = 0
    turn_count = 0
    weak_expectation_turns = 0
    reply_type_coverage_turns = 0
    action_coverage_turns = 0
    info_coverage_turns = 0
    extract_expectations_fn = globals().get("_llm_quality_extract_expectations")
    weak_expectation_fn = globals().get("_llm_quality_is_weak_oracle_expectation")

    for dialog in dialogs or []:
        if not isinstance(dialog, dict):
            continue
        turns = dialog.get("turns")
        if not isinstance(turns, list):
            continue
        first_check_booking = None
        first_confirm_after_check = None
        for idx, turn in enumerate(turns):
            if not isinstance(turn, dict):
                continue
            turn_count += 1
            if callable(extract_expectations_fn):
                expectations = extract_expectations_fn(turn)
            else:
                raw_expect = turn.get("expect")
                expectations = raw_expect if isinstance(raw_expect, dict) else {}
            if callable(weak_expectation_fn):
                is_weak_oracle = bool(weak_expectation_fn(expectations))
            else:
                is_weak_oracle = not bool(expectations)
            if is_weak_oracle:
                weak_expectation_turns += 1
            if expectations.get("reply_type"):
                reply_type_coverage_turns += 1
            if expectations.get("action"):
                action_coverage_turns += 1
            if expectations.get("info_sections"):
                info_coverage_turns += 1
            raw_tags = turn.get("tags")
            if not isinstance(raw_tags, list):
                continue
            tags = []
            for item in raw_tags:
                if not isinstance(item, str):
                    continue
                token = item.strip().casefold()
                if not token:
                    continue
                tags.append(token)
                tag_counts[token] = tag_counts.get(token, 0) + 1
            if "check_booking" in tags and first_check_booking is None:
                first_check_booking = idx
            if (
                "confirm" in tags
                and first_check_booking is not None
                and idx > first_check_booking
                and first_confirm_after_check is None
            ):
                first_confirm_after_check = idx
        if first_check_booking is not None and first_confirm_after_check is not None:
            dialogs_with_check_confirm_sequence += 1

    reasons = []
    required = {}
    for coverage_token, required_tags in required_tags_by_coverage.items():
        if coverage_token not in coverage_tokens:
            continue
        for tag in required_tags:
            present = tag_counts.get(tag, 0) > 0
            required[tag] = present
            if not present:
                reasons.append(f"missing_tag:{tag}")

    if (
        "booking" in coverage_tokens
        and required.get("check_booking")
        and required.get("confirm")
        and dialogs_with_check_confirm_sequence <= 0
    ):
        reasons.append("check_confirm_sequence_missing")
    if weak_expectation_turns > 0 and not allow_weak_oracle:
        reasons.append("weak_oracle_turn")

    weak_expectation_ratio = round(
        weak_expectation_turns / max(turn_count, 1),
        4,
    ) if turn_count else 0.0
    reply_type_coverage_ratio = round(
        reply_type_coverage_turns / max(turn_count, 1),
        4,
    ) if turn_count else 0.0
    action_coverage_ratio = round(
        action_coverage_turns / max(turn_count, 1),
        4,
    ) if turn_count else 0.0
    info_coverage_ratio = round(
        info_coverage_turns / max(turn_count, 1),
        4,
    ) if turn_count else 0.0

    return {
        "valid": not reasons,
        "reasons": reasons,
        "coverage_tokens": sorted(coverage_tokens),
        "tag_counts": tag_counts,
        "dialogs_with_check_confirm_sequence": dialogs_with_check_confirm_sequence,
        "turn_count": turn_count,
        "weak_expectation_turns": weak_expectation_turns,
        "weak_expectation_ratio": weak_expectation_ratio,
        "reply_type_coverage": reply_type_coverage_ratio,
        "action_coverage": action_coverage_ratio,
        "info_coverage": info_coverage_ratio,
        "allow_weak_oracle": bool(allow_weak_oracle),
    }


def _llm_quality_build_run_integrity_status(*, dialogs, stats):
    expected_turns = 0
    for dialog in dialogs or []:
        if not isinstance(dialog, dict):
            continue
        turns = dialog.get("turns")
        if isinstance(turns, list):
            expected_turns += len(turns)
    responses_turns = int((stats or {}).get("turns") or 0)
    trace_rows_written = int((stats or {}).get("trace_rows_written") or 0)
    missing_turns = max(expected_turns - responses_turns, 0)
    extra_turns = max(responses_turns - expected_turns, 0)
    trace_response_delta = abs(trace_rows_written - responses_turns)
    completion_ratio = (
        round(responses_turns / max(expected_turns, 1), 4) if expected_turns else None
    )
    reasons = []
    if missing_turns > 0 or extra_turns > 0:
        reasons.append("run_completion_gap")
    if trace_response_delta > 0:
        reasons.append("trace_response_mismatch")
    return {
        "valid": not reasons,
        "reasons": reasons,
        "expected_turns": expected_turns,
        "responses_turns": responses_turns,
        "trace_rows_written": trace_rows_written,
        "missing_turns": missing_turns,
        "extra_turns": extra_turns,
        "completion_ratio": completion_ratio,
        "trace_response_delta": trace_response_delta,
    }


def _llm_quality_build_tool_evidence_status(
    *,
    scenario_coverage,
    tool_hooks_mode,
    tool_evidence_policy,
    coverage_stats,
):
    policy = _llm_quality_normalize_tool_token(tool_evidence_policy) or "auto"
    if policy not in {"off", "auto", "strict"}:
        policy = "auto"
    hooks_mode = _llm_quality_normalize_tool_token(tool_hooks_mode)

    intents = (coverage_stats or {}).get("intents")
    if not isinstance(intents, dict):
        intents = {}
    actions = (coverage_stats or {}).get("actions")
    if not isinstance(actions, dict):
        actions = {}
    trace_stages = (coverage_stats or {}).get("trace_stages")
    if not isinstance(trace_stages, dict):
        trace_stages = {}
    tools = (coverage_stats or {}).get("tools")
    if not isinstance(tools, dict):
        tools = {}
    tool_events = tools.get("events") if isinstance(tools.get("events"), dict) else {}
    tool_hooks = (coverage_stats or {}).get("tool_hooks")
    if not isinstance(tool_hooks, dict):
        tool_hooks = {}
    hook_by_action = tool_hooks.get("by_action") if isinstance(tool_hooks.get("by_action"), dict) else {}

    def _as_int(value):
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        return 0

    coverage_tokens = _llm_quality_parse_coverage_tokens(scenario_coverage)
    calendar_intent_turns = sum(
        _as_int(count)
        for intent, count in intents.items()
        if isinstance(intent, str) and intent.startswith("calendar.")
    )
    calendar_tool_events = (
        _as_int(tool_events.get("calendar"))
        + _as_int(tool_events.get("commit"))
        + _as_int(tool_events.get("cancel"))
    )
    confirm_tool_events = _as_int(tool_events.get("confirm"))
    calendar_hook_events = _as_int(hook_by_action.get("calendar"))
    confirm_hook_events = _as_int(hook_by_action.get("confirm"))
    booking_commit_trace_events = _as_int(trace_stages.get("booking_commit"))
    booking_confirm_trace_events = _as_int(trace_stages.get("booking_confirm"))
    booking_confirm_actions = _as_int(actions.get("booking_confirm"))
    check_booking_intents = (
        _as_int(intents.get("calendar.get_booking"))
        + _as_int(intents.get("check_booking"))
        + _as_int(intents.get("check_record"))
    )

    calendar_evidence_total = (
        calendar_tool_events + calendar_hook_events + booking_commit_trace_events
    )
    confirm_evidence_total = (
        confirm_tool_events
        + confirm_hook_events
        + booking_confirm_trace_events
        + booking_confirm_actions
    )

    booking_required = "booking" in coverage_tokens or calendar_intent_turns > 0
    confirm_candidates = check_booking_intents + booking_confirm_actions
    require_calendar = policy in {"auto", "strict"} and booking_required
    require_confirm = policy == "strict" and booking_required
    require_hooks = policy == "strict"

    reasons = []
    if policy == "strict" and hooks_mode != "auto":
        reasons.append("tool_hooks_mode_not_auto")
    if require_calendar and calendar_intent_turns == 0:
        reasons.append("calendar_intent_missing")
    if require_calendar and calendar_evidence_total <= 0:
        reasons.append("calendar_evidence_missing")
    if require_confirm and confirm_candidates <= 0:
        reasons.append("confirm_candidate_missing")
    if require_confirm and confirm_evidence_total <= 0:
        reasons.append("confirm_evidence_missing")
    if require_hooks and hooks_mode == "auto" and require_calendar and calendar_hook_events <= 0:
        reasons.append("calendar_hook_missing")
    if require_hooks and hooks_mode == "auto" and require_confirm and confirm_hook_events <= 0:
        reasons.append("confirm_hook_missing")

    return {
        "policy": policy,
        "valid": not reasons,
        "reasons": reasons,
        "required": {
            "booking": booking_required,
            "calendar": require_calendar,
            "confirm": require_confirm,
            "hooks": require_hooks,
            "hooks_mode": hooks_mode,
        },
        "counts": {
            "calendar_intent_turns": calendar_intent_turns,
            "check_booking_intents": check_booking_intents,
            "booking_confirm_actions": booking_confirm_actions,
            "calendar_tool_events": calendar_tool_events,
            "confirm_tool_events": confirm_tool_events,
            "calendar_hook_events": calendar_hook_events,
            "confirm_hook_events": confirm_hook_events,
            "booking_commit_trace_events": booking_commit_trace_events,
            "booking_confirm_trace_events": booking_confirm_trace_events,
            "calendar_evidence_total": calendar_evidence_total,
            "confirm_evidence_total": confirm_evidence_total,
        },
    }


def _llm_quality_build_infra_status(
    stats,
    secret_preflight,
    tool_evidence_status=None,
    openai_preflight=None,
    runtime_preflight=None,
    failure_counts=None,
):
    reasons = []
    if isinstance(secret_preflight, dict) and not secret_preflight.get("valid", False):
        preflight_reasons = secret_preflight.get("reasons") or []
        if preflight_reasons:
            for reason in preflight_reasons:
                reasons.append(f"webhook_secret_preflight:{reason}")
        else:
            reasons.append("webhook_secret_preflight:unknown")
    if (stats or {}).get("webhook_errors", 0):
        reasons.append("webhook_errors")
    if (stats or {}).get("infra_errors", 0):
        reasons.append("infra_errors")
    if (stats or {}).get("decision_meta_errors", 0):
        reasons.append("decision_meta_errors")
    if (stats or {}).get("decision_trace_errors", 0):
        reasons.append("decision_trace_errors")
    if (stats or {}).get("policy_core_infra_errors", 0):
        reasons.append("policy_core_infra_errors")
    if (stats or {}).get("outbox_delivery_failed_turns", 0):
        reasons.append("outbox_delivery_failed_turns")
    if (stats or {}).get("outbox_delivery_timeout_turns", 0):
        reasons.append("outbox_delivery_timeout_turns")
    if (failure_counts or {}).get("outbox_delivery_failed", 0):
        reasons.append("outbox_delivery_failed")
    if (failure_counts or {}).get("outbox_delivery_timeout", 0):
        reasons.append("outbox_delivery_timeout")
    if isinstance(openai_preflight, list):
        for item in openai_preflight:
            if not isinstance(item, dict):
                continue
            if item.get("valid", False):
                continue
            purpose = item.get("purpose") or "unknown"
            reason = item.get("reason") or "unknown"
            reasons.append(f"openai_preflight:{purpose}:{reason}")
    if isinstance(runtime_preflight, dict) and not runtime_preflight.get("valid", False):
        runtime_reasons = runtime_preflight.get("reasons") or []
        if runtime_reasons:
            for reason in runtime_reasons:
                reasons.append(f"runtime_fingerprint_preflight:{reason}")
        else:
            reasons.append("runtime_fingerprint_preflight:unknown")
    if isinstance(tool_evidence_status, dict) and not tool_evidence_status.get("valid", True):
        tool_reasons = tool_evidence_status.get("reasons") or []
        if tool_reasons:
            for reason in tool_reasons:
                reasons.append(f"tool_evidence:{reason}")
        else:
            reasons.append("tool_evidence:invalid")
    return {"valid": not reasons, "reasons": reasons}


def _llm_quality_compute_delta(current, baseline):
    if isinstance(current, (int, float)) and isinstance(baseline, (int, float)):
        return round(current - baseline, 6)
    if isinstance(current, dict) and isinstance(baseline, dict):
        delta = {}
        for key in sorted(set(current.keys()) | set(baseline.keys())):
            delta[key] = _llm_quality_compute_delta(current.get(key), baseline.get(key))
        return delta
    return None

def _llm_quality_check_thresholds(metrics):
    rates = (metrics or {}).get("rates") or {}
    values = {
        "reply_rate": rates.get("reply_rate"),
        "strict_pass_rate": rates.get("strict_pass_rate"),
        "expected_reply_rate": rates.get("expected_reply_rate"),
        "info_answer_rate": rates.get("info_answer_rate"),
        "hard_fail_rate": rates.get("hard_fail_rate"),
        "unknown_state_rate": rates.get("unknown_state_rate"),
        "degraded_fallback_rate": rates.get("degraded_fallback_rate"),
        "booking_slot_progress_rate": rates.get("booking_slot_progress_rate"),
        "handoff_correct_rate": rates.get("handoff_correct_rate"),
    }
    results = {}
    breaches = []
    for key, threshold in LLM_QUALITY_THRESHOLDS.items():
        value = values.get(key)
        direction = LLM_QUALITY_THRESHOLD_DIRECTIONS.get(key, "min")
        if value is None:
            ok = None
        elif direction == "max":
            ok = value <= threshold
        else:
            ok = value >= threshold
        results[key] = {
            "value": value,
            "threshold": threshold,
            "direction": direction,
            "ok": ok,
        }
        if ok is False:
            breaches.append(key)
    return results, breaches

def _llm_quality_check_regression(metrics, baseline_metrics, tolerance):
    if not baseline_metrics:
        return {}, []
    rates = (metrics or {}).get("rates") or {}
    baseline_rates = (baseline_metrics or {}).get("rates") or {}
    results = {}
    breaches = []
    for key in LLM_QUALITY_REGRESSION_KEYS:
        current = rates.get(key)
        baseline = baseline_rates.get(key)
        direction = LLM_QUALITY_THRESHOLD_DIRECTIONS.get(key, "min")
        if current is None or baseline is None:
            ok = None
            delta = None
        else:
            delta = round(current - baseline, 6)
            if direction == "max":
                ok = delta <= tolerance
            else:
                ok = delta >= -tolerance
        results[key] = {
            "value": current,
            "baseline": baseline,
            "delta": delta,
            "direction": direction,
            "ok": ok,
        }
        if ok is False:
            breaches.append(key)
    return results, breaches

def _llm_quality_last_trace_stage(trace_entries):
    for entry in reversed(trace_entries or []):
        if isinstance(entry, dict) and entry.get("stage"):
            return entry.get("stage")
    return None

def _llm_quality_extract_booking_slots(meta, conv_meta):
    slots = {}
    raw_slots = (meta or {}).get("slots")
    if isinstance(raw_slots, dict):
        for key in LLM_QUALITY_BOOKING_SLOTS:
            value = raw_slots.get(key)
            if isinstance(value, str) and value.strip():
                slots[key] = value.strip()
    context = (conv_meta or {}).get("context") if isinstance(conv_meta, dict) else None
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict):
        for key in LLM_QUALITY_BOOKING_SLOTS:
            if key in slots:
                continue
            value = booking.get(key)
            if isinstance(value, str) and value.strip():
                slots[key] = value.strip()
    return slots


def _llm_quality_booking_slots_progressed(prev_slots, current_slots):
    prev = prev_slots if isinstance(prev_slots, dict) else {}
    curr = current_slots if isinstance(current_slots, dict) else {}
    for key, value in curr.items():
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized:
            continue
        prev_value = prev.get(key)
        prev_normalized = (
            prev_value.strip()
            if isinstance(prev_value, str)
            else str(prev_value).strip()
            if prev_value is not None
            else ""
        )
        if normalized != prev_normalized:
            return True
    return False


def _llm_quality_booking_active(conv_meta):
    context = (conv_meta or {}).get("context") if isinstance(conv_meta, dict) else None
    expected_reply = _chaos_extract_expected_reply(context)
    if expected_reply in CHAOS_BOOKING_REPLY_TYPES:
        return True
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict) and booking.get("active") is True:
        return True
    return False


def _llm_quality_trace_missing_soft(meta, trace_error):
    if trace_error != "trace_stale":
        return False
    if not isinstance(meta, dict):
        return False
    timing = meta.get("timing")
    if not isinstance(timing, dict) or not timing.get("pipeline_finished_at"):
        return False
    return bool(meta.get("action") or meta.get("pending_action"))


def _llm_quality_evaluate_turn(
    *,
    meta,
    trace_entries,
    trace_error=None,
    state,
    conv_meta,
    handover_meta,
    bot_response,
    expected_response,
    expected_action,
    expected_info_sections,
    expected_reply_type,
    expected_state,
    expected_reply,
    actual_expected_reply_type,
    info_tags,
    info_answered,
    booking_active,
    booking_progress_expected,
    booking_progressed,
    allow_booking_stall,
    outbox_text=None,
    tool_signals=None,
    outbox_summary=None,
    outbox_payload_status=None,
    bot_response_inferred_duplicate_ack=False,
    meta_error=None,
    webhook_error=None,
):
    reasons = []
    meta_action = (meta or {}).get("action") if isinstance(meta, dict) else None
    if meta is None:
        reasons.append("decision_meta_missing")
    if not trace_entries and not _llm_quality_trace_missing_soft(meta, trace_error):
        reasons.append("decision_trace_missing")
    if state not in LLM_QUALITY_KNOWN_STATES:
        reasons.append("unknown_state")
    if expected_state and not _llm_quality_state_matches_expected(
        expected_state, state, meta, conv_meta, handover_meta
    ):
        reasons.append("expected_state_mismatch")
    if expected_action and not _llm_quality_action_matches_expected(
        expected_action,
        meta,
        conv_meta,
        trace_entries,
        expected_info_sections,
        actual_expected_reply_type,
    ):
        reasons.append("expected_action_mismatch")
    if expected_reply_type and not _llm_quality_value_matches(
        expected_reply_type, actual_expected_reply_type
    ):
        fallback_ok = False
        if booking_progressed:
            fallback_ok = True
        elif _chaos_reply_type_fallback_ok(
            expected_reply_type, actual_expected_reply_type, meta, conv_meta, trace_entries
        ):
            fallback_ok = True
        if not fallback_ok:
            reasons.append("expected_reply_type_mismatch")
    # Scenario fixtures may carry stale `expected_reply=false` even when runtime
    # expectations are explicit (state/reply-type/info/booking signals).
    expected_reply_for_check = expected_reply
    if (
        expected_reply is False
        and expected_response is True
        and (
            expected_state is None
            or expected_reply_type is not None
            or bool(expected_info_sections)
            or bool(booking_active)
        )
    ):
        expected_reply_for_check = None
    if not _llm_quality_expected_reply_matches(
        expected_reply=expected_reply_for_check,
        expected_response=expected_response,
        bot_response=bot_response,
        expected_reply_type=expected_reply_type,
        expected_state=expected_state,
        state=state,
        meta=meta,
        conv_meta=conv_meta,
        handover_meta=handover_meta,
    ):
        reasons.append("expected_reply_mismatch")
    if expected_info_sections:
        skip_expected_info_check = (
            state in {"pending", "manager_active"}
            and (
                meta_action in CHAOS_PENDING_ACTIONS
                or meta_action in {"escalate", "booking_escalated", "booking_captured_pending"}
            )
        )
        if skip_expected_info_check:
            expected_answered = True
        else:
            expected_answered, _, _ = _llm_quality_expected_section_answered(
                expected_info_sections, meta, trace_entries
            )
            if not expected_answered and _llm_quality_has_general_consult_fallback(meta, trace_entries):
                expected_answered = True
        if not expected_answered:
            reasons.append("expected_info_section_miss")
    if _llm_quality_is_unobserved_turn(
        expected_response=expected_response,
        outbox_text=outbox_text,
        outbox_payload_status=outbox_payload_status,
        outbox_summary=outbox_summary,
        bot_response_inferred_duplicate_ack=bot_response_inferred_duplicate_ack,
        meta=meta,
    ):
        reasons.append("unobserved_turn")
    if expected_response and not bot_response:
        suppress_missing_reply = False
        if isinstance(webhook_error, str) and webhook_error.strip():
            lowered = webhook_error.casefold()
            infra_markers = (
                "remote_disconnected",
                "timeout",
                "timed out",
                "connection refused",
                "connection reset",
                "network is unreachable",
                "temporary failure",
                "name or service not known",
                "connection aborted",
                "broken pipe",
            )
            if any(marker in lowered for marker in infra_markers):
                suppress_missing_reply = True
        if not suppress_missing_reply and not isinstance(meta, dict):
            if isinstance(meta_error, str) and meta_error.casefold() in {
                "timeout",
                "conversation_not_found",
            } and state not in LLM_QUALITY_KNOWN_STATES:
                suppress_missing_reply = True
        if not suppress_missing_reply:
            reasons.append("missing_bot_reply")
            delivery_state = _llm_quality_outbox_delivery_state(
                outbox_payload_status, outbox_summary
            )
            if delivery_state == "failed":
                reasons.append("outbox_delivery_failed")
            elif delivery_state in {"pending", "unknown"}:
                reasons.append("outbox_delivery_timeout")
    if state == "manager_active" and bot_response:
        reasons.append("unexpected_bot_reply_manager")
    if state == "manager_active" and not handover_meta:
        reasons.append("handover_missing")
    if (
        info_tags
        and not any(info_answered.values())
        and state not in {"pending", "manager_active"}
        and not _llm_quality_has_general_consult_fallback(meta, trace_entries)
    ):
        reasons.append("info_section_miss")
    booking_stall_ignored = False
    if isinstance(meta, dict):
        intent_value = _llm_quality_effective_intent(meta)
        tool_decision = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
        if intent_value == "calendar.get_booking" and tool_decision in {"ok", "time_mismatch", "not_found"}:
            booking_stall_ignored = True
        elif intent_value == "calendar.list_slots" and tool_decision == "ok":
            has_slots_payload = bool(_llm_quality_parse_slot_candidates(outbox_text))
            has_followup_prompt = _llm_quality_has_expected_followup_prompt(
                outbox_text,
                actual_expected_reply_type,
            )
            signal_map = tool_signals if isinstance(tool_signals, dict) else {}
            calendar_signal = signal_map.get("calendar")
            calendar_outcome = ""
            if isinstance(calendar_signal, dict):
                calendar_outcome = _llm_quality_normalize_tool_token(calendar_signal.get("outcome"))
            # A successful calendar.list_slots turn is already slot progress, even when
            # the reply is a plain slot list without a follow-up question marker.
            if has_slots_payload or (calendar_outcome == "success" and bot_response) or has_followup_prompt:
                booking_stall_ignored = True
    if (
        booking_active
        and booking_progress_expected
        and booking_progressed is False
        and state not in {"pending", "manager_active"}
        and not allow_booking_stall
        and not booking_stall_ignored
    ):
        reasons.append("booking_slot_stall")

    signal_map = tool_signals if isinstance(tool_signals, dict) else {}
    calendar_signal = signal_map.get("calendar")
    calendar_outcome = ""
    if isinstance(calendar_signal, dict):
        calendar_outcome = _llm_quality_normalize_tool_token(calendar_signal.get("outcome"))
    intent_value = _llm_quality_effective_intent(meta if isinstance(meta, dict) else None)
    tool_decision_value = _llm_quality_normalize_tool_token(
        (meta or {}).get("tool_decision") if isinstance(meta, dict) else None
    )
    meta_action_value = _llm_quality_normalize_tool_token(meta_action)
    meta_intent_value = _llm_quality_normalize_tool_token(
        (meta or {}).get("intent") if isinstance(meta, dict) else None
    )
    meta_source_value = _llm_quality_normalize_tool_token(
        (meta or {}).get("source") if isinstance(meta, dict) else None
    )
    slot_contract_error_value = _llm_quality_normalize_tool_token(
        (meta or {}).get("slot_contract_error") if isinstance(meta, dict) else None
    )
    requested_date_value = (
        str((meta or {}).get("requested_date") or "")
        if isinstance(meta, dict)
        else ""
    )
    if (
        intent_value in {"calendar.list_slots", "calendar.get_booking", "calendar.book_slot"}
        and _llm_quality_is_time_like_token(requested_date_value)
    ):
        reasons.append("requested_date_time_like")
    if (
        intent_value == "calendar.list_slots"
        and slot_contract_error_value == "slot_date_resolution_miss"
    ):
        reasons.append("slot_date_resolution_miss")
    stale_prompt_fn = globals().get("_llm_quality_has_stale_prompt_date_mismatch")
    if callable(stale_prompt_fn):
        has_stale_prompt_date_mismatch = stale_prompt_fn(
            meta if isinstance(meta, dict) else None
        )
    else:
        has_stale_prompt_date_mismatch = False
    if has_stale_prompt_date_mismatch:
        reasons.append("stale_prompt_date_mismatch")

    availability_claim_value = _llm_quality_normalize_tool_token(
        (meta or {}).get("availability_claim") if isinstance(meta, dict) else None
    )
    claim_from_text, claim_time = _llm_quality_extract_availability_claim(outbox_text)
    if availability_claim_value not in {"yes", "no"}:
        availability_claim_value = claim_from_text
    requested_time_from_meta = _llm_quality_normalize_time_token(
        str((meta or {}).get("requested_time") or "")
        if isinstance(meta, dict)
        else None
    )
    requested_time_token = requested_time_from_meta or claim_time
    slot_map = _llm_quality_extract_available_slots_by_specialist(
        meta if isinstance(meta, dict) else None,
        outbox_text,
    )
    available_slot_tokens = {
        slot_time
        for specialist_slots in slot_map.values()
        for slot_time in specialist_slots
        if isinstance(slot_time, str) and slot_time
    }
    if (
        intent_value == "calendar.list_slots"
        and availability_claim_value == "yes"
        and requested_time_token
        and available_slot_tokens
        and requested_time_token not in available_slot_tokens
    ):
        reasons.append("slot_availability_contradiction")

    if intent_value == "calendar.book_slot" and tool_decision_value == "conflict":
        if claim_time and (
            not requested_time_from_meta or claim_time != requested_time_from_meta
        ):
            reasons.append("fabricated_conflict_time")

    if _llm_quality_has_booking_prompt_leak(meta=meta, outbox_text=outbox_text):
        reasons.append("booking_prompt_leak")
    mix_info_booking_fn = globals().get("_llm_quality_has_mix_info_booking")
    if callable(mix_info_booking_fn):
        has_mix_info_booking = mix_info_booking_fn(meta=meta, outbox_text=outbox_text)
    else:
        has_mix_info_booking = False
    if has_mix_info_booking:
        reasons.append("mix_info_booking")
    if _llm_quality_has_stale_booking_carryover(meta=meta, outbox_text=outbox_text):
        reasons.append("stale_booking_carryover")
    if _llm_quality_has_timeout_degrade_booking_generic(
        meta=meta,
        booking_active=booking_active,
        outbox_text=outbox_text,
    ):
        reasons.append("timeout_degrade_booking_generic")

    slot_confirmation_required = bool(
        (meta or {}).get("slot_confirmation_required")
        if isinstance(meta, dict)
        else False
    )
    appointment_id = (meta or {}).get("appointment_id") if isinstance(meta, dict) else None
    appointment_status = _llm_quality_normalize_tool_token(
        (meta or {}).get("appointment_status") if isinstance(meta, dict) else None
    )
    booking_verification_handoff = bool(
        state in {"pending", "manager_active"}
        and meta_action_value == "escalate"
        and meta_intent_value == "check_booking"
        and meta_source_value in {"booking_verification", "tool_registry"}
    )
    # `check_booking_prompt` is a collection step (request booking reference),
    # so calendar success is not expected yet.
    booking_verification_collect_prompt = bool(
        meta_action_value == "check_booking_prompt"
        and meta_intent_value in {"check_booking", "check_record"}
    )
    requires_calendar_contract = bool(
        not booking_verification_handoff
        and not booking_verification_collect_prompt
        and (
            appointment_id
            or appointment_status in LLM_QUALITY_BOOKING_CONFIRM_STATUS_HINTS
            or (meta_action_value == "booking_confirm" and not slot_confirmation_required)
            or intent_value == "calendar.get_booking"
            or _llm_quality_is_booking_confirmation_text(outbox_text)
        )
    )
    if requires_calendar_contract and calendar_outcome != "success":
        reasons.append("calendar_tool_contract_miss")

    if _llm_quality_is_booking_confirmation_text(outbox_text):
        if not appointment_id and calendar_outcome != "success":
            reasons.append("false_booking_confirmation")
    return reasons

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
    parser.add_argument("--branch-slug", default=os.environ.get("TRUFFLES_BRANCH_SLUG"))
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
    parser.add_argument(
        "--kinds",
        default=None,
        help="Comma-separated case kinds: booking,policy,consult,info,ood",
    )
    parser.add_argument("--webhook-secret", default=None)
    parser.add_argument("--admin-token", default=None)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--retry-count", type=int, default=2)
    parser.add_argument("--retry-backoff", type=float, default=0.5)
    parser.add_argument("--poll-timeout", type=float, default=20.0)
    parser.add_argument("--poll-interval", type=float, default=0.6)
    parser.add_argument("--min-wait", type=float, default=0.3)
    parser.add_argument("--max-wait", type=float, default=1.2)
    parser.add_argument("--max-runtime", type=float, default=None)
    parser.add_argument("--outbox-wait", type=float, default=None)
    parser.add_argument("--skip-outbox", action="store_true")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--simulation-id", default=None)
    parser.add_argument(
        "--sim-time",
        default=None,
        help="Simulation clock override (ISO 8601, e.g. 2026-01-24T12:00:00+06:00).",
    )
    parser.add_argument("--dump-cases", action="store_true")
    parser.add_argument("--console-base-url", default=os.environ.get("CONSOLE_API_BASE_URL"))
    parser.add_argument("--console-token", default=None)
    parser.add_argument("--console-env", default="/home/zhan/secrets/console-contract.env")
    parser.add_argument("--console-client-id", default=None)
    parser.add_argument("--console-mode", choices=["real", "skip"], default="real")
    parser.add_argument(
        "--manager-mode",
        choices=["check", "skip"],
        default="check",
        help="Skip manager turn verification (useful for chaos-only runs).",
    )
    parser.add_argument(
        "--fail-on-infra",
        action="store_true",
        help="Stop chaos-sim on infra errors (default: continue to next case).",
    )
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug-all", action="store_true")
    parser.add_argument("--rag-audit", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def _llm_quality_apply_timeout_profile(args):
    profile_name = (getattr(args, "timeout_profile", None) or "realistic").strip().lower()
    profile = LLM_QUALITY_TIMEOUT_PROFILES.get(profile_name)
    if profile is None:
        profile_name = "realistic"
        profile = LLM_QUALITY_TIMEOUT_PROFILES[profile_name]
    args.timeout_profile = profile_name
    for field, profile_value in profile.items():
        if getattr(args, field, None) is None:
            setattr(args, field, float(profile_value))

    wait_profile = "replay" if getattr(args, "scenarios_file", None) else "generated"
    wait_defaults = LLM_QUALITY_WAIT_DEFAULTS[wait_profile]
    if getattr(args, "min_wait", None) is None:
        args.min_wait = float(wait_defaults["min_wait"])
    if getattr(args, "max_wait", None) is None:
        args.max_wait = float(wait_defaults["max_wait"])
    return args


def _llm_quality_build_default_run_id(timestamp=None):
    stamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    namespace = _llm_quality_worktree_namespace()
    return f"{stamp}-{namespace}-p{os.getpid()}-{uuid.uuid4().hex[:6]}"


LLM_QUALITY_ARTIFACT_FILES = (
    "brief.md",
    "preflight.json",
    "responses.jsonl",
    "scenarios.json",
    "summary.json",
    "trace_bundle.jsonl",
)


def _llm_quality_prepare_output_dir(path, *, allow_overwrite=False):
    output_dir = os.path.abspath(os.path.expanduser(path))
    os.makedirs(output_dir, exist_ok=True)
    entries = []
    try:
        entries = os.listdir(output_dir)
    except OSError:
        entries = []
    if entries and not allow_overwrite:
        raise SystemExit(
            "llm-quality: output-dir already contains artifacts; "
            "use unique --run-id/--output-dir or pass --allow-output-overwrite"
        )
    if entries and allow_overwrite:
        for entry in entries:
            target = os.path.join(output_dir, entry)
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)
                continue
            try:
                os.remove(target)
            except OSError:
                pass
    return output_dir


def _llm_quality_validate_scenario_artifacts(
    scenarios_file: str,
    *,
    allow_incomplete: bool,
) -> dict:
    scenario_path = os.path.abspath(os.path.expanduser(scenarios_file))
    scenario_name = os.path.basename(scenario_path)
    scenario_dir = os.path.dirname(scenario_path)
    if scenario_name != "scenarios.json":
        return {
            "checked": False,
            "scenarios_file": scenario_path,
            "scenarios_dir": scenario_dir,
            "required": [],
            "missing": [],
            "valid": True,
            "skipped_reason": "custom_scenarios_file",
        }
    required = ("summary.json", "brief.md")
    missing = [
        artifact
        for artifact in required
        if not os.path.exists(os.path.join(scenario_dir, artifact))
    ]
    valid = not missing
    if missing and not allow_incomplete:
        raise SystemExit(
            "llm-quality: INVALID RUN - incomplete scenarios-file artifacts "
            f"(missing={','.join(missing)}; dir={scenario_dir})"
        )
    return {
        "checked": True,
        "scenarios_file": scenario_path,
        "scenarios_dir": scenario_dir,
        "required": list(required),
        "missing": missing,
        "valid": valid,
    }


def _parse_llm_quality_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py llm-quality",
        description="Run booking dialogs (LLM or template) with state-aware evaluation.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRUFFLES_API_BASE_URL"),
        help="Runtime API base URL (required: --base-url or TRUFFLES_API_BASE_URL).",
    )
    parser.add_argument(
        "--client-slug",
        default=os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon"),
    )
    parser.add_argument("--branch-slug", default=os.environ.get("TRUFFLES_BRANCH_SLUG"))
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--scenarios-file",
        default=None,
        help="Reuse dialogs from an existing scenarios.json (deterministic replay).",
    )
    parser.add_argument(
        "--allow-weak-oracle",
        action="store_true",
        help="Allow scenario turns without explicit expectations (debug only).",
    )
    parser.add_argument(
        "--allow-incomplete-run-artifacts",
        action="store_true",
        help="Allow replay from scenarios-file even when sibling summary/brief artifacts are missing.",
    )
    parser.add_argument("--mode", choices=["template", "llm"], default="llm")
    parser.add_argument("--min-turns", type=int, default=10)
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--include-media", action="store_true")
    parser.add_argument("--media-mode", choices=["text", "payload"], default="text")
    parser.add_argument("--media-kind", choices=["photo", "audio"], default="photo")
    parser.add_argument("--scenario-coverage", default="booking,info,interrupt")
    parser.add_argument(
        "--scenario-gen-timeout",
        type=float,
        default=None,
        help=(
            "Timeout in seconds for one scenario generator subprocess. "
            "When omitted, DIAGNOSE_SCENARIO_GEN_TIMEOUT_SEC or 180 is used."
        ),
    )
    parser.add_argument(
        "--scenario-llm-batch-size",
        type=int,
        default=2,
        help="LLM dialogs requested per OpenAI call inside booking_dialog_scenarios.py",
    )
    parser.add_argument(
        "--scenario-llm-max-attempts",
        type=int,
        default=1,
        help=(
            "Inner retries inside booking_dialog_scenarios.py. "
            "Outer retries are controlled by --retry-count."
        ),
    )
    parser.add_argument(
        "--scenario-llm-request-timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds for one OpenAI call inside scenario generation.",
    )
    parser.add_argument(
        "--scenario-llm-attempt-backoff",
        type=float,
        default=0.6,
        help="Backoff seconds between inner scenario LLM attempts.",
    )
    parser.add_argument(
        "--scenario-progress-stderr",
        action="store_true",
        help="Emit scenario generation batch/attempt progress to stderr.",
    )
    parser.add_argument("--llm-model", default="gpt-4o-mini")
    parser.add_argument(
        "--llm-base-url",
        default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com"),
    )
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--retry-count", type=int, default=2)
    parser.add_argument("--retry-backoff", type=float, default=0.6)
    parser.add_argument("--min-wait", type=float, default=None)
    parser.add_argument("--max-wait", type=float, default=None)
    parser.add_argument("--allowlist-jids", default=None)
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument(
        "--jid-mode",
        choices=["auto", "round_robin", "random", "unique"],
        default="auto",
    )
    parser.add_argument("--allow-non-allowlist", action="store_true")
    parser.add_argument("--webhook-secret", default=None)
    parser.add_argument("--admin-token", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument(
        "--timeout-profile",
        choices=sorted(LLM_QUALITY_TIMEOUT_PROFILES.keys()),
        default=os.environ.get("LLM_QUALITY_TIMEOUT_PROFILE", "realistic"),
    )
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--poll-timeout", type=float, default=None)
    parser.add_argument("--poll-interval", type=float, default=None)
    parser.add_argument("--trace-timeout", type=float, default=None)
    parser.add_argument("--trace-interval", type=float, default=None)
    parser.add_argument("--skip-outbox", action="store_true")
    parser.add_argument("--outbox-wait", type=float, default=None)
    parser.add_argument("--manager-mode", choices=["simulate", "check", "skip"], default="simulate")
    parser.add_argument("--manager-channel", choices=["telegram", "console"], default="telegram")
    parser.add_argument("--manager-actions", default="take,resolve")
    parser.add_argument("--manager-wait", type=float, default=1.0)
    parser.add_argument("--pending-mode", choices=["ack", "skip"], default="ack")
    parser.add_argument("--ack-text", default="ок")
    parser.add_argument("--tool-hooks", choices=["off", "check", "auto"], default="check")
    parser.add_argument("--tool-confirm-text", default="да")
    parser.add_argument("--tool-cancel-text", default="отмена")
    parser.add_argument("--tool-calendar-text", default="проверь запись")
    parser.add_argument("--tool-hook-wait", type=float, default=0.8)
    parser.add_argument("--tool-hook-limit", type=int, default=2)
    parser.add_argument(
        "--tool-evidence-policy",
        choices=["off", "auto", "strict"],
        default=os.environ.get("LLM_QUALITY_TOOL_EVIDENCE_POLICY", "strict"),
        help=(
            "Gate booking-quality validity by calendar/confirm tool evidence "
            "(strict marks runs INVALID when booking intents lack tool/hook proof)."
        ),
    )
    parser.add_argument("--reset-before-dialog", action="store_true")
    parser.add_argument("--console-base-url", default=os.environ.get("CONSOLE_API_BASE_URL"))
    parser.add_argument("--console-token", default=None)
    parser.add_argument("--console-env", default="/home/zhan/secrets/console-contract.env")
    parser.add_argument("--console-client-id", default=None)
    parser.add_argument("--console-mode", choices=["real", "skip"], default="real")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--allow-output-overwrite", action="store_true")
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--brief-file",
        default=None,
        help="Write a compact markdown handoff summary (default: <output_dir>/brief.md).",
    )
    parser.add_argument(
        "--expected-runtime-commit",
        default=None,
        help="Expected runtime git commit; defaults to local git HEAD.",
    )
    parser.add_argument(
        "--baseline-summary",
        default=None,
        help="Use explicit summary.json as comparison baseline (instead of ops/results/booking_quality.json).",
    )
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--append-history", action="store_true")
    parser.add_argument("--history-max", type=int, default=20)
    parser.add_argument("--fail-on-thresholds", action="store_true")
    parser.add_argument("--fail-on-regression", action="store_true")
    parser.add_argument(
        "--max-failures",
        type=int,
        default=0,
        help="Stop early after this many failed turns (0 disables).",
    )
    parser.add_argument("--regression-tolerance", type=float, default=0.02)
    parser.add_argument(
        "--max-post-llm-semantic-rewrite-rate",
        type=float,
        default=0.02,
        help="Blocking budget for post-LLM semantic rewrites (fraction of policy-core turns).",
    )
    parser.add_argument(
        "--max-keyword-override-rate",
        type=float,
        default=0.0,
        help="Blocking budget for keyword/regex semantic overrides (fraction of policy-core turns).",
    )
    parser.add_argument(
        "--lexicon-regex-delta-gate",
        choices=["off", "warn", "block"],
        default=os.environ.get("LLM_QUALITY_LEXICON_REGEX_DELTA_GATE", "block"),
        help="Static guard for lexicon/regex deltas without resolver+test updates.",
    )
    parser.add_argument(
        "--delta-gate-base-ref",
        default=os.environ.get("LLM_QUALITY_DELTA_GATE_BASE_REF", "origin/main"),
        help="Base ref used to scan changed files for lexicon/regex delta gate.",
    )
    parser.add_argument(
        "--hardcode-core-gate",
        choices=["off", "warn", "block"],
        default=os.environ.get("LLM_QUALITY_HARDCODE_CORE_GATE", "block"),
        help="Static AST/diff gate for raw phrase/regex branching in webhook core files.",
    )
    parser.add_argument(
        "--hardcode-core-base-ref",
        default=os.environ.get("LLM_QUALITY_HARDCODE_CORE_BASE_REF", "origin/main"),
        help="Base ref used to scan changed files for hardcode core gate.",
    )
    parser.add_argument(
        "--run-economy-gate",
        choices=["off", "warn", "block"],
        default=os.environ.get("LLM_QUALITY_RUN_ECONOMY_GATE", "block"),
        help=(
            "Budget guard: block/warn on full runs without non-doc code delta "
            "and replay runs without baseline/reset guard."
        ),
    )
    parser.add_argument(
        "--run-economy-base-ref",
        default=os.environ.get("LLM_QUALITY_RUN_ECONOMY_BASE_REF", "origin/main"),
        help="Base ref used to scan changed files for run-economy gate.",
    )
    parser.add_argument(
        "--allow-no-code-delta",
        action="store_true",
        help="Allow full run with doc-only/empty diff (debug-only override).",
    )
    parser.add_argument(
        "--judge-mode", choices=["off", "sample", "all", "critical"], default="off"
    )
    parser.add_argument("--judge-sample", type=float, default=0.1)
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument(
        "--judge-base-url",
        default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com"),
    )
    parser.add_argument("--judge-api-key", default=None)
    parser.add_argument("--judge-timeout", type=float, default=25.0)
    parser.add_argument("--judge-max-tokens", type=int, default=320)
    parser.add_argument("--judge-seed", type=int, default=None)
    parser.add_argument("--judge-cache-file", default=None)
    parser.add_argument("--judge-cache-max-entries", type=int, default=5000)
    parser.add_argument("--judge-no-redact", action="store_false", dest="judge_redact")
    parser.add_argument(
        "--allow-judge-off",
        action="store_true",
        help="Allow strict replay without judge (debug only).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.set_defaults(judge_redact=True)
    args = parser.parse_args(argv)
    if not isinstance(args.base_url, str) or not args.base_url.strip():
        parser.error(
            "llm-quality: --base-url is required "
            "(pass --base-url or set TRUFFLES_API_BASE_URL)"
        )
    args.base_url = args.base_url.strip()
    return _llm_quality_apply_timeout_profile(args)


def _parse_llm_quality_gates_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py llm-quality-gates",
        description="Run static llm-quality gates without runtime/webhook execution.",
    )
    parser.add_argument(
        "--lexicon-regex-delta-gate",
        choices=["off", "warn", "block"],
        default=os.environ.get("LLM_QUALITY_LEXICON_REGEX_DELTA_GATE", "block"),
        help="Static guard for lexicon/regex deltas without resolver+test updates.",
    )
    parser.add_argument(
        "--delta-gate-base-ref",
        default=os.environ.get("LLM_QUALITY_DELTA_GATE_BASE_REF", "origin/main"),
        help="Base ref used for lexicon/regex delta scan.",
    )
    parser.add_argument(
        "--hardcode-core-gate",
        choices=["off", "warn", "block"],
        default=os.environ.get("LLM_QUALITY_HARDCODE_CORE_GATE", "block"),
        help="Static guard for phrase/regex branching in webhook core files.",
    )
    parser.add_argument(
        "--hardcode-core-base-ref",
        default=os.environ.get("LLM_QUALITY_HARDCODE_CORE_BASE_REF", "origin/main"),
        help="Base ref used for hardcode-core scan.",
    )
    parser.add_argument(
        "--run-economy-gate",
        choices=["off", "warn", "block"],
        default=os.environ.get("LLM_QUALITY_RUN_ECONOMY_GATE", "block"),
        help="Budget guard for replay/full run contracts.",
    )
    parser.add_argument(
        "--run-economy-base-ref",
        default=os.environ.get("LLM_QUALITY_RUN_ECONOMY_BASE_REF", "origin/main"),
        help="Base ref used for run-economy changed-files scan.",
    )
    parser.add_argument(
        "--scenarios-file",
        default=None,
        help="Replay scenarios path; enables replay branch of run-economy gate.",
    )
    parser.add_argument(
        "--baseline-summary",
        default=None,
        help="Baseline summary.json path used for replay canonicality checks.",
    )
    parser.add_argument(
        "--reset-before-dialog",
        action="store_true",
        help="Mark replay as isolated; required by replay run-economy policy.",
    )
    parser.add_argument(
        "--jid-mode",
        choices=["auto", "round_robin", "random", "unique"],
        default="auto",
        help="JID mode fed into run-economy replay contract checks.",
    )
    parser.add_argument(
        "--runtime-commit",
        default=None,
        help="Runtime commit token for replay fingerprint checks.",
    )
    parser.add_argument(
        "--judge-mode",
        choices=["off", "sample", "all", "critical"],
        default="off",
        help="Judge mode token for replay fingerprint checks.",
    )
    parser.add_argument(
        "--previous-replay-fingerprint",
        default=None,
        help="Previous replay fingerprint to block unchanged reruns.",
    )
    parser.add_argument(
        "--allow-no-code-delta",
        action="store_true",
        help="Allow empty/doc-only diff for full-run run-economy check.",
    )
    parser.add_argument("--output", default=None, help="Optional JSON output file path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args(argv)


def _parse_llm_quality_matrix_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py llm-quality-matrix",
        description=(
            "Run llm-quality with identical args across multiple client slugs "
            "and produce matrix_summary.json."
        ),
    )
    parser.add_argument(
        "--client-slugs",
        required=True,
        help="Comma-separated client slugs, e.g. demo_salon,clinic_pack,spa_pack",
    )
    parser.add_argument(
        "--run-id-prefix",
        default=None,
        help="Prefix for child run_id values (default: matrix-<utc-timestamp>).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Matrix output directory (default: /tmp/booking_quality/<run-id-prefix>).",
    )
    parser.add_argument("--allow-output-overwrite", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    args, llm_quality_args = parser.parse_known_args(argv)
    args.llm_quality_args = list(llm_quality_args or [])
    return args

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
                cleaned_key = key.strip()
                cleaned_value = value.strip().strip('"').strip("'")
                if cleaned_value.startswith("${") and cleaned_value.endswith("}") and len(cleaned_value) > 3:
                    ref_key = cleaned_value[2:-1].strip()
                    if ref_key:
                        cleaned_value = (
                            env.get(ref_key)
                            or os.environ.get(ref_key)
                            or cleaned_value
                        )
                elif cleaned_value.startswith("$") and len(cleaned_value) > 1:
                    ref_key = cleaned_value[1:].strip()
                    if ref_key and all(ch.isalnum() or ch == "_" for ch in ref_key):
                        cleaned_value = (
                            env.get(ref_key)
                            or os.environ.get(ref_key)
                            or cleaned_value
                        )
                env[cleaned_key] = cleaned_value
    except Exception:
        return {}
    return env


def _clean_api_key(value):
    if not value:
        return None
    cleaned = str(value).strip().strip('"').strip("'")
    return cleaned or None


def _export_openai_api_key(value):
    cleaned = _clean_api_key(value)
    if not cleaned:
        return False
    os.environ["OPENAI_API_KEY"] = cleaned
    return True


def _parent_env_candidates(start_path):
    current = os.path.abspath(start_path or os.getcwd())
    candidates = []
    seen = set()
    while True:
        for rel in ("truffles-api/.env", ".env"):
            candidate = os.path.join(current, rel)
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return candidates


def _openai_key_candidate_env_files():
    parent_candidate_builder = globals().get("_parent_env_candidates")
    if not callable(parent_candidate_builder):
        def parent_candidate_builder(start_path):
            current = os.path.abspath(start_path or os.getcwd())
            candidates = []
            seen = set()
            while True:
                for rel in ("truffles-api/.env", ".env"):
                    candidate = os.path.join(current, rel)
                    if candidate not in seen:
                        seen.add(candidate)
                        candidates.append(candidate)
                parent = os.path.dirname(current)
                if parent == current:
                    break
                current = parent
            return candidates

    script_file = globals().get("__file__")
    if script_file:
        script_dir = os.path.dirname(os.path.abspath(script_file))
    else:
        script_dir = os.path.join(os.getcwd(), "ops")
    repo_root = os.path.dirname(script_dir)
    parent_candidates = parent_candidate_builder(os.getcwd())
    parent_candidates.extend(parent_candidate_builder(script_dir))
    candidates = [
        os.environ.get("TRUFFLES_API_ENV_FILE"),
        os.environ.get("ENV_FILE"),
        os.path.join(os.getcwd(), "truffles-api", ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(repo_root, "truffles-api", ".env"),
        os.path.join(repo_root, ".env"),
        "/home/zhan/truffles-main/truffles-api/.env",
        "/home/zhan/truffles-main/.env",
        "/home/zhan/truffles-main-deploy/truffles-api/.env",
        "/home/zhan/truffles-main-deploy/.env",
        "/home/zhan/infrastructure/.env",
        *parent_candidates,
    ]
    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if not item:
            continue
        path = os.path.abspath(os.path.expanduser(str(item)))
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique


def _resolve_openai_api_key(explicit=None, *, container_name=None):
    key_aliases = (
        "OPENAI_API_KEY",
        "OPENAI_KEY",
        "OPENAI_API_TOKEN",
        "OPENAI_TOKEN",
        "LLM_API_KEY",
        "OPENAI_JUDGE_API_KEY",
        "JUDGE_API_KEY",
    )

    def _alias_source(prefix: str, alias: str) -> str:
        if alias == "OPENAI_API_KEY":
            return prefix
        return f"{prefix}:{alias}"

    key = _clean_api_key(explicit)
    if key:
        return key, "explicit"

    for alias in key_aliases:
        env_key = _clean_api_key(os.environ.get(alias))
        if env_key:
            return env_key, _alias_source("env:OPENAI_API_KEY", alias)

    for env_path in _openai_key_candidate_env_files():
        env_map = _load_env_file(env_path)
        for alias in key_aliases:
            file_key = _clean_api_key(env_map.get(alias))
            if file_key:
                return file_key, _alias_source(f"env_file:{env_path}", alias)

    if container_name:
        for alias in key_aliases:
            container_key = _clean_api_key(_resolve_env_from_container(container_name, alias))
            if container_key:
                return container_key, _alias_source(f"container:{container_name}", alias)

    return None, None


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

def _parse_dialog_report_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py dialog-report",
        description="Generate a dialog report (timeline + decisions + outbox + media/ASR).",
    )
    parser.add_argument("--date", default=None, help="Date for the local time window (YYYY-MM-DD).")
    parser.add_argument(
        "--start",
        required=True,
        help="Start time (HH:MM[:SS] or YYYY-MM-DD HH:MM[:SS]).",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End time (HH:MM[:SS] or YYYY-MM-DD HH:MM[:SS]).",
    )
    parser.add_argument("--tz", default="Asia/Almaty", help="Timezone for the time window.")
    parser.add_argument("--sender", default=None, help="Sender phone (used to derive remote_jid).")
    parser.add_argument("--remote-jid", default=None, help="Sender remote_jid (overrides --sender).")
    parser.add_argument("--receiver-phone", default=None, help="Receiver phone (branch).")
    parser.add_argument("--conversation-id", default=None)
    parser.add_argument("--client-slug", default=None)
    parser.add_argument("--branch-id", default=None)
    parser.add_argument("--output", default=None, help="Output markdown path (use '-' for stdout).")
    parser.add_argument("--max-conversations", type=int, default=3)
    return parser.parse_args(argv)

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

def _fetch_client_branch_sender_jids(db_user, client_id):
    if not client_id:
        return set(), None
    safe_client = _escape_sql_literal(client_id)
    query = (
        "SELECT b.phone "
        "FROM branches b "
        f"WHERE b.client_id = '{safe_client}' "
        "AND b.is_active = TRUE "
        "AND b.phone IS NOT NULL;"
    )
    rows_raw, error = _run_psql_query(db_user, query)
    if error:
        return set(), error
    sender_jids = set()
    for line in (rows_raw or "").splitlines():
        phone = line.strip()
        if not phone:
            continue
        remote_jid = _normalize_remote_jid(phone)
        if remote_jid:
            sender_jids.add(remote_jid)
    return sender_jids, None

def _filter_sender_jids(allowlist_jids, blocked_sender_jids):
    if not allowlist_jids:
        return [], []
    blocked = {
        (_normalize_remote_jid(jid) or str(jid).strip())
        for jid in (blocked_sender_jids or set())
        if jid
    }
    filtered = []
    dropped = []
    for jid in allowlist_jids:
        normalized = _normalize_remote_jid(jid) or str(jid).strip()
        if normalized in blocked:
            dropped.append(jid)
            continue
        filtered.append(jid)
    return filtered, dropped

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

def _normalize_remote_jid(value):
    if not value:
        return None
    text = str(value).strip()
    if "@" in text:
        return text
    digits = _normalize_phone_digits(text)
    if not digits:
        return None
    return f"{digits}@s.whatsapp.net"

def _sanitize_timezone(value):
    if not value:
        return "Asia/Almaty"
    text = str(value).strip()
    if not re.fullmatch(r"[A-Za-z0-9_+/\-]+", text):
        raise SystemExit("dialog-report: invalid timezone")
    return text

def _normalize_datetime_input(value, date_hint):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("T", " ")
    if re.search(r"\d{4}-\d{2}-\d{2}", text):
        base = text
    else:
        if not date_hint:
            raise SystemExit("dialog-report: --date required when time has no date")
        base = f"{date_hint} {text}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", base):
        base = f"{base}:00"
    return base

def _clean_webhook_secret(value):
    if not value:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _resolve_webhook_secret_with_source(client_slug, explicit, *, expected_secret=None):
    explicit_secret = _clean_webhook_secret(explicit)
    if explicit_secret:
        return explicit_secret, "explicit"
    for env_name in ("WEBHOOK_SECRET", "TRUFFLES_WEBHOOK_SECRET"):
        env_value = _clean_webhook_secret(os.environ.get(env_name))
        if env_value:
            return env_value, f"env:{env_name}"
    expected_clean = _clean_webhook_secret(expected_secret)
    if expected_clean:
        return expected_clean, "runtime_expected"
    if not client_slug:
        return None, None
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
        return None, None
    resolved = _clean_webhook_secret(result.stdout.strip())
    if resolved:
        return resolved, "client_settings"
    return None, None


def _resolve_webhook_secret(client_slug, explicit, *, expected_secret=None):
    secret, _source = _resolve_webhook_secret_with_source(
        client_slug, explicit, expected_secret=expected_secret
    )
    return secret


def _livecheck_select_webhook_secret(*, client_slug, explicit_secret, client_meta):
    explicit_clean = _clean_webhook_secret(explicit_secret)
    expected_secret, expected_source = _llm_quality_resolve_expected_webhook_secret(client_meta)

    if explicit_clean:
        if expected_secret and explicit_clean != expected_secret:
            raise SystemExit(
                "livecheck-auto: explicit webhook secret mismatch "
                f"(expected_source={expected_source})"
            )
        return explicit_clean, "explicit"

    if expected_secret:
        return expected_secret, f"runtime_expected:{expected_source}"

    fallback_secret, fallback_source = _resolve_webhook_secret_with_source(
        client_slug,
        None,
        expected_secret=None,
    )
    return fallback_secret, fallback_source

def _resolve_psql_timeout(timeout=None):
    if timeout is not None:
        try:
            return max(1.0, float(timeout))
        except (TypeError, ValueError):
            return 8.0
    raw = os.environ.get("DIAGNOSE_PSQL_TIMEOUT_SEC", "8")
    try:
        return max(1.0, float(raw))
    except (TypeError, ValueError):
        return 8.0

def _run_psql_query(db_user, query, *, timeout=None):
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
        ],
        timeout=_resolve_psql_timeout(timeout),
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

def _fetch_client_meta(db_user, client_slug, *, branch_slug=None):
    safe_slug = _escape_sql_literal(client_slug)
    branch_filter = ""
    if branch_slug:
        safe_branch = _escape_sql_literal(branch_slug)
        branch_filter = f"AND b.slug = '{safe_branch}' "
    query = (
        "SELECT c.id, c.config->>'instance_id', b.id, b.instance_id, b.slug, "
        "b.webhook_secret, cs.webhook_secret, cs.telegram_chat_id, cs.owner_telegram_id "
        "FROM clients c "
        "LEFT JOIN branches b ON b.client_id = c.id AND b.is_active = TRUE "
        f"{branch_filter}"
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
        "branch_slug": parts[4] if len(parts) > 4 and parts[4] else None,
        "branch_webhook_secret": _clean_webhook_secret(parts[5] if len(parts) > 5 else None),
        "client_webhook_secret": _clean_webhook_secret(parts[6] if len(parts) > 6 else None),
        "telegram_chat_id": parts[7] if len(parts) > 7 and parts[7] else None,
        "owner_telegram_id": parts[8] if len(parts) > 8 and parts[8] else None,
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

def _settle_state_after_manager_actions(
    db_user,
    client_id,
    remote_jid,
    initial_state,
    *,
    settle_seconds=1.5,
    interval=0.3,
):
    if initial_state not in {"pending", "manager_active"}:
        return None, initial_state, None
    deadline = time.time() + max(settle_seconds, 0.0)
    last_conv_id = None
    last_state = initial_state
    last_error = None
    while time.time() <= deadline:
        conv_id, state, error = _fetch_latest_conversation_state(
            db_user, client_id, remote_jid
        )
        if conv_id:
            last_conv_id = conv_id
        if state:
            last_state = state
        if error:
            last_error = error
        if last_state == "bot_active":
            break
        time.sleep(max(interval, 0.2))
    return last_conv_id, last_state, last_error

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

def _llm_quality_retry_outbox_for_expected_reply(
    *,
    expected_response,
    bot_response,
    db_user,
    client_id,
    inbound_message_id,
    inline_response_text,
    outbox_summary,
    outbox_payload,
    outbox_payload_status,
    outbox_text,
    outbox_wait_seconds,
    poll_interval,
):
    if (
        not expected_response
        or bot_response
        or not db_user
        or not client_id
        or not inbound_message_id
    ):
        return outbox_summary, outbox_payload, outbox_payload_status, outbox_text, bot_response
    sleep_seconds = max(0.2, min(float(poll_interval or 0.6), 0.8))
    wait_budget = max(float(outbox_wait_seconds or 0.0), sleep_seconds * 2)
    attempts = max(1, min(6, int(math.ceil(wait_budget / sleep_seconds))))
    last_summary = outbox_summary
    last_payload = outbox_payload
    last_status = outbox_payload_status
    last_text = outbox_text
    for _ in range(attempts):
        time.sleep(sleep_seconds)
        retry_summary, _ = _fetch_outbox_summary(db_user, client_id, inbound_message_id)
        retry_payload, retry_status, _ = _llm_quality_fetch_outbox_payload(
            db_user, client_id, inbound_message_id
        )
        retry_text = _llm_quality_extract_outbox_text(retry_payload)
        if not retry_text and inline_response_text:
            retry_text = inline_response_text
        last_summary = retry_summary
        last_payload = retry_payload
        last_status = retry_status
        last_text = retry_text
        retry_bot_response = _llm_quality_has_bot_reply(
            outbox_summary=retry_summary,
            outbox_payload_status=retry_status,
            outbox_text=retry_text,
            inline_response_text=inline_response_text,
        )
        if retry_bot_response:
            return retry_summary, retry_payload, retry_status, retry_text, True
    return last_summary, last_payload, last_status, last_text, bot_response

def _llm_quality_payload_is_duplicate_ack(response_payload):
    marker = "duplicate message_id"
    if isinstance(response_payload, str):
        return marker in response_payload.casefold()
    if not isinstance(response_payload, dict):
        return False
    for field in ("message", "error"):
        value = response_payload.get(field)
        if isinstance(value, str) and marker in value.casefold():
            return True
    nested_response = response_payload.get("response")
    if isinstance(nested_response, str):
        if marker in nested_response.casefold():
            return True
        try:
            nested_payload = json.loads(nested_response)
        except Exception:
            nested_payload = None
        if _llm_quality_payload_is_duplicate_ack(nested_payload):
            return True
    return False

def _llm_quality_should_infer_bot_response_from_duplicate_ack(
    *,
    bot_response,
    expected_response,
    response_payload,
    attempts,
    meta,
    meta_error,
    state,
    outbox_payload_status=None,
    outbox_summary=None,
    trace_entries=None,
):
    if bot_response or not expected_response:
        return False
    if attempts <= 1:
        return False
    if meta_error or not isinstance(meta, dict):
        return False
    if not _llm_quality_payload_is_duplicate_ack(response_payload):
        return False
    delivery_state = ""
    delivery_state_resolver = globals().get("_llm_quality_outbox_delivery_state")
    if callable(delivery_state_resolver):
        delivery_state = delivery_state_resolver(outbox_payload_status, outbox_summary) or ""
    elif isinstance(outbox_payload_status, str) and outbox_payload_status.strip().upper() == "FAILED":
        delivery_state = "failed"
    if delivery_state == "failed":
        return False
    delivery_error_kind = str(meta.get("delivery_error_kind") or "").strip().lower()
    delivery_error_code = str(meta.get("delivery_error_code") or "").strip().upper()
    if delivery_error_kind in {"billing_blocked", "provider_billing_blocked", "auth", "provider_auth"}:
        return False
    if "BILLING_BLOCKED" in delivery_error_code or "AUTH" in delivery_error_code:
        return False
    if isinstance(trace_entries, list):
        for entry in reversed(trace_entries):
            if not isinstance(entry, dict):
                continue
            if str(entry.get("stage") or "").strip().lower() != "transport":
                continue
            reason = str(entry.get("reason") or "").strip().lower()
            code = str(entry.get("error_code") or "").strip().upper()
            if reason in {"provider_billing_blocked", "provider_auth"}:
                return False
            if "BILLING_BLOCKED" in code or "AUTH" in code:
                return False
            break
    if state in {"pending", "manager_active"}:
        return False
    action = meta.get("action") or meta.get("pending_action")
    if not isinstance(action, str):
        return False
    if action in CHAOS_PENDING_ACTIONS:
        return False
    if action in {
        "escalate",
        "booking_captured_pending",
        "booking_reuse_handover",
        "booking_paused",
    }:
        return False
    return action in {
        "reply",
        "match",
        "ai_response",
        "booking_prompt",
        "smalltalk",
        "booking_confirm",
        "booking_escalated",
    }

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

def _parse_json_lines(rows_raw):
    if not rows_raw:
        return []
    rows = []
    for line in rows_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows

def _fetch_dialog_conversation_ids(db_user, branch_id, remote_jid, tz_name, start_ts, end_ts):
    safe_branch = _escape_sql_literal(branch_id)
    safe_jid = _escape_sql_literal(remote_jid)
    safe_tz = _escape_sql_literal(tz_name)
    safe_start = _escape_sql_literal(start_ts)
    safe_end = _escape_sql_literal(end_ts)
    query = (
        "SELECT DISTINCT m.conversation_id "
        "FROM messages m "
        "JOIN conversations c ON c.id = m.conversation_id "
        "JOIN users u ON u.id = c.user_id "
        "WHERE m.role = 'user' "
        f"AND c.branch_id = '{safe_branch}' "
        f"AND u.remote_jid = '{safe_jid}' "
        f"AND (m.created_at AT TIME ZONE '{safe_tz}') BETWEEN '{safe_start}' AND '{safe_end}' "
        "ORDER BY m.conversation_id;"
    )
    rows_raw, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not rows_raw:
        return [], None
    return [line.strip() for line in rows_raw.splitlines() if line.strip()], None

def _fetch_dialog_rows(db_user, conversation_id, tz_name, start_ts, end_ts):
    safe_conv = _escape_sql_literal(conversation_id)
    safe_tz = _escape_sql_literal(tz_name)
    safe_start = _escape_sql_literal(start_ts)
    safe_end = _escape_sql_literal(end_ts)
    query = (
        "SELECT json_build_object("
        "'created_at', m.created_at, "
        f"'ts_local', (m.created_at AT TIME ZONE '{safe_tz}'), "
        "'role', m.role, "
        "'content', m.content, "
        "'message_id', m.metadata->>'messageId', "
        "'message_uuid', m.id, "
        "'conversation_id', c.id, "
        "'client_id', m.client_id, "
        "'remote_jid', u.remote_jid, "
        "'instance_id', m.metadata->>'instanceId', "
        "'media_type', m.metadata->'media'->>'media_type', "
        "'media_storage_path', m.metadata->'media'->>'storage_path', "
        "'media_url', m.metadata->'media'->>'url', "
        "'media_transcript', m.metadata->'media'->>'transcript', "
        "'asr_used', m.metadata->'asr'->>'asr_used', "
        "'asr_provider', m.metadata->'asr'->>'asr_provider', "
        "'decision_meta', m.metadata->'decision_meta', "
        "'outbox_id', o.id, "
        "'outbox_status', o.status, "
        f"'outbox_updated_at', (o.updated_at AT TIME ZONE '{safe_tz}'), "
        "'outbox_error', o.last_error"
        ") "
        "FROM messages m "
        "JOIN conversations c ON c.id = m.conversation_id "
        "JOIN users u ON u.id = c.user_id "
        "LEFT JOIN outbox_messages o "
        "ON o.client_id = m.client_id AND o.inbound_message_id = m.metadata->>'messageId' "
        f"WHERE m.conversation_id = '{safe_conv}' "
        f"AND (m.created_at AT TIME ZONE '{safe_tz}') BETWEEN '{safe_start}' AND '{safe_end}' "
        "ORDER BY m.created_at ASC;"
    )
    rows_raw, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    return _parse_json_lines(rows_raw), None

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

def _parse_message_meta_row(row):
    row_text = (row or "").strip()
    if not row_text:
        return None, None
    parts = row_text.split("\t", 1)
    conversation_id = parts[0] if parts else None
    meta_raw = parts[1] if len(parts) > 1 else None
    if meta_raw:
        try:
            meta = json.loads(meta_raw)
        except Exception:
            meta = None
    else:
        meta = None
    return conversation_id, meta


def _fetch_message_meta_by_conversation(db_user, conversation_id, *, timeout=None):
    if not conversation_id:
        return None, None, "missing conversation_id_hint"
    safe_conv_id = str(conversation_id).replace("'", "''")
    query = (
        "SELECT conversation_id, metadata->'decision_meta' AS decision_meta "
        "FROM messages WHERE role='user' "
        f"AND conversation_id = '{safe_conv_id}' "
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
        ],
        timeout=_resolve_psql_timeout(timeout),
    )
    if result.returncode != 0:
        return None, None, result.stderr.strip()
    return (*_parse_message_meta_row(result.stdout), None)


def _fetch_message_meta(db_user, message_id, *, timeout=None, conversation_id_hint=None):
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
        ],
        timeout=_resolve_psql_timeout(timeout),
    )
    primary_error = result.stderr.strip() if result.returncode != 0 else None
    if result.returncode == 0:
        conversation_id, meta = _parse_message_meta_row(result.stdout)
        if conversation_id or meta is not None:
            return conversation_id, meta, None
        return None, None, None
    # Fallback by conversation_id for transient slow JSON-path scans on messageId lookup.
    # This keeps LLM-quality runs from false hard fails when webhook already returned
    # a concrete conversation_id but the messageId query timed out under load.
    timeout_error = "timeout" in primary_error.casefold() if isinstance(primary_error, str) else False
    if conversation_id_hint and timeout_error:
        hint_conv_id, hint_meta, hint_error = _fetch_message_meta_by_conversation(
            db_user,
            conversation_id_hint,
            timeout=max(12.0, _resolve_psql_timeout(timeout)),
        )
        if hint_conv_id or hint_meta is not None:
            return hint_conv_id, hint_meta, None
        if hint_error:
            return None, None, hint_error
    return None, None, primary_error

def _poll_decision_meta(
    db_user,
    message_id,
    timeout,
    interval,
    require_action=True,
    fail_fast_after=None,
    conversation_id_hint=None,
):
    deadline = time.time() + max(timeout, 0)
    last_meta = None
    last_conv_id = None
    last_error = None
    missing_action_since = None
    while time.time() <= deadline:
        conversation_id, meta, error = _fetch_message_meta(
            db_user,
            message_id,
            # Avoid tiny per-query timeouts (1-2s) that create false
            # decision_meta_missing/decision_trace_missing under normal docker latency.
            timeout=None,
            conversation_id_hint=conversation_id_hint,
        )
        if error:
            last_error = error
        if conversation_id:
            last_conv_id = conversation_id
        if meta:
            last_meta = meta
            if not require_action:
                return last_conv_id, last_meta, None
            if _decision_meta_ready(meta):
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
                            "decision_meta_not_ready (message_id="
                            f"{message_id}, conv_id={last_conv_id}, meta_keys={meta_keys})"
                        ),
                    )
        time.sleep(max(interval, 0.2))
    # One final relaxed fetch before declaring timeout to reduce transient
    # false infra fails on slow DB write visibility.
    final_conv_id, final_meta, final_error = _fetch_message_meta(
        db_user,
        message_id,
        timeout=max(8.0, max(timeout, 0.0)),
        conversation_id_hint=conversation_id_hint,
    )
    if final_conv_id:
        last_conv_id = final_conv_id
    if final_meta:
        last_meta = final_meta
        if not require_action or _decision_meta_ready(final_meta):
            return last_conv_id, last_meta, None
    if final_error:
        last_error = final_error
    return last_conv_id, last_meta, last_error or "timeout"


def _decision_meta_ready(meta):
    if not isinstance(meta, dict):
        return False
    if meta.get("action") or meta.get("pending_action") or meta.get("policy_gate"):
        return True
    timing = meta.get("timing")
    if isinstance(timing, dict) and timing.get("pipeline_finished_at"):
        return True
    if meta.get("source") and meta.get("intent"):
        return True
    return False


def _trace_filter_since(trace_entries, min_recorded_at):
    entries = [entry for entry in (trace_entries or []) if isinstance(entry, dict)]
    if not min_recorded_at:
        return entries, False
    min_ts = _parse_iso_datetime(min_recorded_at)
    if not min_ts:
        return entries, False
    fresh_entries = []
    stale_seen = False
    recorded_seen = False
    for entry in entries:
        recorded_at = _parse_iso_datetime(entry.get("recorded_at"))
        if recorded_at is None:
            if fresh_entries:
                fresh_entries.append(entry)
            continue
        recorded_seen = True
        if recorded_at >= min_ts:
            fresh_entries.append(entry)
        else:
            stale_seen = True
    if fresh_entries:
        return fresh_entries, stale_seen
    if not recorded_seen:
        return entries, False
    return [], stale_seen


def _trace_min_recorded_at(meta):
    if not isinstance(meta, dict):
        return None
    timing = meta.get("timing")
    if not isinstance(timing, dict):
        return None
    return _parse_iso_datetime(timing.get("pipeline_started_at"))


def _poll_decision_trace(db_user, conversation_id, timeout, interval, *, min_recorded_at=None):
    if not conversation_id:
        return None, [], "missing conversation_id"
    deadline = time.time() + max(timeout, 0)
    last_meta = None
    last_error = None
    last_trace = []
    saw_stale_trace = False
    while time.time() <= deadline:
        conv_meta, conv_error = _fetch_conversation_meta(db_user, conversation_id)
        if conv_error:
            last_error = conv_error
        elif conv_meta:
            last_meta = conv_meta
            context = conv_meta.get("context") if isinstance(conv_meta, dict) else None
            trace_list = context.get("decision_trace") if isinstance(context, dict) else None
            trace_entries = _trace_as_list(trace_list)
            filtered_trace, stale_seen = _trace_filter_since(trace_entries, min_recorded_at)
            if filtered_trace:
                return conv_meta, filtered_trace, None
            if trace_entries and stale_seen:
                saw_stale_trace = True
            last_trace = filtered_trace
        time.sleep(max(interval, 0.2))
    if saw_stale_trace and min_recorded_at:
        return last_meta, [], "trace_stale"
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
    payload_json = json.dumps(payload, ensure_ascii=False)
    connect_timeout = max(1.0, min(float(timeout), 3.0))
    max_time = max(1.0, float(timeout))
    marker = "__CURL_STATUS__"
    curl_cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        "--connect-timeout",
        str(connect_timeout),
        "--max-time",
        str(max_time),
        "-H",
        "Content-Type: application/json",
    ]
    if secret:
        curl_cmd += ["-H", f"X-Webhook-Secret: {secret}"]
    curl_cmd += [
        "--data-binary",
        "@-",
        "-w",
        f"\n{marker}%{{http_code}}",
        url,
    ]
    try:
        result = subprocess.run(
            curl_cmd,
            input=payload_json,
            capture_output=True,
            text=True,
            timeout=max_time + 2.0,
        )
    except FileNotFoundError:
        result = None
    except subprocess.TimeoutExpired as exc:
        return None, "", f"timeout: {max_time}s ({exc.__class__.__name__})"
    else:
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            return None, "", f"curl_error: rc={result.returncode} err={stderr}"
        output = result.stdout or ""
        if marker in output:
            body, status_raw = output.rsplit(f"\n{marker}", 1)
            try:
                status = int(status_raw.strip())
            except ValueError:
                status = None
            if status and status != 0:
                return status, body, None
            return None, body, f"curl_http_status:{status_raw.strip() or 'unknown'}"

    data = payload_json.encode("utf-8")
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
    except (TimeoutError, socket.timeout) as exc:
        return None, "", f"timeout: {exc}"
    except http.client.RemoteDisconnected as exc:
        return None, "", f"remote_disconnected: {exc}"
    except Exception as exc:
        return None, "", f"{exc.__class__.__name__}: {exc}"


def _http_get(url, timeout):
    req = urllib.request.Request(url, method="GET")
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
    except http.client.RemoteDisconnected as exc:
        return None, "", f"remote_disconnected: {exc}"
    except Exception as exc:
        return None, "", f"{exc.__class__.__name__}: {exc}"


def _is_infra_error(error):
    if not error:
        return False
    lowered = error.lower()
    markers = [
        "curl_error: rc=52",
        "empty reply from server",
        "remote_disconnected",
        "timeout",
        "timed out",
        "connection refused",
        "connection reset",
        "network is unreachable",
        "temporary failure",
        "name or service not known",
        "connection aborted",
        "broken pipe",
    ]
    return any(marker in lowered for marker in markers)


def _send_webhook_payload_with_retry(url, payload, secret, timeout, retry_count, retry_backoff):
    attempts = 0
    status = None
    body = ""
    error = None
    for attempt in range(retry_count + 1):
        attempts = attempt + 1
        status, body, error = _send_webhook_payload(url, payload, secret, timeout)
        if not error or not _is_infra_error(error):
            return status, body, error, attempts
        if attempt < retry_count:
            time.sleep(retry_backoff * (2 ** attempt))
    return status, body, error, attempts


def _chaos_preflight(base_url, timeout):
    checks = {}
    endpoints = {
        "admin_health": f"{base_url}/admin/health",
        "admin_version": f"{base_url}/admin/version",
    }
    ok = True
    for name, url in endpoints.items():
        status, body, error = _http_get(url, timeout)
        checks[name] = {
            "status": status,
            "error": error,
            "body": (body or "")[:300],
        }
        if name == "admin_health" and body and not error and status and status < 500:
            try:
                payload = json.loads(body)
            except Exception:
                payload = None
            if isinstance(payload, dict):
                safety = payload.get("safety")
                if isinstance(safety, dict):
                    danger_flags = safety.get("danger_flags")
                    if isinstance(danger_flags, list):
                        checks[name]["danger_flags"] = danger_flags
                        if danger_flags:
                            ok = False
        if error or status is None or status >= 500:
            ok = False
    return {"ok": ok, "checks": checks}


def _write_failure_bundle(output_dir, record, container_name):
    bundle_dir = os.path.join(output_dir, "failure_bundles")
    os.makedirs(bundle_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    case_id = record.get("case_id", "case")
    turn = record.get("turn", "0")
    base = f"{case_id}_turn{turn}_{stamp}"
    payload_path = os.path.join(bundle_dir, f"{base}.json")
    with open(payload_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    if not container_name:
        return
    since = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    log_result = run_command(["docker", "logs", "--since", since, container_name])
    if log_result.returncode != 0:
        return
    log_path = os.path.join(bundle_dir, f"{base}.log")
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(log_result.stdout)

def _post_outbox_once(url, headers, timeout):
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


def _build_outbox_process_candidates(url):
    normalized = url.rstrip("/")
    if normalized.endswith("/admin/outbox/process"):
        base = normalized[: -len("/admin/outbox/process")]
        # Service-first path keeps legacy endpoint as compatibility fallback.
        return [f"{base}/outbox/process", normalized]
    return [normalized]


def _post_admin_outbox(url, admin_token, timeout):
    outbox_service_token = os.environ.get("OUTBOX_SERVICE_TOKEN")
    candidates = _build_outbox_process_candidates(url)
    last_result = (None, "", "unknown outbox error")

    for candidate in candidates:
        headers = {}
        if candidate.endswith("/outbox/process") and outbox_service_token:
            headers["X-Outbox-Service-Token"] = outbox_service_token
        elif admin_token:
            headers["X-Admin-Token"] = admin_token

        status, body, error = _post_outbox_once(candidate, headers, timeout)
        last_result = (status, body, error)
        if status is None:
            continue
        if status in (401, 403, 404) and candidate != candidates[-1]:
            continue
        return status, body, error

    return last_result


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
                    "simulation_mode": False,
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

def _run_llm_quality(args):
    if args.count < 1:
        raise SystemExit("llm-quality: --count must be >= 1")
    if getattr(args, "scenario_llm_batch_size", 1) < 1:
        raise SystemExit("llm-quality: --scenario-llm-batch-size must be >= 1")
    if getattr(args, "scenario_llm_max_attempts", 1) < 1:
        raise SystemExit("llm-quality: --scenario-llm-max-attempts must be >= 1")
    if getattr(args, "scenario_llm_request_timeout", 1.0) <= 0:
        raise SystemExit("llm-quality: --scenario-llm-request-timeout must be > 0")
    if getattr(args, "scenario_llm_attempt_backoff", 0.0) < 0:
        raise SystemExit("llm-quality: --scenario-llm-attempt-backoff must be >= 0")
    if getattr(args, "scenario_gen_timeout", None) is not None and args.scenario_gen_timeout <= 0:
        raise SystemExit("llm-quality: --scenario-gen-timeout must be > 0")
    rng = random.Random(args.seed or int(time.time()))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = args.run_id or _llm_quality_build_default_run_id(timestamp)
    weak_oracle_debug_waiver = bool(
        args.allow_weak_oracle
        and args.judge_mode == "off"
        and args.allow_judge_off
        and not args.fail_on_thresholds
        and not args.fail_on_regression
    )
    if args.allow_weak_oracle and not weak_oracle_debug_waiver:
        raise SystemExit(
            "llm-quality: INVALID RUN - --allow-weak-oracle is debug-only "
            "(requires --judge-mode off --allow-judge-off and no fail-on-threshold/regression)"
        )
    output_dir = _llm_quality_prepare_output_dir(
        args.output_dir or os.path.join("/tmp/booking_quality", run_id),
        allow_overwrite=bool(getattr(args, "allow_output_overwrite", False)),
    )
    base_url = args.base_url.rstrip("/")
    runtime_preflight = _llm_quality_runtime_fingerprint_preflight(
        base_url=base_url,
        expected_commit=args.expected_runtime_commit,
        timeout=args.timeout,
    )
    runtime_preflight_payload = {
        "stage": "llm_quality_runtime_fingerprint_preflight",
        "valid": runtime_preflight.get("valid"),
        "reasons": runtime_preflight.get("reasons"),
        "endpoint": runtime_preflight.get("endpoint"),
        "expected_commit": runtime_preflight.get("expected_commit"),
        "expected_source": runtime_preflight.get("expected_source"),
        "runtime_commit": runtime_preflight.get("runtime_commit"),
        "runtime_version": runtime_preflight.get("runtime_version"),
        "runtime_error": runtime_preflight.get("runtime_error"),
    }
    print(json.dumps(runtime_preflight_payload, ensure_ascii=False))
    if not runtime_preflight.get("valid", False):
        raise SystemExit(
            "llm-quality: INVALID RUN - runtime fingerprint preflight failed "
            f"({','.join(runtime_preflight.get('reasons') or ['unknown'])})"
        )
    client_slug = args.client_slug
    webhook_url = f"{base_url}/webhook/{client_slug}"

    container_name, _ = resolve_container_name()
    allowlist_jids = _resolve_allowlist_jids(args.allowlist_jids, container_name)
    jid_mode_effective = _llm_quality_resolve_jid_mode(args)
    if args.jid_mode == "auto":
        print(
            json.dumps(
                {
                    "stage": "llm_quality_jid_mode",
                    "requested": "auto",
                    "resolved": jid_mode_effective,
                    "skip_outbox": bool(args.skip_outbox),
                },
                ensure_ascii=False,
            )
        )
    replay_isolation_valid = True
    replay_isolation_reasons = []
    if args.scenarios_file:
        if not args.reset_before_dialog:
            replay_isolation_valid = False
            replay_isolation_reasons.append("reset_before_dialog_required")
        if jid_mode_effective != "unique":
            replay_isolation_valid = False
            replay_isolation_reasons.append("jid_mode_unique_required")
    if args.scenarios_file:
        print(
            json.dumps(
                {
                    "stage": "llm_quality_replay_isolation_preflight",
                    "valid": replay_isolation_valid,
                    "reasons": replay_isolation_reasons,
                    "jid_mode": jid_mode_effective,
                    "reset_before_dialog": bool(args.reset_before_dialog),
                },
                ensure_ascii=False,
            )
        )
    if args.scenarios_file and not replay_isolation_valid:
        raise SystemExit(
            "llm-quality: INVALID RUN - replay isolation preflight failed "
            f"({','.join(replay_isolation_reasons)})"
        )
    if (
        jid_mode_effective == "unique"
        and not args.remote_jid
        and not args.skip_outbox
        and not args.allow_non_allowlist
    ):
        raise SystemExit(
            "llm-quality: --jid-mode unique requires --skip-outbox or --allow-non-allowlist"
        )
    if args.remote_jid:
        if allowlist_jids and args.remote_jid not in allowlist_jids and not args.allow_non_allowlist:
            raise SystemExit(
                f"llm-quality: remote-jid {args.remote_jid} not in allowlist; refusing to send"
            )
        if not allowlist_jids:
            allowlist_jids = [args.remote_jid]
    if not allowlist_jids and not args.allow_non_allowlist:
        raise SystemExit("llm-quality: allowlist-jids required for state mode")

    db_user = _resolve_db_user_simple()
    client_meta, client_error = _fetch_client_meta(
        db_user, client_slug, branch_slug=args.branch_slug
    )
    if client_error:
        raise SystemExit(f"llm-quality: client meta lookup failed ({client_error})")
    client_id = (client_meta or {}).get("client_id")
    branch_sender_jids, branch_sender_error = _fetch_client_branch_sender_jids(
        db_user, client_id
    )
    if branch_sender_error:
        print(
            json.dumps(
                {
                    "stage": "allowlist_filter_branch_sender",
                    "warning": branch_sender_error,
                },
                ensure_ascii=False,
            )
        )
    else:
        if args.remote_jid:
            remote_jid_normalized = _normalize_remote_jid(args.remote_jid)
            if remote_jid_normalized and remote_jid_normalized in branch_sender_jids:
                raise SystemExit(
                    f"llm-quality: remote-jid {args.remote_jid} matches active branch sender"
                )
        filtered_allowlist, dropped_sender_jids = _filter_sender_jids(
            allowlist_jids, branch_sender_jids
        )
        if dropped_sender_jids:
            print(
                json.dumps(
                    {
                        "stage": "allowlist_filter_branch_sender",
                        "dropped_jids": dropped_sender_jids,
                        "dropped_count": len(dropped_sender_jids),
                    },
                    ensure_ascii=False,
                )
            )
        if filtered_allowlist:
            allowlist_jids = filtered_allowlist
        elif allowlist_jids and not args.allow_non_allowlist:
            raise SystemExit(
                "llm-quality: allowlist-jids contains only active branch sender JIDs"
            )
    instance_id = (
        args.instance_id
        or (client_meta or {}).get("branch_instance_id")
        or (client_meta or {}).get("client_instance_id")
    )
    expected_webhook_secret, expected_secret_source = _llm_quality_resolve_expected_webhook_secret(
        client_meta
    )
    webhook_secret, webhook_secret_source = _resolve_webhook_secret_with_source(
        client_slug,
        args.webhook_secret,
        expected_secret=expected_webhook_secret,
    )
    secret_preflight = _llm_quality_webhook_secret_preflight(
        provided_secret=webhook_secret,
        expected_secret=expected_webhook_secret,
        expected_source=expected_secret_source,
        secret_source=webhook_secret_source,
    )
    requested_branch_slug = (
        args.branch_slug.strip() if isinstance(args.branch_slug, str) and args.branch_slug.strip() else None
    )
    if requested_branch_slug and not (client_meta or {}).get("branch_id"):
        secret_preflight["valid"] = False
        reasons = list(secret_preflight.get("reasons") or [])
        if "branch_not_resolved" not in reasons:
            reasons.append("branch_not_resolved")
        secret_preflight["reasons"] = reasons
    preflight_payload = {
        "stage": "llm_quality_webhook_secret_preflight",
        "valid": secret_preflight["valid"],
        "reasons": secret_preflight["reasons"],
        "client_slug": client_slug,
        "requested_branch_slug": requested_branch_slug,
        "branch_slug": (client_meta or {}).get("branch_slug"),
        "branch_id": (client_meta or {}).get("branch_id"),
        "expected_source": secret_preflight["expected_source"],
        "provided_source": secret_preflight["provided_source"],
        "expected_fingerprint": secret_preflight["expected_fingerprint"],
        "provided_fingerprint": secret_preflight["provided_fingerprint"],
    }
    print(json.dumps(preflight_payload, ensure_ascii=False))
    if not secret_preflight["valid"]:
        raise SystemExit(
            "llm-quality: INVALID RUN - webhook_secret preflight failed "
            f"({','.join(secret_preflight.get('reasons') or ['unknown'])})"
        )

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
        raise SystemExit("llm-quality: missing admin token for outbox/process")

    manager_actions = [
        action
        for action in _llm_quality_parse_actions(args.manager_actions)
        if action in {"take", "resolve", "return", "skip"}
    ] or ["resolve"]
    telegram_chat_id = None
    if client_meta and client_meta.get("telegram_chat_id"):
        try:
            telegram_chat_id = int(client_meta.get("telegram_chat_id"))
        except ValueError:
            telegram_chat_id = None
    owner_id, owner_username = _parse_owner_identity((client_meta or {}).get("owner_telegram_id"))
    manager_id = owner_id if owner_id is not None else 10001
    console_token = None
    console_headers = {}
    console_base_url = (args.console_base_url or base_url).rstrip("/")
    if args.manager_channel == "console":
        if args.console_mode == "skip":
            console_token = None
        else:
            console_token, console_error = _resolve_console_token(args)
            if console_error and args.manager_mode == "simulate":
                print(
                    json.dumps(
                        {"stage": "console_token_error", "error": console_error}, ensure_ascii=False
                    )
                )
                args.manager_mode = "check"
        if args.console_client_id:
            console_headers["X-Client-Id"] = args.console_client_id
        elif client_meta and client_meta.get("client_id"):
            console_headers["X-Client-Id"] = client_meta.get("client_id")

    llm_api_key, llm_api_key_source = _resolve_openai_api_key(
        args.llm_api_key,
        container_name=container_name,
    )
    if llm_api_key:
        args.llm_api_key = llm_api_key
        _export_openai_api_key(llm_api_key)
    elif args.mode == "llm":
        raise SystemExit(
            "llm-quality: missing OPENAI_API_KEY for llm-mode run "
            "(checked --llm-api-key, OPENAI_API_KEY aliases in env, *.env candidates, container env)"
        )

    judge_mode = args.judge_mode
    judge_api_key, judge_api_key_source = _resolve_openai_api_key(
        args.judge_api_key,
        container_name=container_name,
    )
    if not judge_api_key and args.llm_api_key:
        judge_api_key = args.llm_api_key
        judge_api_key_source = f"llm:{llm_api_key_source or 'explicit'}"
    if judge_api_key:
        _export_openai_api_key(judge_api_key)
    judge_enabled = judge_mode != "off"
    judge_skip_reason = "judge_mode_off" if judge_mode == "off" else None
    if judge_enabled and not judge_api_key:
        judge_enabled = False
        judge_skip_reason = "missing_api_key"
    if args.update_baseline and not judge_enabled:
        raise SystemExit(
            "llm-quality: cannot update canonical baseline with judge disabled "
            f"(reason={judge_skip_reason or 'judge_disabled'})"
        )
    judge_required = bool(args.scenarios_file and not args.allow_judge_off)
    if judge_required and not judge_enabled:
        raise SystemExit(
            "llm-quality: strict replay requires judge enabled "
            f"(reason={judge_skip_reason or 'judge_disabled'}; key_source={judge_api_key_source or 'none'}; "
            "use --judge-mode sample|all|critical and API key, "
            "or pass --allow-judge-off for debug-only runs)"
        )
    judge_seed = args.judge_seed if args.judge_seed is not None else args.seed
    judge_rng = random.Random(judge_seed or int(time.time()))
    judge_cache_file = None
    judge_cache = {}
    if judge_enabled:
        judge_cache_file = args.judge_cache_file or _llm_quality_default_judge_cache_file(
            args.judge_model, args.judge_base_url
        )
        judge_cache = _llm_quality_load_judge_cache(judge_cache_file)
    openai_preflight = []
    preflight_fingerprint_seen = set()

    def _run_openai_preflight_check(*, purpose, api_key, model, base_url, timeout):
        if not api_key:
            return None
        fingerprint = hashlib.sha256(
            f"{purpose}|{model}|{base_url}|{api_key}".encode("utf-8")
        ).hexdigest()
        if fingerprint in preflight_fingerprint_seen:
            return None
        preflight_fingerprint_seen.add(fingerprint)
        result = _llm_quality_openai_key_preflight(
            purpose=purpose,
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
        )
        openai_preflight.append(result)
        print(
            json.dumps(
                {
                    "stage": "llm_quality_openai_preflight",
                    "purpose": purpose,
                    "valid": result.get("valid"),
                    "reason": result.get("reason"),
                    "status": result.get("status"),
                    "elapsed_ms": result.get("elapsed_ms"),
                    "model": model,
                    "base_url": base_url,
                },
                ensure_ascii=False,
            )
        )
        if not result.get("valid"):
            raise SystemExit(
                "llm-quality: INVALID RUN - openai preflight failed "
                f"(purpose={purpose}, reason={result.get('reason')}, status={result.get('status')})"
            )
        return result

    # Hard preflight: if LLM mode is selected, verify key/quota before run.
    # For replay this still catches shared-key quota outages early.
    if args.mode == "llm" and args.llm_api_key:
        _run_openai_preflight_check(
            purpose="llm",
            api_key=args.llm_api_key,
            model=args.llm_model,
            base_url=args.llm_base_url,
            timeout=args.timeout,
        )
    if judge_enabled and judge_api_key:
        _run_openai_preflight_check(
            purpose="judge",
            api_key=judge_api_key,
            model=args.judge_model,
            base_url=args.judge_base_url,
            timeout=args.judge_timeout,
        )

    dialogs = []
    warnings = {}
    scenario_source = {"type": "generated", "path": None}
    scenario_artifact_status = {"checked": False, "missing": [], "valid": True}
    if args.scenarios_file:
        scenario_artifact_status = _llm_quality_validate_scenario_artifacts(
            args.scenarios_file,
            allow_incomplete=bool(args.allow_incomplete_run_artifacts),
        )
        dialogs, source_warnings, error = _llm_quality_load_dialogs_from_file(args.scenarios_file)
        if error:
            raise SystemExit(f"llm-quality: scenarios-file load failed ({error})")
        if isinstance(source_warnings, dict):
            warnings.update(source_warnings)
        scenario_source = {
            "type": "file",
            "path": os.path.abspath(os.path.expanduser(args.scenarios_file)),
        }
        if len(dialogs) < args.count:
            warnings.setdefault("scenario_source", []).append(
                f"requested_count={args.count},available={len(dialogs)}"
            )
        dialogs = dialogs[: args.count]
    else:
        batch_size = max(1, args.batch_size)
        seed_base = args.seed if args.seed is not None else int(time.time())
        batch_idx = 0
        while len(dialogs) < args.count:
            batch_count = min(batch_size, args.count - len(dialogs))
            batch_seed = seed_base + batch_idx if args.seed is not None else None
            retries = 0
            while True:
                batch_dialogs, batch_warnings, error = _llm_quality_generate_batch(
                    args, count=batch_count, seed=batch_seed
                )
                if not error and batch_dialogs:
                    break
                if retries >= args.retry_count:
                    raise SystemExit(f"llm-quality: scenario generation failed ({error})")
                time.sleep(args.retry_backoff * (2 ** retries))
                retries += 1
            dialogs.extend(batch_dialogs)
            if isinstance(batch_warnings, dict):
                warnings.update(batch_warnings)
            batch_idx += 1
        dialogs = dialogs[: args.count]

    if not dialogs:
        raise SystemExit("llm-quality: no dialogs to execute")

    scenario_contract = _llm_quality_build_scenario_contract_status(
        dialogs=dialogs,
        scenario_coverage=args.scenario_coverage,
        allow_weak_oracle=bool(args.allow_weak_oracle),
    )
    scenario_preflight_payload = {
        "stage": "llm_quality_scenario_contract_preflight",
        "valid": scenario_contract.get("valid"),
        "reasons": scenario_contract.get("reasons"),
        "coverage_tokens": scenario_contract.get("coverage_tokens"),
        "tag_counts": scenario_contract.get("tag_counts"),
        "dialogs_with_check_confirm_sequence": scenario_contract.get(
            "dialogs_with_check_confirm_sequence"
        ),
        "turn_count": scenario_contract.get("turn_count"),
        "weak_expectation_turns": scenario_contract.get("weak_expectation_turns"),
        "weak_expectation_ratio": scenario_contract.get("weak_expectation_ratio"),
        "reply_type_coverage": scenario_contract.get("reply_type_coverage"),
        "action_coverage": scenario_contract.get("action_coverage"),
        "info_coverage": scenario_contract.get("info_coverage"),
        "scenario_artifacts": scenario_artifact_status,
    }
    print(json.dumps(scenario_preflight_payload, ensure_ascii=False))
    if not scenario_contract.get("valid"):
        reason_tokens = scenario_contract.get("reasons") or ["unknown"]
        raise SystemExit(
            "llm-quality: INVALID RUN - scenario contract failed "
            f"({','.join(reason_tokens)})"
        )

    replay_state_path = _llm_quality_replay_fingerprint_state_path()
    replay_state_payload = _llm_quality_load_replay_fingerprint_state(replay_state_path)
    previous_replay_fingerprint = None
    if isinstance(replay_state_payload, dict):
        previous_replay_fingerprint = (
            str(replay_state_payload.get("replay_fingerprint") or "").strip() or None
        )
    baseline_preflight = _llm_quality_preflight_baseline_summary(args.baseline_summary)
    run_economy_status = _llm_quality_build_run_economy_status(
        mode=args.run_economy_gate,
        repo_root=_llm_quality_repo_root(),
        base_ref=args.run_economy_base_ref,
        scenarios_file=args.scenarios_file,
        baseline_summary=args.baseline_summary,
        reset_before_dialog=bool(args.reset_before_dialog),
        allow_no_code_delta=bool(args.allow_no_code_delta),
        jid_mode=jid_mode_effective,
        runtime_commit=runtime_preflight.get("runtime_commit"),
        judge_mode=judge_mode,
        previous_replay_fingerprint=previous_replay_fingerprint,
        baseline_preflight=baseline_preflight,
    )
    print(
        json.dumps(
            {
                "stage": "llm_quality_run_economy_preflight",
                "mode": run_economy_status.get("mode"),
                "valid": run_economy_status.get("valid"),
                "enforced": run_economy_status.get("enforced"),
                "reasons": run_economy_status.get("reasons"),
                "changed_files_count": run_economy_status.get("changed_files_count"),
                "non_doc_changed_files_count": run_economy_status.get("non_doc_changed_files_count"),
                "is_replay": run_economy_status.get("is_replay"),
                "replay_fingerprint": run_economy_status.get("replay_fingerprint"),
                "previous_replay_fingerprint": run_economy_status.get(
                    "previous_replay_fingerprint"
                ),
                "baseline_preflight": baseline_preflight,
            },
            ensure_ascii=False,
        )
    )
    if run_economy_status.get("enforced") and not run_economy_status.get("valid", True):
        reason_tokens = run_economy_status.get("reasons") or ["unknown"]
        raise SystemExit(
            "llm-quality: INVALID RUN - run economy gate failed "
            f"({','.join(reason_tokens)})"
        )

    scenarios_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "count": len(dialogs),
        "turn_range": [args.min_turns, args.max_turns],
        "source": scenario_source,
        "warnings": warnings,
        "dialogs": dialogs,
    }
    scenarios_path = os.path.join(output_dir, "scenarios.json")
    with open(scenarios_path, "w", encoding="utf-8") as handle:
        json.dump(scenarios_payload, handle, ensure_ascii=False, indent=2)
    replay_command = _llm_quality_build_replay_command(args, scenarios_path, len(dialogs))
    brief_path = (
        os.path.abspath(os.path.expanduser(args.brief_file))
        if args.brief_file
        else os.path.join(output_dir, "brief.md")
    )

    responses_path = os.path.join(output_dir, "responses.jsonl")
    trace_bundle_path = os.path.join(output_dir, "trace_bundle.jsonl")
    stats = {
        "dialogs": len(dialogs),
        "turns": 0,
        "turns_expected_response": 0,
        "turns_with_response": 0,
        "turns_missing_response": 0,
        "turns_expected_missing": 0,
        "trace_rows_written": 0,
        "turns_passed": 0,
        "turns_failed": 0,
        "turns_strict_passed": 0,
        "turns_strict_failed": 0,
        "turns_hard_failed": 0,
        "unknown_state": 0,
        "decision_meta_missing": 0,
        "decision_trace_missing": 0,
        "webhook_errors": 0,
        "infra_errors": 0,
        "decision_meta_errors": 0,
        "decision_trace_errors": 0,
        "info_mismatch": 0,
        "unobserved_turns": 0,
        "outbox_delivery_failed_turns": 0,
        "outbox_delivery_timeout_turns": 0,
        "weak_oracle_turns": 0,
        "suppressed_missed_question_count": 0,
        "policy_core_turns": 0,
        "policy_core_degraded_turns": 0,
        "policy_core_infra_errors": 0,
    }
    state_stats = {}
    info_stats = {
        "turns_with_info_request": 0,
        "turns_info_answered": 0,
        "turns_info_missed": 0,
        "by_tag": {tag: {"requested": 0, "answered": 0, "missed": 0} for tag in LLM_QUALITY_INFO_TAGS},
    }
    manager_stats = {
        "handovers_seen": 0,
        "actions": {"take": 0, "resolve": 0, "return": 0, "skip": 0},
        "errors": 0,
        "actions_total": 0,
        "actions_ok": 0,
    }
    booking_stats = {
        "turns": 0,
        "progress_opportunities": 0,
        "progressed": 0,
        "filled_slots_total": 0,
    }
    dedup_stats = {
        "backend": {"redis": 0, "db_fallback": 0, "unknown": 0},
        "fallback_reasons": {},
        "latency": {
            "total_ms": 0.0,
            "samples": 0,
            "redis_total_ms": 0.0,
            "redis_samples": 0,
            "db_total_ms": 0.0,
            "db_samples": 0,
            "messages_total_ms": 0.0,
            "messages_samples": 0,
        },
    }
    stage_stats = {
        "controller": {
            "total_expected": 0,
            "eligible": 0,
            "non_eligible": 0,
            "attempted": 0,
            "skipped": 0,
            "expected_reply_deferred": 0,
            "expected_reply_blocked": 0,
            "skip_reasons": {},
            "non_eligible_reasons": {},
        },
        "tool_selection": {
            "selected": 0,
            "ok": 0,
            "blocked": 0,
            "invalid": 0,
        },
        "tool_args": {
            "checked": 0,
            "valid": 0,
            "invalid": 0,
            "invalid_reasons": {},
        },
    }
    booking_progress = {}
    coverage_stats = {
        "turn_tags": {},
        "turn_kinds": {},
        "media_kind": {},
        "language": {},
        "noise": {"turns": 0, "noisy": 0},
        "intents": {},
        "actions": {},
        "expected_reply_type": {},
        "states": {},
        "trace_stages": {},
        "modality": {},
        "tools": {
            "events": {},
            "outcomes": {key: 0 for key in LLM_QUALITY_TOOL_OUTCOMES},
            "by_tool": {},
        },
        "tool_hooks": {
            "sent_total": 0,
            "errors": 0,
            "by_action": {},
        },
    }
    judge_stats = {
        "enabled": judge_enabled,
        "mode": judge_mode if judge_enabled else "off",
        "required": judge_required,
        "api_key_source": judge_api_key_source if judge_enabled else None,
        "sample": args.judge_sample,
        "model": args.judge_model if judge_enabled else None,
        "base_url": args.judge_base_url if judge_enabled else None,
        "cache_file": judge_cache_file if judge_enabled else None,
        "redact": args.judge_redact,
        "skip_reason": judge_skip_reason,
        "counts": {
            "candidates": 0,
            "judged": 0,
            "pass": 0,
            "fail": 0,
            "uncertain": 0,
            "errors": 0,
            "skipped": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        },
        "reasons": {},
        "skips": {},
    }
    pack_context = _llm_quality_load_pack_context(client_slug)
    judge_stats["pack"] = {
        "truth_loaded": bool(pack_context.get("truth")),
        "consult_playbook_loaded": bool(pack_context.get("consult_playbook")),
        "errors": pack_context.get("errors"),
        "paths": pack_context.get("paths"),
    }
    failures = []
    failure_counts = {}
    taxonomy_counts = {key: 0 for key in LLM_QUALITY_TAXONOMY_CATEGORIES}
    taxonomy_by_reason = {}
    tool_hook_state = {}
    rewrite_governance_state = _llm_quality_init_rewrite_governance_state()
    hq1_class_counts = {name: 0 for name in LLM_QUALITY_HQ1_CLASSES}
    hq1_bad_turn_count = 0

    def _bump_state(state, expected_response, replied):
        key = state or "unknown"
        entry = state_stats.setdefault(
            key,
            {
                "turns": 0,
                "replies": 0,
                "expected_turns": 0,
                "expected_replies": 0,
                "expected_missing": 0,
            },
        )
        entry["turns"] += 1
        if replied:
            entry["replies"] += 1
        if expected_response:
            entry["expected_turns"] += 1
            if replied:
                entry["expected_replies"] += 1
            else:
                entry["expected_missing"] += 1
        return key

    def _record_failure(reasons, record):
        if not reasons:
            return
        taxonomy_map = {}
        for reason in reasons:
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
            category = LLM_QUALITY_REASON_TAXONOMY.get(reason, "unknown")
            taxonomy_counts[category] = taxonomy_counts.get(category, 0) + 1
            taxonomy_by_reason[reason] = taxonomy_by_reason.get(reason, 0) + 1
            taxonomy_map[reason] = category
        if taxonomy_map:
            record["taxonomy"] = taxonomy_map
        if len(failures) < LLM_QUALITY_FAILURE_LIMIT:
            failures.append(record)

    def _record_judge_skip(reason):
        judge_stats["counts"]["skipped"] += 1
        judge_stats["skips"][reason] = judge_stats["skips"].get(reason, 0) + 1

    def _should_judge_turn(
        state,
        bot_response,
        text,
        *,
        turn_tags,
        expected_action,
        expected_reply_type,
        expected_state,
        expected_info_sections,
        info_tags,
        booking_active,
        booking_progress_expected,
        evaluation_reasons,
    ):
        should_judge, skip_reason = _llm_quality_should_judge_turn(
            judge_enabled=judge_enabled,
            judge_mode=judge_mode,
            state=state,
            bot_response=bot_response,
            user_text=text,
            turn_tags=turn_tags,
            expected_action=expected_action,
            expected_reply_type=expected_reply_type,
            expected_state=expected_state,
            expected_info_sections=expected_info_sections,
            info_tags=info_tags,
            booking_active=booking_active,
            booking_progress_expected=booking_progress_expected,
            evaluation_reasons=evaluation_reasons,
        )
        if not should_judge:
            return should_judge, skip_reason
        judge_stats["counts"]["candidates"] += 1
        if judge_mode == "sample" and args.judge_sample > 0:
            if judge_rng.random() >= args.judge_sample:
                return False, "sample_skip"
        return True, None

    def _send_telegram_action(action, handover_id, conv_meta):
        if not telegram_chat_id:
            return None, "", "telegram_chat_id_missing"
        topic_id = (conv_meta or {}).get("telegram_topic_id")
        payload = {
            "update_id": rng.randint(100000, 999999),
            "callback_query": {
                "id": f"sim-{uuid.uuid4().hex[:10]}",
                "from": {"id": manager_id, "is_bot": False, "first_name": "Sim"},
                "data": f"{action}_{handover_id}",
                "message": {
                    "message_id": rng.randint(1, 99999),
                    "date": int(time.time()),
                    "chat": {"id": telegram_chat_id, "type": "group"},
                },
            },
        }
        if topic_id:
            payload["callback_query"]["message"]["message_thread_id"] = topic_id
        return _send_webhook_payload(f"{base_url}/telegram-webhook", payload, None, args.timeout)

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

    def _simulate_manager_actions(handover_id, conv_meta, conversation_id):
        action_results = []
        state_before = (conv_meta or {}).get("state")
        for action in manager_actions:
            if action in manager_stats["actions"]:
                manager_stats["actions"][action] += 1
            manager_stats["actions_total"] += 1
            expected_state, expected_status = _llm_quality_expected_manager_state(
                action, state_before
            )
            if args.manager_channel == "console":
                status, body, error = _send_console_action(action, handover_id)
            else:
                status, body, error = _send_telegram_action(action, handover_id, conv_meta)
            if error and error not in {"console_skipped"}:
                manager_stats["errors"] += 1
            if args.manager_wait and args.manager_wait > 0:
                time.sleep(args.manager_wait)
            conv_meta_after = None
            handover_meta_after = None
            if conversation_id:
                conv_meta_after, _ = _fetch_conversation_meta(db_user, conversation_id)
                handover_meta_after, _ = _fetch_handover_meta(db_user, conversation_id)
            actual_state = (conv_meta_after or {}).get("state")
            actual_status = (handover_meta_after or {}).get("status") if handover_meta_after else None
            action_reasons = []
            if error and error not in {"console_skipped"}:
                action_reasons.append("manager_action_failed")
            if expected_state is not None and actual_state != expected_state:
                action_reasons.append("handoff_state_mismatch")
            if expected_status:
                if not handover_meta_after:
                    action_reasons.append("handover_missing")
                elif actual_status != expected_status:
                    action_reasons.append("handoff_status_mismatch")
            if not action_reasons:
                manager_stats["actions_ok"] += 1
            action_record = {
                "action": action,
                "status": status,
                "error": error,
                "response": (body or "")[:200] if body else None,
                "state_before": state_before,
                "state_after": actual_state,
                "expected_state": expected_state,
                "expected_status": expected_status,
                "actual_status": actual_status,
                "reasons": action_reasons,
            }
            if action_reasons:
                _record_failure(
                    action_reasons,
                    {
                        "type": "manager_action",
                        "action": action,
                        "conversation_id": conversation_id,
                        "handover_id": handover_id,
                        "state_before": state_before,
                        "state_after": actual_state,
                        "expected_state": expected_state,
                        "expected_status": expected_status,
                        "actual_status": actual_status,
                        "error": error,
                        "reasons": action_reasons,
                    },
                )
            action_results.append(action_record)
            if actual_state:
                state_before = actual_state
        return action_results

    def _send_pending_ack(remote_jid):
        if args.pending_mode != "ack":
            return None
        message_id = f"LLM-QUAL-ACK-{run_id}-{uuid.uuid4().hex[:6]}"
        metadata = {
            "sender": "LLMQuality",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
            "simulation_mode": True,
            "simulation_id": run_id,
            "simulation_llm": args.mode == "llm",
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {
            "body": {
                "messageType": "text",
                "message": args.ack_text,
                "metadata": metadata,
            }
        }
        status, body, error = _send_webhook_payload(webhook_url, payload, webhook_secret, args.timeout)
        if not skip_outbox and not args.dry_run:
            _post_admin_outbox_with_wait(
                f"{base_url}/admin/outbox/process",
                admin_token,
                args.timeout,
                outbox_wait_seconds,
            )
        return {
            "action": "pending_ack",
            "message_id": message_id,
            "status": status,
            "error": error,
            "response": (body or "")[:200] if body else None,
        }

    def _send_session_reset(remote_jid):
        if args.dry_run:
            return None
        message_id = f"LLM-QUAL-RESET-{run_id}-{uuid.uuid4().hex[:6]}"
        metadata = {
            "sender": "LLMQuality",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
            "simulation_mode": True,
            "simulation_id": run_id,
            "simulation_action": "session_reset",
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {
            "body": {
                "messageType": "text",
                "message": "начнем сначала",
                "metadata": metadata,
            }
        }
        status, body, error = _send_webhook_payload(webhook_url, payload, webhook_secret, args.timeout)
        if not skip_outbox and not args.dry_run:
            _post_admin_outbox_with_wait(
                f"{base_url}/admin/outbox/process",
                admin_token,
                args.timeout,
                outbox_wait_seconds,
            )
        hook_conv_id = None
        hook_meta = None
        hook_meta_error = None
        hook_trace = None
        hook_trace_error = None
        hook_conv_id, hook_meta, hook_meta_error = _poll_decision_meta(
            db_user,
            message_id,
            args.poll_timeout,
            args.poll_interval,
        )
        if hook_conv_id:
            _, hook_trace, hook_trace_error = _poll_decision_trace(
                db_user,
                hook_conv_id,
                args.trace_timeout,
                args.trace_interval,
                min_recorded_at=_trace_min_recorded_at(hook_meta),
            )
        return {
            "action": "session_reset",
            "message_id": message_id,
            "conversation_id": hook_conv_id,
            "status": status,
            "error": error or hook_meta_error or hook_trace_error,
            "response": (body or "")[:200] if body else None,
            "decision_meta": hook_meta,
            "decision_trace": hook_trace,
        }

    def _send_tool_hook(remote_jid, text, action):
        if args.tool_hooks != "auto":
            return None
        message_id = f"LLM-QUAL-TOOL-{action.upper()}-{run_id}-{uuid.uuid4().hex[:6]}"
        metadata = {
            "sender": "LLMQuality",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
            "simulation_mode": True,
            "simulation_id": run_id,
            "simulation_action": f"tool_{action}",
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {
            "body": {
                "messageType": "text",
                "message": text,
                "metadata": metadata,
            }
        }
        status = "dry_run"
        body = None
        error = None
        hook_meta = None
        hook_meta_error = None
        hook_trace = []
        hook_trace_error = None
        hook_conv_id = None
        if not args.dry_run:
            status, body, error = _send_webhook_payload(
                webhook_url, payload, webhook_secret, args.timeout
            )
            if not skip_outbox:
                _post_admin_outbox_with_wait(
                    f"{base_url}/admin/outbox/process",
                    admin_token,
                    args.timeout,
                    outbox_wait_seconds,
                )
            hook_conv_id, hook_meta, hook_meta_error = _poll_decision_meta(
                db_user,
                message_id,
                args.poll_timeout,
                args.poll_interval,
            )
            if hook_conv_id:
                _, hook_trace, hook_trace_error = _poll_decision_trace(
                    db_user,
                    hook_conv_id,
                    args.trace_timeout,
                    args.trace_interval,
                    min_recorded_at=_trace_min_recorded_at(hook_meta),
                )
        if args.tool_hook_wait and args.tool_hook_wait > 0:
            time.sleep(args.tool_hook_wait)
        return {
            "action": action,
            "message_id": message_id,
            "conversation_id": hook_conv_id,
            "status": status,
            "error": error or hook_meta_error or hook_trace_error,
            "response": (body or "")[:200] if body else None,
            "decision_meta": hook_meta,
            "decision_trace": hook_trace,
        }

    def _reset_dialog_state(remote_jid):
        if args.dry_run:
            return None
        if not client_id:
            return None
        conv_id, state, error = _fetch_latest_conversation_state(db_user, client_id, remote_jid)
        if error:
            return {"action": "preflight_state", "error": error}
        if state not in ("pending", "manager_active", "bot_active"):
            return None
        actions = []
        cleared = state == "bot_active"
        state_after = state
        if state == "pending":
            ack_result = _send_pending_ack(remote_jid)
            if ack_result:
                actions.append(ack_result)
        if state == "manager_active" and args.manager_mode == "simulate":
            handover_meta, _ = _fetch_handover_meta(db_user, conv_id)
            handover_id = (handover_meta or {}).get("handover_id")
            conv_meta, _ = _fetch_conversation_meta(db_user, conv_id)
            if handover_id:
                actions.extend(_simulate_manager_actions(handover_id, conv_meta, conv_id))
        if state in {"pending", "manager_active"}:
            for _ in range(30):
                time.sleep(1.0)
                _, state_after, _ = _fetch_latest_conversation_state(
                    db_user, client_id, remote_jid
                )
                if state_after == "bot_active":
                    cleared = True
                    break
        if state_after == "bot_active":
            reset_result = _send_session_reset(remote_jid)
            if reset_result:
                actions.append(reset_result)
        return {
            "action": "preflight_clear",
            "state_before": state,
            "state_after": state_after,
            "cleared": cleared,
            "actions": actions,
        }

    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)
    started_at = datetime.now(timezone.utc)
    stop_reason = None
    stop_requested = False
    interrupted = False

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)

    def _handle_stop(signum, _frame):
        nonlocal stop_requested, interrupted, stop_reason
        if stop_requested:
            return
        stop_requested = True
        interrupted = True
        if not stop_reason:
            stop_reason = f"signal_{signum}"
        print("llm-quality: stop requested, finishing current turn...", file=sys.stderr)

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    with open(responses_path, "w", encoding="utf-8") as responses_handle, open(
        trace_bundle_path, "w", encoding="utf-8"
    ) as trace_handle:
        for dialog_idx, dialog in enumerate(dialogs, start=1):
            if stop_requested:
                break
            dialog_runtime_state = {"slot_candidates": []}
            remote_jid = args.remote_jid or _llm_quality_pick_jid(
                allowlist_jids, dialog_idx - 1, rng, jid_mode_effective, run_id=run_id
            )
            if not remote_jid:
                raise SystemExit("llm-quality: remote_jid unresolved")
            if args.reset_before_dialog:
                preflight = _reset_dialog_state(remote_jid)
                if preflight:
                    print(json.dumps(preflight, ensure_ascii=False))
                    state_before = preflight.get("state_before")
                    cleared = bool(preflight.get("cleared"))
                    if state_before in {"pending", "manager_active"} and not cleared:
                        raise SystemExit(
                            "llm-quality: contaminated preflight (state_before="
                            f"{state_before}, cleared=false); restart with --jid-mode unique"
                        )

            for turn_idx, turn in enumerate(dialog.get("turns") or [], start=1):
                if stop_requested:
                    break
                stats["turns"] += 1
                if args.dry_run:
                    wait_seconds = 0
                else:
                    wait_seconds = rng.uniform(min_wait, max_wait)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)

                text, dynamic_turn_meta = _llm_quality_prepare_turn_text(
                    turn if isinstance(turn, dict) else {},
                    dialog_runtime_state,
                    now=datetime.now(timezone.utc),
                )
                message_id = (
                    f"LLM-QUAL-{run_id}-{dialog_idx:03d}-{turn_idx:02d}-{uuid.uuid4().hex[:6]}"
                )
                metadata = {
                    "sender": "LLMQuality",
                    "timestamp": int(time.time()),
                    "messageId": message_id,
                    "remoteJid": remote_jid,
                    "simulation_mode": True,
                    "simulation_id": run_id,
                    "simulation_llm": args.mode == "llm",
                }
                if instance_id:
                    metadata["instanceId"] = instance_id

                payload = None
                if turn.get("kind") == "media" and isinstance(turn.get("media"), dict):
                    payload = dict(turn.get("media"))
                    payload["metadata"] = metadata
                    payload.setdefault("message", text)
                else:
                    payload = {
                        "messageType": "text",
                        "message": text,
                        "metadata": metadata,
                    }

                response_status = None
                response_body = None
                response_error = None
                attempts = 0
                response_payload = None
                inline_response_text = None
                conversation_id_hint = None
                if not args.dry_run:
                    response_status, response_body, response_error, attempts = _send_webhook_payload_with_retry(
                        webhook_url,
                        {"body": payload},
                        webhook_secret,
                        args.timeout,
                        args.retry_count,
                        args.retry_backoff,
                    )
                    if response_body:
                        try:
                            response_payload = json.loads(response_body)
                        except Exception:
                            response_payload = None
                    if isinstance(response_payload, dict):
                        inline_response_text = response_payload.get("bot_response")
                        if not isinstance(inline_response_text, str):
                            inline_response_text = None
                        hint_value = response_payload.get("conversation_id")
                        if isinstance(hint_value, str) and hint_value.strip():
                            conversation_id_hint = hint_value.strip()
                    if response_error:
                        stats["webhook_errors"] += 1
                        if _is_infra_error(response_error):
                            stats["infra_errors"] += 1
                    if not skip_outbox:
                        _post_admin_outbox_with_wait(
                            f"{base_url}/admin/outbox/process",
                            admin_token,
                            args.timeout,
                            outbox_wait_seconds,
                        )

                conversation_id = None
                meta = None
                meta_error = None
                trace_entries = []
                trace_error = None
                conv_meta = None
                handover_meta = None
                if not args.dry_run:
                    conversation_id, meta, meta_error = _poll_decision_meta(
                        db_user,
                        message_id,
                        args.poll_timeout,
                        args.poll_interval,
                        conversation_id_hint=conversation_id_hint,
                    )
                    if meta_error:
                        stats["decision_meta_errors"] += 1
                    if meta is None:
                        stats["decision_meta_missing"] += 1
                    if conversation_id:
                        conv_meta, _ = _fetch_conversation_meta(db_user, conversation_id)
                        conv_meta, trace_entries, trace_error = _poll_decision_trace(
                            db_user,
                            conversation_id,
                            args.trace_timeout,
                            args.trace_interval,
                            min_recorded_at=_trace_min_recorded_at(meta),
                        )
                        trace_missing_soft = _llm_quality_trace_missing_soft(meta, trace_error)
                        if trace_error and not trace_missing_soft:
                            stats["decision_trace_errors"] += 1
                        if not trace_entries and not trace_missing_soft:
                            stats["decision_trace_missing"] += 1
                        if (conv_meta or {}).get("state") in {"pending", "manager_active"}:
                            handover_meta, _ = _fetch_handover_meta(db_user, conversation_id)
                else:
                    meta_error = "dry_run"

                state = (conv_meta or {}).get("state")
                state_key = state if state in LLM_QUALITY_KNOWN_STATES else "unknown"
                if state_key == "unknown":
                    stats["unknown_state"] += 1
                coverage_stats["states"][state_key] = (
                    coverage_stats["states"].get(state_key, 0) + 1
                )
                trace_stage_set = {
                    entry.get("stage")
                    for entry in trace_entries
                    if isinstance(entry, dict) and entry.get("stage")
                }
                for stage in trace_stage_set:
                    coverage_stats["trace_stages"][stage] = (
                        coverage_stats["trace_stages"].get(stage, 0) + 1
                    )
                tool_signals = _llm_quality_extract_tool_signals(meta, trace_entries)
                for tool_name, tool_signal in tool_signals.items():
                    coverage_stats["tools"]["events"][tool_name] = (
                        coverage_stats["tools"]["events"].get(tool_name, 0) + 1
                    )
                    outcome = tool_signal.get("outcome")
                    if outcome in LLM_QUALITY_TOOL_OUTCOMES:
                        coverage_stats["tools"]["outcomes"][outcome] += 1
                        by_tool = coverage_stats["tools"]["by_tool"].setdefault(
                            tool_name, {key: 0 for key in LLM_QUALITY_TOOL_OUTCOMES}
                        )
                        by_tool[outcome] += 1

                expected_reply_type_value = _chaos_extract_expected_reply(
                    (conv_meta or {}).get("context")
                )
                if not expected_reply_type_value and isinstance(meta, dict):
                    meta_expected_reply = meta.get("expected_reply_type")
                    if isinstance(meta_expected_reply, str):
                        meta_expected_reply = meta_expected_reply.strip()
                    if meta_expected_reply:
                        expected_reply_type_value = meta_expected_reply
                expected_reply_matched = (
                    (meta or {}).get("expected_reply_matched") if isinstance(meta, dict) else None
                )
                if expected_reply_type_value:
                    coverage_stats["expected_reply_type"][expected_reply_type_value] = (
                        coverage_stats["expected_reply_type"].get(expected_reply_type_value, 0) + 1
                    )
                policy_core_mode = (
                    (meta or {}).get("policy_core_mode") if isinstance(meta, dict) else None
                )
                if policy_core_mode in {"policy_core", "degraded_fallback"}:
                    stats["policy_core_turns"] += 1
                    if policy_core_mode == "degraded_fallback":
                        stats["policy_core_degraded_turns"] += 1
                        degrade_reason = (
                            (meta or {}).get("policy_core_degrade_reason")
                            if isinstance(meta, dict)
                            else None
                        )
                        if _llm_quality_is_policy_core_infra_reason(degrade_reason):
                            stats["policy_core_infra_errors"] += 1
                _llm_quality_track_rewrite_governance(
                    rewrite_governance_state,
                    meta if isinstance(meta, dict) else None,
                )
                _llm_quality_collect_dedup_stats(
                    meta if isinstance(meta, dict) else None,
                    dedup_stats,
                )
                action_value = (meta or {}).get("action") if isinstance(meta, dict) else None
                if action_value:
                    coverage_stats["actions"][action_value] = (
                        coverage_stats["actions"].get(action_value, 0) + 1
                    )
                intent_value = _llm_quality_effective_intent(meta if isinstance(meta, dict) else None)
                if intent_value:
                    coverage_stats["intents"][intent_value] = (
                        coverage_stats["intents"].get(intent_value, 0) + 1
                    )
                outbox_summary = None
                outbox_payload = None
                outbox_payload_status = None
                outbox_text = None
                if not args.dry_run and client_id and not args.skip_outbox:
                    outbox_summary, _ = _fetch_outbox_summary(db_user, client_id, message_id)
                    outbox_payload, outbox_payload_status, _ = _llm_quality_fetch_outbox_payload(
                        db_user, client_id, message_id
                    )
                    outbox_text = _llm_quality_extract_outbox_text(outbox_payload)
                if not outbox_text and inline_response_text:
                    outbox_text = inline_response_text
                _llm_quality_update_dialog_runtime_slots(
                    dialog_runtime_state,
                    meta=meta if isinstance(meta, dict) else None,
                    outbox_text=outbox_text,
                )

                bot_response = _llm_quality_has_bot_reply(
                    outbox_summary=outbox_summary,
                    outbox_payload_status=outbox_payload_status,
                    outbox_text=outbox_text,
                    inline_response_text=inline_response_text,
                )
                expected_response, expected_reason = _llm_quality_expected_response(state, meta)
                if not args.dry_run and not args.skip_outbox:
                    (
                        outbox_summary,
                        outbox_payload,
                        outbox_payload_status,
                        outbox_text,
                        bot_response,
                    ) = _llm_quality_retry_outbox_for_expected_reply(
                        expected_response=expected_response,
                        bot_response=bot_response,
                        db_user=db_user,
                        client_id=client_id,
                        inbound_message_id=message_id,
                        inline_response_text=inline_response_text,
                        outbox_summary=outbox_summary,
                        outbox_payload=outbox_payload,
                        outbox_payload_status=outbox_payload_status,
                        outbox_text=outbox_text,
                        outbox_wait_seconds=outbox_wait_seconds,
                        poll_interval=args.poll_interval,
                    )
                bot_response_inferred_duplicate_ack = False
                if _llm_quality_should_infer_bot_response_from_duplicate_ack(
                    bot_response=bot_response,
                    expected_response=expected_response,
                    response_payload=response_payload,
                    attempts=attempts,
                    meta=meta,
                    meta_error=meta_error,
                    state=state,
                    outbox_payload_status=outbox_payload_status,
                    outbox_summary=outbox_summary,
                    trace_entries=trace_entries,
                ):
                    bot_response = True
                    bot_response_inferred_duplicate_ack = True
                state_settled_from = None
                if (
                    not args.dry_run
                    and bot_response
                    and state in {"pending", "manager_active"}
                    and args.manager_mode == "simulate"
                    and client_id
                ):
                    _, settled_state, settle_error = _settle_state_after_manager_actions(
                        db_user,
                        client_id,
                        remote_jid,
                        state,
                    )
                    if settle_error:
                        # Keep original state for deterministic evaluation when settle probe fails.
                        settled_state = state
                    if settled_state and settled_state != state:
                        state_settled_from = state
                        state = settled_state
                        if conversation_id:
                            refreshed_conv_meta, _ = _fetch_conversation_meta(db_user, conversation_id)
                            if isinstance(refreshed_conv_meta, dict):
                                conv_meta = refreshed_conv_meta
                            if state in {"pending", "manager_active"}:
                                handover_meta, _ = _fetch_handover_meta(db_user, conversation_id)
                            else:
                                handover_meta = None
                expected_response, expected_reason = _llm_quality_expected_response(state, meta)
                if bot_response:
                    stats["turns_with_response"] += 1
                else:
                    stats["turns_missing_response"] += 1

                if expected_response:
                    stats["turns_expected_response"] += 1
                    if not bot_response:
                        stats["turns_expected_missing"] += 1

                _bump_state(state, expected_response, bot_response)

                if isinstance(meta, dict):
                    controller_stats = stage_stats["controller"]
                    if expected_response:
                        controller_stats["total_expected"] += 1
                        skip_reason = (
                            _llm_quality_normalize_tool_token(meta.get("controller_skipped_reason"))
                            or _llm_quality_normalize_tool_token(meta.get("router_skipped_reason"))
                            or "not_attempted"
                        )
                        expected_reply_blocked = _llm_quality_is_expected_reply_blocked(meta)
                        expected_reply_deferred = _llm_quality_is_expected_reply_deferred(meta)
                        if expected_reply_blocked:
                            controller_stats["expected_reply_blocked"] += 1
                        if expected_reply_deferred:
                            controller_stats["expected_reply_deferred"] += 1
                        non_eligible_reason_tokens = {
                            "expected_reply_deferred",
                            "law_gate",
                            "policy_gate",
                            "pending",
                            "not_run",
                            "guard_not_eligible",
                        }
                        controller_eligible = meta.get("controller_eligible")
                        if controller_eligible is None and isinstance(meta.get("router_eligible"), bool):
                            controller_eligible = meta.get("router_eligible")
                        if meta.get("controller_attempted") is True:
                            controller_stats["eligible"] += 1
                            controller_stats["attempted"] += 1
                        else:
                            skip_reasons = controller_stats.setdefault("skip_reasons", {})
                            skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
                            if controller_eligible is True:
                                controller_stats["eligible"] += 1
                                controller_stats["skipped"] += 1
                            elif controller_eligible is False:
                                controller_stats["non_eligible"] += 1
                                non_eligible_map = controller_stats.setdefault(
                                    "non_eligible_reasons", {}
                                )
                                non_eligible_reason = skip_reason
                                if expected_reply_deferred:
                                    non_eligible_reason = "expected_reply_deferred"
                                elif non_eligible_reason == "not_run" and expected_reply_blocked:
                                    non_eligible_reason = "expected_reply_blocked"
                                non_eligible_map[non_eligible_reason] = (
                                    non_eligible_map.get(non_eligible_reason, 0) + 1
                                )
                            else:
                                fallback_non_eligible = expected_reply_deferred or (
                                    skip_reason in non_eligible_reason_tokens
                                )
                                if fallback_non_eligible:
                                    controller_stats["non_eligible"] += 1
                                    non_eligible_map = controller_stats.setdefault(
                                        "non_eligible_reasons", {}
                                    )
                                    non_eligible_reason = (
                                        "expected_reply_deferred"
                                        if expected_reply_deferred
                                        else skip_reason
                                    )
                                    non_eligible_map[non_eligible_reason] = (
                                        non_eligible_map.get(non_eligible_reason, 0) + 1
                                    )
                                else:
                                    controller_stats["eligible"] += 1
                                    controller_stats["skipped"] += 1

                    tool_action_token = _llm_quality_normalize_tool_token(meta.get("tool_action"))
                    if tool_action_token and "." in tool_action_token:
                        selection_stats = stage_stats["tool_selection"]
                        args_stats = stage_stats["tool_args"]
                        selection_stats["selected"] += 1
                        tool_decision_token = _llm_quality_normalize_tool_token(meta.get("tool_decision"))
                        if tool_decision_token == "capability_blocked":
                            selection_stats["blocked"] += 1
                        elif tool_decision_token in {"invalid", "invalid_args"}:
                            selection_stats["invalid"] += 1
                        else:
                            selection_stats["ok"] += 1

                        if bool(meta.get("tool_args_checked")):
                            args_stats["checked"] += 1
                            args_contract = _llm_quality_normalize_tool_token(
                                meta.get("tool_args_contract")
                            )
                            if args_contract == "invalid":
                                args_stats["invalid"] += 1
                                args_error = (
                                    _llm_quality_normalize_tool_token(meta.get("tool_args_error"))
                                    or "unknown"
                                )
                                invalid_reasons = args_stats.setdefault("invalid_reasons", {})
                                invalid_reasons[args_error] = invalid_reasons.get(args_error, 0) + 1
                            else:
                                args_stats["valid"] += 1

                turn_tags = _llm_quality_extract_turn_tags(turn)
                for tag in turn_tags:
                    coverage_stats["turn_tags"][tag] = coverage_stats["turn_tags"].get(tag, 0) + 1
                turn_kind = turn.get("kind") or "text"
                coverage_stats["turn_kinds"][turn_kind] = (
                    coverage_stats["turn_kinds"].get(turn_kind, 0) + 1
                )
                is_media = turn_kind in {"media", "image", "audio", "file"} or "media" in turn_tags
                modality = "media" if is_media else "text"
                coverage_stats["modality"][modality] = (
                    coverage_stats["modality"].get(modality, 0) + 1
                )
                if "media" in turn_tags:
                    media_kind = "audio" if "audio" in turn_tags else "photo"
                    coverage_stats["media_kind"][media_kind] = (
                        coverage_stats["media_kind"].get(media_kind, 0) + 1
                    )
                lang = _llm_quality_detect_language(text)
                coverage_stats["language"][lang] = coverage_stats["language"].get(lang, 0) + 1
                coverage_stats["noise"]["turns"] += 1
                if _llm_quality_is_noise(text, turn_tags):
                    coverage_stats["noise"]["noisy"] += 1
                expectations = _llm_quality_extract_expectations(turn)
                weak_oracle_expectation = _llm_quality_is_weak_oracle_expectation(expectations)
                if weak_oracle_expectation:
                    stats["weak_oracle_turns"] += 1
                expected_action = expectations.get("action")
                expected_info_sections = expectations.get("info_sections") or []
                expected_reply_type = expectations.get("reply_type")
                expected_state = expectations.get("state")
                expected_reply = expectations.get("expected_reply")
                allow_booking_stall = expectations.get("allow_booking_stall", False)
                info_tags = [tag for tag in turn_tags if tag in LLM_QUALITY_INFO_TAGS]
                if not info_tags:
                    info_tags = sorted(_llm_quality_infer_info_tags(text))
                info_answered = {}
                info_sections = []
                info_intents = []
                info_mismatch = False
                if expected_info_sections:
                    info_stats["turns_with_info_request"] += 1
                    answered_any, info_sections, info_intents = _llm_quality_expected_section_answered(
                        expected_info_sections, meta, trace_entries
                    )
                    actual_section_set = set(info_sections) | set(info_intents)
                    actual_tag_set = set()
                    for token in actual_section_set:
                        actual_tag_set.update(_llm_quality_token_to_info_tags(token))
                    tag_hits = {}
                    for section in expected_info_sections:
                        normalized_section = section.strip().lower() if isinstance(section, str) else ""
                        section_hit = bool(normalized_section and normalized_section in actual_section_set)
                        if not section_hit:
                            expected_tags = _llm_quality_token_to_info_tags(normalized_section)
                            section_hit = bool(expected_tags & actual_tag_set)
                        key = normalized_section or section
                        info_answered[key] = section_hit
                        tag = LLM_QUALITY_SECTION_TAG_MAP.get(normalized_section)
                        if tag:
                            tag_hits[tag] = bool(tag_hits.get(tag)) or section_hit
                    for tag, tag_hit in tag_hits.items():
                        info_stats["by_tag"][tag]["requested"] += 1
                        if tag_hit:
                            info_stats["by_tag"][tag]["answered"] += 1
                        else:
                            info_stats["by_tag"][tag]["missed"] += 1
                    if answered_any:
                        info_stats["turns_info_answered"] += 1
                    else:
                        info_stats["turns_info_missed"] += 1
                    if not answered_any and state not in {"manager_active", "pending"}:
                        info_mismatch = True
                        stats["info_mismatch"] += 1
                elif info_tags:
                    info_stats["turns_with_info_request"] += 1
                    info_answered, info_sections, info_intents = _llm_quality_info_answered(
                        info_tags, meta, trace_entries
                    )
                    answered_any = any(info_answered.values())
                    if answered_any:
                        info_stats["turns_info_answered"] += 1
                    else:
                        info_stats["turns_info_missed"] += 1
                    for tag in info_tags:
                        info_stats["by_tag"][tag]["requested"] += 1
                        if info_answered.get(tag):
                            info_stats["by_tag"][tag]["answered"] += 1
                        else:
                            info_stats["by_tag"][tag]["missed"] += 1
                    if not answered_any and state not in {"manager_active", "pending"}:
                        info_mismatch = True
                        stats["info_mismatch"] += 1

                booking_active = _llm_quality_booking_active(conv_meta)
                booking_slots = _llm_quality_extract_booking_slots(meta, conv_meta)
                progress_expected = False
                booking_progressed = None
                if booking_active:
                    booking_stats["turns"] += 1
                    progress_key = conversation_id or f"dialog-{dialog_idx}"
                    prev_slots = booking_progress.get(progress_key, {})
                    slot_count = len(booking_slots)
                    progress_expected = _llm_quality_should_expect_booking_progress(
                        expected_reply_type_value,
                        turn_tags,
                        meta,
                    )
                    if progress_expected and info_tags and expected_reply_matched is not True:
                        progress_expected = False
                    if progress_expected and isinstance(meta, dict):
                        intent_value = _llm_quality_effective_intent(meta)
                        tool_decision_value = _llm_quality_normalize_tool_token(
                            meta.get("tool_decision")
                        )
                        if tool_decision_value in {"provider_unavailable", "branch_missing"}:
                            progress_expected = False
                        if (
                            progress_expected
                            and intent_value == "calendar.get_booking"
                            and tool_decision_value in {"ok", "time_mismatch", "not_found"}
                        ):
                            progress_expected = False
                    if progress_expected:
                        booking_stats["progress_opportunities"] += 1
                        booking_progressed = _llm_quality_booking_slots_progressed(
                            prev_slots,
                            booking_slots,
                        )
                        if not booking_progressed and expected_reply_matched is True:
                            booking_progressed = True
                        if booking_progressed:
                            booking_stats["progressed"] += 1
                    updated_slots = dict(prev_slots) if isinstance(prev_slots, dict) else {}
                    updated_slots.update(booking_slots)
                    booking_progress[progress_key] = updated_slots
                    booking_stats["filled_slots_total"] = max(
                        booking_stats["filled_slots_total"], slot_count
                    )

                if args.dry_run:
                    evaluation_reasons = []
                else:
                    evaluation_reasons = _llm_quality_evaluate_turn(
                        meta=meta,
                        trace_entries=trace_entries,
                        trace_error=trace_error,
                        state=state,
                        conv_meta=conv_meta,
                        handover_meta=handover_meta,
                        bot_response=bot_response,
                        expected_response=expected_response,
                        expected_action=expected_action,
                        expected_info_sections=expected_info_sections,
                        expected_reply_type=expected_reply_type,
                        expected_state=expected_state,
                        expected_reply=expected_reply,
                        actual_expected_reply_type=expected_reply_type_value,
                        info_tags=info_tags,
                        info_answered=info_answered,
                        booking_active=booking_active,
                        booking_progress_expected=progress_expected,
                        booking_progressed=booking_progressed,
                        allow_booking_stall=allow_booking_stall,
                        outbox_text=outbox_text,
                        tool_signals=tool_signals,
                        outbox_summary=outbox_summary,
                        outbox_payload_status=outbox_payload_status,
                        bot_response_inferred_duplicate_ack=bot_response_inferred_duplicate_ack,
                        meta_error=meta_error,
                        webhook_error=response_error,
                    )
                if evaluation_reasons:
                    stats["turns_failed"] += 1
                else:
                    stats["turns_passed"] += 1
                trace_id = (meta or {}).get("trace_id") if isinstance(meta, dict) else None
                judge_result = None
                should_judge, judge_skip_reason = _should_judge_turn(
                    state,
                    bot_response,
                    text,
                    turn_tags=turn_tags,
                    expected_action=expected_action,
                    expected_reply_type=expected_reply_type,
                    expected_state=expected_state,
                    expected_info_sections=expected_info_sections,
                    info_tags=info_tags,
                    booking_active=booking_active,
                    booking_progress_expected=progress_expected,
                    evaluation_reasons=evaluation_reasons,
                )
                if should_judge and not outbox_text:
                    should_judge = False
                    judge_skip_reason = "missing_bot_text"
                if should_judge:
                    judge_payload = {
                        "user_text": _llm_quality_redact_text(text)
                        if args.judge_redact
                        else text,
                        "bot_response": _llm_quality_redact_text(outbox_text)
                        if args.judge_redact
                        else outbox_text,
                        "conversation_state": state,
                        "turn_tags": turn_tags,
                        "expected": {
                            "action": expected_action,
                            "reply_type": expected_reply_type,
                            "state": expected_state,
                            "expected_reply": expected_reply,
                            "info_sections": expected_info_sections,
                        },
                        "decision_meta": {
                            "action": (meta or {}).get("action") if isinstance(meta, dict) else None,
                            "intent": (meta or {}).get("intent") if isinstance(meta, dict) else None,
                            "info_sections": (meta or {}).get("info_sections")
                            if isinstance(meta, dict)
                            else None,
                            "expected_reply_type": expected_reply_type_value,
                            "pending_action": (meta or {}).get("pending_action")
                            if isinstance(meta, dict)
                            else None,
                            "policy_gate": (meta or {}).get("policy_gate") if isinstance(meta, dict) else None,
                        },
                        "trace_summary": {
                            "stages": [
                                entry.get("stage")
                                for entry in trace_entries
                                if isinstance(entry, dict) and entry.get("stage")
                            ][:12],
                        },
                        "booking_active": booking_active,
                        "booking_slots": booking_slots,
                        "info_tags": info_tags,
                    }
                    pack_payload = _llm_quality_build_pack_context(
                        pack_context,
                        info_tags,
                        expected_info_sections,
                        meta,
                        trace_entries,
                    )
                    if pack_payload:
                        judge_payload.update(pack_payload)
                    prompt = _llm_quality_build_judge_prompt(judge_payload)
                    cache_key = _llm_quality_judge_cache_key(
                        args.judge_model, args.judge_base_url, prompt
                    )
                    try:
                        judge_raw = None
                        if cache_key in judge_cache:
                            judge_raw = judge_cache.get(cache_key)
                            judge_stats["counts"]["cache_hits"] += 1
                        else:
                            judge_stats["counts"]["cache_misses"] += 1
                            judge_raw = _llm_quality_call_judge(
                                api_key=judge_api_key,
                                model=args.judge_model,
                                base_url=args.judge_base_url,
                                prompt=prompt,
                                timeout=args.judge_timeout,
                                max_tokens=args.judge_max_tokens,
                            )
                            judge_cache[cache_key] = judge_raw
                        verdict = (judge_raw or {}).get("verdict")
                        verdict = verdict.lower().strip() if isinstance(verdict, str) else None
                        reasons = (judge_raw or {}).get("reasons") or []
                        if isinstance(reasons, str):
                            reasons = [item.strip() for item in reasons.split(",") if item.strip()]
                        elif not isinstance(reasons, list):
                            reasons = []
                        summary_text = (judge_raw or {}).get("summary")
                        score = (judge_raw or {}).get("score")
                        if verdict not in LLM_QUALITY_JUDGE_VERDICTS:
                            verdict = "uncertain"
                        judge_stats["counts"]["judged"] += 1
                        judge_stats["counts"][verdict] += 1
                        for reason in reasons:
                            judge_stats["reasons"][reason] = (
                                judge_stats["reasons"].get(reason, 0) + 1
                            )
                        judge_result = {
                            "verdict": verdict,
                            "score": score,
                            "reasons": reasons,
                            "summary": summary_text,
                            "model": args.judge_model,
                        }
                    except Exception as exc:
                        judge_stats["counts"]["errors"] += 1
                        judge_result = {"error": str(exc), "model": args.judge_model}
                else:
                    if judge_skip_reason:
                        _record_judge_skip(judge_skip_reason)

                strict_reasons = list(evaluation_reasons or [])
                meta_action = (
                    (meta or {}).get("action")
                    if isinstance(meta, dict)
                    else None
                )
                suppress_judge_fail = _llm_quality_should_suppress_missed_question_judge_fail(
                    judge_result=judge_result,
                    strict_reasons=strict_reasons,
                    meta=meta,
                    meta_action=meta_action,
                    expected_reply_type_value=expected_reply_type_value,
                    booking_active=booking_active,
                    turn_tags=turn_tags,
                    outbox_text=outbox_text,
                )
                if suppress_judge_fail:
                    stats["suppressed_missed_question_count"] += 1
                if (
                    isinstance(judge_result, dict)
                    and judge_result.get("verdict") == "fail"
                    and not suppress_judge_fail
                    and "judge_fail" not in strict_reasons
                ):
                    strict_reasons.append("judge_fail")
                strict_reasons = list(dict.fromkeys(strict_reasons))
                if "unobserved_turn" in strict_reasons:
                    stats["unobserved_turns"] += 1
                if "outbox_delivery_failed" in strict_reasons:
                    stats["outbox_delivery_failed_turns"] += 1
                if "outbox_delivery_timeout" in strict_reasons:
                    stats["outbox_delivery_timeout_turns"] += 1
                hard_reasons = [
                    reason for reason in strict_reasons if reason in LLM_QUALITY_HARD_FAIL_REASONS
                ]
                strict_ok = not strict_reasons
                if strict_ok:
                    stats["turns_strict_passed"] += 1
                else:
                    stats["turns_strict_failed"] += 1
                if hard_reasons:
                    stats["turns_hard_failed"] += 1

                _record_failure(
                    strict_reasons,
                    {
                        "type": "turn",
                        "dialog_id": dialog.get("dialog_id"),
                        "dialog_index": dialog_idx,
                        "turn_index": turn_idx,
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                        "trace_id": trace_id,
                        "last_trace_stage": _llm_quality_last_trace_stage(trace_entries),
                        "conversation_state": state,
                        "expected_response": expected_response,
                        "bot_response": bot_response,
                        "info_tags": info_tags,
                        "booking_slots": booking_slots,
                        "reasons": strict_reasons,
                        "hard_reasons": hard_reasons,
                        "strict_ok": strict_ok,
                    },
                )

                manager_actions_run = []
                handover_id = (handover_meta or {}).get("handover_id") if handover_meta else None
                simulate_manager = args.manager_mode == "simulate" and handover_id
                if state in {"pending", "manager_active"} and handover_id:
                    manager_stats["handovers_seen"] += 1
                if state in {"pending", "manager_active"} and args.manager_mode == "simulate":
                    if handover_id:
                        manager_actions_run = _simulate_manager_actions(
                            handover_id, conv_meta, conversation_id
                        )
                    else:
                        manager_stats["errors"] += 1
                pending_action_result = None
                if state == "pending" and args.pending_mode == "ack" and not simulate_manager:
                    pending_action_result = _send_pending_ack(remote_jid)

                tool_hook_results = []
                tool_hook_result = None
                if args.tool_hooks == "auto":
                    hook_key = conversation_id or f"dialog-{dialog_idx}"
                    hook_state = tool_hook_state.setdefault(
                        hook_key, {"confirm": 0, "cancel": 0, "calendar": 0}
                    )
                    hook_limit = max(args.tool_hook_limit, 1)
                    if tool_signals.get("confirm") and "confirm" not in turn_tags:
                        if hook_state["confirm"] < hook_limit:
                            tool_hook_results.append(
                                _send_tool_hook(
                                    remote_jid, args.tool_confirm_text, "confirm"
                                )
                            )
                            hook_state["confirm"] += 1
                    if tool_signals.get("cancel") and "cancel" not in turn_tags:
                        if hook_state["cancel"] < hook_limit:
                            tool_hook_results.append(
                                _send_tool_hook(
                                    remote_jid, args.tool_cancel_text, "cancel"
                                )
                            )
                            hook_state["cancel"] += 1
                    if _llm_quality_should_send_calendar_hook(tool_signals, turn_tags):
                        if hook_state["calendar"] < hook_limit:
                            tool_hook_results.append(
                                _send_tool_hook(
                                    remote_jid, args.tool_calendar_text, "calendar"
                                )
                            )
                            hook_state["calendar"] += 1
                if tool_hook_results:
                    tool_hook_result = tool_hook_results[0]
                hook_stats = coverage_stats.get("tool_hooks")
                if isinstance(hook_stats, dict):
                    by_action = hook_stats.setdefault("by_action", {})
                    for hook in tool_hook_results:
                        if not isinstance(hook, dict):
                            continue
                        action = _llm_quality_normalize_tool_token(hook.get("action"))
                        if action:
                            hook_stats["sent_total"] = hook_stats.get("sent_total", 0) + 1
                            by_action[action] = by_action.get(action, 0) + 1
                        if hook.get("error"):
                            hook_stats["errors"] = hook_stats.get("errors", 0) + 1

                record = {
                    "dialog_id": dialog.get("dialog_id"),
                    "dialog_goal": dialog.get("goal"),
                    "dialog_index": dialog_idx,
                    "turn_index": turn_idx,
                    "turn_kind": turn.get("kind"),
                    "turn_tags": turn_tags,
                    "turn_text": text,
                    "turn_dynamic": dynamic_turn_meta,
                    "remote_jid": remote_jid,
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "conversation_state": state,
                    "conversation_state_settled_from": state_settled_from,
                    "expected_reply_type": expected_reply_type_value,
                    "decision_meta": meta,
                    "decision_meta_error": meta_error,
                    "trace_id": trace_id,
                    "decision_trace": trace_entries,
                    "decision_trace_error": trace_error,
                    "decision_trace_stages": [
                        entry.get("stage")
                        for entry in trace_entries
                        if isinstance(entry, dict)
                    ],
                    "handover": handover_meta,
                    "outbox_summary": outbox_summary,
                    "outbox_payload_status": outbox_payload_status,
                    "outbox_text": outbox_text,
                    "bot_response": bot_response,
                    "bot_response_inferred_duplicate_ack": bot_response_inferred_duplicate_ack,
                    "expected_response": expected_response,
                    "expected_response_reason": expected_reason,
                    "turn_expectations": expectations,
                    "weak_oracle_expectation": weak_oracle_expectation,
                    "info_tags": info_tags,
                    "info_answered": info_answered,
                    "info_sections": sorted(info_sections),
                    "info_intents": sorted(info_intents),
                    "info_mismatch": info_mismatch,
                    "booking_active": booking_active,
                    "booking_slots": booking_slots,
                    "booking_progressed": booking_progressed,
                    "tool_signals": tool_signals,
                    "tool_hook": tool_hook_result,
                    "tool_hooks": tool_hook_results,
                    "evaluation": {
                        "ok": not evaluation_reasons,
                        "reasons": evaluation_reasons,
                        "strict_ok": strict_ok,
                        "strict_reasons": strict_reasons,
                        "hard_fail": bool(hard_reasons),
                        "hard_reasons": hard_reasons,
                    },
                    "judge": judge_result,
                    "manager_actions": manager_actions_run,
                    "pending_action": pending_action_result,
                    "inline_response_text": inline_response_text,
                    "webhook": {
                        "status": response_status,
                        "error": response_error,
                        "attempts": attempts,
                        "response": (response_body or "")[:200] if response_body else None,
                    },
                }
                hq1_classes = _llm_quality_collect_hq1_classes(record)
                if hq1_classes:
                    record["hq1_classes"] = hq1_classes
                    hq1_bad_turn_count += 1
                    for hq1_class in hq1_classes:
                        hq1_class_counts[hq1_class] = hq1_class_counts.get(hq1_class, 0) + 1
                responses_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                trace_handle.write(
                    json.dumps(
                        {
                            "dialog_id": dialog.get("dialog_id"),
                            "dialog_index": dialog_idx,
                            "turn_index": turn_idx,
                            "message_id": message_id,
                            "conversation_id": conversation_id,
                            "trace_id": trace_id,
                            "conversation_state": state,
                            "conversation_state_settled_from": state_settled_from,
                            "expected_reply_type": expected_reply_type_value,
                            "decision_meta": meta,
                            "decision_trace": trace_entries,
                            "decision_trace_error": trace_error,
                            "last_trace_stage": _llm_quality_last_trace_stage(trace_entries),
                            "handover": handover_meta,
                            "outbox_summary": outbox_summary,
                            "outbox_payload_status": outbox_payload_status,
                            "outbox_text": outbox_text,
                            "bot_response": bot_response,
                            "expected_response": expected_response,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                stats["trace_rows_written"] += 1
                if stats["policy_core_infra_errors"] >= 3:
                    stop_reason = "policy_core_infra_errors"
                    stop_requested = True
                    break
                if stats["outbox_delivery_failed_turns"] >= 3:
                    stop_reason = "outbox_delivery_failed"
                    stop_requested = True
                    break
                if args.max_failures > 0 and stats["turns_strict_failed"] >= args.max_failures:
                    stop_reason = f"max_failures_reached:{args.max_failures}"
                    stop_requested = True
                    break
            if stop_requested:
                break

    signal.signal(signal.SIGINT, previous_sigint)
    signal.signal(signal.SIGTERM, previous_sigterm)
    if stop_requested and not stop_reason:
        stop_reason = "stop_requested"

    if stop_reason:
        print(
            json.dumps(
                {
                    "stage": "llm_quality_stop",
                    "reason": stop_reason,
                    "turns_failed": stats["turns_failed"],
                    "turns_strict_failed": stats["turns_strict_failed"],
                    "turns": stats["turns"],
                },
                ensure_ascii=False,
            )
        )

    run_integrity_status = _llm_quality_build_run_integrity_status(
        dialogs=dialogs,
        stats=stats,
    )
    finished_at = datetime.now(timezone.utc)
    duration_s = round((finished_at - started_at).total_seconds(), 2)
    reply_rate_by_state = {}
    expected_reply_rate_by_state = {}
    state_counts = {}
    for state_key, entry in state_stats.items():
        state_counts[state_key] = entry.get("turns", 0)
        if entry.get("turns"):
            reply_rate_by_state[state_key] = round(
                entry.get("replies", 0) / max(entry.get("turns", 1), 1), 4
            )
        if entry.get("expected_turns"):
            expected_reply_rate_by_state[state_key] = round(
                entry.get("expected_replies", 0) / max(entry.get("expected_turns", 1), 1), 4
            )
    metrics = {
        "counts": {
            "dialogs": stats["dialogs"],
            "turns": stats["turns"],
            "turns_expected_response": stats["turns_expected_response"],
            "turns_with_response": stats["turns_with_response"],
            "turns_missing_response": stats["turns_missing_response"],
            "turns_expected_missing": stats["turns_expected_missing"],
            "trace_rows_written": stats["trace_rows_written"],
            "turns_passed": stats["turns_passed"],
            "turns_failed": stats["turns_failed"],
            "turns_strict_passed": stats["turns_strict_passed"],
            "turns_strict_failed": stats["turns_strict_failed"],
            "turns_hard_failed": stats["turns_hard_failed"],
            "unknown_state": stats["unknown_state"],
            "decision_meta_missing": stats["decision_meta_missing"],
            "decision_trace_missing": stats["decision_trace_missing"],
            "webhook_errors": stats["webhook_errors"],
            "infra_errors": stats["infra_errors"],
            "decision_meta_errors": stats["decision_meta_errors"],
            "decision_trace_errors": stats["decision_trace_errors"],
            "info_mismatch": stats["info_mismatch"],
            "unobserved_turns": stats["unobserved_turns"],
            "outbox_delivery_failed_turns": stats["outbox_delivery_failed_turns"],
            "outbox_delivery_timeout_turns": stats["outbox_delivery_timeout_turns"],
            "weak_oracle_turns": stats["weak_oracle_turns"],
            "suppressed_missed_question_count": stats["suppressed_missed_question_count"],
            "policy_core_turns": stats["policy_core_turns"],
            "policy_core_degraded_turns": stats["policy_core_degraded_turns"],
            "policy_core_infra_errors": stats["policy_core_infra_errors"],
            "dedup_backend_redis": int((dedup_stats.get("backend") or {}).get("redis", 0)),
            "dedup_backend_db_fallback": int((dedup_stats.get("backend") or {}).get("db_fallback", 0)),
            "dedup_backend_unknown": int((dedup_stats.get("backend") or {}).get("unknown", 0)),
        },
        "state": {
            "counts": state_counts,
            "reply_rate_by_state": reply_rate_by_state,
            "expected_reply_rate_by_state": expected_reply_rate_by_state,
            "raw": state_stats,
        },
        "info": info_stats,
        "manager": manager_stats,
        "booking": booking_stats,
        "dedup": dedup_stats,
        "suppression": {
            "suppressed_missed_question_count": stats["suppressed_missed_question_count"],
        },
        "rates": {},
    }
    if stats["turns"]:
        metrics["rates"]["reply_rate"] = round(
            stats["turns_with_response"] / max(stats["turns"], 1), 4
        )
    if stats["turns_expected_response"]:
        expected_replies = stats["turns_expected_response"] - stats["turns_expected_missing"]
        metrics["rates"]["expected_reply_rate"] = round(
            expected_replies / max(stats["turns_expected_response"], 1), 4
        )
    if stats["turns"]:
        metrics["rates"]["decision_meta_coverage"] = round(
            (stats["turns"] - stats["decision_meta_missing"]) / max(stats["turns"], 1),
            4,
        )
        metrics["rates"]["decision_trace_coverage"] = round(
            (stats["turns"] - stats["decision_trace_missing"]) / max(stats["turns"], 1),
            4,
        )
        metrics["rates"]["unknown_state_rate"] = round(
            stats["unknown_state"] / max(stats["turns"], 1), 4
        )
        metrics["rates"]["pass_rate"] = round(
            stats["turns_passed"] / max(stats["turns"], 1), 4
        )
        metrics["rates"]["strict_pass_rate"] = round(
            stats["turns_strict_passed"] / max(stats["turns"], 1), 4
        )
        metrics["rates"]["hard_fail_rate"] = round(
            stats["turns_hard_failed"] / max(stats["turns"], 1), 4
        )
    if info_stats["turns_with_info_request"]:
        metrics["rates"]["info_answer_rate"] = round(
            info_stats["turns_info_answered"] / max(info_stats["turns_with_info_request"], 1),
            4,
        )
    if booking_stats["progress_opportunities"]:
        metrics["rates"]["booking_slot_progress_rate"] = round(
            booking_stats["progressed"] / max(booking_stats["progress_opportunities"], 1),
            4,
        )
    if manager_stats["actions_total"]:
        metrics["rates"]["handoff_correct_rate"] = round(
            manager_stats["actions_ok"] / max(manager_stats["actions_total"], 1), 4
        )
    if stats["policy_core_turns"]:
        metrics["rates"]["degraded_fallback_rate"] = round(
            stats["policy_core_degraded_turns"] / max(stats["policy_core_turns"], 1),
            4,
        )
    if stats["turns"]:
        metrics["rates"]["dedup_redis_rate"] = round(
            int((dedup_stats.get("backend") or {}).get("redis", 0)) / max(stats["turns"], 1),
            4,
        )
        metrics["rates"]["dedup_db_fallback_rate"] = round(
            int((dedup_stats.get("backend") or {}).get("db_fallback", 0))
            / max(stats["turns"], 1),
            4,
        )
    dedup_latency = dedup_stats.get("latency") if isinstance(dedup_stats, dict) else {}
    if isinstance(dedup_latency, dict):
        samples = int(dedup_latency.get("samples") or 0)
        if samples > 0:
            metrics["rates"]["dedup_latency_avg_ms"] = round(
                float(dedup_latency.get("total_ms") or 0.0) / max(samples, 1),
                2,
            )
        redis_samples = int(dedup_latency.get("redis_samples") or 0)
        if redis_samples > 0:
            dedup_latency["redis_avg_ms"] = round(
                float(dedup_latency.get("redis_total_ms") or 0.0) / max(redis_samples, 1),
                2,
            )
        db_samples = int(dedup_latency.get("db_samples") or 0)
        if db_samples > 0:
            dedup_latency["db_avg_ms"] = round(
                float(dedup_latency.get("db_total_ms") or 0.0) / max(db_samples, 1),
                2,
            )
        messages_samples = int(dedup_latency.get("messages_samples") or 0)
        if messages_samples > 0:
            dedup_latency["messages_avg_ms"] = round(
                float(dedup_latency.get("messages_total_ms") or 0.0)
                / max(messages_samples, 1),
                2,
            )
    controller_stage = stage_stats.get("controller") or {}
    tool_selection_stage = stage_stats.get("tool_selection") or {}
    tool_args_stage = stage_stats.get("tool_args") or {}
    state_transition_checks = manager_stats.get("actions_total", 0)
    state_transition_passed = manager_stats.get("actions_ok", 0)
    state_transition_failed = max(state_transition_checks - state_transition_passed, 0)
    response_contract_checks = stats.get("turns_expected_response", 0)
    response_contract_passed = max(
        response_contract_checks - stats.get("turns_expected_missing", 0), 0
    )
    response_contract_failed = max(response_contract_checks - response_contract_passed, 0)
    strict_contract_checks = stats.get("turns", 0)
    strict_contract_passed = stats.get("turns_strict_passed", 0)
    strict_contract_failed = stats.get("turns_strict_failed", 0)
    metrics["stages"] = {
        "controller": {
            "total_expected": controller_stage.get("total_expected", 0),
            "opportunities": controller_stage.get("eligible", 0),
            "eligible": controller_stage.get("eligible", 0),
            "non_eligible": controller_stage.get("non_eligible", 0),
            "attempted": controller_stage.get("attempted", 0),
            "skipped": controller_stage.get("skipped", 0),
            "expected_reply_deferred": controller_stage.get("expected_reply_deferred", 0),
            "expected_reply_blocked": controller_stage.get("expected_reply_blocked", 0),
            "skip_reasons": controller_stage.get("skip_reasons", {}),
            "non_eligible_reasons": controller_stage.get("non_eligible_reasons", {}),
            "eligibility_rate": round(
                controller_stage.get("eligible", 0)
                / max(controller_stage.get("total_expected", 1), 1),
                4,
            )
            if controller_stage.get("total_expected", 0)
            else None,
            "attempt_rate": round(
                controller_stage.get("attempted", 0)
                / max(controller_stage.get("eligible", 1), 1),
                4,
            )
            if controller_stage.get("eligible", 0)
            else None,
            "skip_rate": round(
                controller_stage.get("skipped", 0)
                / max(controller_stage.get("eligible", 1), 1),
                4,
            )
            if controller_stage.get("eligible", 0)
            else None,
        },
        "tool_selection": {
            "selected": tool_selection_stage.get("selected", 0),
            "ok": tool_selection_stage.get("ok", 0),
            "blocked": tool_selection_stage.get("blocked", 0),
            "invalid": tool_selection_stage.get("invalid", 0),
            "ok_rate": round(
                tool_selection_stage.get("ok", 0)
                / max(tool_selection_stage.get("selected", 1), 1),
                4,
            )
            if tool_selection_stage.get("selected", 0)
            else None,
        },
        "tool_args": {
            "checked": tool_args_stage.get("checked", 0),
            "valid": tool_args_stage.get("valid", 0),
            "invalid": tool_args_stage.get("invalid", 0),
            "invalid_reasons": tool_args_stage.get("invalid_reasons", {}),
            "valid_rate": round(
                tool_args_stage.get("valid", 0)
                / max(tool_args_stage.get("checked", 1), 1),
                4,
            )
            if tool_args_stage.get("checked", 0)
            else None,
        },
        "state_transition": {
            "checks": state_transition_checks,
            "passed": state_transition_passed,
            "failed": state_transition_failed,
            "pass_rate": round(
                state_transition_passed / max(state_transition_checks, 1),
                4,
            )
            if state_transition_checks
            else None,
        },
        "response_contract": {
            "checks": response_contract_checks,
            "passed": response_contract_passed,
            "failed": response_contract_failed,
            "pass_rate": round(
                response_contract_passed / max(response_contract_checks, 1),
                4,
            )
            if response_contract_checks
            else None,
        },
        "strict_contract": {
            "checks": strict_contract_checks,
            "passed": strict_contract_passed,
            "failed": strict_contract_failed,
            "pass_rate": round(
                strict_contract_passed / max(strict_contract_checks, 1),
                4,
            )
            if strict_contract_checks
            else None,
        },
    }
    rewrite_governance = _llm_quality_finalize_rewrite_governance(
        rewrite_governance_state,
        max_post_llm_semantic_rewrite_rate=args.max_post_llm_semantic_rewrite_rate,
        max_keyword_override_rate=args.max_keyword_override_rate,
    )
    metrics["rates"]["post_llm_semantic_rewrite_rate"] = rewrite_governance[
        "post_llm_semantic_rewrite_rate"
    ]
    metrics["rates"]["keyword_override_rate"] = rewrite_governance["keyword_override_rate"]
    metrics["rates"]["rewrite_reason_coverage"] = rewrite_governance["rewrite_reason_coverage"]
    lexicon_regex_delta_gate = _llm_quality_build_lexicon_regex_delta_status(
        mode=args.lexicon_regex_delta_gate,
        repo_root=_llm_quality_repo_root(),
        base_ref=args.delta_gate_base_ref,
    )
    hardcode_core_gate = _llm_quality_build_hardcode_core_gate_status(
        mode=args.hardcode_core_gate,
        repo_root=_llm_quality_repo_root(),
        base_ref=args.hardcode_core_base_ref,
    )
    governance_blocking_counts = dict(rewrite_governance.get("blocking_counts") or {})
    hq1_blocking_counts = {name: count for name, count in hq1_class_counts.items() if count > 0}
    process_blocking_counts = {}
    if not args.allow_weak_oracle and int(stats.get("weak_oracle_turns") or 0) > 0:
        process_blocking_counts["weak_oracle_turn"] = int(stats.get("weak_oracle_turns") or 0)
    if not run_economy_status.get("valid", True) and run_economy_status.get("mode") in {"warn", "block"}:
        process_blocking_counts["run_economy_violation"] = max(
            len(run_economy_status.get("reasons") or []),
            1,
        )
    missing_scenario_artifacts = list((scenario_artifact_status or {}).get("missing") or [])
    if missing_scenario_artifacts:
        process_blocking_counts["incomplete_run_artifact"] = len(missing_scenario_artifacts)
    run_integrity_reasons = set(run_integrity_status.get("reasons") or [])
    if "run_completion_gap" in run_integrity_reasons:
        process_blocking_counts["run_completion_gap"] = int(
            max(
                run_integrity_status.get("missing_turns") or 0,
                run_integrity_status.get("extra_turns") or 0,
                1,
            )
        )
    if "trace_response_mismatch" in run_integrity_reasons:
        process_blocking_counts["trace_response_mismatch"] = int(
            max(run_integrity_status.get("trace_response_delta") or 0, 1)
        )
    if (
        lexicon_regex_delta_gate.get("enforced")
        and not lexicon_regex_delta_gate.get("valid", True)
    ):
        governance_blocking_counts["lexicon_regex_delta_violation"] = max(
            len(lexicon_regex_delta_gate.get("reasons") or []),
            1,
        )
    if (
        hardcode_core_gate.get("enforced")
        and not hardcode_core_gate.get("valid", True)
    ):
        governance_blocking_counts["hardcode_core_violation"] = max(
            len(hardcode_core_gate.get("reasons") or []),
            1,
        )

    baseline_path = os.path.join(_llm_quality_repo_root(), "ops", "results", "booking_quality.json")
    baseline_source = baseline_path
    baseline_payload = None
    baseline_metrics = None
    baseline_updated_at = None
    baseline_canonical = None
    baseline_canonical_reason = None
    if args.baseline_summary:
        baseline_source = os.path.abspath(os.path.expanduser(args.baseline_summary))
        if not os.path.exists(baseline_source):
            raise SystemExit(f"llm-quality: baseline-summary not found ({baseline_source})")
        try:
            with open(baseline_source, "r", encoding="utf-8") as handle:
                baseline_payload = json.load(handle)
            baseline_metrics = (baseline_payload or {}).get("metrics")
            baseline_updated_at = (baseline_payload or {}).get("finished_at") or (
                baseline_payload or {}
            ).get("updated_at")
            baseline_canonical, baseline_canonical_reason = _llm_quality_baseline_is_canonical(
                baseline_payload
            )
            if baseline_metrics is None:
                raise SystemExit(
                    f"llm-quality: baseline-summary has no metrics ({baseline_source})"
                )
        except SystemExit:
            raise
        except Exception as exc:
            raise SystemExit(f"llm-quality: baseline-summary parse failed ({exc})")
    elif os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as handle:
                baseline_payload = json.load(handle)
            baseline_metrics = (baseline_payload or {}).get("metrics")
            baseline_updated_at = (baseline_payload or {}).get("updated_at")
            baseline_canonical, baseline_canonical_reason = _llm_quality_baseline_is_canonical(
                baseline_payload
            )
        except Exception:
            baseline_metrics = None
            baseline_canonical = None
            baseline_canonical_reason = None

    threshold_results, threshold_breaches = _llm_quality_check_thresholds(metrics)
    if args.dry_run:
        threshold_results = {}
        threshold_breaches = []
    blocking_reasons = _llm_quality_collect_blocking_reasons(
        failure_counts,
        extra_counts={
            **governance_blocking_counts,
            **hq1_blocking_counts,
            **process_blocking_counts,
        },
    )
    blocking_reason_count = blocking_reasons.get("count", 0)
    tool_evidence_policy = args.tool_evidence_policy
    if args.dry_run:
        tool_evidence_policy = "off"
    tool_evidence_status = _llm_quality_build_tool_evidence_status(
        scenario_coverage=args.scenario_coverage,
        tool_hooks_mode=args.tool_hooks,
        tool_evidence_policy=tool_evidence_policy,
        coverage_stats=coverage_stats,
    )
    infra_status = _llm_quality_build_infra_status(
        stats,
        secret_preflight,
        tool_evidence_status=tool_evidence_status,
        openai_preflight=openai_preflight,
        runtime_preflight=runtime_preflight,
        failure_counts=failure_counts,
    )
    comparison_enforced = bool(args.fail_on_regression)
    comparison_block_reasons = []
    if args.dry_run:
        comparison_block_reasons.append("dry_run")
    if comparison_enforced and not infra_status["valid"]:
        comparison_block_reasons.append("infra_invalid")
    if comparison_enforced and baseline_metrics is not None and baseline_canonical is False:
        comparison_block_reasons.append(
            f"baseline_non_canonical:{baseline_canonical_reason or 'unknown'}"
        )
    comparison_blocked = bool(comparison_block_reasons)
    delta = None
    regression_results = {}
    regression_breaches = []
    if not comparison_blocked and baseline_metrics:
        delta = _llm_quality_compute_delta(metrics, baseline_metrics)
        regression_results, regression_breaches = _llm_quality_check_regression(
            metrics, baseline_metrics, args.regression_tolerance
        )
    semantic_reasons = []
    if args.dry_run:
        semantic_reasons.append("comparison_blocked:dry_run")
    else:
        if blocking_reason_count:
            semantic_reasons.append("blocking_reason")
        if threshold_breaches:
            semantic_reasons.append("threshold_breach")
        if comparison_enforced:
            if comparison_blocked:
                for reason in comparison_block_reasons:
                    semantic_reasons.append(f"comparison_blocked:{reason}")
            elif regression_breaches:
                semantic_reasons.append("regression_breach")
    semantic_status = {"valid": not semantic_reasons, "reasons": semantic_reasons}
    top_failures = _llm_quality_top_failure_reasons(failure_counts, limit=3)
    top_failure_turns = _llm_quality_top_failure_turns(failures, limit=3, sample_limit=3)
    safe_config = {
        "mode": args.mode,
        "count": len(dialogs),
        "requested_count": args.count,
        "min_turns": args.min_turns,
        "max_turns": args.max_turns,
        "include_media": args.include_media,
        "media_mode": args.media_mode,
        "media_kind": args.media_kind,
        "scenario_coverage": args.scenario_coverage,
        "scenarios_file": args.scenarios_file,
        "allow_weak_oracle": bool(args.allow_weak_oracle),
        "weak_oracle_debug_waiver": weak_oracle_debug_waiver,
        "allow_incomplete_run_artifacts": bool(args.allow_incomplete_run_artifacts),
        "seed": args.seed,
        "manager_mode": args.manager_mode,
        "pending_mode": args.pending_mode,
        "tool_hooks": args.tool_hooks,
        "tool_hook_limit": args.tool_hook_limit,
        "tool_confirm_text": args.tool_confirm_text,
        "tool_cancel_text": args.tool_cancel_text,
        "tool_calendar_text": args.tool_calendar_text,
        "tool_hook_wait": args.tool_hook_wait,
        "tool_evidence_policy": tool_evidence_policy,
        "reset_before_dialog": bool(args.reset_before_dialog),
        "jid_mode": jid_mode_effective,
        "jid_mode_requested": args.jid_mode,
        "max_failures": args.max_failures,
        "baseline_summary": args.baseline_summary,
        "regression_tolerance": args.regression_tolerance,
        "max_post_llm_semantic_rewrite_rate": args.max_post_llm_semantic_rewrite_rate,
        "max_keyword_override_rate": args.max_keyword_override_rate,
        "lexicon_regex_delta_gate": args.lexicon_regex_delta_gate,
        "delta_gate_base_ref": args.delta_gate_base_ref,
        "hardcode_core_gate": args.hardcode_core_gate,
        "hardcode_core_base_ref": args.hardcode_core_base_ref,
        "run_economy_gate": args.run_economy_gate,
        "run_economy_base_ref": args.run_economy_base_ref,
        "allow_no_code_delta": bool(args.allow_no_code_delta),
        "judge_mode": judge_mode,
        "judge_required": judge_required,
        "llm_api_key_source": llm_api_key_source,
        "judge_api_key_source": judge_api_key_source if judge_enabled else None,
        "judge_sample": args.judge_sample,
        "judge_model": args.judge_model if judge_enabled else None,
        "judge_max_tokens": args.judge_max_tokens if judge_enabled else None,
        "judge_cache_file": judge_cache_file if judge_enabled else None,
        "judge_cache_max_entries": args.judge_cache_max_entries if judge_enabled else None,
        "judge_redact": args.judge_redact,
        "runtime_expected_commit": runtime_preflight.get("expected_commit"),
        "runtime_expected_commit_source": runtime_preflight.get("expected_source"),
        "runtime_commit": runtime_preflight.get("runtime_commit"),
    }
    summary = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_s": duration_s,
        "client_slug": client_slug,
        "base_url": base_url,
        "config": safe_config,
        "allowlist_count": len(allowlist_jids),
        "output_dir": output_dir,
        "scenarios_path": scenarios_path,
        "responses_path": responses_path,
        "trace_bundle_path": trace_bundle_path,
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "baseline_source": baseline_source,
        "baseline_canonical": baseline_canonical,
        "baseline_canonical_reason": baseline_canonical_reason,
        "delta": delta,
        "failure_counts": failure_counts,
        "hq1_bad_turn_count": hq1_bad_turn_count,
        "hq1_class_counts": hq1_class_counts,
        "unobserved_turn_count": int(failure_counts.get("unobserved_turn") or 0),
        "weak_oracle_turn_count": int(stats.get("weak_oracle_turns") or 0),
        "scenario_artifacts": scenario_artifact_status,
        "suppressed_missed_question_count": int(
            metrics.get("suppression", {}).get("suppressed_missed_question_count") or 0
        ),
        "blocking_reasons": blocking_reasons,
        "process_blocking_counts": process_blocking_counts,
        "rewrite_governance": rewrite_governance,
        "lexicon_regex_delta_gate": lexicon_regex_delta_gate,
        "hardcode_core_gate": hardcode_core_gate,
        "run_economy": run_economy_status,
        "top_failures": top_failures,
        "top_failure_turns": top_failure_turns,
        "failures": failures,
        "coverage": coverage_stats,
        "run_integrity": run_integrity_status,
        "scenario_contract": scenario_contract,
        "tool_evidence": tool_evidence_status,
        "judge": judge_stats,
        "runtime_fingerprint_preflight": runtime_preflight,
        "webhook_secret_preflight": secret_preflight,
        "openai_preflight": openai_preflight,
        "infra_valid": infra_status["valid"],
        "semantic_valid": semantic_status["valid"],
        "quality_status": {
            "infra_valid": infra_status["valid"],
            "infra_reasons": infra_status["reasons"],
            "semantic_valid": semantic_status["valid"],
            "semantic_reasons": semantic_status["reasons"],
            "blocking_reason_count": blocking_reason_count,
            "blocking_reasons": blocking_reasons.get("reasons", {}),
            "process_blocking_counts": process_blocking_counts,
            "hq1_bad_turn_count": hq1_bad_turn_count,
            "hq1_class_counts": hq1_class_counts,
            "unobserved_turn_count": int(failure_counts.get("unobserved_turn") or 0),
            "weak_oracle_turn_count": int(stats.get("weak_oracle_turns") or 0),
            "suppressed_missed_question_count": int(
                metrics.get("suppression", {}).get("suppressed_missed_question_count") or 0
            ),
            "rewrite_governance_valid": rewrite_governance.get("valid", True),
            "rewrite_governance_reasons": rewrite_governance.get("reasons", []),
            "post_llm_semantic_rewrite_rate": rewrite_governance.get(
                "post_llm_semantic_rewrite_rate"
            ),
            "keyword_override_rate": rewrite_governance.get("keyword_override_rate"),
            "rewrite_reason_coverage": rewrite_governance.get("rewrite_reason_coverage"),
            "lexicon_regex_delta_gate_valid": lexicon_regex_delta_gate.get("valid", True),
            "lexicon_regex_delta_gate_enforced": lexicon_regex_delta_gate.get(
                "enforced", False
            ),
            "lexicon_regex_delta_gate_reasons": lexicon_regex_delta_gate.get("reasons", []),
            "hardcode_core_gate_valid": hardcode_core_gate.get("valid", True),
            "hardcode_core_gate_enforced": hardcode_core_gate.get("enforced", False),
            "hardcode_core_gate_reasons": hardcode_core_gate.get("reasons", []),
            "run_economy_gate_valid": run_economy_status.get("valid", True),
            "run_economy_gate_enforced": run_economy_status.get("enforced", False),
            "run_economy_gate_reasons": run_economy_status.get("reasons", []),
            "tool_evidence_valid": tool_evidence_status.get("valid"),
            "tool_evidence_reasons": tool_evidence_status.get("reasons"),
            "scenario_contract_valid": scenario_contract.get("valid"),
            "scenario_contract_reasons": scenario_contract.get("reasons"),
            "run_integrity_valid": run_integrity_status.get("valid"),
            "run_integrity_reasons": run_integrity_status.get("reasons"),
            "run_completion_ratio": run_integrity_status.get("completion_ratio"),
            "run_expected_turns": run_integrity_status.get("expected_turns"),
            "run_responses_turns": run_integrity_status.get("responses_turns"),
            "run_trace_rows_written": run_integrity_status.get("trace_rows_written"),
            "scenario_artifacts_valid": bool((scenario_artifact_status or {}).get("valid", True)),
            "scenario_artifacts_missing": list((scenario_artifact_status or {}).get("missing") or []),
            "comparison_blocked": comparison_blocked,
            "comparison_block_reasons": comparison_block_reasons,
        },
        "scenario_source": scenario_source,
        "replay_command": replay_command,
        "stop_reason": stop_reason,
        "interrupted": interrupted,
        "brief_path": brief_path,
        "taxonomy": {
            "counts": taxonomy_counts,
            "by_reason": {
                reason: {
                    "count": count,
                    "category": LLM_QUALITY_REASON_TAXONOMY.get(reason, "unknown"),
                }
                for reason, count in taxonomy_by_reason.items()
            },
        },
        "thresholds": {
            "rules": LLM_QUALITY_THRESHOLDS,
            "results": threshold_results,
            "breaches": threshold_breaches,
        },
        "regression": {
            "tolerance": args.regression_tolerance,
            "baseline_source": baseline_source,
            "baseline_updated_at": baseline_updated_at,
            "baseline_canonical": baseline_canonical,
            "baseline_canonical_reason": baseline_canonical_reason,
            "blocked": comparison_blocked,
            "block_reasons": comparison_block_reasons,
            "results": regression_results,
            "breaches": regression_breaches,
        },
        "reason_labels": LLM_QUALITY_REASON_LABELS,
    }
    if judge_enabled and judge_cache_file:
        _llm_quality_save_judge_cache(
            judge_cache_file, judge_cache, args.judge_cache_max_entries
        )
    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    _llm_quality_write_brief(brief_path, summary)
    if run_economy_status.get("is_replay") and run_economy_status.get("replay_fingerprint"):
        _llm_quality_save_replay_fingerprint_state(
            replay_state_path,
            {
                "run_id": run_id,
                "saved_at": finished_at.isoformat(),
                "summary_path": summary_path,
                "replay_fingerprint": run_economy_status.get("replay_fingerprint"),
                "scenario_fingerprint": run_economy_status.get("scenario_fingerprint"),
                "baseline_fingerprint": run_economy_status.get("baseline_fingerprint"),
                "code_fingerprint": run_economy_status.get("code_fingerprint"),
                "runtime_commit": runtime_preflight.get("runtime_commit"),
                "judge_mode": judge_mode,
                "jid_mode": jid_mode_effective,
            },
        )

    history_entry = {
        "run_id": run_id,
        "finished_at": finished_at.isoformat(),
        "config": safe_config,
        "rates": metrics.get("rates"),
        "failure_counts": failure_counts,
        "taxonomy": taxonomy_counts,
        "judge": judge_stats.get("counts"),
        "infra_valid": infra_status["valid"],
        "semantic_valid": semantic_status["valid"],
    }
    baseline_update_block_reasons = []
    if args.update_baseline:
        if not infra_status["valid"]:
            baseline_update_block_reasons.append("infra_invalid")
        if not semantic_status["valid"]:
            baseline_update_block_reasons.append("semantic_invalid")
        if not judge_enabled:
            baseline_update_block_reasons.append("judge_disabled")
        if blocking_reason_count:
            baseline_update_block_reasons.append("blocking_reasons_present")
        if baseline_update_block_reasons:
            raise SystemExit(
                "llm-quality: baseline update blocked "
                f"({', '.join(baseline_update_block_reasons)})"
            )
    if args.update_baseline or args.append_history:
        os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
        baseline_payload = dict(baseline_payload or {})
        history = list(baseline_payload.get("history") or [])
        history.append(history_entry)
        history_max = max(args.history_max or 0, 1)
        if len(history) > history_max:
            history = history[-history_max:]
        baseline_payload["history"] = history
        if args.update_baseline or "metrics" not in baseline_payload:
            baseline_payload["metrics"] = metrics
        if args.update_baseline or "config" not in baseline_payload:
            baseline_payload["config"] = safe_config
        if args.update_baseline or "updated_at" not in baseline_payload:
            baseline_payload["updated_at"] = finished_at.isoformat()
        with open(baseline_path, "w", encoding="utf-8") as handle:
            json.dump(baseline_payload, handle, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "output_dir": output_dir,
                "summary": summary_path,
                "brief": brief_path,
                "replay_command": replay_command,
            },
            ensure_ascii=False,
        )
    )
    if args.fail_on_thresholds and blocking_reason_count:
        blocked = ", ".join(
            f"{reason}:{count}" for reason, count in blocking_reasons.get("reasons", {}).items()
        )
        raise SystemExit(f"llm-quality: blocking reasons ({blocked})")
    if args.fail_on_thresholds and threshold_breaches:
        raise SystemExit(
            f"llm-quality: threshold breaches ({', '.join(threshold_breaches)})"
        )
    if args.fail_on_regression:
        if comparison_blocked:
            raise SystemExit(
                "llm-quality: regression comparison blocked "
                f"({', '.join(comparison_block_reasons)})"
            )
        if regression_breaches:
            raise SystemExit(
                f"llm-quality: regression breaches ({', '.join(regression_breaches)})"
            )


def _run_llm_quality_entry(argv):
    args = _parse_llm_quality_args(argv)
    if not isinstance(args.run_id, str) or not args.run_id.strip():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        args.run_id = _llm_quality_build_default_run_id(timestamp)
    run_id = args.run_id
    output_dir = _llm_quality_default_output_dir(run_id, args.output_dir)
    started_at = datetime.now(timezone.utc)
    try:
        _run_llm_quality(args)
    except SystemExit as exc:
        code = exc.code
        if code not in (None, 0):
            _llm_quality_write_failure_artifacts(
                args=args,
                run_id=run_id,
                output_dir=output_dir,
                started_at=started_at,
                stop_reason=_llm_quality_stop_reason_from_system_exit(code),
                error_message=str(code),
            )
        raise
    except Exception as exc:
        _llm_quality_write_failure_artifacts(
            args=args,
            run_id=run_id,
            output_dir=output_dir,
            started_at=started_at,
            stop_reason="unexpected_exception",
            error_message=f"{exc.__class__.__name__}:{exc}",
        )
        raise


def _run_llm_quality_gates(args):
    repo_root = _llm_quality_repo_root()
    generated_at = datetime.now(timezone.utc).isoformat()
    changed_cache = {}

    def _collect_changed_files(base_ref):
        normalized_ref = str(base_ref or "").strip() or "origin/main"
        cached = changed_cache.get(normalized_ref)
        if cached is None:
            cached = _llm_quality_collect_git_changed_files(repo_root, normalized_ref)
            changed_cache[normalized_ref] = cached
        return cached

    def _merge_scan_warnings(status, extra_warnings):
        merged = list(status.get("scan_warnings") or [])
        merged.extend(extra_warnings or [])
        status["scan_warnings"] = sorted({str(item) for item in merged if str(item).strip()})
        return status

    lexicon_changed, lexicon_scan_warnings = _collect_changed_files(args.delta_gate_base_ref)
    lexicon_regex_delta_gate = _llm_quality_build_lexicon_regex_delta_status(
        mode=args.lexicon_regex_delta_gate,
        repo_root=repo_root,
        base_ref=args.delta_gate_base_ref,
        changed_files=lexicon_changed,
    )
    _merge_scan_warnings(lexicon_regex_delta_gate, lexicon_scan_warnings)

    hardcode_changed, hardcode_scan_warnings = _collect_changed_files(args.hardcode_core_base_ref)
    hardcode_core_gate = _llm_quality_build_hardcode_core_gate_status(
        mode=args.hardcode_core_gate,
        repo_root=repo_root,
        base_ref=args.hardcode_core_base_ref,
        changed_files=hardcode_changed,
    )
    _merge_scan_warnings(hardcode_core_gate, hardcode_scan_warnings)

    run_economy_changed, run_economy_scan_warnings = _collect_changed_files(
        args.run_economy_base_ref
    )
    baseline_preflight = _llm_quality_preflight_baseline_summary(args.baseline_summary)
    run_economy_gate = _llm_quality_build_run_economy_status(
        mode=args.run_economy_gate,
        repo_root=repo_root,
        base_ref=args.run_economy_base_ref,
        scenarios_file=args.scenarios_file,
        baseline_summary=args.baseline_summary,
        reset_before_dialog=bool(args.reset_before_dialog),
        allow_no_code_delta=bool(args.allow_no_code_delta),
        jid_mode=args.jid_mode,
        runtime_commit=args.runtime_commit,
        judge_mode=args.judge_mode,
        previous_replay_fingerprint=args.previous_replay_fingerprint,
        changed_files=run_economy_changed,
        baseline_preflight=baseline_preflight,
    )
    _merge_scan_warnings(run_economy_gate, run_economy_scan_warnings)

    gate_statuses = {
        "lexicon_regex_delta_gate": lexicon_regex_delta_gate,
        "hardcode_core_gate": hardcode_core_gate,
        "run_economy_gate": run_economy_gate,
    }
    blocking_reasons = []
    warn_reasons = []
    for gate_name, status in gate_statuses.items():
        reasons = [str(reason) for reason in (status.get("reasons") or []) if str(reason).strip()]
        if status.get("enforced") and not status.get("valid", True):
            blocking_reasons.extend(f"{gate_name}:{reason}" for reason in reasons)
        elif str(status.get("mode") or "").strip().casefold() == "warn":
            warn_reasons.extend(f"{gate_name}:{reason}" for reason in reasons)

    payload = {
        "command": "llm-quality-gates",
        "generated_at": generated_at,
        "repo_root": repo_root,
        "quality_status": {
            "valid": not blocking_reasons,
            "blocking_reason_count": len(blocking_reasons),
            "blocking_reasons": blocking_reasons,
            "warn_reason_count": len(warn_reasons),
            "warn_reasons": warn_reasons,
        },
        "baseline_preflight": baseline_preflight,
        "gates": gate_statuses,
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None)
    if isinstance(args.output, str) and args.output.strip():
        output_path = os.path.abspath(os.path.expanduser(args.output))
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    print(output)
    return 0 if not blocking_reasons else 2


def _run_llm_quality_matrix(args):
    raw_client_slugs = _parse_csv_values(getattr(args, "client_slugs", None))
    client_slugs = []
    seen_slugs = set()
    for slug in raw_client_slugs:
        normalized = slug.strip()
        if not normalized or normalized in seen_slugs:
            continue
        seen_slugs.add(normalized)
        client_slugs.append(normalized)
    if not client_slugs:
        raise SystemExit("llm-quality-matrix: provide at least one --client-slugs value")

    forwarded_args = list(getattr(args, "llm_quality_args", []) or [])
    if forwarded_args and forwarded_args[0] == "--":
        forwarded_args = forwarded_args[1:]
    forbidden_flags = ("--client-slug", "--run-id", "--output-dir")
    for token in forwarded_args:
        if token in forbidden_flags:
            raise SystemExit(
                f"llm-quality-matrix: forward args must not override {token}; use matrix options"
            )
        for flag in forbidden_flags:
            if token.startswith(f"{flag}="):
                raise SystemExit(
                    f"llm-quality-matrix: forward args must not override {flag}; use matrix options"
                )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id_prefix = (args.run_id_prefix or f"matrix-{timestamp}").strip()
    if not run_id_prefix:
        run_id_prefix = f"matrix-{timestamp}"
    output_dir = _llm_quality_prepare_output_dir(
        args.output_dir or os.path.join("/tmp/booking_quality", run_id_prefix),
        allow_overwrite=bool(getattr(args, "allow_output_overwrite", False)),
    )

    matrix_rows = []
    for index, client_slug in enumerate(client_slugs, start=1):
        child_run_id = f"{run_id_prefix}-{index:02d}-{client_slug}"
        child_output_dir = os.path.join(output_dir, child_run_id)
        child_argv = [
            "--client-slug",
            client_slug,
            "--run-id",
            child_run_id,
            "--output-dir",
            child_output_dir,
            *forwarded_args,
        ]
        started_at = datetime.now(timezone.utc)
        row = {
            "client_slug": client_slug,
            "run_id": child_run_id,
            "output_dir": child_output_dir,
            "started_at": started_at.isoformat(),
            "finished_at": None,
            "status": "ok",
            "exit_code": 0,
            "error": None,
            "summary": None,
            "infra_valid": None,
            "semantic_valid": None,
            "comparison_blocked": None,
            "strict_pass_rate": None,
            "degraded_fallback_rate": None,
            "missing_bot_reply": None,
        }
        try:
            child_args = _parse_llm_quality_args(child_argv)
            _run_llm_quality(child_args)
        except SystemExit as exc:
            code = exc.code
            if code in (None, 0):
                row["exit_code"] = 0
            elif isinstance(code, int):
                row["exit_code"] = code
                row["status"] = "failed"
            else:
                row["exit_code"] = 1
                row["status"] = "failed"
            if row["status"] != "ok":
                row["error"] = str(code)
        except Exception as exc:
            row["exit_code"] = 1
            row["status"] = "failed"
            row["error"] = str(exc)

        summary_path = os.path.join(child_output_dir, "summary.json")
        row["summary"] = summary_path if os.path.exists(summary_path) else None
        if row["summary"]:
            try:
                with open(summary_path, "r", encoding="utf-8") as handle:
                    summary_payload = json.load(handle)
                row["infra_valid"] = summary_payload.get("infra_valid")
                row["semantic_valid"] = summary_payload.get("semantic_valid")
                quality_status = summary_payload.get("quality_status")
                if isinstance(quality_status, dict):
                    row["comparison_blocked"] = quality_status.get("comparison_blocked")
                metrics = summary_payload.get("metrics")
                if isinstance(metrics, dict):
                    rates = metrics.get("rates")
                    if isinstance(rates, dict):
                        row["strict_pass_rate"] = rates.get("strict_pass_rate")
                        row["degraded_fallback_rate"] = rates.get("degraded_fallback_rate")
                    counts = metrics.get("counts")
                    if isinstance(counts, dict):
                        row["missing_bot_reply"] = counts.get("turns_missing_response")
            except Exception as exc:
                row["status"] = "failed"
                row["exit_code"] = row["exit_code"] or 1
                row["error"] = f"summary_parse_error:{exc}"
        row["finished_at"] = datetime.now(timezone.utc).isoformat()
        matrix_rows.append(row)
        print(
            json.dumps(
                {
                    "stage": "llm_quality_matrix_child",
                    "client_slug": row["client_slug"],
                    "run_id": row["run_id"],
                    "status": row["status"],
                    "exit_code": row["exit_code"],
                    "summary": row["summary"],
                    "strict_pass_rate": row["strict_pass_rate"],
                    "degraded_fallback_rate": row["degraded_fallback_rate"],
                    "missing_bot_reply": row["missing_bot_reply"],
                },
                ensure_ascii=False,
            )
        )
        if row["status"] != "ok" and not args.continue_on_error:
            break

    all_ok = all(row.get("status") == "ok" for row in matrix_rows)
    matrix_summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id_prefix": run_id_prefix,
        "output_dir": output_dir,
        "client_slugs": client_slugs,
        "all_ok": all_ok,
        "rows": matrix_rows,
        "forwarded_args": forwarded_args,
    }
    matrix_summary_path = os.path.join(output_dir, "matrix_summary.json")
    with open(matrix_summary_path, "w", encoding="utf-8") as handle:
        json.dump(matrix_summary, handle, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "stage": "llm_quality_matrix_done",
                "output_dir": output_dir,
                "summary": matrix_summary_path,
                "all_ok": all_ok,
                "rows": len(matrix_rows),
            },
            ensure_ascii=False,
        )
    )
    if not all_ok:
        raise SystemExit("llm-quality-matrix: one or more child runs failed")


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
    continue_on_infra = not args.fail_on_infra

    container_name, _ = resolve_container_name()
    if not args.skip_preflight:
        preflight = _chaos_preflight(base_url, args.timeout)
        print(
            json.dumps(
                {
                    "event": "preflight",
                    "ok": preflight.get("ok"),
                    "checks": preflight.get("checks"),
                },
                ensure_ascii=False,
            )
        )
        if not preflight.get("ok") and not continue_on_infra:
            raise SystemExit("chaos-sim: preflight failed")

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
    start_time = time.time()
    max_runtime = args.max_runtime
    continue_on_infra = not args.fail_on_infra

    output_dir = args.output_dir or os.path.join(
        os.getcwd(),
        "ops",
        "artifacts",
        "chaos_sim",
        timestamp,
    )
    os.makedirs(output_dir, exist_ok=True)
    events_path = os.path.join(output_dir, "events.jsonl")
    events_handle = open(events_path, "w", encoding="utf-8")
    failures_partial_path = os.path.join(output_dir, "failures.partial.jsonl")
    failures_handle = open(failures_partial_path, "w", encoding="utf-8")
    summary_partial_path = os.path.join(output_dir, "summary.partial.json")
    preflight_path = None
    rag_summary_path = None

    def _record_event(event):
        events_handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        events_handle.flush()

    def _record_failure(record):
        failures_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        failures_handle.flush()

    def _write_checkpoint(summary_payload, stats_payload):
        with open(summary_partial_path, "w", encoding="utf-8") as handle:
            json.dump(summary_payload, handle, ensure_ascii=False, indent=2)
        stats_path = os.path.join(output_dir, "stats.json")
        with open(stats_path, "w", encoding="utf-8") as handle:
            json.dump(stats_payload, handle, ensure_ascii=False, indent=2)

    def _build_summary_payload():
        return {
            "simulation_id": simulation_id,
            "seed": seed,
            "cases": stats["cases"],
            "cases_processed": processed_cases,
            "turns": stats["turns"],
            "failures": stats["failures"],
            "infra_failures": stats["infra_failures"],
            "infra_retries": stats["infra_retries"],
            "failure_types": failure_counts,
            "failure_patterns": pattern_counts,
            "output_dir": output_dir,
            "jid_base": jid_base,
            "client_slug": client_slug,
            "console_mode": args.console_mode,
            "llm_mode": args.mode,
            "turns_path": turns_path,
            "events_path": events_path,
            "failures_partial_path": failures_partial_path,
            "preflight_path": preflight_path,
            "max_runtime": max_runtime,
            "continue_on_infra": continue_on_infra,
            "rag_audit": rag_audit,
            "rag_debug_path": rag_debug_path,
            "rag_summary_path": rag_summary_path,
            "interrupted": interrupted,
            "stop_reason": stop_reason,
        }
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
    if not args.skip_preflight:
        preflight = _chaos_preflight(base_url, args.timeout)
        preflight_path = os.path.join(output_dir, "preflight.json")
        with open(preflight_path, "w", encoding="utf-8") as handle:
            json.dump(preflight, handle, ensure_ascii=False, indent=2)
        _record_event(
            {
                "event": "preflight",
                "ok": preflight.get("ok"),
                "checks": preflight.get("checks"),
            }
        )
        if not preflight.get("ok") and not continue_on_infra:
            raise SystemExit("chaos-sim: preflight failed")
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
    client_meta, client_error = _fetch_client_meta(
        db_user, client_slug, branch_slug=args.branch_slug
    )
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

    allowed_kinds = {"booking", "policy", "consult", "info", "ood"}
    kinds = None
    if args.kinds:
        kinds = [item.strip() for item in args.kinds.split(",") if item.strip()]
        invalid = sorted(set(kinds) - allowed_kinds)
        if invalid:
            raise SystemExit(f"chaos-sim: invalid --kinds value(s): {', '.join(invalid)}")
    cases = _chaos_generate_cases(args.count, rng, args.min_turns, args.max_turns, args.noise, kinds=kinds)
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
        "infra_failures": 0,
        "infra_retries": 0,
        "escalations": 0,
        "lead_captured": 0,
        "booking_failed": 0,
        "manager_resolved": 0,
        "console_resolved": 0,
    }
    processed_cases = 0
    _record_event(
        {
            "event": "start",
            "simulation_id": simulation_id,
            "seed": seed,
            "cases": len(cases),
            "client_slug": client_slug,
        }
    )

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
        if max_runtime and time.time() - start_time > max_runtime:
            stop_requested = True
            interrupted = True
            stop_reason = "max_runtime"
            break
        remote_jid = _build_remote_jid(case_idx)
        conversation_id = None
        case_infra_failed = False
        for turn_idx, turn in enumerate(case["turns"], start=1):
            if stop_requested:
                break
            if max_runtime and time.time() - start_time > max_runtime:
                stop_requested = True
                interrupted = True
                stop_reason = "max_runtime"
                break
            if turn.get("type") == "manager":
                if args.manager_mode == "skip":
                    if turns_handle:
                        turns_handle.write(
                            json.dumps(
                                {
                                    "case_id": case["case_id"],
                                    "turn": turn_idx,
                                    "type": "manager",
                                    "skipped": "manager_mode_skip",
                                    "conversation_id": conversation_id,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                    continue
                if not conversation_id:
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "manager",
                        "failure": ["missing_conversation_id"],
                    }
                    failures.append(record)
                    _record_failure(record)
                    _bump_failure_counts(["missing_conversation_id"])
                    stats["failures"] += 1
                    continue
                handover_meta, _ = _fetch_handover_meta(db_user, conversation_id)
                handover_id = (handover_meta or {}).get("handover_id")
                if not handover_id:
                    conv_meta, _ = _fetch_conversation_meta(db_user, conversation_id)
                    if (conv_meta or {}).get("state") != "pending":
                        if turns_handle:
                            turns_handle.write(
                                json.dumps(
                                    {
                                        "case_id": case["case_id"],
                                        "turn": turn_idx,
                                        "type": "manager",
                                        "failure": [],
                                        "skipped": "handover_missing_not_pending",
                                        "conversation_id": conversation_id,
                                        "conversation_state": (conv_meta or {}).get("state"),
                                    },
                                    ensure_ascii=False,
                                )
                                + "\n"
                            )
                        continue
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "manager",
                        "failure": ["handover_missing"],
                    }
                    failures.append(record)
                    _record_failure(record)
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
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "manager",
                        "handover_id": handover_id,
                        "failure": ["manager_action_failed"],
                        "error": error,
                    }
                    failures.append(record)
                    _record_failure(record)
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
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "manager",
                        "handover_id": handover_id,
                        "failure": ["state_mismatch"],
                        "expected_state": expected_state,
                        "actual_state": (conv_meta or {}).get("state"),
                    }
                    failures.append(record)
                    _record_failure(record)
                    _bump_failure_counts(["state_mismatch"])
                    stats["failures"] += 1
                if (handover_meta or {}).get("status") != expected_status:
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "manager",
                        "handover_id": handover_id,
                        "failure": ["handover_status_mismatch"],
                        "expected_status": expected_status,
                        "actual_status": (handover_meta or {}).get("status"),
                    }
                    failures.append(record)
                    _record_failure(record)
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
            if args.sim_time:
                metadata["simulation_time"] = args.sim_time
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
            attempts = 0
            if not args.dry_run:
                response_status, response_body, response_error, attempts = _send_webhook_payload_with_retry(
                    webhook_url,
                    payload,
                    webhook_secret,
                    args.timeout,
                    args.retry_count,
                    args.retry_backoff,
                )
                if attempts > 1:
                    stats["infra_retries"] += max(0, attempts - 1)
                _record_event(
                    {
                        "event": "webhook_send",
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                        "status": response_status,
                        "error": response_error,
                        "attempts": attempts,
                    }
                )
                if response_error and _is_infra_error(response_error):
                    stats["infra_failures"] += 1
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "user",
                        "text": turn.get("text"),
                        "message_id": message_id,
                        "failure": ["infra_error"],
                        "error": response_error,
                        "status": response_status,
                        "attempts": attempts,
                    }
                    failures.append(record)
                    _record_failure(record)
                    _write_failure_bundle(output_dir, record, container_name)
                    _bump_failure_counts(["infra_error"])
                    stats["failures"] += 1
                    _record_event(
                        {
                            "event": "infra_error",
                            "case_id": case["case_id"],
                            "turn": turn_idx,
                            "message_id": message_id,
                            "error": response_error,
                        }
                    )
                    if not continue_on_infra:
                        stop_requested = True
                        interrupted = True
                        stop_reason = "infra_error"
                        break
                    case_infra_failed = True
                    break
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
                    record = {
                        "case_id": case["case_id"],
                        "turn": turn_idx,
                        "type": "user",
                        "text": turn.get("text"),
                        "message_id": message_id,
                        "failure": ["decision_meta_poll_failed"],
                        "error": poll_error,
                    }
                    failures.append(record)
                    _record_failure(record)
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
                    pattern_meta = meta
                    trace_action = _chaos_trace_action(trace_entries)
                    if trace_action:
                        pattern_meta = dict(meta or {})
                        pattern_meta["action"] = trace_action
                    pattern_keys = _chaos_build_failure_patterns(
                        failures_for_turn,
                        pattern_meta,
                        conv_meta,
                    )
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
                    _record_failure(record)
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

        if case_infra_failed:
            _record_event(
                {
                    "event": "case_infra_failed",
                    "case_id": case["case_id"],
                    "remote_jid": remote_jid,
                }
            )
        if stop_requested:
            break
        processed_cases += 1
        _write_checkpoint(_build_summary_payload(), stats)

    if turns_handle:
        turns_handle.close()
    if rag_debug_handle:
        rag_debug_handle.close()
    events_handle.close()
    failures_handle.close()

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
        "infra_failures": stats["infra_failures"],
        "infra_retries": stats["infra_retries"],
        "failure_types": failure_counts,
        "failure_patterns": pattern_counts,
        "output_dir": output_dir,
        "jid_base": jid_base,
        "client_slug": client_slug,
        "console_mode": args.console_mode,
        "llm_mode": args.mode,
        "turns_path": turns_path,
        "events_path": events_path,
        "failures_partial_path": failures_partial_path,
        "preflight_path": preflight_path,
        "max_runtime": max_runtime,
        "continue_on_infra": continue_on_infra,
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
        handle.write(f"- infra_failures: {stats['infra_failures']}\n")
        handle.write(f"- infra_retries: {stats['infra_retries']}\n")
        handle.write(f"- jid_base: {jid_base}\n")
        handle.write(f"- interrupted: {str(interrupted).lower()}\n")
        if stop_reason:
            handle.write(f"- stop_reason: {stop_reason}\n")
        handle.write(f"- escalations: {stats['escalations']}\n")
        handle.write(f"- lead_captured: {stats['lead_captured']}\n")
        handle.write(f"- booking_failed: {stats['booking_failed']}\n")
        handle.write(f"- manager_resolved: {stats['manager_resolved']}\n")
        handle.write(f"- console_resolved: {stats['console_resolved']}\n\n")
        handle.write(f"- events_path: {events_path}\n")
        handle.write(f"- failures_partial_path: {failures_partial_path}\n")
        if preflight_path:
            handle.write(f"- preflight_path: {preflight_path}\n")
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

def _run_dialog_report(args):
    db_user = _resolve_db_user_simple()
    tz_name = _sanitize_timezone(args.tz)
    start_ts = _normalize_datetime_input(args.start, args.date)
    end_ts = _normalize_datetime_input(args.end, args.date)
    if not start_ts or not end_ts:
        raise SystemExit("dialog-report: --start and --end are required")

    receiver_phone = args.receiver_phone
    client_slug = args.client_slug
    branch_id = args.branch_id
    instance_id = None
    remote_jid = args.remote_jid or _normalize_remote_jid(args.sender)

    if args.conversation_id:
        conv_ids = [args.conversation_id]
    else:
        if receiver_phone:
            resolved_branch, error = _fetch_client_by_branch_phone(db_user, receiver_phone)
            if error:
                raise SystemExit(f"dialog-report: receiver phone lookup failed ({error})")
            if not resolved_branch:
                raise SystemExit("dialog-report: receiver phone not found; provide --branch-id")
            client_slug = client_slug or resolved_branch.get("client_slug")
            branch_id = branch_id or resolved_branch.get("branch_id")
            instance_id = resolved_branch.get("instance_id")
        if not branch_id:
            raise SystemExit("dialog-report: provide --receiver-phone or --branch-id")
        if not remote_jid:
            raise SystemExit("dialog-report: provide --sender or --remote-jid")
        conv_ids, error = _fetch_dialog_conversation_ids(
            db_user, branch_id, remote_jid, tz_name, start_ts, end_ts
        )
        if error:
            raise SystemExit(f"dialog-report: db error ({error})")
        if not conv_ids:
            print("dialog-report: no conversations found for the window.")
            return
        max_convs = max(1, int(args.max_conversations))
        conv_ids = conv_ids[:max_convs]

    def _clean_text(value):
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Dialog Report",
        "",
        f"- generated_at: {generated_at}",
        f"- timezone: {tz_name}",
        f"- window: {start_ts} — {end_ts}",
        f"- sender: {args.sender or ''}",
        f"- receiver: {receiver_phone or ''}",
        f"- remote_jid: {remote_jid or ''}",
        f"- client_slug: {client_slug or ''}",
        f"- branch_id: {branch_id or ''}",
        f"- instance_id: {instance_id or ''}",
        f"- conversation_ids: {', '.join(conv_ids)}",
        "",
        "Notes:",
        "- Audio transcripts are shown only if ASR succeeded and saved.",
        "- Media files live under /home/zhan/truffles-media and may be cleaned by TTL.",
        "",
    ]

    for conv_id in conv_ids:
        rows, error = _fetch_dialog_rows(db_user, conv_id, tz_name, start_ts, end_ts)
        if error:
            raise SystemExit(f"dialog-report: db error ({error})")
        lines.append(f"## Conversation {conv_id}")
        lines.append("")
        if not rows:
            lines.append("_No messages in the requested window._")
            lines.append("")
            continue

        lines.append("### Timeline")
        for row in rows:
            ts = row.get("ts_local") or row.get("created_at") or ""
            role = row.get("role") or ""
            message_id = row.get("message_id") or row.get("message_uuid") or ""
            content = _clean_text(row.get("content"))
            media_bits = []
            media_type = row.get("media_type")
            if media_type:
                media_bits.append(f"media={media_type}")
            if row.get("asr_used"):
                media_bits.append(f"asr_used={row.get('asr_used')}")
            if row.get("asr_provider"):
                media_bits.append(f"asr_provider={row.get('asr_provider')}")
            if row.get("media_storage_path"):
                media_bits.append(f"storage={row.get('media_storage_path')}")
            transcript = _clean_text(row.get("media_transcript"))
            if transcript and transcript != content:
                media_bits.append(f"transcript={transcript}")
            suffix = f" [{'; '.join(media_bits)}]" if media_bits else ""
            lines.append(f"- {ts} {role} ({message_id}): {content}{suffix}")
        lines.append("")

        lines.append("### Decisions (user messages)")
        for row in rows:
            if row.get("role") != "user":
                continue
            ts = row.get("ts_local") or row.get("created_at") or ""
            message_id = row.get("message_id") or row.get("message_uuid") or ""
            content = _clean_text(row.get("content"))
            decision_meta = row.get("decision_meta")
            if not isinstance(decision_meta, dict):
                decision_meta = {}
            summary = {
                "action": decision_meta.get("action"),
                "intent": decision_meta.get("intent"),
                "source": decision_meta.get("source"),
                "fact_source": decision_meta.get("fact_source"),
                "info_sections": decision_meta.get("info_sections"),
                "fact_intents": decision_meta.get("fact_intents"),
                "service_query": decision_meta.get("service_query"),
                "service_query_source": decision_meta.get("service_query_source"),
                "service_query_score": decision_meta.get("service_query_score"),
                "rag_reason": decision_meta.get("rag_reason"),
                "llm_used": decision_meta.get("llm_used"),
                "trace_id": decision_meta.get("trace_id"),
            }
            outbox_summary = None
            if row.get("outbox_id") or row.get("outbox_status"):
                outbox_summary = {
                    "outbox_id": row.get("outbox_id"),
                    "status": row.get("outbox_status"),
                    "updated_at": row.get("outbox_updated_at"),
                    "error": row.get("outbox_error"),
                }
            lines.append(f"Message {message_id} ({ts}): {content}")
            lines.append(f"Decision summary: {json.dumps(summary, ensure_ascii=False)}")
            if outbox_summary:
                lines.append(f"Outbox: {json.dumps(outbox_summary, ensure_ascii=False)}")
            lines.append("Decision meta (raw):")
            lines.append("```json")
            lines.append(json.dumps(decision_meta, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

    output_path = args.output
    if not output_path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_path = f"/tmp/dialog-report-{stamp}.md"
    report = "\n".join(lines).rstrip() + "\n"
    if output_path == "-":
        print(report)
        return
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(json.dumps({"output": output_path, "conversations": len(conv_ids)}, ensure_ascii=False))


def _resolve_booking_commit_steps(case, *, time_shift_minutes: int = 0):
    now = datetime.now(timezone.utc) + timedelta(days=2, minutes=time_shift_minutes)
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
                    "simulation_mode": False,
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
            "simulation_mode": False,
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
    steps, booking_values = _resolve_booking_commit_steps(case, time_shift_minutes=0)
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
            "simulation_mode": False,
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

def _run_livecheck_ca12_booking_full(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    steps, booking_values = _resolve_booking_commit_steps(case, time_shift_minutes=60)
    if not steps:
        raise SystemExit("livecheck-auto: CA12 booking-full missing steps")
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
        raise SystemExit("livecheck-auto: CA12 remote_jid not in allowlist")

    confirm_reply = case.get("confirm_message") or "да"
    handover_message = case.get("handover_message") or "хочу поговорить с менеджером"
    manager_actions = case.get("manager_actions") or ["take", "resolve"]

    results = []
    manager_results = []
    conv_id = None
    appointment_id = None
    appointment_row = None
    audit_rows = None
    booking_commit_trace = None
    outbox_summary = None
    outbox_rows = None
    commit_message_id = None
    commit_meta = None
    booking_confirm_prompted = False
    booking_confirmed = False
    booking_confirm_decision = None

    for idx, step in enumerate(steps, start=1):
        base_text = step.get("message") or ""
        if not base_text:
            raise SystemExit("livecheck-auto: CA12 empty step message")
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"LC:AUTO:CA12:{timestamp}:{idx:02d}"
        include_marker = not step.get("suppress_marker")
        message = f"{text} [{marker}]" if include_marker else text
        message_id = f"LC-AUTO-{timestamp}-CA12-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()

        metadata = {
            "sender": "LivecheckAuto",
            "simulation_mode": False,
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
                raise SystemExit(f"livecheck-auto: CA12 decision_meta poll failed ({error})")
            conv_meta, conv_error = _fetch_conversation_meta(db_user, conv_id)

        conv_context = conv_meta.get("context") if isinstance(conv_meta, dict) else None
        expected_reply_type = conv_context.get("expected_reply_type") if isinstance(conv_context, dict) else None
        booking_state = conv_context.get("booking") if isinstance(conv_context, dict) else None
        trace_list = conv_context.get("decision_trace") if isinstance(conv_context, dict) else None

        if not args.dry_run:
            expected_reply = step.get("expect_expected_reply_type")
            if expected_reply and expected_reply_type != expected_reply:
                if (meta or {}).get("action") != "booking_confirm":
                    raise SystemExit(
                        f"livecheck-auto: CA12 expected_reply_type mismatch ({expected_reply_type})"
                    )
            expected_llm = step.get("expect_llm_used")
            if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                raise SystemExit("livecheck-auto: CA12 llm_used mismatch")
            expected_service = step.get("expect_booking_service")
            if expected_service:
                service = None
                if isinstance(booking_state, dict):
                    service = booking_state.get("service")
                if not service or expected_service not in str(service).lower():
                    raise SystemExit("livecheck-auto: CA12 booking.service mismatch")

        for entry in reversed(_trace_as_list(trace_list)):
            if entry.get("stage") == "booking_commit":
                booking_commit_trace = entry
                break
        if booking_commit_trace and not commit_message_id:
            commit_message_id = message_id
        if trace_list:
            booking_confirm_prompted = booking_confirm_prompted or _trace_has_entry(
                trace_list, "booking_confirm", "prompt"
            )
            booking_confirmed = booking_confirmed or _trace_has_entry(
                trace_list, "booking_confirm", "confirmed"
            )

        results.append(
            {
                "step": idx,
                "phase": "booking",
                "message_id": message_id,
                "conversation_id": conv_id,
                "expected_reply_type": expected_reply_type,
                "action": (meta or {}).get("action"),
                "slot_confirmation_required": (meta or {}).get("slot_confirmation_required"),
                "slot_confirmation_decision": (meta or {}).get("slot_confirmation_decision"),
                "booking_service": booking_state.get("service") if isinstance(booking_state, dict) else None,
                "trace_booking_commit": bool(booking_commit_trace),
                "llm_used": (meta or {}).get("llm_used"),
                "error": conv_error,
            }
        )

        if step.get("expect_booking_commit"):
            commit_message_id = message_id
            commit_meta = meta

        needs_confirmation = bool(
            (meta or {}).get("action") == "booking_confirm"
            or (meta or {}).get("slot_confirmation_required")
        )
        if needs_confirmation:
            confirm_marker = f"LC:AUTO:CA12:CONFIRM:{timestamp}:{idx:02d}"
            confirm_message_id = f"LC-AUTO-{timestamp}-CA12C-{idx:02d}-{uuid.uuid4().hex[:8]}"
            confirm_sent_at = datetime.now(timezone.utc).isoformat()
            confirm_payload = {
                "body": {
                    "messageType": "text",
                    "message": confirm_reply,
                    "metadata": {
                        "sender": "LivecheckAuto",
                        "simulation_mode": False,
                        "timestamp": int(time.time()),
                        "messageId": confirm_message_id,
                        "remoteJid": remote_jid,
                    },
                }
            }
            if instance_id:
                confirm_payload["body"]["metadata"]["instanceId"] = instance_id

            confirm_status = "dry_run"
            confirm_response_status = None
            confirm_response_body = None
            confirm_response_error = None
            if not args.dry_run:
                confirm_response_status, confirm_response_body, confirm_response_error = (
                    _send_webhook_payload(
                        webhook_url,
                        confirm_payload,
                        webhook_secret,
                        args.timeout,
                    )
                )
                confirm_status = (
                    "sent"
                    if confirm_response_status and 200 <= confirm_response_status < 300
                    else "error"
                )
            print(
                json.dumps(
                    {
                        "case_id": case["case_id"],
                        "step": f"{idx}.confirm",
                        "marker": confirm_marker,
                        "message_id": confirm_message_id,
                        "remote_jid": remote_jid,
                        "text": confirm_reply,
                        "sent_at": confirm_sent_at,
                        "status": confirm_status,
                        "http_status": confirm_response_status,
                        "error": confirm_response_error,
                        "response": (confirm_response_body or "")[:200]
                        if confirm_response_body
                        else None,
                    },
                    ensure_ascii=False,
                )
            )

            confirm_meta = None
            confirm_conv_meta = None
            confirm_conv_error = None
            if not args.dry_run:
                _post_admin_outbox_with_wait(
                    outbox_url,
                    admin_token,
                    args.timeout,
                    outbox_wait_seconds,
                )
                conv_id, confirm_meta, confirm_error = _poll_decision_meta(
                    db_user,
                    confirm_message_id,
                    args.poll_timeout,
                    args.poll_interval,
                    fail_fast_after=fail_fast_after,
                )
                if confirm_error:
                    raise SystemExit(
                        f"livecheck-auto: CA12 booking-confirm poll failed ({confirm_error})"
                    )
                confirm_conv_meta, confirm_conv_error = _fetch_conversation_meta(db_user, conv_id)

            confirm_context = (
                confirm_conv_meta.get("context") if isinstance(confirm_conv_meta, dict) else None
            )
            confirm_expected_reply_type = (
                confirm_context.get("expected_reply_type") if isinstance(confirm_context, dict) else None
            )
            confirm_booking_state = (
                confirm_context.get("booking") if isinstance(confirm_context, dict) else None
            )
            confirm_trace_list = (
                confirm_context.get("decision_trace") if isinstance(confirm_context, dict) else None
            )
            if confirm_trace_list:
                booking_confirmed = booking_confirmed or _trace_has_entry(
                    confirm_trace_list, "booking_confirm", "confirmed"
                )
            booking_confirm_decision = (confirm_meta or {}).get("slot_confirmation_decision")

            results.append(
                {
                    "step": f"{idx}.confirm",
                    "phase": "confirm",
                    "message_id": confirm_message_id,
                    "conversation_id": conv_id,
                    "expected_reply_type": confirm_expected_reply_type,
                    "action": (confirm_meta or {}).get("action"),
                    "slot_confirmation_required": (confirm_meta or {}).get(
                        "slot_confirmation_required"
                    ),
                    "slot_confirmation_decision": booking_confirm_decision,
                    "booking_service": confirm_booking_state.get("service")
                    if isinstance(confirm_booking_state, dict)
                    else None,
                    "trace_booking_commit": bool(booking_commit_trace),
                    "llm_used": (confirm_meta or {}).get("llm_used"),
                    "error": confirm_conv_error,
                }
            )

            for entry in reversed(_trace_as_list(confirm_trace_list)):
                if entry.get("stage") == "booking_commit":
                    booking_commit_trace = entry
                    break
            if booking_commit_trace and not commit_message_id:
                commit_message_id = confirm_message_id
            if idx < len(steps):
                time.sleep(rng.uniform(min_wait, max_wait))
        elif idx < len(steps):
            time.sleep(rng.uniform(min_wait, max_wait))

    if not args.dry_run:
        commit_required = any(step.get("expect_booking_commit") for step in steps)
        if commit_required and not booking_commit_trace:
            raise SystemExit("livecheck-auto: CA12 booking_commit trace missing")
        if commit_required:
            appointment_id = (commit_meta or {}).get("appointment_id") or (
                booking_commit_trace or {}
            ).get("appointment_id")
            if not appointment_id:
                raise SystemExit("livecheck-auto: CA12 appointment_id missing")
            appointment_row, appointment_error = _fetch_appointment_row(db_user, appointment_id)
            if appointment_error:
                raise SystemExit(
                    f"livecheck-auto: CA12 appointment fetch failed ({appointment_error})"
                )
            if not appointment_row:
                raise SystemExit("livecheck-auto: CA12 appointment row missing")
            audit_rows, audit_error = _fetch_appointment_audit_rows(
                db_user, appointment_id, limit=3
            )
            if audit_error:
                raise SystemExit(
                    f"livecheck-auto: CA12 appointment_audit fetch failed ({audit_error})"
                )
            if not audit_rows:
                raise SystemExit("livecheck-auto: CA12 appointment_audit missing")
            if not commit_message_id:
                raise SystemExit("livecheck-auto: CA12 commit message id missing")
            outbox_summary, outbox_error = _fetch_outbox_summary(
                db_user, client_id, commit_message_id
            )
            if outbox_error:
                raise SystemExit(
                    f"livecheck-auto: CA12 outbox summary failed ({outbox_error})"
                )
            if not outbox_summary or not outbox_summary.get("count"):
                raise SystemExit("livecheck-auto: CA12 outbox missing")
            outbox_rows, outbox_rows_error = _fetch_outbox_rows(
                db_user, client_id, commit_message_id, limit=3
            )
            if outbox_rows_error:
                raise SystemExit(
                    f"livecheck-auto: CA12 outbox rows failed ({outbox_rows_error})"
                )
            if outbox_summary.get("status") == "FAILED":
                raise SystemExit("livecheck-auto: CA12 outbox status FAILED")

    handover_before = None
    handover_after = None
    conv_before = None
    conv_after = None
    if not args.dry_run:
        conv_before, _ = _fetch_conversation_meta(db_user, conv_id)
        handover_before, _ = _fetch_handover_meta(db_user, conv_id)
        handover_id = (handover_before or {}).get("handover_id")
        if not handover_id:
            handover_marker = f"LC:AUTO:CA12:HANDOVER:{timestamp}"
            handover_message_id = f"LC-AUTO-{timestamp}-CA12H-{uuid.uuid4().hex[:8]}"
            handover_sent_at = datetime.now(timezone.utc).isoformat()
            handover_payload = {
                "body": {
                    "messageType": "text",
                    "message": f"{handover_message} [{handover_marker}]",
                    "metadata": {
                        "sender": "LivecheckAuto",
                        "simulation_mode": False,
                        "timestamp": int(time.time()),
                        "messageId": handover_message_id,
                        "remoteJid": remote_jid,
                    },
                }
            }
            if instance_id:
                handover_payload["body"]["metadata"]["instanceId"] = instance_id
            handover_status, handover_body, handover_error = _send_webhook_payload(
                webhook_url, handover_payload, webhook_secret, args.timeout
            )
            print(
                json.dumps(
                    {
                        "case_id": case["case_id"],
                        "step": "handover",
                        "marker": handover_marker,
                        "message_id": handover_message_id,
                        "remote_jid": remote_jid,
                        "text": handover_payload["body"]["message"],
                        "sent_at": handover_sent_at,
                        "status": "sent"
                        if handover_status and 200 <= handover_status < 300
                        else "error",
                        "http_status": handover_status,
                        "error": handover_error,
                        "response": (handover_body or "")[:200] if handover_body else None,
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
            conv_id, handover_meta, handover_meta_error = _poll_decision_meta(
                db_user,
                handover_message_id,
                args.poll_timeout,
                args.poll_interval,
                fail_fast_after=fail_fast_after,
            )
            if handover_meta_error:
                raise SystemExit(
                    f"livecheck-auto: CA12 handover meta poll failed ({handover_meta_error})"
                )
            if (handover_meta or {}).get("action") != "escalate":
                raise SystemExit("livecheck-auto: CA12 handover action mismatch")

            conv_before, _ = _fetch_conversation_meta(db_user, conv_id)
            handover_before, _ = _fetch_handover_meta(db_user, conv_id)
            handover_id = (handover_before or {}).get("handover_id")
            if not handover_id:
                raise SystemExit("livecheck-auto: CA12 handover_id missing")
        chat_id_raw = client_meta.get("telegram_chat_id")
        if not chat_id_raw:
            raise SystemExit("livecheck-auto: CA12 missing telegram_chat_id for client")
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            raise SystemExit(f"livecheck-auto: CA12 invalid telegram_chat_id {chat_id_raw}")
        topic_id = (conv_before or {}).get("telegram_topic_id")
        owner_id, owner_username = _parse_owner_identity(client_meta.get("owner_telegram_id"))
        manager_id = owner_id if owner_id is not None else 10001
        manager_username = owner_username or "ci_manager"

        for action in manager_actions:
            callback_payload = {
                "update_id": int(time.time()),
                "callback_query": {
                    "id": f"LC-AUTO-{timestamp}-CA12-{uuid.uuid4().hex[:6]}",
                    "from": {
                        "id": manager_id,
                        "is_bot": False,
                        "first_name": "CI",
                        "last_name": "Runner",
                        "username": manager_username,
                    },
                    "message": {
                        "message_id": int(time.time() * 1000) % 1000000,
                        "date": int(time.time()),
                        "chat": {"id": chat_id, "type": "supergroup", "title": "CI"},
                    },
                    "data": f"{action}_{handover_id}",
                },
            }
            if topic_id:
                callback_payload["callback_query"]["message"]["message_thread_id"] = topic_id
            action_status, action_body, action_error = _send_json_payload(
                f"{base_url}/telegram-webhook", callback_payload, args.timeout
            )
            _post_admin_outbox_with_wait(
                outbox_url,
                admin_token,
                args.timeout,
                outbox_wait_seconds,
            )
            conv_after, _ = _fetch_conversation_meta(db_user, conv_id)
            handover_after, _ = _fetch_handover_meta(db_user, conv_id)
            expected_state = "manager_active" if action == "take" else "bot_active"
            expected_status = "active" if action == "take" else "resolved"
            if (conv_after or {}).get("state") != expected_state:
                raise SystemExit(
                    "livecheck-auto: CA12 manager state mismatch "
                    f"(expected {expected_state}, got {(conv_after or {}).get('state')})"
                )
            if (handover_after or {}).get("status") != expected_status:
                raise SystemExit(
                    "livecheck-auto: CA12 handover status mismatch "
                    f"(expected {expected_status}, got {(handover_after or {}).get('status')})"
                )
            manager_results.append(
                {
                    "action": action,
                    "status": action_status,
                    "error": action_error,
                    "expected_state": expected_state,
                    "actual_state": (conv_after or {}).get("state"),
                    "expected_handover_status": expected_status,
                    "actual_handover_status": (handover_after or {}).get("status"),
                }
            )

    summary = {
        "suite": "ca12-booking-full",
        "case_id": case["case_id"],
        "conversation_id": conv_id,
        "booking_time": booking_values.get("booking_time"),
        "booking_name": booking_values.get("booking_name"),
        "booking_confirm_prompted": booking_confirm_prompted,
        "booking_confirmed": booking_confirmed,
        "booking_confirm_decision": booking_confirm_decision,
        "appointment_id": appointment_id,
        "appointment_status": appointment_row.get("status") if isinstance(appointment_row, dict) else None,
        "appointment_audit_action": audit_rows[0].get("action")
        if isinstance(audit_rows, list) and audit_rows
        else None,
        "trace_booking_commit": bool(booking_commit_trace),
        "outbox_status": outbox_summary.get("status") if isinstance(outbox_summary, dict) else None,
        "conversation_state_before": (conv_before or {}).get("state"),
        "conversation_state_after": (conv_after or {}).get("state"),
        "handover_status_before": (handover_before or {}).get("status"),
        "handover_status_after": (handover_after or {}).get("status"),
        "manager_actions": manager_results,
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
                "simulation_mode": False,
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
        "simulation_mode": False,
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
                "simulation_mode": False,
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
        "simulation_mode": False,
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
                    "simulation_mode": False,
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

    db_user = _resolve_db_user_simple()
    client_meta, client_error = _fetch_client_meta(
        db_user, client_slug, branch_slug=args.branch_slug
    )
    if client_error:
        raise SystemExit(f"livecheck-auto: client meta lookup failed ({client_error})")
    if not client_meta or not client_meta.get("client_id"):
        raise SystemExit(f"livecheck-auto: client {client_slug} not found in DB")

    webhook_secret, webhook_secret_source = _livecheck_select_webhook_secret(
        client_slug=client_slug,
        explicit_secret=args.webhook_secret,
        client_meta=client_meta,
    )
    if not webhook_secret:
        raise SystemExit("livecheck-auto: missing webhook secret")

    admin_token = args.admin_token or os.environ.get("ALERTS_ADMIN_TOKEN")
    if not admin_token and container_name:
        admin_token = _resolve_env_from_container(container_name, "ALERTS_ADMIN_TOKEN")
    if not admin_token and not args.dry_run:
        raise SystemExit("livecheck-auto: missing admin token")

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
        "webhook_secret_source": webhook_secret_source,
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
        "ca12-booking-full",
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
    if args.suite == "ca12-booking-full":
        summary = _run_livecheck_ca12_booking_full(args, context)
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
            "simulation_mode": False,
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
            # Skip ACK for CA06/CA07 to avoid overwriting consult/OOD traces.
            if args.suite not in {"ca06-consult", "ca07-ood"}:
                ack_marker = f"LC:ACK:{case['case_id']}:{timestamp}:{idx:02d}"
                ack_message_id = f"LC-ACK-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
                ack_text = args.ack_text or "ок"
                ack_payload = {
                    "body": {
                        "messageType": "text",
                        "message": ack_text,
                        "metadata": {
                            "sender": "LivecheckAuto",
                            "simulation_mode": False,
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
                    "trace_policy_source": (trace_entry or {}).get("source") if trace_entry else None,
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


def _parse_branch_domain_pairs(values):
    mapping = {}
    for raw in values or []:
        token = str(raw or "").strip()
        if not token:
            continue
        if "=" not in token:
            raise SystemExit(
                "onboarding-fleet-remediate: --branch-domain requires key=domain_slug"
            )
        key, domain = token.split("=", 1)
        key = key.strip().lower()
        domain = domain.strip().lower()
        if not key or not domain:
            raise SystemExit(
                "onboarding-fleet-remediate: --branch-domain requires non-empty key and domain_slug"
            )
        mapping[key] = domain
    return mapping


_ONBOARDING_HARD_GATE_DEFAULT_CODES = {
    "delivery:backlog_critical",
    "delivery:failed_24h_critical",
    "delivery:stale_processing_critical",
    "delivery:provider_billing_blocked_critical",
    "delivery:provider_auth_critical",
    "traffic:whatsapp_capability_mismatch",
    "traffic:telegram_capability_mismatch",
}


def _parse_env_bool_token(value, *, default=False):
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _normalize_branch_id(value):
    return str(value or "").strip().lower()


def _parse_branch_ids(values):
    result = set()
    for raw in values or []:
        token = str(raw or "").strip()
        if not token:
            continue
        for part in token.split(","):
            normalized = _normalize_branch_id(part)
            if normalized:
                result.add(normalized)
    return result


def _resolve_hard_gate_enforced(
    *,
    mode,
    branch_id,
    actual_global_enabled,
    actual_canary_ids,
    canary_branch_ids,
):
    if mode == "enforced":
        return True
    if mode == "shadow":
        return False
    if mode == "canary":
        return branch_id in canary_branch_ids
    return bool(actual_global_enabled) or branch_id in actual_canary_ids


def _project_hard_gate_row(
    row,
    *,
    mode,
    actual_global_enabled,
    actual_canary_ids,
    canary_branch_ids,
):
    branch_id = _normalize_branch_id(row.get("branch_id"))
    scorecard_ready = bool(row.get("scorecard_ready"))
    hard_gate_blockers = list(row.get("hard_gate_blockers") or [])
    scorecard_missing = list(row.get("scorecard_missing") or [])
    enforced = _resolve_hard_gate_enforced(
        mode=mode,
        branch_id=branch_id,
        actual_global_enabled=actual_global_enabled,
        actual_canary_ids=actual_canary_ids,
        canary_branch_ids=canary_branch_ids,
    )

    projected_status = "pass"
    projected_blockers = []
    if not scorecard_ready:
        projected_status = "blocked_scorecard"
        projected_blockers = scorecard_missing
    elif enforced and hard_gate_blockers:
        projected_status = "blocked_hard_gate"
        projected_blockers = hard_gate_blockers

    projected = dict(row)
    projected.update(
        {
            "rollout_mode": mode,
            "hard_gate_enforced": bool(enforced),
            "hard_gate_blockers": hard_gate_blockers,
            "projected_status": projected_status,
            "projected_blockers": projected_blockers,
        }
    )
    return projected


def _delivery_blockers_from_row(row):
    return [
        code
        for code in (row.get("readiness_blocker_codes") or [])
        if isinstance(code, str) and code.startswith("delivery:")
    ]


def _delivery_critical_blockers_from_row(row):
    return [code for code in _delivery_blockers_from_row(row) if code.endswith("_critical")]


def _delivery_reason_totals(rows):
    totals = {}
    for row in rows:
        profile = row.get("delivery_failure_profile")
        if not isinstance(profile, dict):
            continue
        for key, raw in profile.items():
            if key in {"window_hours", "total_failed_24h"}:
                continue
            try:
                value = int(raw or 0)
            except Exception:
                value = 0
            totals[key] = int(totals.get(key, 0)) + value
    return totals


def _delivery_remediation_actions_for_row(row):
    actions = []
    blockers = set(_delivery_blockers_from_row(row))
    profile = row.get("delivery_failure_profile") or {}
    primary_reason = row.get("delivery_primary_reason_code")

    if "delivery:stale_processing_critical" in blockers or int(profile.get("stale_processing") or 0) > 0:
        actions.append("release_stale_processing_queue")
    if "delivery:provider_billing_blocked_critical" in blockers or primary_reason == "provider_billing_blocked":
        actions.append("resolve_provider_billing_block")
    if "delivery:provider_auth_critical" in blockers or primary_reason == "provider_auth":
        actions.append("rotate_provider_credentials")
    if blockers:
        actions.append("run_outbox_process_and_review_failed")
        actions.append("classify_delivery_errors_and_apply_remediation")

    unique = []
    seen = set()
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        unique.append(action)
    return unique


def _resolve_diagnose_container(explicit_name):
    if explicit_name:
        return explicit_name
    container_name, docker_error = resolve_container_name()
    if docker_error:
        raise SystemExit(f"onboarding-fleet: docker error ({docker_error})")
    if not container_name:
        raise SystemExit("onboarding-fleet: truffles-api container not found")
    return container_name


def _load_json_output(raw_stdout, *, command_name):
    text = (raw_stdout or "").strip()
    if not text:
        raise SystemExit(f"{command_name}: empty response")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except Exception:
            continue
    raise SystemExit(f"{command_name}: non-json response ({text[:200]})")


def _run_onboarding_fleet_container(payload, *, container_name):
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_literal = json.dumps(payload_json)
    script = f"""python - <<'PY'
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func

from app.database import SessionLocal
from app.models import (
    Branch,
    Client,
    ClientCapability,
    ClientOnboardingContract,
    Conversation,
    Message,
    OutboxMessage,
    ReferencePack,
)
from app.services.onboarding_state import build_onboarding_scorecard
from app.services.provider_error_policy import classify_provider_error
from app.services.reference_pack_integrity import (
    REFERENCE_PACK_SCHEMA_VERSION,
    build_reference_pack_metadata,
    evaluate_reference_pack_integrity,
)

payload = json.loads({payload_literal})
mode = payload.get("mode")
active_only = bool(payload.get("active_only", True))
apply_changes = bool(payload.get("apply_changes", False))
default_domain_slug = (payload.get("default_domain_slug") or "").strip().lower() or None
branch_domain_map = payload.get("branch_domain_map") or {{}}
confirm_payment = bool(payload.get("confirm_payment", False))
ensure_contract = bool(payload.get("ensure_contract", True))
sync_reference_pack = bool(payload.get("sync_reference_pack", False))
hard_gate_codes = set(payload.get("hard_gate_codes") or [])
delivery_window_hours = int(payload.get("delivery_window_hours") or 24)
normalize_reference_branch = bool(payload.get("normalize_reference_branch", True))
if delivery_window_hours <= 0:
    delivery_window_hours = 24

session = SessionLocal()
try:
    query = session.query(Branch)
    if active_only:
        query = query.filter(Branch.is_active.is_(True))
    branches = query.order_by(Branch.created_at.asc()).all()

    report_rows = []
    missing_counts = {{}}
    actions = []
    unresolved = []
    now = datetime.now(timezone.utc)

    def load_recent_inbound_map():
        rows = (
            session.query(
                Conversation.branch_id.label("branch_id"),
                func.max(Message.created_at).label("last_inbound_at"),
            )
            .join(Message, Message.conversation_id == Conversation.id)
            .filter(
                Conversation.branch_id.isnot(None),
                Message.role == "user",
            )
            .group_by(Conversation.branch_id)
            .all()
        )
        payload = {{}}
        for row in rows:
            branch_id = row.branch_id
            observed_at = row.last_inbound_at
            if branch_id and observed_at:
                payload[branch_id] = observed_at
        return payload

    recent_inbound_by_branch = load_recent_inbound_map()

    def has_recent_inbound_at(last_inbound_at, *, window_days=30):
        if last_inbound_at is None:
            return False
        try:
            safe_days = max(1, int(window_days or 30))
        except Exception:
            safe_days = 30
        return last_inbound_at >= now - timedelta(days=safe_days)

    def _row_rank(row):
        score = 0
        if row.get("go_live_allowed"):
            score += 100
        if row.get("has_recent_inbound"):
            score += 70
        has_instance_id = bool(row.get("has_instance_id"))
        has_phone = bool(row.get("has_phone"))
        if has_instance_id and has_phone:
            score += 60
        elif has_instance_id:
            score += 25
        elif has_phone:
            score += 15
        if row.get("onboarding_go_no_go"):
            score += 20
        if row.get("integration_ok"):
            score += 5
        return (
            -score,
            str(row.get("branch_slug") or ""),
            str(row.get("branch_id") or ""),
        )

    def _row_is_production_like(row):
        if not row.get("is_active"):
            return False
        if row.get("go_live_allowed"):
            return True
        if row.get("has_recent_inbound"):
            return True
        return bool(row.get("has_instance_id")) and bool(row.get("has_phone"))

    def select_reference_rows(rows):
        grouped = {{}}
        for row in rows:
            client_id = str(row.get("client_id") or "")
            if not client_id:
                continue
            grouped.setdefault(client_id, []).append(row)
        decisions = {{}}
        for client_id, client_rows in grouped.items():
            active_rows = [row for row in client_rows if row.get("is_active")]
            if not active_rows:
                decisions[client_id] = {{"branch_ids": [], "reason": "no_active_branches"}}
                continue
            production_rows = [row for row in active_rows if _row_is_production_like(row)]
            if production_rows:
                ordered = sorted(production_rows, key=_row_rank)
                decisions[client_id] = {{
                    "branch_ids": [str(row.get("branch_id")) for row in ordered if row.get("branch_id")],
                    "reason": "active_live_signals",
                }}
                continue
            best_row = sorted(active_rows, key=_row_rank)[0]
            best_id = str(best_row.get("branch_id")) if best_row.get("branch_id") else None
            decisions[client_id] = {{
                "branch_ids": [best_id] if best_id else [],
                "reason": "active_fallback_best_candidate",
            }}
        return decisions

    def latest_capability(branch):
        return (
            session.query(ClientCapability)
            .filter(
                ClientCapability.client_id == branch.client_id,
                ClientCapability.branch_id == branch.id,
                ClientCapability.scope == "branch",
                ClientCapability.status == "active",
            )
            .order_by(ClientCapability.created_at.desc())
            .first()
        )

    def latest_contract(branch):
        return (
            session.query(ClientOnboardingContract)
            .filter(
                ClientOnboardingContract.client_id == branch.client_id,
                ClientOnboardingContract.branch_id == branch.id,
                ClientOnboardingContract.scope == "branch",
                ClientOnboardingContract.status == "active",
            )
            .order_by(ClientOnboardingContract.created_at.desc())
            .first()
        )

    def read_domain(payload_json):
        if not isinstance(payload_json, dict):
            return None
        value = payload_json.get("domain_slug")
        if not isinstance(value, str):
            return None
        value = value.strip().lower()
        return value or None

    def resolve_domain(branch, cap_domain, contract_domain):
        if contract_domain:
            return contract_domain, "contract"
        if cap_domain:
            return cap_domain, "capability"
        branch_key_id = str(branch.id).strip().lower()
        branch_key_slug = (branch.slug or "").strip().lower()
        if branch_key_id and branch_key_id in branch_domain_map:
            return str(branch_domain_map[branch_key_id]).strip().lower(), "map:branch_id"
        if branch_key_slug and branch_key_slug in branch_domain_map:
            return str(branch_domain_map[branch_key_slug]).strip().lower(), "map:branch_slug"
        if default_domain_slug:
            return default_domain_slug, "default"
        return None, None

    def ensure_capability_domain(record, *, domain_slug):
        payload_json = record.payload_json if isinstance(record.payload_json, dict) else {{}}
        next_payload = dict(payload_json)
        if str(next_payload.get("domain_slug") or "").strip().lower() == domain_slug:
            return False
        next_payload["domain_slug"] = domain_slug
        record.payload_json = next_payload
        record.updated_at = now
        return True

    def ensure_contract_domain(record, *, domain_slug):
        payload_json = record.payload_json if isinstance(record.payload_json, dict) else {{}}
        next_payload = dict(payload_json)
        if str(next_payload.get("domain_slug") or "").strip().lower() != domain_slug:
            next_payload["domain_slug"] = domain_slug
        purchased = next_payload.get("purchased")
        if not isinstance(purchased, dict):
            purchased = {{}}
        if str(purchased.get("domain_slug") or "").strip().lower() != domain_slug:
            purchased = dict(purchased)
            purchased["domain_slug"] = domain_slug
        next_payload["purchased"] = purchased
        changed = next_payload != payload_json
        if changed:
            record.payload_json = next_payload
            record.updated_at = now
        return changed

    def ensure_reference_pack(domain_slug):
        record = (
            session.query(ReferencePack)
            .filter(ReferencePack.domain_slug == domain_slug)
            .first()
        )
        if not sync_reference_pack:
            return record, []
        act = []
        if not record:
            metadata = build_reference_pack_metadata(
                domain_slug=domain_slug,
                metadata={{"source": "onboarding_fleet_remediate"}},
            )
            record = ReferencePack(
                id=uuid4(),
                domain_slug=domain_slug,
                title=f"Reference pack: {{domain_slug}}",
                description="Auto-created by onboarding fleet remediation",
                schema_version=REFERENCE_PACK_SCHEMA_VERSION,
                status="active",
                metadata_json=metadata,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            act.append("reference_pack_created")
            return record, act
        metadata_json = record.metadata_json if isinstance(record.metadata_json, dict) else None
        next_metadata = build_reference_pack_metadata(
            domain_slug=domain_slug,
            metadata=metadata_json,
        )
        if (
            record.schema_version != REFERENCE_PACK_SCHEMA_VERSION
            or record.metadata_json != next_metadata
            or record.status != "active"
        ):
            record.schema_version = REFERENCE_PACK_SCHEMA_VERSION
            record.metadata_json = next_metadata
            record.status = "active"
            record.updated_at = now
            act.append("reference_pack_integrity_synced")
        return record, act

    def classify_delivery_reason(last_error):
        normalized = str(last_error or "").strip().lower()
        if not normalized:
            return "unknown", "Unknown delivery error"
        if normalized.startswith("stale_processing"):
            return "stale_processing", "Stale processing"
        classified = classify_provider_error(last_error)
        if classified.kind == "billing_blocked":
            return "provider_billing_blocked", classified.incident_reason_label
        if classified.kind == "auth":
            return "provider_auth", classified.incident_reason_label
        if classified.kind == "rate_limited":
            return "provider_rate_limited", classified.incident_reason_label
        if classified.kind == "unavailable":
            return "provider_unavailable", classified.incident_reason_label
        return "unknown", classified.incident_reason_label

    def extract_delivery_event_type(payload_json):
        if not isinstance(payload_json, dict):
            return None
        value = payload_json.get("event_type")
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        return normalized or None

    def is_delivery_event(event_type):
        if not event_type:
            return False
        if event_type in {{"provider_gateway.outbound"}}:
            return True
        return any(
            event_type.startswith(prefix)
            for prefix in ("whatsapp.send_", "telegram.send_", "instagram.send_", "web.send_")
        )

    def collect_delivery_failure_profile(branch):
        delivery_cutoff = now - timedelta(hours=delivery_window_hours)
        failed_rows = (
            session.query(OutboxMessage.last_error, OutboxMessage.payload_json)
            .filter(
                OutboxMessage.client_id == branch.client_id,
                OutboxMessage.branch_id == branch.id,
                OutboxMessage.status == "FAILED",
                OutboxMessage.updated_at >= delivery_cutoff,
            )
            .all()
        )
        counts = {{
            "window_hours": delivery_window_hours,
            "total_failed_24h": 0,
            "non_delivery_failed_24h": 0,
            "stale_processing": 0,
            "provider_billing_blocked": 0,
            "provider_auth": 0,
            "provider_rate_limited": 0,
            "provider_unavailable": 0,
            "unknown": 0,
        }}
        labels = {{}}
        for row in failed_rows:
            if isinstance(row, (tuple, list)):
                last_error = row[0] if row else None
                payload_json = row[1] if len(row) > 1 else None
            else:
                last_error = getattr(row, "last_error", None)
                payload_json = getattr(row, "payload_json", None)
            event_type = extract_delivery_event_type(payload_json)
            if not is_delivery_event(event_type):
                counts["non_delivery_failed_24h"] = int(counts.get("non_delivery_failed_24h", 0)) + 1
                continue
            counts["total_failed_24h"] = int(counts.get("total_failed_24h", 0)) + 1
            reason_code, reason_label = classify_delivery_reason(last_error)
            counts[reason_code] = int(counts.get(reason_code, 0)) + 1
            if reason_label and reason_code not in labels:
                labels[reason_code] = reason_label

        primary_reason_code = "unknown"
        primary_reason_label = labels.get("unknown") or "Unknown delivery error"
        primary_reason_count = int(counts.get("unknown", 0))
        for candidate in [
            "provider_billing_blocked",
            "provider_auth",
            "provider_unavailable",
            "provider_rate_limited",
            "stale_processing",
            "unknown",
        ]:
            candidate_count = int(counts.get(candidate, 0))
            if candidate_count > primary_reason_count:
                primary_reason_code = candidate
                primary_reason_label = labels.get(candidate) or candidate
                primary_reason_count = candidate_count

        return counts, primary_reason_code, primary_reason_label, primary_reason_count

    for branch in branches:
        client = session.query(Client).filter(Client.id == branch.client_id).first()
        cap = latest_capability(branch)
        contract = latest_contract(branch)
        cap_domain = read_domain(cap.payload_json if cap else None)
        contract_domain = read_domain(contract.payload_json if contract else None)
        resolved_domain, domain_source = resolve_domain(branch, cap_domain, contract_domain)

        row_actions = []

        if mode == "remediate":
            if not resolved_domain:
                unresolved.append(
                    {{
                        "branch_id": str(branch.id),
                        "branch_slug": branch.slug,
                        "client_id": str(branch.client_id),
                        "client_slug": client.name if client else None,
                        "reason": "domain_unresolved",
                    }}
                )
            else:
                if cap:
                    if ensure_capability_domain(cap, domain_slug=resolved_domain):
                        row_actions.append("capability_domain_updated")
                else:
                    cap = ClientCapability(
                        id=uuid4(),
                        client_id=branch.client_id,
                        branch_id=branch.id,
                        scope="branch",
                        payload_json={{
                            "domain_slug": resolved_domain,
                            "channels": {{}},
                            "providers": {{}},
                            "features": {{}},
                        }},
                        schema_version="v1",
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(cap)
                    row_actions.append("capability_created")

                if ensure_contract:
                    if contract:
                        if ensure_contract_domain(contract, domain_slug=resolved_domain):
                            row_actions.append("onboarding_contract_domain_updated")
                    else:
                        contract = ClientOnboardingContract(
                            id=uuid4(),
                            client_id=branch.client_id,
                            branch_id=branch.id,
                            scope="branch",
                            payload_json={{
                                "domain_slug": resolved_domain,
                                "purchased": {{
                                    "domain_slug": resolved_domain,
                                    "channels": {{}},
                                    "providers": {{}},
                                    "features": {{}},
                                }},
                            }},
                            schema_version="v1",
                            status="active",
                            payment_status="pending",
                            created_at=now,
                            updated_at=now,
                        )
                        session.add(contract)
                        row_actions.append("onboarding_contract_created")

                if contract and confirm_payment and contract.payment_status != "confirmed":
                    contract.payment_status = "confirmed"
                    contract.payment_confirmed_at = now
                    contract.payment_confirmed_by = None
                    contract.updated_at = now
                    row_actions.append("payment_confirmed")

                if resolved_domain:
                    _, pack_actions = ensure_reference_pack(resolved_domain)
                    row_actions.extend(pack_actions)

            if row_actions:
                session.flush()
                cap_domain = read_domain(cap.payload_json if cap else None)
                contract_domain = read_domain(contract.payload_json if contract else None)
                resolved_domain = contract_domain or cap_domain or resolved_domain

        effective_domain = resolved_domain or contract_domain or cap_domain
        reference_pack = None
        reference_pack_integrity_missing = []
        if effective_domain:
            reference_pack = (
                session.query(ReferencePack)
                .filter(ReferencePack.domain_slug == effective_domain)
                .first()
            )
            if reference_pack:
                reference_pack_integrity_missing = evaluate_reference_pack_integrity(
                    domain_slug=reference_pack.domain_slug,
                    schema_version=reference_pack.schema_version,
                    metadata=reference_pack.metadata_json if isinstance(reference_pack.metadata_json, dict) else None,
                )
            else:
                reference_pack_integrity_missing = ["reference_pack"]
        else:
            reference_pack_integrity_missing = ["reference_pack_domain"]

        scorecard = build_onboarding_scorecard(session, branch)
        missing = list(scorecard.missing or [])
        sla_loop = getattr(scorecard, "sla_control_loop", None)
        pipeline = getattr(scorecard, "operational_pipeline", None)
        readiness_kernel = getattr(scorecard, "readiness_kernel", None)
        readiness_status = getattr(readiness_kernel, "status", None) if readiness_kernel is not None else None
        readiness_blocker_codes = (
            list(getattr(readiness_kernel, "blocker_codes", []) or [])
            if readiness_kernel is not None
            else []
        )
        hard_gate_candidates = (
            list(getattr(readiness_kernel, "shadow_hard_gate_blockers", []) or [])
            if readiness_kernel is not None
            else []
        )
        if not hard_gate_candidates:
            hard_gate_candidates = list(readiness_blocker_codes)
        hard_gate_blockers = [
            code
            for code in hard_gate_candidates
            if isinstance(code, str) and (code.startswith("go_no_go:") or code in hard_gate_codes)
        ]
        (
            delivery_failure_profile,
            delivery_primary_reason_code,
            delivery_primary_reason_label,
            delivery_primary_reason_count,
        ) = collect_delivery_failure_profile(branch)
        last_inbound_at = recent_inbound_by_branch.get(branch.id)
        has_instance_id = bool(str(branch.instance_id or "").strip())
        has_phone = bool(str(branch.phone or "").strip())
        go_live_state = str(branch.go_live_state or "").strip().lower() or "pending"
        waiver_until = branch.go_live_waiver_until
        go_live_allowed = bool(
            go_live_state == "approved"
            or (waiver_until is not None and waiver_until > now)
        )
        onboarding_go_no_go = (branch.onboarding_state or "").strip().lower() == "go_no_go"
        integration_ok = (branch.integration_state or "").strip().lower() == "ok"
        branch_has_recent_inbound = has_recent_inbound_at(
            last_inbound_at,
            window_days=30,
        )
        for code in missing:
            missing_counts[code] = int(missing_counts.get(code, 0)) + 1

        report_rows.append(
            {{
                "branch_id": str(branch.id),
                "branch_slug": branch.slug,
                "client_id": str(branch.client_id),
                "client_slug": client.name if client else None,
                "is_active": bool(branch.is_active),
                "has_instance_id": has_instance_id,
                "has_phone": has_phone,
                "has_recent_inbound": branch_has_recent_inbound,
                "last_inbound_at": last_inbound_at.isoformat() if last_inbound_at else None,
                "go_live_state": go_live_state,
                "go_live_waiver_until": waiver_until.isoformat() if waiver_until else None,
                "go_live_allowed": go_live_allowed,
                "onboarding_go_no_go": onboarding_go_no_go,
                "integration_ok": integration_ok,
                "scorecard_ready": bool(scorecard.ready),
                "scorecard_missing": missing,
                "sla_status": getattr(sla_loop, "status", None),
                "sla_pending_total": getattr(sla_loop, "pending_total", None),
                "sla_warning_total": getattr(sla_loop, "warning_total", None),
                "sla_breached_total": getattr(sla_loop, "breached_total", None),
                "sla_incidents": list(getattr(sla_loop, "active_incidents", []) or []),
                "pipeline_status": getattr(pipeline, "status", None),
                "pipeline_blocked": bool(getattr(pipeline, "blocked", False)) if pipeline is not None else None,
                "pipeline_current_stage_id": getattr(pipeline, "current_stage_id", None),
                "pipeline_blockers": list(getattr(pipeline, "blockers", []) or []),
                "readiness_status": readiness_status,
                "readiness_blocker_codes": readiness_blocker_codes,
                "hard_gate_blockers": hard_gate_blockers,
                "delivery_failure_profile": delivery_failure_profile,
                "delivery_primary_reason_code": delivery_primary_reason_code,
                "delivery_primary_reason_label": delivery_primary_reason_label,
                "delivery_primary_reason_count": delivery_primary_reason_count,
                "cap_domain": cap_domain,
                "contract_domain": contract_domain,
                "resolved_domain": effective_domain,
                "domain_source": domain_source,
                "payment_status": contract.payment_status if contract else None,
                "reference_pack_status": reference_pack.status if reference_pack else None,
                "reference_pack_integrity_missing": reference_pack_integrity_missing,
            }}
        )
        if row_actions:
            actions.append(
                {{
                    "branch_id": str(branch.id),
                    "branch_slug": branch.slug,
                    "actions": row_actions,
                }}
            )

    reference_by_client = select_reference_rows(report_rows)

    for row in report_rows:
        client_key = str(row.get("client_id") or "")
        branch_key = str(row.get("branch_id") or "")
        decision = reference_by_client.get(client_key) or {{"branch_ids": [], "reason": "no_active_branches"}}
        row["reference_branch"] = branch_key in set(decision.get("branch_ids") or [])
        row["reference_branch_reason"] = decision.get("reason") or "no_active_branches"

    active_rows = [row for row in report_rows if row.get("is_active")]
    active_reference_rows = [row for row in active_rows if row.get("reference_branch")]
    active_scope_rows = active_rows
    reference_mode = "all_active"
    if normalize_reference_branch and active_reference_rows:
        active_scope_rows = active_reference_rows
        reference_mode = "normalized"
    elif normalize_reference_branch:
        reference_mode = "fallback_all_active"

    active_not_ready = [row for row in active_scope_rows if not row.get("scorecard_ready")]
    active_sla_fail = [
        row
        for row in active_scope_rows
        if row.get("sla_status") == "fail"
    ]
    active_pipeline_blocked = [
        row
        for row in active_scope_rows
        if row.get("pipeline_blocked") is True
    ]
    active_delivery_critical = [
        row
        for row in active_scope_rows
        if any(
            isinstance(code, str)
            and code.startswith("delivery:")
            and code.endswith("_critical")
            for code in (row.get("readiness_blocker_codes") or [])
        )
    ]
    scoped_missing_counts = {{}}
    for row in active_scope_rows:
        for code in (row.get("scorecard_missing") or []):
            scoped_missing_counts[code] = int(scoped_missing_counts.get(code, 0)) + 1

    summary = {{
        "mode": mode,
        "active_only": active_only,
        "reference_mode": reference_mode,
        "total_branches": len(report_rows),
        "active_branches": len(active_scope_rows),
        "active_branches_raw": len(active_rows),
        "active_reference_branches": len(active_reference_rows),
        "active_not_ready": len(active_not_ready),
        "active_not_ready_raw": len([row for row in active_rows if not row.get("scorecard_ready")]),
        "active_sla_fail": len(active_sla_fail),
        "active_pipeline_blocked": len(active_pipeline_blocked),
        "active_delivery_critical": len(active_delivery_critical),
        "active_missing_codes": scoped_missing_counts,
        "active_missing_codes_raw": missing_counts,
        "changed_branches": len(actions),
        "unresolved_branches": len(unresolved),
        "apply_changes": apply_changes,
    }}

    if apply_changes and mode == "remediate":
        session.commit()
    else:
        session.rollback()

    print(
        json.dumps(
            {{
                "summary": summary,
                "rows": report_rows,
                "active_not_ready_rows": active_not_ready,
                "active_sla_fail_rows": active_sla_fail,
                "active_pipeline_blocked_rows": active_pipeline_blocked,
                "active_delivery_critical_rows": active_delivery_critical,
                "active_rows_raw": active_rows,
                "active_reference_rows": active_reference_rows,
                "reference_by_client": reference_by_client,
                "actions": actions,
                "unresolved": unresolved,
            }},
            ensure_ascii=False,
        )
    )
finally:
    session.close()
PY"""
    result = run_docker_exec(container_name, script)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise SystemExit(
            f"onboarding-fleet: container command failed ({stderr or 'unknown error'})"
        )
    return _load_json_output(result.stdout, command_name="onboarding-fleet")


def _parse_onboarding_fleet_check_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py onboarding-fleet-check",
        description="Check onboarding readiness for branches and fail on active missing gates.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive branches in report (default: active only).",
    )
    parser.add_argument(
        "--fail-on-active-missing",
        action="store_true",
        help="Exit non-zero when at least one active branch is not scorecard-ready.",
    )
    parser.add_argument(
        "--all-active-branches",
        action="store_true",
        help="Disable reference-branch normalization and evaluate all active branches.",
    )
    parser.add_argument("--container-name", default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _run_onboarding_fleet_check(args):
    container_name = _resolve_diagnose_container(args.container_name)
    payload = {
        "mode": "check",
        "active_only": not args.include_inactive,
        "apply_changes": False,
        "normalize_reference_branch": not bool(args.all_active_branches),
    }
    result = _run_onboarding_fleet_container(payload, container_name=container_name)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        summary = result.get("summary") or {}
        print(
            json.dumps(
                {
                    "active_not_ready": summary.get("active_not_ready"),
                    "active_missing_codes": summary.get("active_missing_codes"),
                    "active_branches": summary.get("active_branches"),
                },
                ensure_ascii=False,
            )
        )
        rows = result.get("active_not_ready_rows") or []
        for row in rows:
            print(
                f"- {row.get('client_slug')}/{row.get('branch_slug')} "
                f"missing={','.join(row.get('scorecard_missing') or [])}"
            )
    active_not_ready = int((result.get("summary") or {}).get("active_not_ready") or 0)
    if args.fail_on_active_missing and active_not_ready > 0:
        raise SystemExit(
            f"onboarding-fleet-check: active branches not ready ({active_not_ready})"
        )


def _parse_onboarding_fleet_remediate_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py onboarding-fleet-remediate",
        description="Backfill onboarding domain/contract/payment for branches with controlled flags.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive branches in remediation/report.",
    )
    parser.add_argument(
        "--branch-domain",
        action="append",
        default=[],
        help="Explicit mapping: branch_id=domain_slug or branch_slug=domain_slug (repeatable).",
    )
    parser.add_argument(
        "--default-domain-slug",
        default=None,
        help="Fallback domain_slug used only when branch has no contract/capability domain and no explicit mapping.",
    )
    parser.add_argument(
        "--confirm-payment",
        action="store_true",
        help="Set onboarding contract payment_status=confirmed for touched branches.",
    )
    parser.add_argument(
        "--no-ensure-contract",
        action="store_true",
        help="Do not create missing onboarding contracts during remediation.",
    )
    parser.add_argument(
        "--sync-reference-pack-integrity",
        action="store_true",
        help="Create/update reference packs to integrity v2 for resolved domains.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes (default is dry-run).",
    )
    parser.add_argument("--container-name", default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _run_onboarding_fleet_remediate(args):
    container_name = _resolve_diagnose_container(args.container_name)
    branch_domain_map = _parse_branch_domain_pairs(args.branch_domain)
    payload = {
        "mode": "remediate",
        "active_only": not args.include_inactive,
        "apply_changes": bool(args.apply),
        "default_domain_slug": args.default_domain_slug,
        "branch_domain_map": branch_domain_map,
        "confirm_payment": bool(args.confirm_payment),
        "ensure_contract": not bool(args.no_ensure_contract),
        "sync_reference_pack": bool(args.sync_reference_pack_integrity),
        "normalize_reference_branch": False,
    }
    result = _run_onboarding_fleet_container(payload, container_name=container_name)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return
    summary = result.get("summary") or {}
    print(
        json.dumps(
            {
                "apply_changes": summary.get("apply_changes"),
                "changed_branches": summary.get("changed_branches"),
                "unresolved_branches": summary.get("unresolved_branches"),
                "active_not_ready": summary.get("active_not_ready"),
                "active_missing_codes": summary.get("active_missing_codes"),
            },
            ensure_ascii=False,
        )
    )
    for row in (result.get("actions") or []):
        print(
            f"- changed {row.get('branch_slug')} ({row.get('branch_id')}): "
            f"{', '.join(row.get('actions') or [])}"
        )
    for row in (result.get("unresolved") or []):
        print(
            f"- unresolved {row.get('branch_slug')} ({row.get('branch_id')}): {row.get('reason')}"
        )


def _parse_onboarding_hard_gate_rollout_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py onboarding-hard-gate-rollout",
        description="Evaluate onboarding hard-gate rollout modes (shadow/canary/enforced).",
    )
    parser.add_argument(
        "--mode",
        choices=["actual", "shadow", "canary", "enforced"],
        default="actual",
        help="Rollout mode projection.",
    )
    parser.add_argument(
        "--canary-branch-id",
        action="append",
        default=[],
        help="Branch UUID(s) for canary mode (repeatable, comma-separated allowed).",
    )
    parser.add_argument(
        "--hard-gate-codes",
        default=None,
        help="CSV hard-gate blocker codes; default is readiness hard-gate baseline set.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive branches in report (default: active only).",
    )
    parser.add_argument(
        "--all-active-branches",
        action="store_true",
        help="Disable reference-branch normalization and evaluate all active branches.",
    )
    parser.add_argument(
        "--fail-on-blocked-active",
        action="store_true",
        help="Exit non-zero when active branches are blocked for selected rollout mode.",
    )
    parser.add_argument("--container-name", default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _run_onboarding_hard_gate_rollout(args):
    container_name = _resolve_diagnose_container(args.container_name)
    hard_gate_codes = (
        set(_parse_csv_values(args.hard_gate_codes))
        if args.hard_gate_codes
        else set(_ONBOARDING_HARD_GATE_DEFAULT_CODES)
    )
    if not hard_gate_codes:
        hard_gate_codes = set(_ONBOARDING_HARD_GATE_DEFAULT_CODES)
    payload = {
        "mode": "check",
        "active_only": not args.include_inactive,
        "apply_changes": False,
        "hard_gate_codes": sorted(hard_gate_codes),
        "normalize_reference_branch": not bool(args.all_active_branches),
    }
    result = _run_onboarding_fleet_container(payload, container_name=container_name)

    actual_global_enabled = _parse_env_bool_token(
        os.environ.get("ONBOARDING_READINESS_HARD_GATE_ENABLED", "0"),
        default=False,
    )
    actual_canary_ids = _parse_branch_ids(
        [os.environ.get("ONBOARDING_READINESS_HARD_GATE_CANARY_BRANCH_IDS", "")]
    )
    canary_branch_ids = _parse_branch_ids(args.canary_branch_id)

    projected_rows = [
        _project_hard_gate_row(
            row,
            mode=args.mode,
            actual_global_enabled=actual_global_enabled,
            actual_canary_ids=actual_canary_ids,
            canary_branch_ids=canary_branch_ids,
        )
        for row in (result.get("rows") or [])
    ]

    active_rows_raw = [row for row in projected_rows if row.get("is_active")]
    active_reference_rows = [row for row in active_rows_raw if row.get("reference_branch")]
    active_rows = active_rows_raw
    if not args.all_active_branches and active_reference_rows:
        active_rows = active_reference_rows
    active_blocked_rows = [row for row in active_rows if row.get("projected_status") != "pass"]
    summary = {
        "mode": args.mode,
        "hard_gate_codes": sorted(hard_gate_codes),
        "reference_mode": "all_active"
        if args.all_active_branches
        else ("normalized" if active_reference_rows else "fallback_all_active"),
        "actual_global_enabled": bool(actual_global_enabled),
        "actual_canary_branch_ids": sorted(actual_canary_ids),
        "input_canary_branch_ids": sorted(canary_branch_ids),
        "total_branches": len(projected_rows),
        "active_branches": len(active_rows),
        "active_branches_raw": len(active_rows_raw),
        "active_reference_branches": len(active_reference_rows),
        "active_blocked": len(active_blocked_rows),
        "active_blocked_scorecard": sum(
            1 for row in active_blocked_rows if row.get("projected_status") == "blocked_scorecard"
        ),
        "active_blocked_hard_gate": sum(
            1 for row in active_blocked_rows if row.get("projected_status") == "blocked_hard_gate"
        ),
    }

    payload_out = {
        "summary": summary,
        "rows": projected_rows,
        "active_blocked_rows": active_blocked_rows,
        "fleet_summary": result.get("summary") or {},
    }
    if args.json:
        print(json.dumps(payload_out, ensure_ascii=False))
    else:
        print(json.dumps(summary, ensure_ascii=False))
        for row in active_blocked_rows:
            print(
                f"- {row.get('client_slug')}/{row.get('branch_slug')} "
                f"status={row.get('projected_status')} "
                f"enforced={row.get('hard_gate_enforced')} "
                f"blockers={','.join(row.get('projected_blockers') or [])}"
            )
    if args.fail_on_blocked_active and active_blocked_rows:
        raise SystemExit(
            f"onboarding-hard-gate-rollout: active branches blocked ({len(active_blocked_rows)})"
        )


def _parse_onboarding_delivery_stabilize_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py onboarding-delivery-stabilize",
        description="Summarize delivery critical blockers and remediation actions for onboarding rollout.",
    )
    parser.add_argument(
        "--window-hours",
        type=int,
        default=24,
        help="Delivery failure aggregation window in hours (default: 24).",
    )
    parser.add_argument(
        "--hard-gate-codes",
        default=None,
        help="CSV hard-gate blocker codes; default is readiness hard-gate baseline set.",
    )
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive branches in report (default: active only).",
    )
    parser.add_argument(
        "--all-active-branches",
        action="store_true",
        help="Disable reference-branch normalization and evaluate all active branches.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero when active branches have delivery critical blockers.",
    )
    parser.add_argument("--container-name", default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _run_onboarding_delivery_stabilize(args):
    container_name = _resolve_diagnose_container(args.container_name)
    hard_gate_codes = (
        set(_parse_csv_values(args.hard_gate_codes))
        if args.hard_gate_codes
        else set(_ONBOARDING_HARD_GATE_DEFAULT_CODES)
    )
    if not hard_gate_codes:
        hard_gate_codes = set(_ONBOARDING_HARD_GATE_DEFAULT_CODES)
    payload = {
        "mode": "check",
        "active_only": not args.include_inactive,
        "apply_changes": False,
        "hard_gate_codes": sorted(hard_gate_codes),
        "delivery_window_hours": max(1, int(args.window_hours or 24)),
        "normalize_reference_branch": not bool(args.all_active_branches),
    }
    result = _run_onboarding_fleet_container(payload, container_name=container_name)
    rows = [dict(row) for row in (result.get("rows") or [])]
    for row in rows:
        row["delivery_blockers"] = _delivery_blockers_from_row(row)
        row["delivery_critical_blockers"] = _delivery_critical_blockers_from_row(row)
        row["delivery_remediation_actions"] = _delivery_remediation_actions_for_row(row)

    active_rows_raw = [row for row in rows if row.get("is_active")]
    active_reference_rows = [row for row in active_rows_raw if row.get("reference_branch")]
    active_rows = active_rows_raw
    if not args.all_active_branches and active_reference_rows:
        active_rows = active_reference_rows
    active_critical_rows = [row for row in active_rows if row.get("delivery_critical_blockers")]
    active_with_failures = [
        row
        for row in active_rows
        if int((row.get("delivery_failure_profile") or {}).get("total_failed_24h") or 0) > 0
    ]
    summary = {
        "window_hours": max(1, int(args.window_hours or 24)),
        "hard_gate_codes": sorted(hard_gate_codes),
        "reference_mode": "all_active"
        if args.all_active_branches
        else ("normalized" if active_reference_rows else "fallback_all_active"),
        "total_branches": len(rows),
        "active_branches": len(active_rows),
        "active_branches_raw": len(active_rows_raw),
        "active_reference_branches": len(active_reference_rows),
        "active_delivery_critical": len(active_critical_rows),
        "active_with_failed_24h": len(active_with_failures),
        "active_reason_totals": _delivery_reason_totals(active_rows),
    }
    payload_out = {
        "summary": summary,
        "rows": rows,
        "active_delivery_critical_rows": active_critical_rows,
        "active_with_failed_24h_rows": active_with_failures,
        "fleet_summary": result.get("summary") or {},
    }
    if args.json:
        print(json.dumps(payload_out, ensure_ascii=False))
    else:
        print(json.dumps(summary, ensure_ascii=False))
        for row in active_critical_rows:
            print(
                f"- {row.get('client_slug')}/{row.get('branch_slug')} "
                f"critical={','.join(row.get('delivery_critical_blockers') or [])} "
                f"reason={row.get('delivery_primary_reason_code')} "
                f"actions={','.join(row.get('delivery_remediation_actions') or [])}"
            )
    if args.fail_on_critical and active_critical_rows:
        raise SystemExit(
            f"onboarding-delivery-stabilize: active branches with delivery critical blockers ({len(active_critical_rows)})"
        )


def _onboarding_quality_imports():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    api_root = os.path.join(repo_root, "truffles-api")
    if api_root not in sys.path:
        sys.path.insert(0, api_root)
    from app.services.knowledge_validation import get_missing_required_fields, get_required_fields_for_domain
    from app.services.onboarding_intake_service import (
        build_intake_pack_quality_summary,
        build_intake_payload,
        evaluate_intake_payload,
    )
    from app.services.reference_pack_integrity import (
        REFERENCE_PACK_SCHEMA_VERSION,
        build_reference_pack_metadata,
        build_required_fields_checksum,
        evaluate_reference_pack_integrity,
    )

    return {
        "get_missing_required_fields": get_missing_required_fields,
        "get_required_fields_for_domain": get_required_fields_for_domain,
        "evaluate_intake_payload": evaluate_intake_payload,
        "build_intake_payload": build_intake_payload,
        "build_intake_pack_quality_summary": build_intake_pack_quality_summary,
        "REFERENCE_PACK_SCHEMA_VERSION": REFERENCE_PACK_SCHEMA_VERSION,
        "build_reference_pack_metadata": build_reference_pack_metadata,
        "build_required_fields_checksum": build_required_fields_checksum,
        "evaluate_reference_pack_integrity": evaluate_reference_pack_integrity,
    }


def _set_nested_path(payload, path, value):
    current = payload
    parts = path.split(".")
    for idx, key in enumerate(parts):
        last = idx == len(parts) - 1
        if last:
            current[key] = value
            return
        next_value = current.get(key)
        if not isinstance(next_value, dict):
            next_value = {}
            current[key] = next_value
        current = next_value


def _domain_smoke_value_for_field(path):
    mapping = {
        "client_pack.business.name": "Smoke Biz",
        "client_pack.location.city": "Almaty",
        "client_pack.location.address.full": "Abylai Khan 1",
        "client_pack.operations.hours.days": ["mon", "tue", "wed", "thu", "fri"],
        "client_pack.operations.hours.open": "10:00",
        "client_pack.operations.hours.close": "20:00",
        "client_pack.catalog.summary": "Basic services",
        "client_pack.communication.languages": ["ru", "kk"],
        "client_pack.services_catalog.services": [
            {"name": "base_service", "price": "10000", "duration_minutes": 60}
        ],
        "client_pack.guest_policy": "ask_manager",
        "client_pack.safety.medical_note": "consult specialist",
        "client_pack.pricing.price_from_reason": "depends_on_scope",
        "client_pack.quality.expectations_photo": "reference_required",
        "client_pack.price_list": [{"service": "base_service", "price": "10000"}],
        "client_pack.service_duration_estimates": [
            {"service": "base_service", "duration_minutes": 60}
        ],
        "client_pack.booking.collect_fields": ["service", "time", "name", "phone"],
        "client_pack.booking.bot_can_confirm": True,
        "client_pack.policy.hard_law": "no_medical_claims",
        "client_pack.policy.payment_info": "cash_or_card",
        "client_pack.policy.reschedule": "2h_notice",
        "client_pack.policy.cancel": "free_before_2h",
        "client_pack.policy.medical": "no_diagnosis",
        "client_pack.policy.legal": "consumer_law",
        "client_pack.policy.complaint": "manager_review",
        "client_pack.policy.discounts": "published_only",
        "client_pack.policy.guard_topics.refund": ["refund", "возврат"],
    }
    return mapping.get(path, "smoke_value")


def _build_domain_smoke_payload(required_fields):
    payload = {}
    for path in required_fields:
        _set_nested_path(payload, path, _domain_smoke_value_for_field(path))
    return payload


def _onboarding_quality_evaluate_domain(domain_slug, *, imports):
    required_fields = imports["get_required_fields_for_domain"](domain_slug=domain_slug)
    payload = _build_domain_smoke_payload(required_fields)
    missing = imports["get_missing_required_fields"](payload, domain_slug=domain_slug)
    intake_missing, intake_questions = imports["evaluate_intake_payload"](
        payload,
        domain_slug=domain_slug,
    )
    metadata = imports["build_reference_pack_metadata"](domain_slug=domain_slug)
    integrity_missing = imports["evaluate_reference_pack_integrity"](
        domain_slug=domain_slug,
        schema_version=imports["REFERENCE_PACK_SCHEMA_VERSION"],
        metadata=metadata,
    )
    checksum = imports["build_required_fields_checksum"](required_fields)
    status = "pass"
    if missing or intake_missing or integrity_missing:
        status = "fail"
    return {
        "domain_slug": domain_slug,
        "status": status,
        "required_fields_count": len(required_fields),
        "required_fields_checksum": checksum,
        "missing_required_fields": missing,
        "intake_missing_fields": intake_missing,
        "intake_missing_questions": intake_questions,
        "integrity_missing": integrity_missing,
    }


def _onboarding_quality_compare_baseline(summary, baseline_summary):
    regressions = []
    current_by_domain = {
        row.get("domain_slug"): row
        for row in (summary.get("domains") or [])
        if row.get("domain_slug")
    }
    baseline_by_domain = {
        row.get("domain_slug"): row
        for row in (baseline_summary.get("domains") or [])
        if row.get("domain_slug")
    }
    for domain_slug, current in current_by_domain.items():
        baseline = baseline_by_domain.get(domain_slug)
        if not baseline:
            continue
        if baseline.get("status") == "pass" and current.get("status") != "pass":
            regressions.append(f"{domain_slug}:status")
        if baseline.get("required_fields_checksum") != current.get("required_fields_checksum"):
            regressions.append(f"{domain_slug}:required_fields_checksum")
        baseline_missing = len(baseline.get("missing_required_fields") or [])
        current_missing = len(current.get("missing_required_fields") or [])
        if current_missing > baseline_missing:
            regressions.append(f"{domain_slug}:missing_required_fields")
    return regressions


def _parse_onboarding_quality_smoke_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py onboarding-quality-smoke",
        description="Run deterministic onboarding quality smoke for multiple domains.",
    )
    parser.add_argument(
        "--domains",
        default="beauty,clinic,legal,ecom",
        help="Comma-separated domain slugs.",
    )
    parser.add_argument(
        "--baseline-summary",
        default=None,
        help="Path to baseline summary json for regression comparison.",
    )
    parser.add_argument(
        "--save-summary",
        default=None,
        help="Write current summary json to this path.",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit non-zero when regression is detected vs baseline-summary.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _run_onboarding_quality_smoke(args):
    domains = _parse_csv_values(args.domains)
    if not domains:
        raise SystemExit("onboarding-quality-smoke: no domains provided")
    imports = _onboarding_quality_imports()
    rows = []
    for domain_slug in domains:
        rows.append(_onboarding_quality_evaluate_domain(domain_slug, imports=imports))
    failed_domains = [
        row.get("domain_slug")
        for row in rows
        if row.get("status") != "pass"
    ]
    summary = {
        "domains": rows,
        "checked_domains": len(rows),
        "failed_domains": failed_domains,
        "status": "pass" if not failed_domains else "fail",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    regressions = []
    if args.baseline_summary:
        if not os.path.isfile(args.baseline_summary):
            raise SystemExit(
                f"onboarding-quality-smoke: baseline-summary not found ({args.baseline_summary})"
            )
        try:
            with open(args.baseline_summary, "r", encoding="utf-8") as handle:
                baseline_summary = json.load(handle)
        except Exception as exc:
            raise SystemExit(
                f"onboarding-quality-smoke: baseline-summary parse failed ({exc})"
            ) from exc
        regressions = _onboarding_quality_compare_baseline(summary, baseline_summary)
        summary["regressions"] = regressions

    if args.save_summary:
        output_dir = os.path.dirname(args.save_summary)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(args.save_summary, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(
            json.dumps(
                {
                    "status": summary["status"],
                    "checked_domains": summary["checked_domains"],
                    "failed_domains": failed_domains,
                    "regressions": regressions,
                },
                ensure_ascii=False,
            )
        )
        for row in rows:
            print(
                f"- {row.get('domain_slug')}: status={row.get('status')} "
                f"required_fields={row.get('required_fields_count')} "
                f"missing={len(row.get('missing_required_fields') or [])} "
                f"integrity_missing={len(row.get('integrity_missing') or [])}"
            )

    if failed_domains:
        raise SystemExit(
            f"onboarding-quality-smoke: failed domains ({', '.join(failed_domains)})"
        )
    if args.fail_on_regression and regressions:
        raise SystemExit(
            f"onboarding-quality-smoke: regressions ({', '.join(regressions)})"
        )


def _parse_onboarding_pack_quality_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py onboarding-pack-quality",
        description=(
            "Run document-driven onboarding pack compile + quality matrix "
            "with optional baseline regression comparison."
        ),
    )
    parser.add_argument("--domain-slug", default="beauty", help="Domain slug for minimum-data contract.")
    parser.add_argument(
        "--require-booking",
        default="auto",
        choices=["auto", "true", "false"],
        help="Booking requirement mode: auto by domain, true, or false.",
    )
    parser.add_argument(
        "--client-data-text",
        default=None,
        help="Inline client_data_text payload.",
    )
    parser.add_argument(
        "--client-data-text-file",
        default=None,
        help="Path to client data markdown/text document.",
    )
    parser.add_argument(
        "--client-data-json-file",
        default=None,
        help="Path to client_data_json file.",
    )
    parser.add_argument(
        "--baseline-summary",
        default=None,
        help="Path to previous onboarding-pack-quality summary.json for regression compare.",
    )
    parser.add_argument(
        "--save-summary",
        default=None,
        help="Write current summary json to this path.",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit non-zero on baseline regressions.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _onboarding_pack_quality_resolve_require_booking(value):
    token = str(value or "auto").strip().lower()
    if token == "true":
        return True
    if token == "false":
        return False
    return None


def _onboarding_pack_quality_load_json(path):
    if not path:
        return None
    if not os.path.isfile(path):
        raise SystemExit(f"onboarding-pack-quality: json file not found ({path})")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception as exc:
        raise SystemExit(f"onboarding-pack-quality: json parse failed ({exc})") from exc
    if payload is not None and not isinstance(payload, dict):
        raise SystemExit("onboarding-pack-quality: client_data_json must be an object")
    return payload


def _onboarding_pack_quality_load_text(file_path, inline_text):
    parts = []
    if file_path:
        if not os.path.isfile(file_path):
            raise SystemExit(f"onboarding-pack-quality: text file not found ({file_path})")
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                parts.append(handle.read())
        except Exception as exc:
            raise SystemExit(f"onboarding-pack-quality: text file read failed ({exc})") from exc
    if inline_text:
        parts.append(str(inline_text))
    if not parts:
        return None
    return "\n\n".join(parts).strip() or None


def _onboarding_pack_quality_compile_to_dict(compile_summary):
    return {
        "status": compile_summary.status,
        "infra_valid": bool(compile_summary.infra_valid),
        "schema_version": compile_summary.schema_version,
        "hash": compile_summary.hash,
        "pack_index_hash": compile_summary.pack_index_hash,
        "signal_graph_present": bool(compile_summary.signal_graph_present),
        "policy_bundle_present": bool(compile_summary.policy_bundle_present),
        "errors": list(compile_summary.errors or []),
    }


def _onboarding_pack_quality_matrix_to_dict(matrix):
    return {
        "status": matrix.status,
        "infra_valid": bool(matrix.infra_valid),
        "semantic_valid": bool(matrix.semantic_valid),
        "required_fields_count": int(matrix.required_fields_count),
        "missing_fields_count": int(matrix.missing_fields_count),
        "critical_missing_fields_count": int(matrix.critical_missing_fields_count),
        "integrity_missing_count": int(matrix.integrity_missing_count),
        "missing_fields": list(matrix.missing_fields or []),
        "critical_missing_fields": list(matrix.critical_missing_fields or []),
        "integrity_missing": list(matrix.integrity_missing or []),
        "dimensions": [
            {
                "id": item.id,
                "status": item.status,
                "required": bool(item.required),
                "details": list(item.details or []),
            }
            for item in (matrix.dimensions or [])
        ],
        "regressions": list(matrix.regressions or []),
        "comparison_blocked": bool(matrix.comparison_blocked),
        "comparison_block_reason": matrix.comparison_block_reason,
    }


def _run_onboarding_pack_quality(args):
    imports = _onboarding_quality_imports()
    require_booking = _onboarding_pack_quality_resolve_require_booking(args.require_booking)
    client_data_json = _onboarding_pack_quality_load_json(args.client_data_json_file)
    client_data_text = _onboarding_pack_quality_load_text(
        args.client_data_text_file,
        args.client_data_text,
    )
    baseline_summary = _onboarding_pack_quality_load_json(args.baseline_summary)

    payload = imports["build_intake_payload"](
        client_data_json=client_data_json,
        client_data_text=client_data_text,
    )
    missing_fields, missing_questions = imports["evaluate_intake_payload"](
        payload,
        domain_slug=args.domain_slug,
        require_booking=require_booking,
    )
    quality_summary = imports["build_intake_pack_quality_summary"](
        payload,
        domain_slug=args.domain_slug,
        require_booking=require_booking,
        baseline_summary=baseline_summary,
    )
    compile_summary = _onboarding_pack_quality_compile_to_dict(quality_summary.compile)
    quality_matrix = _onboarding_pack_quality_matrix_to_dict(quality_summary.quality_matrix)

    summary = {
        "status": quality_matrix["status"],
        "domain_slug": args.domain_slug,
        "require_booking": require_booking,
        "input": {
            "text_file": args.client_data_text_file,
            "json_file": args.client_data_json_file,
            "text_present": bool(client_data_text),
            "json_present": isinstance(client_data_json, dict),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "missing_questions": missing_questions,
        "compile": compile_summary,
        "quality_matrix": quality_matrix,
    }

    if args.save_summary:
        output_dir = os.path.dirname(args.save_summary)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(args.save_summary, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(
            json.dumps(
                {
                    "status": summary["status"],
                    "domain_slug": summary["domain_slug"],
                    "infra_valid": quality_matrix["infra_valid"],
                    "semantic_valid": quality_matrix["semantic_valid"],
                    "missing_fields_count": quality_matrix["missing_fields_count"],
                    "critical_missing_fields_count": quality_matrix["critical_missing_fields_count"],
                    "compile_status": compile_summary["status"],
                    "regressions": quality_matrix["regressions"],
                    "comparison_blocked": quality_matrix["comparison_blocked"],
                },
                ensure_ascii=False,
            )
        )

    if quality_matrix["status"] != "pass":
        raise SystemExit("onboarding-pack-quality: status=fail")

    if args.fail_on_regression and quality_matrix["comparison_blocked"]:
        raise SystemExit(
            "onboarding-pack-quality: regression compare blocked "
            f"({quality_matrix.get('comparison_block_reason') or 'unknown'})"
        )
    if args.fail_on_regression and quality_matrix["regressions"]:
        raise SystemExit(
            "onboarding-pack-quality: regressions "
            f"({', '.join(quality_matrix['regressions'])})"
        )


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

    if suite_name == "ca12-booking-full" and isinstance(results, list):
        booking_time = summary.get("booking_time")
        booking_name = summary.get("booking_name")
        if booking_time:
            lines.append(f"- booking_time: `{_format_cell(booking_time)}`")
        if booking_name:
            lines.append(f"- booking_name: `{_format_cell(booking_name)}`")
        lines.append(
            f"- booking_confirm_prompted: `{_format_cell(summary.get('booking_confirm_prompted'))}`"
        )
        lines.append(
            f"- booking_confirmed: `{_format_cell(summary.get('booking_confirmed'))}`"
        )
        if summary.get("booking_confirm_decision") is not None:
            lines.append(
                f"- booking_confirm_decision: `{_format_cell(summary.get('booking_confirm_decision'))}`"
            )
        if summary.get("appointment_id"):
            lines.append(f"- appointment_id: `{_format_cell(summary.get('appointment_id'))}`")
        if summary.get("appointment_status"):
            lines.append(
                f"- appointment_status: `{_format_cell(summary.get('appointment_status'))}`"
            )
        if summary.get("appointment_audit_action"):
            lines.append(
                f"- appointment_audit_action: `{_format_cell(summary.get('appointment_audit_action'))}`"
            )
        if summary.get("outbox_status"):
            lines.append(f"- outbox_status: `{_format_cell(summary.get('outbox_status'))}`")
        if summary.get("conversation_state_before") or summary.get("conversation_state_after"):
            lines.append(
                "- conversation_state: "
                f"`{_format_cell(summary.get('conversation_state_before'))}` → "
                f"`{_format_cell(summary.get('conversation_state_after'))}`"
            )
        if summary.get("handover_status_before") or summary.get("handover_status_after"):
            lines.append(
                "- handover_status: "
                f"`{_format_cell(summary.get('handover_status_before'))}` → "
                f"`{_format_cell(summary.get('handover_status_after'))}`"
            )
        lines.append("")
        columns = [
            ("step", "step"),
            ("phase", "phase"),
            ("message_id", "message_id"),
            ("expected_reply_type", "expected_reply_type"),
            ("action", "action"),
            ("slot_confirmation_required", "slot_confirmation_required"),
            ("slot_confirmation_decision", "slot_confirmation_decision"),
            ("booking_service", "booking_service"),
            ("trace_booking_commit", "trace_booking_commit"),
            ("llm_used", "llm_used"),
        ]
        lines.extend(_render_table(columns, results))
        manager_actions = summary.get("manager_actions")
        if isinstance(manager_actions, list) and manager_actions:
            lines.append("")
            lines.append("### Manager Actions")
            manager_columns = [
                ("action", "action"),
                ("status", "status"),
                ("error", "error"),
                ("expected_state", "expected_state"),
                ("actual_state", "actual_state"),
                ("expected_handover_status", "expected_handover_status"),
                ("actual_handover_status", "actual_handover_status"),
            ]
            lines.extend(_render_table(manager_columns, manager_actions))
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


def _parse_integrity_gate_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py integrity-gate",
        description="Run deterministic data-integrity checks for runtime core tables.",
    )
    parser.add_argument(
        "--client-slug",
        default="demo_salon",
        help="Client slug scope for checks (ignored with --all-clients).",
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help="Client UUID scope for checks (overrides --client-slug).",
    )
    parser.add_argument(
        "--all-clients",
        action="store_true",
        help="Run checks across all clients.",
    )
    parser.add_argument("--container-name", default="truffles_postgres_1", help="Postgres container name.")
    parser.add_argument("--database", default="chatbot", help="Postgres database name.")
    parser.add_argument("--db-user", default=None, help="Postgres user; defaults to DB_USER or POSTGRES_USER.")
    parser.add_argument(
        "--stuck-processing-minutes",
        type=int,
        default=30,
        help="Age threshold for PROCESSING outbox messages.",
    )
    parser.add_argument("--sample-limit", type=int, default=10, help="Max rows per check in sample output.")
    parser.add_argument("--timeout", type=float, default=45.0, help="Command timeout in seconds.")
    parser.add_argument("--output", default=None, help="Write JSON result to path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit 2 when critical checks return violations.",
    )
    return parser.parse_args(argv)


def _integrity_sql_escape(value):
    return str(value).replace("'", "''")


def _integrity_extract_last_line(stdout):
    lines = [line.strip() for line in str(stdout or "").splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[-1]


def _integrity_resolve_db_user(container_name, explicit_user, timeout):
    if explicit_user:
        return explicit_user
    env_user = os.environ.get("DB_USER")
    if env_user:
        return env_user
    result = run_command(
        [
            "docker",
            "exec",
            "-i",
            container_name,
            "/bin/sh",
            "-lc",
            "printf '%s' \"${POSTGRES_USER:-postgres}\"",
        ],
        timeout=timeout,
    )
    if result.returncode == 0:
        detected = _integrity_extract_last_line(result.stdout)
        if detected:
            return detected
    return "postgres"


def _integrity_run_psql(container_name, db_name, db_user, sql, *, timeout):
    command = [
        "docker",
        "exec",
        "-i",
        container_name,
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-Atc",
        sql,
    ]
    result = run_command(command, timeout=timeout)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(stderr or f"psql failed with exit={result.returncode}")
    return _integrity_extract_last_line(result.stdout)


def _integrity_resolve_client_scope(args, *, container_name, db_name, db_user):
    if args.all_clients:
        return {
            "client_id": None,
            "client_slug": None,
            "scope": "all_clients",
        }

    if args.client_id:
        return {
            "client_id": args.client_id,
            "client_slug": args.client_slug,
            "scope": "single_client_id",
        }

    if not args.client_slug:
        raise SystemExit("integrity-gate: provide --client-slug/--client-id or use --all-clients")

    escaped_slug = _integrity_sql_escape(args.client_slug)
    sql = f"SELECT id::text FROM clients WHERE name = '{escaped_slug}' LIMIT 1;"
    client_id = _integrity_run_psql(
        container_name,
        db_name,
        db_user,
        sql,
        timeout=args.timeout,
    )
    if not client_id:
        raise SystemExit(f"integrity-gate: client not found for slug '{args.client_slug}'")
    return {
        "client_id": client_id,
        "client_slug": args.client_slug,
        "scope": "single_client_slug",
    }


def _integrity_client_filter(alias, column, client_id):
    if not client_id:
        return "TRUE"
    return f"{alias}.{column} = '{client_id}'::uuid"


def _integrity_membership_filter(client_id):
    if not client_id:
        return "TRUE"
    return (
        "("
        f"(m.scope = 'client' AND m.client_id = '{client_id}'::uuid)"
        " OR "
        f"(m.scope = 'branch' AND EXISTS ("
        "SELECT 1 FROM branches b "
        f"WHERE b.id = m.branch_id AND b.client_id = '{client_id}'::uuid"
        "))"
        " OR "
        f"(m.scope = 'company' AND EXISTS ("
        "SELECT 1 FROM clients c "
        f"WHERE c.id = '{client_id}'::uuid AND c.company_id = m.company_id"
        "))"
        ")"
    )


def _integrity_json_rows(container_name, db_name, db_user, sample_sql, *, timeout):
    wrapped = (
        "WITH rows AS ("
        f"{sample_sql}"
        ") SELECT COALESCE(json_agg(row_to_json(rows)), '[]'::json)::text FROM rows;"
    )
    raw = _integrity_run_psql(container_name, db_name, db_user, wrapped, timeout=timeout)
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid json payload from psql: {exc}") from exc
    if isinstance(payload, list):
        return payload
    return []


def _integrity_count(container_name, db_name, db_user, count_sql, *, timeout):
    raw = _integrity_run_psql(container_name, db_name, db_user, count_sql, timeout=timeout)
    try:
        return int(raw or "0")
    except ValueError as exc:
        raise RuntimeError(f"invalid count payload: {raw!r}") from exc


def _integrity_build_checks(client_id, args):
    sample_limit = max(int(args.sample_limit or 10), 1)
    stuck_minutes = max(int(args.stuck_processing_minutes or 30), 1)

    outbox_filter = _integrity_client_filter("o", "client_id", client_id)
    handover_filter = _integrity_client_filter("h", "client_id", client_id)
    conversation_filter = _integrity_client_filter("c", "client_id", client_id)
    appointment_pair_filter = _integrity_client_filter("a1", "client_id", client_id)
    appointment_filter = _integrity_client_filter("a", "client_id", client_id)
    visit_filter = _integrity_client_filter("v", "client_id", client_id)
    message_filter = _integrity_client_filter("m", "client_id", client_id)
    membership_filter = _integrity_membership_filter(client_id)

    active_appointment_statuses = (
        "'HOLD', 'PENDING_CONFIRMATION', 'CONFIRMED', 'RESCHEDULE_REQUESTED', 'CHECKED_IN'"
    )

    checks = [
        {
            "id": "OUTBOX_DUPLICATE_IDEMPOTENCY",
            "severity": "critical",
            "description": "Duplicate outbox rows by (client_id, inbound_message_id).",
            "count_sql": (
                "SELECT COUNT(*) FROM ("
                "SELECT o.client_id, o.inbound_message_id "
                "FROM outbox_messages o "
                f"WHERE {outbox_filter} "
                "GROUP BY o.client_id, o.inbound_message_id "
                "HAVING COUNT(*) > 1"
                ") dup;"
            ),
            "sample_sql": (
                "SELECT "
                "o.client_id::text AS client_id, "
                "o.inbound_message_id, "
                "COUNT(*)::int AS duplicate_count, "
                "MAX(o.updated_at) AS last_updated_at, "
                "(ARRAY_AGG(o.id::text ORDER BY o.created_at DESC))[1:5] AS sample_outbox_ids "
                "FROM outbox_messages o "
                f"WHERE {outbox_filter} "
                "GROUP BY o.client_id, o.inbound_message_id "
                "HAVING COUNT(*) > 1 "
                "ORDER BY duplicate_count DESC, last_updated_at DESC "
                f"LIMIT {sample_limit}"
            ),
        },
        {
            "id": "OUTBOX_STUCK_PROCESSING",
            "severity": "critical",
            "description": "Outbox rows stuck in PROCESSING older than threshold.",
            "count_sql": (
                "SELECT COUNT(*) FROM outbox_messages o "
                "WHERE o.status = 'PROCESSING' "
                f"AND {outbox_filter} "
                f"AND o.updated_at < NOW() - INTERVAL '{stuck_minutes} minutes';"
            ),
            "sample_sql": (
                "SELECT "
                "o.id::text AS outbox_id, "
                "o.client_id::text AS client_id, "
                "o.conversation_id::text AS conversation_id, "
                "o.inbound_message_id, "
                "o.attempts, "
                "o.last_error, "
                "o.updated_at, "
                "EXTRACT(EPOCH FROM (NOW() - o.updated_at))::int AS age_seconds "
                "FROM outbox_messages o "
                "WHERE o.status = 'PROCESSING' "
                f"AND {outbox_filter} "
                f"AND o.updated_at < NOW() - INTERVAL '{stuck_minutes} minutes' "
                "ORDER BY o.updated_at ASC "
                f"LIMIT {sample_limit}"
            ),
        },
        {
            "id": "HANDOVER_OPEN_UNIQUENESS",
            "severity": "critical",
            "description": "At most one open handover (pending/active) per conversation.",
            "count_sql": (
                "SELECT COUNT(*) FROM ("
                "SELECT h.conversation_id "
                "FROM handovers h "
                f"WHERE {handover_filter} "
                "AND h.status IN ('pending', 'active') "
                "GROUP BY h.conversation_id "
                "HAVING COUNT(*) > 1"
                ") conflicts;"
            ),
            "sample_sql": (
                "SELECT "
                "h.conversation_id::text AS conversation_id, "
                "COUNT(*)::int AS open_handover_count, "
                "(ARRAY_AGG(h.id::text ORDER BY h.created_at DESC))[1:5] AS open_handover_ids, "
                "MAX(h.created_at) AS latest_created_at "
                "FROM handovers h "
                f"WHERE {handover_filter} "
                "AND h.status IN ('pending', 'active') "
                "GROUP BY h.conversation_id "
                "HAVING COUNT(*) > 1 "
                "ORDER BY open_handover_count DESC, latest_created_at DESC "
                f"LIMIT {sample_limit}"
            ),
        },
        {
            "id": "CONVERSATION_STATE_CONSISTENCY",
            "severity": "critical",
            "description": "Conversation state must match open handover presence.",
            "count_sql": (
                "SELECT COUNT(*) FROM ("
                "SELECT c.id "
                "FROM conversations c "
                f"WHERE {conversation_filter} "
                "AND c.state IN ('pending', 'manager_active') "
                "AND NOT EXISTS ("
                "SELECT 1 FROM handovers h "
                "WHERE h.conversation_id = c.id AND h.status IN ('pending', 'active')"
                ") "
                "UNION ALL "
                "SELECT c.id "
                "FROM handovers h "
                "JOIN conversations c ON c.id = h.conversation_id "
                f"WHERE {handover_filter} "
                "AND h.status IN ('pending', 'active') "
                "AND COALESCE(c.state, '') NOT IN ('pending', 'manager_active')"
                ") anomalies;"
            ),
            "sample_sql": (
                "SELECT * FROM ("
                "SELECT "
                "'conversation_state_without_open_handover'::text AS issue_type, "
                "c.id::text AS conversation_id, "
                "c.state::text AS conversation_state, "
                "NULL::text AS handover_id, "
                "NULL::text AS handover_status, "
                "c.last_message_at AS observed_at "
                "FROM conversations c "
                f"WHERE {conversation_filter} "
                "AND c.state IN ('pending', 'manager_active') "
                "AND NOT EXISTS ("
                "SELECT 1 FROM handovers h "
                "WHERE h.conversation_id = c.id AND h.status IN ('pending', 'active')"
                ") "
                "UNION ALL "
                "SELECT "
                "'open_handover_with_inactive_conversation'::text AS issue_type, "
                "c.id::text AS conversation_id, "
                "c.state::text AS conversation_state, "
                "h.id::text AS handover_id, "
                "h.status::text AS handover_status, "
                "h.created_at AS observed_at "
                "FROM handovers h "
                "JOIN conversations c ON c.id = h.conversation_id "
                f"WHERE {handover_filter} "
                "AND h.status IN ('pending', 'active') "
                "AND COALESCE(c.state, '') NOT IN ('pending', 'manager_active')"
                ") anomalies "
                "ORDER BY observed_at DESC NULLS LAST "
                f"LIMIT {sample_limit}"
            ),
        },
        {
            "id": "APPOINTMENT_TIME_CONFLICT",
            "severity": "critical",
            "description": "Overlapping active appointments for one specialist/branch.",
            "count_sql": (
                "SELECT COUNT(*) FROM ("
                "SELECT a1.id, a2.id "
                "FROM appointments a1 "
                "JOIN appointments a2 ON a1.id < a2.id "
                "AND a1.branch_id = a2.branch_id "
                "AND a1.specialist_id = a2.specialist_id "
                "AND a1.specialist_id IS NOT NULL "
                f"AND a1.status IN ({active_appointment_statuses}) "
                f"AND a2.status IN ({active_appointment_statuses}) "
                "AND tstzrange(a1.start_at, a1.end_at, '[)') && tstzrange(a2.start_at, a2.end_at, '[)') "
                f"WHERE {appointment_pair_filter}"
                ") conflicts;"
            ),
            "sample_sql": (
                "SELECT "
                "a1.client_id::text AS client_id, "
                "a1.branch_id::text AS branch_id, "
                "a1.specialist_id::text AS specialist_id, "
                "a1.id::text AS appointment_a_id, "
                "a2.id::text AS appointment_b_id, "
                "a1.status AS status_a, "
                "a2.status AS status_b, "
                "a1.start_at AS start_a, "
                "a1.end_at AS end_a, "
                "a2.start_at AS start_b, "
                "a2.end_at AS end_b "
                "FROM appointments a1 "
                "JOIN appointments a2 ON a1.id < a2.id "
                "AND a1.branch_id = a2.branch_id "
                "AND a1.specialist_id = a2.specialist_id "
                "AND a1.specialist_id IS NOT NULL "
                f"AND a1.status IN ({active_appointment_statuses}) "
                f"AND a2.status IN ({active_appointment_statuses}) "
                "AND tstzrange(a1.start_at, a1.end_at, '[)') && tstzrange(a2.start_at, a2.end_at, '[)') "
                f"WHERE {appointment_pair_filter} "
                "ORDER BY a1.start_at DESC "
                f"LIMIT {sample_limit}"
            ),
        },
        {
            "id": "APPOINTMENT_VISIT_CONSISTENCY",
            "severity": "warning",
            "description": "Appointment and visit statuses should not contradict each other.",
            "count_sql": (
                "SELECT COUNT(*) FROM ("
                "SELECT a.id "
                "FROM appointments a "
                f"WHERE {appointment_filter} "
                "AND a.status IN ('CHECKED_IN', 'COMPLETED') "
                "AND NOT EXISTS (SELECT 1 FROM visits v WHERE v.appointment_id = a.id) "
                "UNION ALL "
                "SELECT v.id "
                "FROM visits v "
                "JOIN appointments a ON a.id = v.appointment_id "
                f"WHERE {visit_filter} "
                "AND LOWER(COALESCE(v.status, '')) IN ('arrived', 'checked_in', 'completed') "
                "AND COALESCE(a.status, '') NOT IN ('CHECKED_IN', 'COMPLETED')"
                ") anomalies;"
            ),
            "sample_sql": (
                "SELECT * FROM ("
                "SELECT "
                "'appointment_requires_visit_missing'::text AS issue_type, "
                "a.id::text AS appointment_id, "
                "a.status::text AS appointment_status, "
                "NULL::text AS visit_id, "
                "NULL::text AS visit_status, "
                "a.updated_at AS observed_at "
                "FROM appointments a "
                f"WHERE {appointment_filter} "
                "AND a.status IN ('CHECKED_IN', 'COMPLETED') "
                "AND NOT EXISTS (SELECT 1 FROM visits v WHERE v.appointment_id = a.id) "
                "UNION ALL "
                "SELECT "
                "'visit_without_completed_appointment'::text AS issue_type, "
                "a.id::text AS appointment_id, "
                "a.status::text AS appointment_status, "
                "v.id::text AS visit_id, "
                "v.status::text AS visit_status, "
                "v.created_at AS observed_at "
                "FROM visits v "
                "JOIN appointments a ON a.id = v.appointment_id "
                f"WHERE {visit_filter} "
                "AND LOWER(COALESCE(v.status, '')) IN ('arrived', 'checked_in', 'completed') "
                "AND COALESCE(a.status, '') NOT IN ('CHECKED_IN', 'COMPLETED')"
                ") anomalies "
                "ORDER BY observed_at DESC NULLS LAST "
                f"LIMIT {sample_limit}"
            ),
        },
        {
            "id": "MEMBERSHIP_DUPLICATE_ACTIVE",
            "severity": "critical",
            "description": "Duplicate active agent memberships for same scope/role target.",
            "count_sql": (
                "SELECT COUNT(*) FROM ("
                "SELECT "
                "m.agent_id, m.scope, m.role, m.company_id, m.client_id, m.branch_id "
                "FROM agent_memberships m "
                f"WHERE {membership_filter} "
                "AND m.is_active IS TRUE "
                "GROUP BY m.agent_id, m.scope, m.role, m.company_id, m.client_id, m.branch_id "
                "HAVING COUNT(*) > 1"
                ") dup;"
            ),
            "sample_sql": (
                "SELECT "
                "m.agent_id::text AS agent_id, "
                "m.scope, "
                "m.role, "
                "m.company_id::text AS company_id, "
                "m.client_id::text AS client_id, "
                "m.branch_id::text AS branch_id, "
                "COUNT(*)::int AS duplicate_count, "
                "(ARRAY_AGG(m.id::text ORDER BY m.created_at DESC))[1:5] AS sample_membership_ids "
                "FROM agent_memberships m "
                f"WHERE {membership_filter} "
                "AND m.is_active IS TRUE "
                "GROUP BY m.agent_id, m.scope, m.role, m.company_id, m.client_id, m.branch_id "
                "HAVING COUNT(*) > 1 "
                "ORDER BY duplicate_count DESC "
                f"LIMIT {sample_limit}"
            ),
        },
        {
            "id": "ORPHAN_REFERENCE_CHECK",
            "severity": "critical",
            "description": "Operational rows must not reference missing parent entities.",
            "count_sql": (
                "SELECT COUNT(*) FROM ("
                "SELECT h.id "
                "FROM handovers h "
                "LEFT JOIN conversations c ON c.id = h.conversation_id "
                f"WHERE {handover_filter} "
                "AND c.id IS NULL "
                "UNION ALL "
                "SELECT h.id "
                "FROM handovers h "
                "LEFT JOIN clients cl ON cl.id = h.client_id "
                f"WHERE {handover_filter} "
                "AND cl.id IS NULL "
                "UNION ALL "
                "SELECT o.id "
                "FROM outbox_messages o "
                "LEFT JOIN conversations c ON c.id = o.conversation_id "
                f"WHERE {outbox_filter} "
                "AND o.conversation_id IS NOT NULL "
                "AND c.id IS NULL "
                "UNION ALL "
                "SELECT o.id "
                "FROM outbox_messages o "
                "LEFT JOIN clients cl ON cl.id = o.client_id "
                f"WHERE {outbox_filter} "
                "AND cl.id IS NULL "
                "UNION ALL "
                "SELECT o.id "
                "FROM outbox_messages o "
                "LEFT JOIN branches b ON b.id = o.branch_id "
                f"WHERE {outbox_filter} "
                "AND o.branch_id IS NOT NULL "
                "AND b.id IS NULL "
                "UNION ALL "
                "SELECT a.id "
                "FROM appointments a "
                "LEFT JOIN conversations c ON c.id = a.conversation_id "
                f"WHERE {appointment_filter} "
                "AND a.conversation_id IS NOT NULL "
                "AND c.id IS NULL "
                "UNION ALL "
                "SELECT v.id "
                "FROM visits v "
                "LEFT JOIN appointments a ON a.id = v.appointment_id "
                f"WHERE {visit_filter} "
                "AND a.id IS NULL "
                "UNION ALL "
                "SELECT m.id "
                "FROM messages m "
                "LEFT JOIN conversations c ON c.id = m.conversation_id "
                f"WHERE {message_filter} "
                "AND c.id IS NULL"
                ") orphans;"
            ),
            "sample_sql": (
                "SELECT * FROM ("
                "SELECT "
                "'handover_missing_conversation'::text AS issue_type, "
                "h.id::text AS entity_id, "
                "h.client_id::text AS client_id, "
                "h.conversation_id::text AS reference_id, "
                "'conversations.id'::text AS reference_table, "
                "h.created_at AS observed_at "
                "FROM handovers h "
                "LEFT JOIN conversations c ON c.id = h.conversation_id "
                f"WHERE {handover_filter} "
                "AND c.id IS NULL "
                "UNION ALL "
                "SELECT "
                "'handover_missing_client'::text, "
                "h.id::text, "
                "h.client_id::text, "
                "h.client_id::text, "
                "'clients.id'::text, "
                "h.created_at "
                "FROM handovers h "
                "LEFT JOIN clients cl ON cl.id = h.client_id "
                f"WHERE {handover_filter} "
                "AND cl.id IS NULL "
                "UNION ALL "
                "SELECT "
                "'outbox_missing_conversation'::text, "
                "o.id::text, "
                "o.client_id::text, "
                "o.conversation_id::text, "
                "'conversations.id'::text, "
                "o.created_at "
                "FROM outbox_messages o "
                "LEFT JOIN conversations c ON c.id = o.conversation_id "
                f"WHERE {outbox_filter} "
                "AND o.conversation_id IS NOT NULL "
                "AND c.id IS NULL "
                "UNION ALL "
                "SELECT "
                "'outbox_missing_client'::text, "
                "o.id::text, "
                "o.client_id::text, "
                "o.client_id::text, "
                "'clients.id'::text, "
                "o.created_at "
                "FROM outbox_messages o "
                "LEFT JOIN clients cl ON cl.id = o.client_id "
                f"WHERE {outbox_filter} "
                "AND cl.id IS NULL "
                "UNION ALL "
                "SELECT "
                "'outbox_missing_branch'::text, "
                "o.id::text, "
                "o.client_id::text, "
                "o.branch_id::text, "
                "'branches.id'::text, "
                "o.created_at "
                "FROM outbox_messages o "
                "LEFT JOIN branches b ON b.id = o.branch_id "
                f"WHERE {outbox_filter} "
                "AND o.branch_id IS NOT NULL "
                "AND b.id IS NULL "
                "UNION ALL "
                "SELECT "
                "'appointment_missing_conversation'::text, "
                "a.id::text, "
                "a.client_id::text, "
                "a.conversation_id::text, "
                "'conversations.id'::text, "
                "a.updated_at "
                "FROM appointments a "
                "LEFT JOIN conversations c ON c.id = a.conversation_id "
                f"WHERE {appointment_filter} "
                "AND a.conversation_id IS NOT NULL "
                "AND c.id IS NULL "
                "UNION ALL "
                "SELECT "
                "'visit_missing_appointment'::text, "
                "v.id::text, "
                "v.client_id::text, "
                "v.appointment_id::text, "
                "'appointments.id'::text, "
                "v.created_at "
                "FROM visits v "
                "LEFT JOIN appointments a ON a.id = v.appointment_id "
                f"WHERE {visit_filter} "
                "AND a.id IS NULL "
                "UNION ALL "
                "SELECT "
                "'message_missing_conversation'::text, "
                "m.id::text, "
                "m.client_id::text, "
                "m.conversation_id::text, "
                "'conversations.id'::text, "
                "m.created_at "
                "FROM messages m "
                "LEFT JOIN conversations c ON c.id = m.conversation_id "
                f"WHERE {message_filter} "
                "AND c.id IS NULL "
                ") anomalies "
                "ORDER BY observed_at DESC NULLS LAST "
                f"LIMIT {sample_limit}"
            ),
        },
    ]
    return checks


def _run_integrity_gate(args):
    container_name = args.container_name
    db_name = args.database
    db_user = _integrity_resolve_db_user(container_name, args.db_user, args.timeout)
    generated_at = datetime.now(timezone.utc).isoformat()

    scope = _integrity_resolve_client_scope(
        args,
        container_name=container_name,
        db_name=db_name,
        db_user=db_user,
    )
    checks = _integrity_build_checks(scope.get("client_id"), args)

    results = []
    runtime_errors = []
    summary_counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "ERROR": 0}
    critical_failures = []

    for check in checks:
        check_result = {
            "id": check["id"],
            "severity": check["severity"],
            "description": check["description"],
            "status": "PASS",
            "row_count": 0,
            "sample_rows": [],
            "count_sql": check["count_sql"],
            "sample_sql": check["sample_sql"],
        }
        try:
            row_count = _integrity_count(
                container_name,
                db_name,
                db_user,
                check["count_sql"],
                timeout=args.timeout,
            )
            sample_rows = _integrity_json_rows(
                container_name,
                db_name,
                db_user,
                check["sample_sql"],
                timeout=args.timeout,
            )
            check_result["row_count"] = row_count
            check_result["sample_rows"] = sample_rows
            if row_count > 0:
                if check["severity"] == "critical":
                    check_result["status"] = "FAIL"
                else:
                    check_result["status"] = "WARN"
        except Exception as exc:
            check_result["status"] = "ERROR"
            check_result["error"] = f"{type(exc).__name__}: {exc}"
            runtime_errors.append(
                {
                    "check_id": check["id"],
                    "error": check_result["error"],
                }
            )

        summary_counts[check_result["status"]] += 1
        if check_result["status"] in {"FAIL", "ERROR"} and check["severity"] == "critical":
            critical_failures.append(check["id"])
        results.append(check_result)

    summary_status = "PASS"
    if summary_counts["ERROR"] > 0 or summary_counts["FAIL"] > 0:
        summary_status = "FAIL"
    elif summary_counts["WARN"] > 0:
        summary_status = "WARN"

    payload = {
        "command": "integrity-gate",
        "generated_at": generated_at,
        "scope": scope,
        "db": {
            "container_name": container_name,
            "database": db_name,
            "db_user": db_user,
        },
        "summary": {
            "status": summary_status,
            "infra_valid": len(runtime_errors) == 0,
            "checks_total": len(results),
            "pass_count": summary_counts["PASS"],
            "warn_count": summary_counts["WARN"],
            "fail_count": summary_counts["FAIL"],
            "error_count": summary_counts["ERROR"],
            "critical_failures": critical_failures,
        },
        "checks": results,
        "runtime_errors": runtime_errors,
    }

    indent = 2 if args.pretty else None
    output = json.dumps(payload, ensure_ascii=False, indent=indent)
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output + "\n")
    print(output)

    if runtime_errors:
        return 1
    if args.fail_on_critical and critical_failures:
        return 2
    return 0

_RUN_COMMAND_TIMEOUT_SEC = float(os.getenv("DIAGNOSE_CMD_TIMEOUT_SEC", "30"))
_RUN_COMMAND_REDACTED_VALUE = "<redacted>"
_RUN_COMMAND_SENSITIVE_FLAGS = {
    "--llm-api-key",
    "--judge-api-key",
    "--api-key",
    "--token",
    "--access-token",
    "--password",
    "--webhook-secret",
}


def _sanitize_command_for_logging(command):
    sanitized = []
    redact_next = False
    for raw_part in command:
        part = str(raw_part)
        if redact_next:
            sanitized.append(_RUN_COMMAND_REDACTED_VALUE)
            redact_next = False
            continue
        if not part:
            sanitized.append(part)
            continue
        lower = part.lower()
        if lower in _RUN_COMMAND_SENSITIVE_FLAGS:
            sanitized.append(part)
            redact_next = True
            continue
        if "=" in part and part.startswith("--"):
            key, _value = part.split("=", 1)
            if key.lower() in _RUN_COMMAND_SENSITIVE_FLAGS:
                sanitized.append(f"{key}={_RUN_COMMAND_REDACTED_VALUE}")
                continue
        if lower.startswith("authorization:") and "bearer " in lower:
            sanitized.append("Authorization: Bearer <redacted>")
            continue
        sanitized.append(part)
    return sanitized


def _render_command_for_logging(command):
    sanitized = _sanitize_command_for_logging(command)
    return " ".join(shlex.quote(str(part)) for part in sanitized)


def run_command(command, *, timeout=None, env=None):
    effective_timeout = _RUN_COMMAND_TIMEOUT_SEC if timeout is None else timeout
    merged_env = None
    if env:
        merged_env = os.environ.copy()
        for key, value in env.items():
            merged_env[str(key)] = str(value)
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            env=merged_env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timeout_note = (
            f"[timeout] command exceeded {effective_timeout}s: "
            f"{_render_command_for_logging(command)}"
        )
        stderr = (stderr + "\n" + timeout_note).strip()
        return subprocess.CompletedProcess(command, 124, stdout=stdout, stderr=stderr)

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
if len(sys.argv) > 1 and sys.argv[1] == "llm-quality":
    _run_llm_quality_entry(sys.argv[2:])
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "llm-quality-gates":
    raise SystemExit(_run_llm_quality_gates(_parse_llm_quality_gates_args(sys.argv[2:])))
if len(sys.argv) > 1 and sys.argv[1] == "llm-quality-matrix":
    _run_llm_quality_matrix(_parse_llm_quality_matrix_args(sys.argv[2:]))
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
if len(sys.argv) > 1 and sys.argv[1] == "dialog-report":
    _run_dialog_report(_parse_dialog_report_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "emit-evidence":
    _run_emit_evidence(_parse_emit_evidence_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "onboarding-fleet-check":
    _run_onboarding_fleet_check(_parse_onboarding_fleet_check_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "onboarding-fleet-remediate":
    _run_onboarding_fleet_remediate(_parse_onboarding_fleet_remediate_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "onboarding-hard-gate-rollout":
    _run_onboarding_hard_gate_rollout(_parse_onboarding_hard_gate_rollout_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "onboarding-delivery-stabilize":
    _run_onboarding_delivery_stabilize(_parse_onboarding_delivery_stabilize_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "onboarding-quality-smoke":
    _run_onboarding_quality_smoke(_parse_onboarding_quality_smoke_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "onboarding-pack-quality":
    _run_onboarding_pack_quality(_parse_onboarding_pack_quality_args(sys.argv[2:]))
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
if len(sys.argv) > 1 and sys.argv[1] == "integrity-gate":
    raise SystemExit(_run_integrity_gate(_parse_integrity_gate_args(sys.argv[2:])))

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
