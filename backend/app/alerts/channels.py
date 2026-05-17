"""Notification delivery channels.

Network/SMTP calls go through small module-level helpers so tests can
substitute them without real I/O. Each channel maps a config dict +
message to a delivery.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx


async def _http_post(url: str, payload: dict) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()


def _smtp_send(host: str, port: int, user: str, password: str, msg: EmailMessage) -> None:
    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        if user:
            server.login(user, password)
        server.send_message(msg)


class Channel(Protocol):
    name: str

    async def send(self, message: str, config: dict) -> None: ...


class TelegramChannel:
    name = "telegram"

    async def send(self, message: str, config: dict) -> None:
        token = config["bot_token"]
        await _http_post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            {"chat_id": config["chat_id"], "text": message},
        )


class WebhookChannel:
    """Discord/Slack-compatible: posts ``{"content": message}``."""

    name = "webhook"

    async def send(self, message: str, config: dict) -> None:
        await _http_post(config["url"], {"content": message, "text": message})


class EmailChannel:
    name = "email"

    async def send(self, message: str, config: dict) -> None:
        msg = EmailMessage()
        msg["Subject"] = config.get("subject", "Trading Bot Alert")
        msg["From"] = config["from"]
        msg["To"] = config["to"]
        msg.set_content(message)
        _smtp_send(
            config["smtp_host"],
            int(config.get("smtp_port", 587)),
            config.get("smtp_user", ""),
            config.get("smtp_password", ""),
            msg,
        )


_CHANNELS: dict[str, Channel] = {
    c.name: c for c in (TelegramChannel(), WebhookChannel(), EmailChannel())
}


def get_channel(name: str) -> Channel:
    try:
        return _CHANNELS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown channel '{name}'") from exc
