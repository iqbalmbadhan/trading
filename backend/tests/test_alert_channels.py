"""Phase 11: notification channels."""

import pytest

import app.alerts.channels as channels
from app.alerts.channels import get_channel


async def test_telegram_posts_message(monkeypatch):
    calls = []

    async def _fake_post(url, payload):
        calls.append((url, payload))

    monkeypatch.setattr(channels, "_http_post", _fake_post)
    await get_channel("telegram").send("hello", {"bot_token": "T", "chat_id": "42"})
    url, payload = calls[0]
    assert url == "https://api.telegram.org/botT/sendMessage"
    assert payload == {"chat_id": "42", "text": "hello"}


async def test_webhook_posts_content(monkeypatch):
    calls = []

    async def _fake_post(url, payload):
        calls.append((url, payload))

    monkeypatch.setattr(channels, "_http_post", _fake_post)
    await get_channel("webhook").send("ping", {"url": "https://hook.test/x"})
    assert calls[0][0] == "https://hook.test/x"
    assert calls[0][1]["content"] == "ping"


async def test_email_uses_smtp(monkeypatch):
    sent = {}

    def _fake_smtp(host, port, user, password, msg):
        sent.update(host=host, port=port, to=msg["To"], body=msg.get_content())

    monkeypatch.setattr(channels, "_smtp_send", _fake_smtp)
    await get_channel("email").send(
        "body text",
        {"from": "a@x.com", "to": "b@y.com", "smtp_host": "smtp.test"},
    )
    assert sent["host"] == "smtp.test" and sent["to"] == "b@y.com"
    assert "body text" in sent["body"]


def test_unknown_channel_raises():
    with pytest.raises(ValueError):
        get_channel("carrier-pigeon")
