"""Route tests with a fake client; no Elexon requests are made."""

from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.elexon_client import ElexonRequestError
from app.main import create_app


class FakeClient:
    def __init__(self, forecasts: object, actuals: object) -> None:
        self.forecasts = forecasts
        self.actuals = actuals
        self.forecast_arguments: tuple[str, str] | None = None
        self.actual_argument: str | None = None

    def get_wind_forecasts(self, publish_datetime_from: str, publish_datetime_to: str) -> object:
        self.forecast_arguments = (publish_datetime_from, publish_datetime_to)
        return self.forecasts

    def get_wind_actuals(self, settlement_date_from: str) -> object:
        self.actual_argument = settlement_date_from
        return self.actuals


PARAMETERS = {
    "publish_datetime_from": datetime(2026, 1, 1, 6, tzinfo=timezone.utc),
    "publish_datetime_to": datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
    "settlement_date_from": date(2026, 1, 1),
    "purchasing_decision_cutoff": datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
}


def endpoint(app: object, path: str) -> object:
    return next(route.endpoint for route in app.routes if route.path == path)  # type: ignore[attr-defined]


def test_health_is_available_without_elexon_configuration() -> None:
    assert endpoint(create_app(), "/api/health")() == {"status": "ok"}  # type: ignore[operator]


def test_cors_preflight_allows_the_local_frontend_origin() -> None:
    messages = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "OPTIONS",
        "scheme": "http",
        "path": "/api/health",
        "raw_path": b"/api/health",
        "query_string": b"",
        "headers": [
            (b"origin", b"http://localhost:5173"),
            (b"access-control-request-method", b"GET"),
            (b"access-control-request-headers", b"content-type"),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }

    _complete_coroutine(create_app()(scope, receive, send))

    headers = dict(messages[0]["headers"])
    assert headers[b"access-control-allow-origin"] == b"http://localhost:5173"
    assert headers[b"access-control-allow-methods"] == b"GET"


def _complete_coroutine(coroutine: object) -> None:
    """Run an immediately-completing ASGI preflight without a network server."""

    try:
        while True:
            coroutine.send(None)  # type: ignore[attr-defined]
    except StopIteration:
        pass


def test_summary_delegates_to_client_and_analysis() -> None:
    fake = FakeClient(
        [
            {"publishTime": "2026-01-01T07:00:00Z", "startTime": "2026-01-01T10:00:00Z", "generation": 12},
            {"publishTime": "2026-01-01T08:00:00Z", "startTime": "2026-01-01T10:00:00Z", "generation": 11},
        ],
        [{"startTime": "2026-01-01T10:00:00Z", "generation": 9}],
    )
    response = endpoint(create_app(lambda: fake), "/api/summary")(client=fake, **PARAMETERS)  # type: ignore[operator]

    assert response == {
        "mae": 2.0,
        "rmse": 2.0,
        "meanForecastBias": 2.0,
        "matchedIntervalCount": 1,
        "periods": [
            {
                "startTime": "2026-01-01T10:00:00+00:00",
                "publishTime": "2026-01-01T08:00:00+00:00",
                "forecastGeneration": 11.0,
                "actualGeneration": 9.0,
            }
        ],
    }
    assert fake.forecast_arguments == ("2026-01-01T06:00:00+00:00", "2026-01-01T08:00:00+00:00")
    assert fake.actual_argument == "2026-01-01"


def test_series_and_periods_include_period_level_data() -> None:
    fake = FakeClient(
        [{"publishTime": "2026-01-01T07:00:00Z", "startTime": "2026-01-01T10:00:00Z", "generation": 3}],
        [{"startTime": "2026-01-01T10:00:00Z", "generation": 2}],
    )
    app = create_app(lambda: fake)

    series = endpoint(app, "/api/series")(client=fake, **PARAMETERS)  # type: ignore[operator]
    periods = endpoint(app, "/api/periods")(client=fake, **PARAMETERS)  # type: ignore[operator]

    assert "series" in series
    assert "periods" in periods
    assert series["matchedIntervalCount"] == periods["matchedIntervalCount"] == 1


def test_invalid_range_and_naive_cutoff_are_rejected() -> None:
    fake = FakeClient([], [])
    handler = endpoint(create_app(lambda: fake), "/api/summary")

    with pytest.raises(HTTPException) as backwards:
        handler(client=fake, **{**PARAMETERS, "publish_datetime_from": datetime(2026, 1, 1, 9, tzinfo=timezone.utc)})  # type: ignore[operator]
    with pytest.raises(HTTPException) as naive:
        handler(client=fake, **{**PARAMETERS, "purchasing_decision_cutoff": datetime(2026, 1, 1, 8)})  # type: ignore[operator]

    assert backwards.value.status_code == naive.value.status_code == 422


def test_empty_data_is_an_explicit_empty_analysis() -> None:
    fake = FakeClient([], [])
    response = endpoint(create_app(lambda: fake), "/api/summary")(client=fake, **PARAMETERS)  # type: ignore[operator]

    assert response["matchedIntervalCount"] == 0
    assert response["mae"] is None


def test_upstream_failures_and_unconfigured_response_envelope_are_clear() -> None:
    class FailingClient:
        def get_wind_forecasts(self, *_args: str) -> object:
            raise ElexonRequestError("synthetic failure")

        def get_wind_actuals(self, *_args: str) -> object:
            raise AssertionError("should not be called")

    with pytest.raises(HTTPException) as failure:
        endpoint(create_app(lambda: FailingClient()), "/api/summary")(client=FailingClient(), **PARAMETERS)  # type: ignore[operator]
    malformed_client = FakeClient({"data": []}, [])
    with pytest.raises(HTTPException) as envelope:
        endpoint(create_app(lambda: malformed_client), "/api/summary")(client=malformed_client, **PARAMETERS)  # type: ignore[operator]

    assert failure.value.status_code == envelope.value.status_code == 502
