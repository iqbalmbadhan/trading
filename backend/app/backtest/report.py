"""Backtest artifacts: inline SVG equity curve, CSV trades, HTML report."""

from __future__ import annotations

import csv
import html
import io


def equity_svg(equity_curve: list[tuple[int, float]], width: int = 720, height: int = 240) -> str:
    if len(equity_curve) < 2:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"></svg>'
    values = [e for _, e in equity_curve]
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = i / (n - 1) * (width - 20) + 10
        y = height - 10 - (v - lo) / span * (height - 20)
        pts.append(f"{x:.1f},{y:.1f}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="{width}" height="{height}" fill="#0a0a0a"/>'
        f'<polyline fill="none" stroke="#34d399" stroke-width="2" points="{" ".join(pts)}"/>'
        f"</svg>"
    )


def trades_csv(trade_pnls: list[float]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["trade", "pnl", "cumulative_pnl"])
    cum = 0.0
    for i, pnl in enumerate(trade_pnls, start=1):
        cum += pnl
        writer.writerow([i, f"{pnl:.6f}", f"{cum:.6f}"])
    return buf.getvalue()


def html_report(
    title: str,
    metrics: dict[str, float],
    monte_carlo: dict[str, float],
    equity_curve: list[tuple[int, float]],
) -> str:
    def rows(d: dict[str, float]) -> str:
        return "".join(f"<tr><td>{html.escape(k)}</td><td>{v:.6g}</td></tr>" for k, v in d.items())

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{background:#0a0a0a;color:#e5e5e5;font-family:system-ui;margin:24px}}
table{{border-collapse:collapse;margin:12px 0}}
td{{border:1px solid #333;padding:4px 10px}}
h2{{color:#a3a3a3}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div>{equity_svg(equity_curve)}</div>
<h2>Metrics</h2><table>{rows(metrics)}</table>
<h2>Monte Carlo</h2><table>{rows(monte_carlo)}</table>
</body></html>"""
