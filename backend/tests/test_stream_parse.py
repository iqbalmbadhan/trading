"""Phase 4: Binance kline message parsing."""

import json

from app.market_data.stream import parse_binance_kline


def _msg(closed: bool) -> dict:
    return {
        "s": "BTCUSDT",
        "k": {
            "t": 1_700_000_000_000,
            "o": "100.0",
            "h": "110.0",
            "l": "95.0",
            "c": "105.0",
            "v": "12.5",
            "x": closed,
        },
    }


def test_unfinished_kline_ignored():
    assert parse_binance_kline(_msg(closed=False)) is None


def test_finished_kline_normalized_from_json_string():
    candle = parse_binance_kline(json.dumps(_msg(closed=True)))
    assert candle == {
        "symbol": "BTCUSDT",
        "ts": 1_700_000_000,
        "o": 100.0,
        "h": 110.0,
        "l": 95.0,
        "c": 105.0,
        "v": 12.5,
    }


def test_non_kline_message_ignored():
    assert parse_binance_kline({"e": "ping"}) is None
