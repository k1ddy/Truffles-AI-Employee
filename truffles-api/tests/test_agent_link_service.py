from app.services.agent_link_service import build_telegram_deep_link, generate_link_token, hash_link_token


def test_hash_link_token_stable():
    token = "ABC12345"
    assert hash_link_token(token) == hash_link_token(token)


def test_generate_link_token_length():
    token = generate_link_token()
    assert len(token) == 8
    assert token.isalnum()


def test_build_telegram_deep_link():
    assert build_telegram_deep_link("truffles_bot", "TOKEN") == "https://t.me/truffles_bot?start=TOKEN"
    assert build_telegram_deep_link("@truffles_bot", "TOKEN") == "https://t.me/truffles_bot?start=TOKEN"
    assert build_telegram_deep_link("", "TOKEN") is None
