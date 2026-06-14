"""Tushare Pro client helpers for A-share tools."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import pandas as pd

TOKEN_ENV_VAR = "TUSHARE_TOKEN"


def to_ts_code(code: str) -> str:
    """Convert a six-digit A-share code into Tushare's ts_code format."""

    normalized = code.strip().upper()
    if "." in normalized:
        return normalized
    if normalized.startswith(("6", "9")):
        return f"{normalized}.SH"
    if normalized.startswith(("0", "2", "3")):
        return f"{normalized}.SZ"
    if normalized.startswith(("4", "8")):
        return f"{normalized}.BJ"
    return normalized


def from_ts_code(ts_code: str) -> str:
    """Return the six-digit symbol part from a Tushare ts_code."""

    return ts_code.split(".", maxsplit=1)[0].zfill(6)


def date_range_for_days(days: int) -> dict[str, str]:
    """Build Tushare start/end date parameters for recent natural days."""

    end = date.today()
    start = end - timedelta(days=days)
    return {
        "start_date": start.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
    }


class TushareClient:
    """Small wrapper around Tushare Pro with lazy import and token handling."""

    def __init__(self, token: str | None = None, pro_api: Any | None = None) -> None:
        self.token = token or os.environ.get(TOKEN_ENV_VAR)
        self._pro_api = pro_api

    @property
    def pro_api(self) -> Any:
        """Return a configured Tushare Pro API object."""

        if self._pro_api is not None:
            return self._pro_api
        if not self.token:
            raise RuntimeError(f"Missing {TOKEN_ENV_VAR} environment variable")

        try:
            import tushare as ts
        except ImportError as error:
            raise RuntimeError(
                "tushare is not installed. Run `uv sync` after updating pyproject.toml."
            ) from error

        ts.set_token(self.token)
        self._pro_api = ts.pro_api(self.token)
        return self._pro_api

    def call(self, endpoint: str, **params: Any) -> pd.DataFrame:
        """Call one Tushare endpoint by name."""

        function = getattr(self.pro_api, endpoint)
        call_params = {key: value for key, value in params.items() if value is not None}
        return function(**call_params)

    def stock_basic(self, **params: Any) -> pd.DataFrame:
        """Return the listed A-share code table."""

        fields = params.pop(
            "fields",
            "ts_code,symbol,name,area,industry,market,exchange,list_date",
        )
        return self.call(
            "stock_basic",
            exchange=params.pop("exchange", ""),
            list_status=params.pop("list_status", "L"),
            fields=fields,
            **params,
        )

    def daily(self, ts_code: str, days: int = 30, **params: Any) -> pd.DataFrame:
        """Return daily OHLCV data for a stock."""

        return self.call(
            "daily", ts_code=ts_code, **date_range_for_days(days), **params
        )

    def weekly(self, ts_code: str, days: int = 365, **params: Any) -> pd.DataFrame:
        """Return weekly OHLCV data for a stock."""

        return self.call(
            "weekly", ts_code=ts_code, **date_range_for_days(days), **params
        )

    def monthly(self, ts_code: str, days: int = 730, **params: Any) -> pd.DataFrame:
        """Return monthly OHLCV data for a stock."""

        return self.call(
            "monthly", ts_code=ts_code, **date_range_for_days(days), **params
        )

    def latest_basic(self, ts_code: str | None = None, **params: Any) -> pd.DataFrame:
        """Return the latest daily-basic records available to the token."""

        return self.call("daily_basic", ts_code=ts_code, **params)
