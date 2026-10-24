"""Pure forecast-versus-actual analysis helpers.

This module deliberately has no HTTP, API, or unit-conversion concerns.  It
operates only on mappings containing the field names verified for this project.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite, sqrt
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class MatchedPeriod:
    """One unambiguous forecast/actual pair for a delivery interval."""

    start_time: datetime
    publish_time: datetime
    forecast_generation: float
    actual_generation: float


@dataclass(frozen=True)
class AnalysisResult:
    """Pairs and aggregate errors; metrics are ``None`` when no pairs exist."""

    periods: tuple[MatchedPeriod, ...]
    mae: float | None
    rmse: float | None
    mean_forecast_bias: float | None
    skipped_forecasts: int
    skipped_actuals: int


def analyze_forecasts(
    forecasts: Sequence[Mapping[str, Any]],
    actuals: Sequence[Mapping[str, Any]],
    purchasing_decision_cutoff: datetime | str,
) -> AnalysisResult:
    """Select eligible forecasts and compare them to actuals.

    ``startTime`` is the delivery-interval key because it is the only verified
    delivery field common to the two supplied datasets.  All timestamps must be
    timezone-aware. Invalid records are omitted; ambiguous duplicate actuals or
    latest forecast versions are omitted rather than guessed.
    """

    cutoff = _parse_timestamp(purchasing_decision_cutoff, "purchasing_decision_cutoff")
    forecast_candidates: dict[datetime, list[tuple[datetime, float]]] = defaultdict(list)
    skipped_forecasts = 0

    for record in forecasts:
        try:
            start = _parse_timestamp(record["startTime"], "startTime")
            publish = _parse_timestamp(record["publishTime"], "publishTime")
            generation = _parse_generation(record["generation"])
        except (KeyError, TypeError, ValueError):
            skipped_forecasts += 1
            continue
        if publish <= cutoff:
            forecast_candidates[start].append((publish, generation))

    selected_forecasts: dict[datetime, tuple[datetime, float]] = {}
    for start, candidates in forecast_candidates.items():
        latest_publish = max(publish for publish, _ in candidates)
        latest = [(publish, value) for publish, value in candidates if publish == latest_publish]
        if len(latest) != 1:
            skipped_forecasts += len(latest)
            continue
        selected_forecasts[start] = latest[0]

    actual_candidates: dict[datetime, list[float]] = defaultdict(list)
    skipped_actuals = 0
    for record in actuals:
        try:
            start = _parse_timestamp(record["startTime"], "startTime")
            generation = _parse_generation(record["generation"])
        except (KeyError, TypeError, ValueError):
            skipped_actuals += 1
            continue
        actual_candidates[start].append(generation)

    unique_actuals: dict[datetime, float] = {}
    for start, candidates in actual_candidates.items():
        if len(candidates) != 1:
            skipped_actuals += len(candidates)
            continue
        unique_actuals[start] = candidates[0]

    periods = tuple(
        MatchedPeriod(
            start_time=start,
            publish_time=selected_forecasts[start][0],
            forecast_generation=selected_forecasts[start][1],
            actual_generation=unique_actuals[start],
        )
        for start in sorted(selected_forecasts.keys() & unique_actuals.keys())
    )
    errors = [period.forecast_generation - period.actual_generation for period in periods]

    return AnalysisResult(
        periods=periods,
        mae=sum(abs(error) for error in errors) / len(errors) if errors else None,
        rmse=sqrt(sum(error**2 for error in errors) / len(errors)) if errors else None,
        mean_forecast_bias=sum(errors) / len(errors) if errors else None,
        skipped_forecasts=skipped_forecasts,
        skipped_actuals=skipped_actuals,
    )


def _parse_timestamp(value: datetime | str, field_name: str) -> datetime:
    if isinstance(value, str):
        value = value.replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO 8601 timestamp") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _parse_generation(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("generation must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("generation must be numeric") from exc
    if not isfinite(parsed):
        raise ValueError("generation must be finite")
    return parsed
