"""Offline tests for the web API and Telegram webhook (no network, no keys)."""
from fastapi.testclient import TestClient

from app import api, config


def test_health_and_index():
    with TestClient(api.app) as c:
        assert c.get("/health").json()["ok"] is True
        assert c.get("/").status_code == 200


def test_webhook_off_without_public_url():
    with TestClient(api.app) as c:
        assert c.post("/telegram/webhook", json={}).status_code == 404


def test_webhook_rejects_wrong_secret_and_accepts_right_one(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "123:fake")
    processed = []

    class FakeApp:
        bot = None
        async def process_update(self, update):
            processed.append(update)
        async def stop(self): ...
        async def shutdown(self): ...

    from app.bot import webhook_secret
    with TestClient(api.app) as c:
        monkeypatch.setattr(api, "_tg_app", FakeApp())
        update = {"update_id": 1}
        assert c.post("/telegram/webhook", json=update).status_code == 403
        assert c.post("/telegram/webhook", json=update,
                      headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 403
        ok = c.post("/telegram/webhook", json=update,
                    headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret()})
        assert ok.status_code == 200
    assert len(processed) == 1


def test_explain_rejects_bad_file():
    with TestClient(api.app) as c:
        r = c.post("/api/explain", files={"file": ("x.txt", b"hello", "text/plain")}, data={"lang": "hi"})
        assert r.status_code == 400
