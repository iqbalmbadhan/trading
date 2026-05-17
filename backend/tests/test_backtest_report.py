"""Phase 8: report artifacts."""

from app.backtest.report import equity_svg, html_report, trades_csv


def test_equity_svg_has_polyline():
    svg = equity_svg([(0, 100.0), (1, 110.0), (2, 105.0)])
    assert "<svg" in svg and "<polyline" in svg


def test_equity_svg_empty_is_valid():
    svg = equity_svg([(0, 100.0)])
    assert svg.startswith("<svg") and "polyline" not in svg


def test_trades_csv_header_and_cumulative():
    csv = trades_csv([10.0, -4.0, 6.0])
    lines = csv.strip().splitlines()
    assert lines[0] == "trade,pnl,cumulative_pnl"
    assert lines[1].startswith("1,10.0")
    assert lines[-1].split(",")[2].startswith("12")


def test_html_report_contains_metrics():
    html = html_report("BT", {"sharpe": 1.23}, {"total_return_p50": 0.1}, [(0, 100.0), (1, 101.0)])
    assert "<html" in html and "sharpe" in html and "1.23" in html
