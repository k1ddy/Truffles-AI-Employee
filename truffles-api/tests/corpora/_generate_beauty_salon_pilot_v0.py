"""Generator for `beauty_salon_pilot_v0.jsonl`.

Produces the DRAFT internal pilot corpus. Run from repo root:

    python3 truffles-api/tests/corpora/_generate_beauty_salon_pilot_v0.py

The script is deterministic. Output is JSONL, one CorpusDialog per line.
This file is the source of truth for the JSONL; do not hand-edit the JSONL.
"""
from __future__ import annotations

import json
import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "truffles-api"))


from app.policy_core_v3.schema import (  # noqa: E402
    CandidateAction,
    Intent,
    PolicyDecisionV3,
    Uncertainty,
)
from app.policy_core_v3_corpus.schema import (  # noqa: E402
    CorpusDialog,
    CorpusTurn,
)
from app.policy_core_v3_shadow import LegacySummary  # noqa: E402


def _dec(intent: Intent, *, tool: str = "none", slots=None, evidence_refs=None,
         message: str = "", uncertainty: Uncertainty = Uncertainty.low,
         args=None) -> PolicyDecisionV3:
    return PolicyDecisionV3(
        intent=intent,
        slots=slots or {},
        candidate_action=CandidateAction(tool=tool, args=args or {}),
        evidence_refs=evidence_refs or [],
        message_draft=message,
        uncertainty=uncertainty,
    )


def _legacy(intent: str, action: str, *, tool: str | None = None,
            text: str = "", rescue: bool = False, degrade: bool = False) -> LegacySummary:
    return LegacySummary(
        intent=intent,
        action=action,
        tool_action=tool,
        message_text=text,
        rescue_flag=rescue,
        policy_core_degrade=degrade,
    )


def _build_corpus() -> list[CorpusDialog]:
    dialogs: list[CorpusDialog] = []

    # 1. Простой booking, всё известно сразу
    dialogs.append(CorpusDialog(
        dialog_id="bs-001-simple-booking",
        notes="Услуга/дата/время в одном сообщении; нужно собрать имя/телефон.",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="можно завтра в 6 вечера на брови",
            legacy_summary=_legacy(
                "booking_request", "collect", tool="calendar.list_slots",
                text="Подскажите ваше имя.",
            ),
            oracle_v3=_dec(
                Intent.slot_collect,
                slots={"service_id": "brows_lashes", "datetime": "2026-05-12T18:00:00+05:00"},
                message="Записываю на брови завтра в 18:00. Подскажите ваше имя?",
            ),
        )],
    ))

    # 2. Fragmented messages — последовательность коротких реплик
    dialogs.append(CorpusDialog(
        dialog_id="bs-002-fragmented-booking",
        notes="Клиент пишет короткие сообщения подряд.",
        turns=[
            CorpusTurn(
                turn_index=0, current_message="брови",
                legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                       text="На какую дату?"),
                oracle_v3=_dec(Intent.slot_collect, slots={"service_id": "brows_lashes"},
                               message="Брови. На какую дату?"),
            ),
            CorpusTurn(
                turn_index=1, current_message="завтра",
                state_slots={"service_id": "brows_lashes"},
                legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                       text="Во сколько?"),
                oracle_v3=_dec(Intent.slot_collect,
                               slots={"service_id": "brows_lashes", "datetime_day": "tomorrow"},
                               message="Завтра. Во сколько вам удобно?"),
            ),
            CorpusTurn(
                turn_index=2, current_message="на 17 30",
                state_slots={"service_id": "brows_lashes", "datetime_day": "tomorrow"},
                legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                       text="Подскажите ваше имя."),
                oracle_v3=_dec(Intent.slot_collect,
                               slots={"service_id": "brows_lashes", "datetime": "2026-05-12T17:30:00+05:00"},
                               message="Записываю на 17:30. Подскажите имя?"),
            ),
        ],
    ))

    # 3. Voice-transcript style — без знаков препинания, разговорный
    dialogs.append(CorpusDialog(
        dialog_id="bs-003-voice-style",
        notes="Транскрипт голосового сообщения.",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="ну я бы хотела на маникюр на пятницу вечером после работы",
            legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                   text="Уточните, пожалуйста, точное время."),
            oracle_v3=_dec(Intent.slot_collect,
                           slots={"service_id": "manicure", "datetime_day": "friday",
                                  "datetime_hint": "evening"},
                           message="Маникюр в пятницу вечером. После шести подойдёт?"),
        )],
    ))

    # 4. Missing service — клиент пишет про услугу, которой нет
    dialogs.append(CorpusDialog(
        dialog_id="bs-004-unsupported-service",
        notes="Татуаж бровей салон не делает.",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="а татуаж бровей у вас делают?",
            legacy_summary=_legacy("fact_question", "reply",
                                   text="Татуаж не делаем. Из бровного: коррекция, окрашивание, ламинирование."),
            oracle_v3=_dec(
                Intent.unsupported, tool="none",
                evidence_refs=["pack:services"],
                message="Татуаж не делаем. По бровям: коррекция, окрашивание, ламинирование.",
            ),
        )],
    ))

    # 5. Cancel — должен handoff
    dialogs.append(CorpusDialog(
        dialog_id="bs-005-cancel-handoff",
        notes="Cancel: bot_can_confirm=false → handoff.",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="отмените мою запись на завтра",
            legacy_summary=_legacy("cancel_request", "escalate", tool="handoff.create",
                                   text="Администратор подтвердит отмену. Передам.",
                                   rescue=False),
            oracle_v3=_dec(
                Intent.handoff_request, tool="handoff.create",
                args={"reason": "cancel_request"},
                message="Отмену подтверждает администратор. Передаю запрос.",
            ),
        )],
    ))

    # 6. Reschedule — handoff
    dialogs.append(CorpusDialog(
        dialog_id="bs-006-reschedule-handoff",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="можно перенести на другой день?",
            legacy_summary=_legacy("reschedule", "escalate", tool="handoff.create",
                                   text="Перенос подтверждает администратор."),
            oracle_v3=_dec(Intent.handoff_request, tool="handoff.create",
                           args={"reason": "reschedule"},
                           message="Перенос подтверждает администратор. Передаю запрос."),
        )],
    ))

    # 7. Medical — handoff
    dialogs.append(CorpusDialog(
        dialog_id="bs-007-medical-handoff",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="у меня аллергия на гель-лак, что делать?",
            legacy_summary=_legacy("medical", "escalate", tool="handoff.create",
                                   text="Передам мастеру/администратору."),
            oracle_v3=_dec(Intent.handoff_request, tool="handoff.create",
                           args={"reason": "medical"},
                           message="По таким вопросам нужна консультация мастера. Передаю запрос."),
        )],
    ))

    # 8. Complaint — handoff
    dialogs.append(CorpusDialog(
        dialog_id="bs-008-complaint-handoff",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="вчера сделали ужасно, ноготь треснул через час",
            legacy_summary=_legacy("complaint", "escalate", tool="handoff.create",
                                   text="Жаль, что так вышло. Передам администратору."),
            oracle_v3=_dec(Intent.handoff_request, tool="handoff.create",
                           args={"reason": "complaint"},
                           message="Жаль, что так вышло. Передаю администратору."),
        )],
    ))

    # 9. FACT: цена
    dialogs.append(CorpusDialog(
        dialog_id="bs-009-fact-price",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="сколько стоит маникюр?",
            legacy_summary=_legacy("fact_question", "reply",
                                   text="Маникюр от 6000 KZT."),
            oracle_v3=_dec(Intent.fact_question, evidence_refs=["pack:service:manicure"],
                           message="Маникюр у нас от 6000 KZT, классический/аппаратный/комбинированный."),
        )],
    ))

    # 10. FACT: часы
    dialogs.append(CorpusDialog(
        dialog_id="bs-010-fact-hours",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="до скольки вы работаете?",
            legacy_summary=_legacy("fact_question", "reply",
                                   text="Работаем ежедневно с 9 до 21."),
            oracle_v3=_dec(Intent.fact_question, evidence_refs=["pack:business:hours"],
                           message="Ежедневно 9:00–21:00. Последняя запись 20:00–20:30."),
        )],
    ))

    # 11. FACT: адрес
    dialogs.append(CorpusDialog(
        dialog_id="bs-011-fact-address",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="вы где находитесь?",
            legacy_summary=_legacy("fact_question", "reply",
                                   text="Алматы, ул. Абая 150."),
            oracle_v3=_dec(Intent.fact_question, evidence_refs=["pack:business:address"],
                           message="Алматы, Абая 150, угол Розыбакиева. Вход со стороны Розыбакиева, 2 этаж."),
        )],
    ))

    # 12. FACT: master
    dialogs.append(CorpusDialog(
        dialog_id="bs-012-fact-master",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="кто у вас делает брови?",
            legacy_summary=_legacy("master_query", "reply",
                                   text="Динара делает брови и ресницы."),
            oracle_v3=_dec(Intent.fact_question,
                           evidence_refs=["pack:specialist:dinara"],
                           message="По бровям: Динара (4 года опыта)."),
        )],
    ))

    # 13. Booking без контакта — boundary должен заблокировать
    dialogs.append(CorpusDialog(
        dialog_id="bs-013-missing-phone",
        notes="Service+date+time+name есть, нет телефона; boundary блокирует commit.",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="меня зовут Айгуль, забронируйте на завтра 17:00 маникюр",
            state_slots={
                "service_id": "manicure",
                "datetime": "2026-05-12T17:00:00+05:00",
            },
            legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                   text="Подскажите ваш контактный номер."),
            oracle_v3=_dec(Intent.slot_collect,
                           slots={"service_id": "manicure",
                                  "datetime": "2026-05-12T17:00:00+05:00",
                                  "customer_name": "Айгуль"},
                           message="Айгуль, маникюр завтра в 17:00. Какой ваш телефон?"),
        )],
    ))

    # 14. Lookup без identity — privacy guard
    dialogs.append(CorpusDialog(
        dialog_id="bs-014-lookup-no-identity",
        notes="Клиент просит проверить запись, не дав ни имени ни телефона.",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="у меня же запись на маникюр завтра?",
            legacy_summary=_legacy("booking_manage", "collect",
                                   tool="calendar.get_booking",
                                   text="Чтобы найти запись, подскажите имя или телефон."),
            oracle_v3=_dec(Intent.slot_collect,
                           message="Чтобы проверить запись, подскажите ваше имя или номер телефона."),
        )],
    ))

    # 15. KZ-mix
    dialogs.append(CorpusDialog(
        dialog_id="bs-015-kz-mix",
        locale="ru-KZ",
        notes="Клиентское сообщение на KZ/RU mix.",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="ертең маникюрге жаздыр",
            legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                   text="Маникюр на завтра. Во сколько?"),
            oracle_v3=_dec(Intent.slot_collect,
                           slots={"service_id": "manicure", "datetime_day": "tomorrow"},
                           message="Маникюр на завтра. Во сколько вам удобно?"),
        )],
    ))

    # 16. Vague time
    dialogs.append(CorpusDialog(
        dialog_id="bs-016-vague-time",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="запишите на стрижку как-нибудь вечером на этой неделе",
            legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                   text="Уточните день и время."),
            oracle_v3=_dec(Intent.slot_collect,
                           slots={"service_id": "haircut", "datetime_hint": "evening_this_week"},
                           message="Стрижка вечером. Какой день недели подходит?"),
        )],
    ))

    # 17. Multi-service confusion
    dialogs.append(CorpusDialog(
        dialog_id="bs-017-multi-service",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="сделайте мне маникюр и педикюр и брови сразу",
            legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                   text="Хорошо, маникюр + педикюр + брови. На какой день?"),
            oracle_v3=_dec(Intent.slot_collect,
                           slots={"service_ids": ["manicure", "pedicure", "brows_lashes"]},
                           message="Маникюр + педикюр + брови. На какой день записать?"),
        )],
    ))

    # 18. Discount question — bot отвечает из pack
    dialogs.append(CorpusDialog(
        dialog_id="bs-018-fact-discount",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="скидки есть?",
            legacy_summary=_legacy("discount_haggle", "reply",
                                   text="Первое посещение -10%, именинникам -15%."),
            oracle_v3=_dec(Intent.fact_question, evidence_refs=["pack:promotions"],
                           message="Да: первое посещение -10%, именинник -15%, студент/пенсионер -10% по будням 11–16. Не суммируются."),
        )],
    ))

    # 19. Smalltalk
    dialogs.append(CorpusDialog(
        dialog_id="bs-019-smalltalk",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="привет",
            legacy_summary=_legacy("smalltalk", "reply",
                                   text="Здравствуйте! Чем могу помочь?"),
            oracle_v3=_dec(Intent.smalltalk,
                           message="Здравствуйте! Чем помочь — записать на услугу или ответить на вопрос?"),
        )],
    ))

    # 20. Phone formats
    dialogs.append(CorpusDialog(
        dialog_id="bs-020-phone-formats",
        notes="Разные форматы телефонов в pending_phone-стадии.",
        turns=[
            CorpusTurn(
                turn_index=0, current_message="Айгуль, 87015705555",
                state_slots={
                    "service_id": "manicure",
                    "datetime": "2026-05-12T17:00:00+05:00",
                    "pending": "name_and_phone",
                },
                legacy_summary=_legacy("booking_request", "collect",
                                       tool="calendar.book_slot",
                                       text="Принято, Айгуль. Записываю на 17:00, передам мастеру."),
                oracle_v3=_dec(Intent.booking_request, tool="calendar.book_slot",
                               args={"service_query": "manicure",
                                     "start_at": "2026-05-12T17:00:00+05:00",
                                     "customer_name": "Айгуль",
                                     "customer_phone": "87015705555"},
                               slots={"customer_name": "Айгуль",
                                      "customer_phone": "87015705555"},
                               message="Принято, Айгуль. Запишу на 17:00, передам мастеру."),
            ),
        ],
    ))

    # 21. Pending phone, клиент задерживает — должно остаться collect
    dialogs.append(CorpusDialog(
        dialog_id="bs-021-pending-phone-delay",
        notes="Клиент пишет 'позже скажу' — booking не должен committed.",
        turns=[CorpusTurn(
            turn_index=0, current_message="позже скажу",
            state_slots={"service_id": "manicure", "pending": "phone"},
            legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                   text="Хорошо, без телефона записать не получится. Дайте номер, как будете готовы."),
            oracle_v3=_dec(Intent.slot_collect,
                           slots={"service_id": "manicure"},
                           message="Хорошо. Без телефона запись не оформляем; дайте номер, как будете готовы."),
        )],
    ))

    # 22. Refund — handoff
    dialogs.append(CorpusDialog(
        dialog_id="bs-022-refund-handoff",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="можно вернуть деньги, мне не понравилось",
            legacy_summary=_legacy("refund", "escalate", tool="handoff.create",
                                   text="Передам администратору, разберёмся."),
            oracle_v3=_dec(Intent.handoff_request, tool="handoff.create",
                           args={"reason": "refund"},
                           message="Передаю администратору, разберёмся."),
        )],
    ))

    # 23. Question about parking — FACT
    dialogs.append(CorpusDialog(
        dialog_id="bs-023-fact-parking",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="у вас есть парковка?",
            legacy_summary=_legacy("fact_question", "reply",
                                   text="Бесплатная парковка во дворе, 5–6 мест."),
            oracle_v3=_dec(Intent.fact_question, evidence_refs=["pack:business:parking"],
                           message="Да, бесплатная парковка во дворе, обычно 5–6 мест."),
        )],
    ))

    # 24. Booking same-day, требует handoff
    dialogs.append(CorpusDialog(
        dialog_id="bs-024-same-day-booking",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="можно сегодня в 19:00 на маникюр?",
            legacy_summary=_legacy("booking_request", "collect", tool="calendar.list_slots",
                                   text="Передам администратору, чтобы посмотрел окна."),
            oracle_v3=_dec(Intent.slot_collect,
                           slots={"service_id": "manicure", "datetime_hint": "today_19:00"},
                           message="Сегодня в 19:00 на маникюр — уточню окна у администратора. Подскажите имя и телефон."),
        )],
    ))

    # 25. Совершенно левый запрос
    dialogs.append(CorpusDialog(
        dialog_id="bs-025-out-of-domain",
        turns=[CorpusTurn(
            turn_index=0,
            current_message="а заточить ножи у вас можно?",
            legacy_summary=_legacy("unsupported", "reply",
                                   text="Мы салон красоты, ножи не точим."),
            oracle_v3=_dec(Intent.unsupported,
                           message="Мы салон красоты — ножи не точим. Из бьюти-услуг могу подсказать."),
        )],
    ))

    return dialogs


def main() -> None:
    out_path = REPO_ROOT / "truffles-api" / "tests" / "corpora" / "beauty_salon_pilot_v0.jsonl"
    dialogs = _build_corpus()
    lines = [
        json.dumps(d.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        for d in dialogs
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(dialogs)} dialogs to {out_path}")


if __name__ == "__main__":
    main()
