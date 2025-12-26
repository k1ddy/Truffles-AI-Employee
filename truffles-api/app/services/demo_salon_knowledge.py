from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_DEMO_SALON_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "demo_salon"
_TRUTH_PATH = _DEMO_SALON_DIR / "SALON_TRUTH.yaml"
_INTENTS_PATH = _DEMO_SALON_DIR / "INTENTS_PHRASES_DEMO_SALON.yaml"


@dataclass(frozen=True)
class DemoSalonDecision:
    action: str
    response: str
    intent: str | None = None
    collect: list[str] | None = None


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.casefold().replace("ё", "е")
    normalized = re.sub(r"\[.*?\]", " ", normalized)
    normalized = normalized.replace("гель-лак", "гель лак").replace("гельлак", "гель лак")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


@lru_cache(maxsize=4)
def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_yaml_truth() -> dict:
    return _load_yaml(_TRUTH_PATH)


def load_intents_phrases() -> dict:
    data = _load_yaml(_INTENTS_PATH)
    intents = data.get("demo_salon_intents") if isinstance(data, dict) else None
    return intents if isinstance(intents, dict) else {}


@lru_cache(maxsize=2)
def _build_phrase_index() -> dict[str, list[str]]:
    intents = load_intents_phrases()
    index: dict[str, list[str]] = {}
    for intent, phrases in intents.items():
        if isinstance(phrases, list):
            normalized = [_normalize_text(str(phrase)) for phrase in phrases if str(phrase).strip()]
            index[intent] = [p for p in normalized if p]
    return index


def phrase_match_intent(text: str) -> set[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return set()
    matches: set[str] = set()
    for intent, phrases in _build_phrase_index().items():
        for phrase in phrases:
            if not phrase:
                continue
            if len(phrase) <= 3:
                if re.search(rf"\b{re.escape(phrase)}\b", normalized):
                    matches.add(intent)
                    break
                continue
            if phrase in normalized:
                matches.add(intent)
                break
    return matches


def _flatten_offtopic_phrases() -> list[str]:
    intents = load_intents_phrases()
    offtopic = intents.get("offtopic_examples") if isinstance(intents, dict) else None
    if not isinstance(offtopic, dict):
        return []
    phrases: list[str] = []
    for group in offtopic.values():
        if isinstance(group, list):
            phrases.extend(group)
    normalized = [_normalize_text(str(item)) for item in phrases if str(item).strip()]
    return [p for p in normalized if p]


@lru_cache(maxsize=2)
def _offtopic_phrases() -> list[str]:
    return _flatten_offtopic_phrases()


def _format_money(value: Any) -> str:
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{amount:,}".replace(",", " ")


def _tokenize(text: str) -> list[str]:
    normalized = _normalize_text(text)
    return [token for token in normalized.split() if token]


@lru_cache(maxsize=2)
def _build_price_index() -> list[dict[str, Any]]:
    truth = load_yaml_truth()
    items: list[dict[str, Any]] = []
    for category in truth.get("price_list", []) if isinstance(truth, dict) else []:
        for item in category.get("items", []) if isinstance(category, dict) else []:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            tokens = _tokenize(name)
            if not tokens:
                continue
            items.append(
                {
                    "name": name,
                    "tokens": tokens,
                    "item": item,
                }
            )
    return items


def _token_matches(token: str, message_tokens: list[str]) -> bool:
    for msg in message_tokens:
        if msg == token:
            return True
        if len(token) >= 3 and msg.startswith(token):
            return True
        if len(msg) >= 3 and token.startswith(msg):
            return True
    return False


def _find_best_price_item(message: str) -> dict[str, Any] | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    message_tokens = normalized.split()
    best = None
    best_len = 0
    for entry in _build_price_index():
        tokens = entry["tokens"]
        if not tokens:
            continue
        if all(_token_matches(token, message_tokens) for token in tokens):
            if len(tokens) > best_len:
                best = entry
                best_len = len(tokens)
    return best


def _contains_any(normalized: str, keywords: list[str]) -> bool:
    return any(keyword in normalized for keyword in keywords)


def _contains_word(normalized: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", normalized) is not None


def _contains_any_words(normalized: str, words: list[str]) -> bool:
    return any(_contains_word(normalized, word) for word in words)


def _looks_like_hours_question(normalized: str) -> bool:
    if not normalized:
        return False
    if _contains_any(normalized, ["график", "до скольки", "открыты", "открыто"]):
        return True
    if "работаете" in normalized:
        return True
    if "работает" in normalized and _contains_any(normalized, ["вы", "салон"]):
        if _contains_any(normalized, ["сегодня", "сейчас", "открыт"]):
            return True
    return False


def _extract_minutes(text: str) -> int | None:
    match = re.search(r"\b(\d{1,3})\s*(?:мин|минут|м)\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _format_price_reply(item: dict[str, Any]) -> str:
    name = item.get("name", "Услуга")
    if "price" in item:
        price = _format_money(item.get("price"))
        return f"{name} — {price} ₸."
    if "price_from" in item:
        price = _format_money(item.get("price_from"))
        return f"{name} — от {price} ₸."
    return f"{name} — уточните цену у администратора."


def _format_promotions(truth: dict, intent: str | None = None) -> str:
    promotions = truth.get("promotions") if isinstance(truth, dict) else {}
    items = promotions.get("items") if isinstance(promotions, dict) else []
    if not isinstance(items, list):
        items = []

    if intent == "promotion_first_visit":
        for promo in items:
            if "перв" in str(promo.get("name", "")).casefold():
                return (
                    f"На первое посещение действует скидка {promo.get('discount_percent')}% "
                    "на услуги. Скидки не суммируются."
                )
    if intent == "promotion_birthday":
        for promo in items:
            if "именин" in str(promo.get("name", "")).casefold():
                return (
                    f"Именинникам скидка {promo.get('discount_percent')}% — "
                    "7 дней до/после даты рождения при документе."
                )
    if intent == "promotion_student":
        for promo in items:
            if "студент" in str(promo.get("name", "")).casefold() or "пенсион" in str(promo.get("name", "")).casefold():
                return (
                    f"Студентам/пенсионерам скидка {promo.get('discount_percent')}% "
                    "по будням 11:00–16:00 при документе."
                )

    parts = []
    for promo in items:
        name = promo.get("name")
        percent = promo.get("discount_percent")
        if name and percent:
            parts.append(f"{name}: {percent}%")
    if parts:
        stacking = promotions.get("stacking")
        stacking_text = f" {stacking}." if stacking else ""
        return "Официальные акции: " + "; ".join(parts) + "." + stacking_text
    return "Скидки действуют только по официальным акциям."


def format_reply_from_truth(intent: str, slots: dict | None = None) -> str | None:
    truth = load_yaml_truth()
    slots = slots or {}

    if intent == "location":
        address = truth.get("salon", {}).get("address", {})
        return (
            f"Адрес: {address.get('full')}. "
            f"{address.get('entrance') or ''}".strip()
        )
    if intent == "location_directions":
        address = truth.get("salon", {}).get("address", {})
        landmarks = address.get("landmarks") or []
        if landmarks:
            return landmarks[0]
        return "Подскажите, откуда вам удобнее добираться?"
    if intent == "location_signage":
        signage = truth.get("salon", {}).get("address", {}).get("signage")
        if signage:
            return f"Да, есть {signage}."
        return "Да, вывеска есть."
    if intent == "parking":
        parking = truth.get("salon", {}).get("parking", {})
        details = parking.get("details") or ""
        return details or "Есть парковка рядом с салоном."
    if intent == "hours":
        hours = truth.get("salon", {}).get("hours", {})
        days = hours.get("days")
        open_time = hours.get("open")
        close_time = hours.get("close")
        return f"Работаем {days}, с {open_time} до {close_time}."
    if intent == "services_overview":
        summary = truth.get("salon", {}).get("services_summary")
        if summary:
            return summary
        categories = [
            str(item.get("category", "")).strip()
            for item in (truth.get("price_list", []) if isinstance(truth, dict) else [])
            if isinstance(item, dict) and item.get("category")
        ]
        categories = [item for item in categories if item]
        if categories:
            return "Мы оказываем услуги: " + ", ".join(categories) + "."
        return "Мы салон красоты. Подскажите, какая услуга интересует?"
    if intent == "last_appointment":
        last_time = truth.get("salon", {}).get("hours", {}).get("last_appointment")
        if last_time:
            return f"Последняя запись обычно на {last_time}."
        return "Последняя запись обычно за 30–60 минут до закрытия."
    if intent == "price_query":
        item = slots.get("price_item")
        if item:
            return _format_price_reply(item)
        return "Подскажите, какая услуга интересует? Сориентирую по цене."
    if intent == "why_price_from":
        reason = truth.get("pricing", {}).get("price_from_reason")
        return reason or "Цена «от» зависит от деталей услуги."
    if intent == "promotions_rules":
        stacking = truth.get("promotions", {}).get("stacking")
        return stacking or "Скидки не суммируются."
    if intent == "promotions":
        return _format_promotions(truth, slots.get("promotion_intent"))
    if intent == "objection_price":
        hygiene = truth.get("hygiene", {}).get("instrument_processing")
        if hygiene:
            return (
                "Понимаю вопрос. У нас строгая стерилизация инструментов — это про безопасность, "
                "поэтому цена может быть выше."
            )
        return "Цена зависит от качества и безопасности процедур."
    if intent == "booking_intake":
        return (
            "Могу передать администратору запрос на запись. "
            "Напишите, пожалуйста: услуга, точная дата, точное время, имя, контактный номер."
        )
    if intent == "cancel_policy":
        notice = truth.get("booking", {}).get("cancel_policy", {}).get("notice", {})
        standard = notice.get("standard_services_min_hours")
        long_services = notice.get("long_services_min_hours")
        return (
            f"Для стандартных услуг — минимум за {standard} часа, "
            f"для длительных (3+ часа) — за {long_services} часа."
        )
    if intent == "lateness_ok":
        notes = truth.get("booking", {}).get("lateness_policy", {}).get("notes")
        return notes or "Если опоздание до 10–15 минут — постараемся принять."
    if intent == "guest_child" or intent == "guest_partner":
        guest = truth.get("guest_policy", {}).get("allowed_guests")
        return guest or "Можно, есть зона ожидания."
    if intent == "guest_animals":
        animals = truth.get("guest_policy", {}).get("animals")
        return animals or "С животными нельзя по гигиене."
    if intent == "guest_early":
        early = truth.get("guest_policy", {}).get("early_arrival")
        return early or "Можно прийти на 10–15 минут раньше и подождать."
    if intent == "hygiene":
        hygiene = truth.get("hygiene", {})
        parts = [
            hygiene.get("instrument_processing"),
            hygiene.get("dry_heat"),
            hygiene.get("disposables"),
        ]
        return " ".join([p for p in parts if p])
    if intent == "hygiene_dry_heat":
        return "Да, есть сухожарный шкаф."
    if intent == "hygiene_disposables":
        return "Да, пилки и бафы одноразовые."
    if intent == "brands":
        brands = truth.get("brands", {})
        hair = ", ".join(brands.get("hair", []) if isinstance(brands, dict) else [])
        nails = ", ".join(brands.get("nails", []) if isinstance(brands, dict) else [])
        face = ", ".join(brands.get("face", []) if isinstance(brands, dict) else [])
        return f"Волосы: {hair}. Ногти: {nails}. Лицо: {face}."
    if intent == "amenities_wifi":
        wifi = truth.get("salon", {}).get("amenities", {}).get("wifi")
        return f"{wifi or 'Бесплатный Wi‑Fi'}."
    if intent == "amenities_drinks":
        drinks = truth.get("salon", {}).get("amenities", {}).get("drinks")
        return f"{drinks or 'Чай/кофе бесплатно'}."
    if intent == "amenities_toilet":
        toilet = truth.get("salon", {}).get("amenities", {}).get("toilet")
        return toilet or "Есть туалет для клиентов."
    if intent == "gift_certificate":
        gift = truth.get("salon", {}).get("amenities", {}).get("gift_certificates")
        return gift or "Можно купить сертификат на любую сумму."
    if intent == "off_topic":
        return "Я помогаю только с вопросами о наших услугах салона — цены, запись, адрес."
    return None


def _detect_promotion_intent(normalized: str) -> str | None:
    if any(keyword in normalized for keyword in ["перв", "первое", "первый"]):
        return "promotion_first_visit"
    if "именин" in normalized or "день рождения" in normalized:
        return "promotion_birthday"
    if "студент" in normalized or "пенсион" in normalized:
        return "promotion_student"
    return None


def _detect_policy_intent(normalized: str, phrase_intents: set[str]) -> str | None:
    def _contains_keyword(keyword: str) -> bool:
        if not keyword:
            return False
        if len(keyword) <= 3:
            return re.search(rf"\b{re.escape(keyword)}\b", normalized) is not None
        return keyword in normalized

    payment_keywords = [
        "kaspi",
        "каспи",
        "red",
        "ред",
        "рассроч",
        "долям",
        "pay",
        "оплат",
        "предоплат",
        "перевод",
        "перечис",
        "квитанц",
        "qr",
        "карт",
        "терминал",
        "эквайр",
        "касса",
        "счет",
        "счёт",
        "реквизит",
        "iban",
        "swift",
        "налич",
        "безнал",
        "чек",
    ]
    if "payment" in phrase_intents or any(_contains_keyword(keyword) for keyword in payment_keywords):
        return "policy_payment"

    reschedule_keywords = [
        "перенес",
        "перенести",
        "перенос",
        "переносит",
        "переносить",
        "перезапис",
        "перезапиш",
        "перепис",
        "сдвин",
        "передвин",
        "перемест",
        "изменить запись",
        "поменять время",
        "поменять дату",
        "изменить дату",
        "на другое время",
        "на другой день",
        "на другую дату",
    ]
    if _contains_any(normalized, reschedule_keywords):
        return "policy_reschedule"

    cancel_keywords = ["отмен", "отмена", "откаж", "не приду"]
    if _contains_any(normalized, cancel_keywords):
        return "policy_cancel"

    medical_keywords = [
        "беремен",
        "аллерг",
        "противопоказ",
        "кормл",
        "лактац",
        "ожог",
        "ожг",
        "жжет",
        "жжёт",
        "печет",
        "печёт",
        "болит",
        "больно",
        "кров",
        "воспал",
        "покрасн",
        "сып",
        "реакц",
        "раздраж",
        "анестез",
        "обезбол",
        "кож",
        "дермат",
        "болезн",
        "лиценз",
        "медобраз",
    ]
    if _contains_any(normalized, medical_keywords):
        return "policy_medical"

    hours_like = _looks_like_hours_question(normalized)
    complaint_keywords = [
        "не понрав",
        "жалоб",
        "претенз",
        "разочар",
        "плохо",
        "недовол",
        "ужас",
        "кошмар",
        "хам",
        "грубо",
        "брак",
        "треснул",
        "отпал",
        "слезл",
        "сломал",
        "испор",
        "задерж",
        "жду уже",
        "не приш",
        "сожг",
        "обожг",
        "порез",
        "кров",
        "не слыш",
        "одно и то же",
        "одно и тоже",
    ]
    if ("complaint" in phrase_intents or _contains_any(normalized, complaint_keywords)) and not hours_like:
        return "policy_complaint"

    discount_keywords = ["скидк", "скидоч", "скидос", "дешевл", "подешевле", "купон", "акци", "промо", "промокод", "торг", "уступ"]
    if _contains_any(normalized, discount_keywords):
        return "policy_discount"

    return None


def get_demo_salon_decision(message: str) -> DemoSalonDecision | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None

    phrase_intents = phrase_match_intent(message)
    if "отмен" in normalized and "за сколько" in normalized:
        reply = format_reply_from_truth("cancel_policy")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="cancel_policy")

    policy_intent = _detect_policy_intent(normalized, phrase_intents)

    if policy_intent == "policy_payment":
        return DemoSalonDecision(
            action="escalate",
            response="По оплате уточню у администратора — передам администратору ваш вопрос.",
            intent="payment",
        )
    if policy_intent == "policy_reschedule":
        return DemoSalonDecision(
            action="escalate",
            response="Перенос записи подтверждает администратор. Передам ваш запрос.",
            intent="reschedule",
        )
    if policy_intent == "policy_cancel":
        return DemoSalonDecision(
            action="escalate",
            response=(
                "Администратор подтвердит отмену. "
                "Напишите, пожалуйста: имя, услуга, контактный номер."
            ),
            intent="cancel_request",
            collect=["имя", "услуга", "контактный номер"],
        )
    if policy_intent == "policy_medical":
        return DemoSalonDecision(
            action="escalate",
            response=(
                "По таким вопросам нужна консультация мастера или администратора — "
                "передам ваш вопрос."
            ),
            intent="medical",
        )
    if policy_intent == "policy_complaint":
        return DemoSalonDecision(
            action="escalate",
            response="Жаль, что так вышло. Передам администратору, чтобы разобрались.",
            intent="complaint",
        )

    if "сегодня" in normalized or "прямо сейчас" in normalized:
        if _contains_any(normalized, ["запис", "окошк", "свободн"]):
            return DemoSalonDecision(
                action="escalate",
                response=(
                    "На сегодня уточню у администратора. Подскажите, пожалуйста: услуга и удобное время — передам."
                ),
                intent="same_day_booking",
                collect=["услуга", "время"],
            )

    if "скидки сумм" in normalized or "скидк" in normalized and "сумм" in normalized:
        reply = format_reply_from_truth("promotions_rules")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="promotions_rules")

    promotion_intent = _detect_promotion_intent(normalized)
    if promotion_intent:
        reply = format_reply_from_truth("promotions", {"promotion_intent": promotion_intent})
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="promotions")

    if policy_intent == "policy_discount":
        reply = _format_promotions(load_yaml_truth())
        return DemoSalonDecision(action="reply", response=reply, intent="discount_haggle")

    if "почему" in normalized and "от" in normalized and ("цена" in normalized or "стоим" in normalized):
        reply = format_reply_from_truth("why_price_from")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="why_price_from")

    if "дороже" in normalized or ("дорог" in normalized and "скид" not in normalized):
        reply = format_reply_from_truth("objection_price")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="objection_price")

    if "адрес" in normalized or "где вы" in normalized or "где наход" in normalized:
        reply = format_reply_from_truth("location")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="location")

    if "остановк" in normalized or "как пройти" in normalized or "как добрать" in normalized:
        reply = format_reply_from_truth("location_directions")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="location_directions")

    if "вывеск" in normalized:
        reply = format_reply_from_truth("location_signage")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="location_signage")

    if "парков" in normalized:
        reply = format_reply_from_truth("parking")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="parking")

    if "последняя запись" in normalized or "до какого времени можно запис" in normalized:
        reply = format_reply_from_truth("last_appointment")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="last_appointment")

    if _contains_any(
        normalized,
        ["график", "работаете", "открыты", "открыто", "до скольки", "ашык", "ашық", "бугин", "бүгін"],
    ) and not _contains_any(normalized, ["косметик", "материал", "бренд", "марки"]):
        reply = format_reply_from_truth("hours")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hours")

    if "services_overview" in phrase_intents or _contains_any(
        normalized,
        [
            "чем занимает",
            "какие услуги",
            "что вы делаете",
            "что у вас есть",
            "какой спектр услуг",
            "какие процедуры",
            "что можно сделать",
        ],
    ):
        reply = format_reply_from_truth("services_overview")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="services_overview")

    if "опозда" in normalized:
        minutes = _extract_minutes(message)
        tolerated = load_yaml_truth().get("booking", {}).get("lateness_policy", {}).get("tolerated_minutes", 15)
        try:
            tolerated = int(tolerated)
        except (TypeError, ValueError):
            tolerated = 15
        if minutes is not None and minutes > tolerated:
            return DemoSalonDecision(
                action="escalate",
                response="Если опоздание больше 15 минут — передам администратору, чтобы уточнить.",
                intent="lateness_over",
            )
        reply = format_reply_from_truth("lateness_ok")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="lateness_ok")

    if _contains_any(normalized, ["ребен", "ребён"]) or _contains_any_words(
        normalized, ["муж", "мужем", "мужу", "мужа"]
    ):
        reply = format_reply_from_truth("guest_child")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="guest_policy")

    if _contains_any(normalized, ["собак", "животн"]):
        reply = format_reply_from_truth("guest_animals")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="guest_policy")

    if _contains_any(normalized, ["пораньше", "раньше", "подождать"]):
        reply = format_reply_from_truth("guest_early")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="guest_policy")

    if _contains_any(normalized, ["стерилиз", "инструмент", "обрабатываете", "дез", "сухожар"]):
        reply = format_reply_from_truth("hygiene")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hygiene")

    if _contains_any(normalized, ["сухожар"]):
        reply = format_reply_from_truth("hygiene_dry_heat")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hygiene")

    if _contains_any(normalized, ["пилк", "однораз"]):
        reply = format_reply_from_truth("hygiene_disposables")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="hygiene")

    if _contains_any(normalized, ["какой космет", "материал", "бренд", "марки"]):
        reply = format_reply_from_truth("brands")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="brands")

    if _contains_any(normalized, ["wifi", "вайфай", "вай фай", "wi fi"]):
        reply = format_reply_from_truth("amenities_wifi")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="amenities")

    if _contains_any(normalized, ["кофе", "чай"]):
        reply = format_reply_from_truth("amenities_drinks")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="amenities")

    if _contains_any(normalized, ["туалет", "санузел"]):
        reply = format_reply_from_truth("amenities_toilet")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="amenities")

    if "сертификат" in normalized:
        reply = format_reply_from_truth("gift_certificate")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="gift_certificate")

    if "запис" in normalized or "окошк" in normalized or "свободн" in normalized:
        reply = format_reply_from_truth("booking_intake")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="booking_intake")

    offtopic_keywords = ["чат бот", "ботов", "разработк", "сайт", "crm", "интеграц", "мессенджер"]
    if any(phrase and phrase in normalized for phrase in _offtopic_phrases()) or _contains_any(
        normalized, offtopic_keywords
    ):
        reply = format_reply_from_truth("off_topic")
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="off_topic")

    price_item = _find_best_price_item(message)
    if price_item or _contains_any(normalized, ["сколько", "цена", "прайс", "стоим", "почем"]):
        reply = format_reply_from_truth("price_query", {"price_item": price_item["item"]} if price_item else {})
        if reply:
            return DemoSalonDecision(action="reply", response=reply, intent="price_query")

    return None


def get_demo_salon_price_reply(message: str) -> str | None:
    normalized = _normalize_text(message)
    if not normalized:
        return None
    price_item = _find_best_price_item(message)
    if not price_item:
        return None
    return format_reply_from_truth("price_query", {"price_item": price_item["item"]})


def get_demo_salon_price_item(message: str) -> str | None:
    price_item = _find_best_price_item(message)
    if not price_item:
        return None
    item = price_item.get("item")
    if not item:
        return None
    return str(item).strip() or None


def get_truth_reply(message: str) -> str | None:
    decision = get_demo_salon_decision(message)
    if decision and decision.action == "reply":
        return decision.response
    return None
