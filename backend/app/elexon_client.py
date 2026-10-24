"""Minimal client for the verified Elexon dataset paths.

The verified public endpoints can be requested without authentication.
"""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Callable
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ElexonClientError(RuntimeError):
    """Base error for Elexon client failures."""


class ElexonRequestError(ElexonClientError):
    """The request could not be completed."""


class ElexonHttpError(ElexonClientError):
    """The server returned a non-successful HTTP status."""


class ElexonResponseError(ElexonClientError):
    """The server returned a body that is not valid JSON."""


Transport = Callable[..., Any]


class ElexonClient:
    """Fetch verified Elexon paths without interpreting their response bodies.

    ``api_key`` is optional and read from ``ELEXON_API_KEY`` when not passed
    explicitly. Requests do not include authentication headers or query
    parameters, so they work with the verified public endpoints.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        transport: Transport = urlopen,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._base_url = base_url.rstrip("/")
        self._api_key = os.getenv("ELEXON_API_KEY") if api_key is None else api_key
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def get_wind_forecasts(self, publish_datetime_from: str, publish_datetime_to: str) -> Any:
        """Fetch WINDFOR using the verified publication-window parameters."""

        return self._get(
            "/bmrs/api/v1/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": publish_datetime_from,
                "publishDateTimeTo": publish_datetime_to,
            },
        )

    def get_wind_actuals(self, settlement_date_from: str) -> Any:
        """Fetch FUELHH actuals for the requested settlement date and WIND."""

        payload = self._get(
            "/bmrs/api/v1/datasets/FUELHH/stream",
            {"settlementDateFrom": settlement_date_from, "fuelType": "WIND"},
        )
        if not isinstance(payload, list):
            return payload

        requested_date = date.fromisoformat(settlement_date_from)
        return [
            record
            for record in payload
            if isinstance(record, dict) and _has_settlement_date(record, requested_date)
        ]

    def _get(self, path: str, query: dict[str, str]) -> Any:
        request = Request(f"{self._base_url}{path}?{urlencode(query)}", method="GET")
        try:
            response = self._transport(request, timeout=self._timeout_seconds)
            status = getattr(response, "status", response.getcode())
            if not 200 <= status < 300:
                raise ElexonHttpError(f"Elexon returned HTTP {status}")
            payload = response.read().decode("utf-8")
        except ElexonClientError:
            raise
        except HTTPError as exc:
            raise ElexonHttpError(f"Elexon returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise ElexonRequestError("Elexon request failed or timed out") from exc

        try:
            return json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ElexonResponseError("Elexon response was not valid JSON") from exc


def _has_settlement_date(record: dict[str, Any], requested_date: date) -> bool:
    """Accept only a verified, ISO-format settlementDate matching the request."""

    value = record.get("settlementDate")
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value) == requested_date
    except ValueError:
        return False
