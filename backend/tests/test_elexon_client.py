"""Network-free tests for the Elexon HTTP client."""

import json
from urllib.parse import parse_qs, urlparse

import pytest

from app.elexon_client import ElexonClient, ElexonHttpError, ElexonRequestError, ElexonResponseError


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def getcode(self) -> int:
        return self.status

    def read(self) -> bytes:
        return self._body


def test_wind_forecasts_uses_only_verified_query_parameters() -> None:
    captured = {}

    def transport(request: object, *, timeout: float) -> FakeResponse:
        captured["url"] = request.full_url  # type: ignore[attr-defined]
        captured["timeout"] = timeout
        return FakeResponse(json.dumps([{"startTime": "synthetic"}]).encode())

    client = ElexonClient("https://example.test", timeout_seconds=4, transport=transport)
    result = client.get_wind_forecasts("from-value", "to-value")

    parsed = urlparse(captured["url"])
    assert parsed.path == "/bmrs/api/v1/datasets/WINDFOR/stream"
    assert parse_qs(parsed.query) == {"publishDateTimeFrom": ["from-value"], "publishDateTimeTo": ["to-value"]}
    assert captured["timeout"] == 4
    assert result == [{"startTime": "synthetic"}]


def test_wind_actuals_uses_verified_wind_filter() -> None:
    def transport(request: object, *, timeout: float) -> FakeResponse:
        assert urlparse(request.full_url).path == "/bmrs/api/v1/datasets/FUELHH/stream"  # type: ignore[attr-defined]
        assert parse_qs(urlparse(request.full_url).query) == {"settlementDateFrom": ["date-value"], "fuelType": ["WIND"]}  # type: ignore[attr-defined]
        return FakeResponse(b"{}")

    assert ElexonClient("https://example.test", transport=transport).get_wind_actuals("date-value") == {}


def test_wind_actuals_retains_only_valid_records_for_the_requested_settlement_date() -> None:
    payload = [
        {"settlementDate": "2026-01-14", "startTime": "previous"},
        {"settlementDate": "2026-01-15", "startTime": "retained"},
        {"settlementDate": "2026-01-16", "startTime": "next"},
        {"settlementDate": "not-a-date", "startTime": "malformed"},
        {"startTime": "missing-date"},
        "not-a-record",
    ]

    client = ElexonClient(
        "https://example.test",
        transport=lambda *_args, **_kwargs: FakeResponse(json.dumps(payload).encode()),
    )

    assert client.get_wind_actuals("2026-01-15") == [{"settlementDate": "2026-01-15", "startTime": "retained"}]


def test_reads_api_key_from_environment_without_putting_it_in_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEXON_API_KEY", "test-key")

    def transport(request: object, *, timeout: float) -> FakeResponse:
        assert "test-key" not in request.full_url  # type: ignore[attr-defined]
        assert request.headers == {}  # type: ignore[attr-defined]
        return FakeResponse(b"[]")

    ElexonClient("https://example.test", transport=transport).get_wind_actuals("2026-01-15")


def test_unauthenticated_request_has_no_authentication_header_or_query_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ELEXON_API_KEY", raising=False)

    def transport(request: object, *, timeout: float) -> FakeResponse:
        assert "api" not in parse_qs(urlparse(request.full_url).query)
        assert request.headers == {}  # type: ignore[attr-defined]
        return FakeResponse(b"[]")

    assert ElexonClient("https://example.test", transport=transport).get_wind_actuals("2026-01-15") == []


def test_non_success_status_raises_clear_error() -> None:
    with pytest.raises(ElexonHttpError, match="HTTP 503"):
        ElexonClient("https://example.test", transport=lambda *_args, **_kwargs: FakeResponse(b"{}", 503)).get_wind_actuals("date-value")


def test_timeout_raises_clear_error() -> None:
    def transport(*_args: object, **_kwargs: object) -> FakeResponse:
        raise TimeoutError

    with pytest.raises(ElexonRequestError, match="timed out"):
        ElexonClient("https://example.test", transport=transport).get_wind_actuals("date-value")


def test_malformed_json_raises_clear_error() -> None:
    with pytest.raises(ElexonResponseError, match="valid JSON"):
        ElexonClient("https://example.test", transport=lambda *_args, **_kwargs: FakeResponse(b"not-json")).get_wind_actuals("date-value")
