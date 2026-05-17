"""Prometheus metrics: HTTP instrumentation + domain counters."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

ORDERS_PLACED = Counter("orders_placed_total", "Orders submitted through the router", ["mode"])
SIGNALS_RECORDED = Counter("signals_recorded_total", "Strategy signals persisted")
KILL_SWITCH_TRIPS = Counter("kill_switch_trips_total", "Global kill-switch trips")
STRATEGY_STARTS = Counter("strategy_starts_total", "Strategy runs started")
