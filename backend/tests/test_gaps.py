"""Phase 4: gap detection for backfill."""

from app.market_data.gaps import expected_timestamps, find_gaps


def test_expected_timestamps_aligned():
    assert expected_timestamps(0, 180, "1m") == [0, 60, 120, 180]
    # start not aligned -> first expected is the next aligned open
    assert expected_timestamps(30, 180, "1m") == [60, 120, 180]


def test_no_gaps_when_all_present():
    existing = {0, 60, 120, 180}
    assert find_gaps(0, 180, "1m", existing) == []


def test_single_contiguous_gap():
    existing = {0, 180}
    assert find_gaps(0, 180, "1m", existing) == [(60, 120)]


def test_multiple_separated_gaps():
    existing = {0, 120, 240}
    # missing 60, 180, 300 -> three isolated single-bar gaps
    assert find_gaps(0, 300, "1m", existing) == [(60, 60), (180, 180), (300, 300)]


def test_everything_missing():
    assert find_gaps(0, 120, "1m", set()) == [(0, 120)]
