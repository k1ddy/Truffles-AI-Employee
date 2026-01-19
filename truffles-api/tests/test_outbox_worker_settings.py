from app import main


def test_outbox_worker_settings_parses_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "12")
    settings = main._get_outbox_worker_settings()
    assert settings[3] == 12


def test_outbox_worker_settings_clamps_negative_max_wait(monkeypatch):
    monkeypatch.setenv("OUTBOX_MAX_WAIT_SECONDS", "-5")
    settings = main._get_outbox_worker_settings()
    assert settings[3] == 0
