"""Synthetic fixtures only; values are not Elexon data."""

from datetime import datetime, timedelta, timezone

import pytest

from app.analysis import analyze_forecasts


UTC = timezone.utc


def stamp(hour: int) -> datetime:
    return datetime(2026, 1, 1, hour, tzinfo=UTC)


def forecast(start: int, published: int, generation: object) -> dict[str, object]:
    return {"publishTime": stamp(published), "startTime": stamp(start), "generation": generation}


def actual(start: int, generation: object) -> dict[str, object]:
    return {"startTime": stamp(start), "generation": generation}


def test_cutoff_is_inclusive_and_selects_latest_eligible_version() -> None:
    result = analyze_forecasts(
        [forecast(10, 7, 10), forecast(10, 8, 11), forecast(10, 9, 12)],
        [actual(10, 9)],
        stamp(8),
    )

    assert len(result.periods) == 1
    assert result.periods[0].publish_time == stamp(8)
    assert result.periods[0].forecast_generation == 11


def test_forecasts_after_cutoff_are_not_used() -> None:
    result = analyze_forecasts([forecast(10, 9, 12)], [actual(10, 9)], stamp(8))

    assert result.periods == ()
    assert result.mae is None


def test_matches_only_equal_delivery_start_times_and_calculates_metrics() -> None:
    result = analyze_forecasts(
        [forecast(10, 7, 12), forecast(11, 7, 6)],
        [actual(10, 10), actual(11, 10), actual(12, 99)],
        stamp(8),
    )

    assert [period.start_time for period in result.periods] == [stamp(10), stamp(11)]
    assert result.mae == pytest.approx(3)
    assert result.rmse == pytest.approx((10**0.5))
    assert result.mean_forecast_bias == pytest.approx(-1)


def test_missing_invalid_and_duplicate_actuals_are_not_replaced_with_zero() -> None:
    result = analyze_forecasts(
        [forecast(10, 7, 5), forecast(11, 7, 7), forecast(12, 7, 9)],
        [actual(10, None), actual(11, 6), actual(11, 6)],
        stamp(8),
    )

    assert result.periods == ()
    assert result.skipped_actuals == 3


def test_duplicate_latest_forecast_and_naive_timestamps_are_excluded() -> None:
    result = analyze_forecasts(
        [forecast(10, 7, 5), forecast(10, 7, 6), {"publishTime": stamp(7), "startTime": datetime(2026, 1, 1, 11), "generation": 1}],
        [actual(10, 5)],
        stamp(8),
    )

    assert result.periods == ()
    assert result.skipped_forecasts == 3


def test_cutoff_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        analyze_forecasts([], [], datetime(2026, 1, 1, 8))


def test_timezone_aware_delivery_times_are_normalized_before_matching() -> None:
    plus_one = timezone(timedelta(hours=1))
    result = analyze_forecasts(
        [{"publishTime": stamp(7), "startTime": stamp(10), "generation": 5}],
        [{"startTime": datetime(2026, 1, 1, 11, tzinfo=plus_one), "generation": 4}],
        stamp(8),
    )

    assert len(result.periods) == 1
    assert result.mae == 1
