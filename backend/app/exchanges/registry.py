"""Factory that builds connector instances from credentials."""

from app.exchanges.base import BaseExchange
from app.exchanges.ccxt_adapter import CCXTExchange

PAPER = "paper"


def build_exchange(exchange_id: str, api_key: str, secret: str) -> BaseExchange:
    """Build a live/credentialed connector.

    The paper connector is constructed separately because it needs a live
    price source rather than private credentials.
    """
    return CCXTExchange(exchange_id, api_key, secret)
