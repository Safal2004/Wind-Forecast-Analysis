"""FastAPI endpoints for wind forecast analysis."""

from __future__ import annotations

import os
import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Protocol

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.analysis import AnalysisResult, analyze_forecasts
from app.elexon_client import ElexonClient, ElexonClientError


logger = logging.getLogger(__name__)


class WindDataClient(Protocol):
    def get_wind_forecasts(self, publish_datetime_from: str, publish_datetime_to: str) -> Any: ...

    def get_wind_actuals(self, settlement_date_from: str) -> Any: ...


def get_elexon_client() -> ElexonClient:
    """Create a client for the public Elexon Insights base URL by default."""

    base_url = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk")
    return ElexonClient(base_url)


def create_app(client_provider: Callable[[], WindDataClient] = get_elexon_client) -> FastAPI:
    app = FastAPI(title="Wind forecast analysis API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/summary")
    def summary(
        publish_datetime_from: datetime = Query(),
        publish_datetime_to: datetime = Query(),
        settlement_date_from: date = Query(),
        purchasing_decision_cutoff: datetime = Query(),
        client: WindDataClient = Depends(client_provider),
    ) -> dict[str, Any]:
        return _analyze_request(
            client,
            publish_datetime_from,
            publish_datetime_to,
            settlement_date_from,
            purchasing_decision_cutoff,
        )

    @app.get("/api/series")
    def series(
        publish_datetime_from: datetime = Query(),
        publish_datetime_to: datetime = Query(),
        settlement_date_from: date = Query(),
        purchasing_decision_cutoff: datetime = Query(),
        client: WindDataClient = Depends(client_provider),
    ) -> dict[str, Any]:
        result = _analyze_request(
            client,
            publish_datetime_from,
            publish_datetime_to,
            settlement_date_from,
            purchasing_decision_cutoff,
        )
        result["series"] = result.pop("periods")
        return result

    @app.get("/api/periods")
    def periods(
        publish_datetime_from: datetime = Query(),
        publish_datetime_to: datetime = Query(),
        settlement_date_from: date = Query(),
        purchasing_decision_cutoff: datetime = Query(),
        client: WindDataClient = Depends(client_provider),
    ) -> dict[str, Any]:
        return _analyze_request(
            client,
            publish_datetime_from,
            publish_datetime_to,
            settlement_date_from,
            purchasing_decision_cutoff,
        )

    return app


def _analyze_request(
    client: WindDataClient,
    publish_datetime_from: datetime,
    publish_datetime_to: datetime,
    settlement_date_from: date,
    purchasing_decision_cutoff: datetime,
) -> dict[str, Any]:
    _validate_parameters(publish_datetime_from, publish_datetime_to, purchasing_decision_cutoff)
    try:
        forecasts = client.get_wind_forecasts(publish_datetime_from.isoformat(), publish_datetime_to.isoformat())
        actuals = client.get_wind_actuals(settlement_date_from.isoformat())
    except ElexonClientError as exc:
        raise HTTPException(status_code=502, detail="Unable to retrieve Elexon data") from exc

    if not isinstance(forecasts, list) or not isinstance(actuals, list):
        raise HTTPException(
            status_code=502,
            detail="Elexon response structure is not a record list; its envelope is not yet configured",
        )

    result = analyze_forecasts(forecasts, actuals, purchasing_decision_cutoff)
    settlement_day_actuals = sum(
        1
        for record in actuals
        if isinstance(record, dict) and record.get("settlementDate") == settlement_date_from.isoformat()
    )
    logger.info(
        "Wind analysis: raw WINDFOR=%d, raw FUELHH=%d, FUELHH for settlement date=%d, "
        "matched=%d, skipped forecasts=%d, skipped actuals=%d",
        len(forecasts),
        len(actuals),
        settlement_day_actuals,
        len(result.periods),
        result.skipped_forecasts,
        result.skipped_actuals,
    )
    return _serialize_result(result)


def _validate_parameters(
    publish_datetime_from: datetime,
    publish_datetime_to: datetime,
    purchasing_decision_cutoff: datetime,
) -> None:
    if publish_datetime_from.tzinfo is None or publish_datetime_from.utcoffset() is None:
        raise HTTPException(status_code=422, detail="publish_datetime_from must be timezone-aware")
    if publish_datetime_to.tzinfo is None or publish_datetime_to.utcoffset() is None:
        raise HTTPException(status_code=422, detail="publish_datetime_to must be timezone-aware")
    if purchasing_decision_cutoff.tzinfo is None or purchasing_decision_cutoff.utcoffset() is None:
        raise HTTPException(status_code=422, detail="purchasing_decision_cutoff must be timezone-aware")
    if publish_datetime_from > publish_datetime_to:
        raise HTTPException(status_code=422, detail="publish_datetime_from must not be after publish_datetime_to")


def _serialize_result(result: AnalysisResult) -> dict[str, Any]:
    periods = [
        {
            "startTime": period.start_time.isoformat(),
            "publishTime": period.publish_time.isoformat(),
            "forecastGeneration": period.forecast_generation,
            "actualGeneration": period.actual_generation,
        }
        for period in result.periods
    ]
    return {
        "mae": result.mae,
        "rmse": result.rmse,
        "meanForecastBias": result.mean_forecast_bias,
        "matchedIntervalCount": len(result.periods),
        "periods": periods,
    }


app = create_app()
