from types import SimpleNamespace

from app.routers.webhook import media


def test_media_policy_default_allowed_hosts_include_public_base(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.truffles.kz")
    monkeypatch.delenv("CHATFLOW_MEDIA_BASE_URL", raising=False)
    monkeypatch.delenv("CHATFLOW_API_URL", raising=False)

    policy = media._get_media_policy(None)

    assert "app.chatflow.kz" in policy["allowed_hosts"]
    assert "api.truffles.kz" in policy["allowed_hosts"]


def test_media_policy_normalizes_allowed_hosts_from_client_config():
    client = SimpleNamespace(
        config={
            "media": {
                "allowed_hosts": [
                    "FILES.Example.com",
                    " api.Truffles.kz ",
                ]
            }
        }
    )

    policy = media._get_media_policy(client)

    assert policy["allowed_hosts"] == ["files.example.com", "api.truffles.kz"]


def test_allowed_media_url_uses_case_insensitive_host_match():
    assert media._is_allowed_media_url(
        "https://API.TRUFFLES.KZ/media/ref.jpg?sig=abc",
        ["api.truffles.kz"],
    )
