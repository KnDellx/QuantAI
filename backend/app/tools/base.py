"""Controlled Tushare wrapper execution and normalization."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, Callable

import pandas as pd

from backend.app.docs_index.schemas import ToolDocument
from backend.app.model.schemas import ToolError, ToolResult
from backend.app.tools.stock_resolver import StockResolver
from backend.app.tools.tushare_client import TushareClient, to_ts_code


def normalize_data(value: Any, limit: int = 100) -> Any:
    """Convert common Tushare return values into compact JSON-compatible data."""

    if isinstance(value, pd.DataFrame):
        return json.loads(
            value.head(limit).to_json(
                orient="records", force_ascii=False, date_format="iso"
            )
        )
    if isinstance(value, pd.Series):
        return json.loads(value.to_json(force_ascii=False, date_format="iso"))
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class TushareWrapper:
    """Execute one whitelisted Tushare interface behind a stable contract."""

    def __init__(
        self,
        document: ToolDocument,
        resolver: StockResolver,
        tushare_client: TushareClient | None = None,
    ) -> None:
        self.document = document
        self.resolver = resolver
        self.tushare = tushare_client or TushareClient()

    def invoke(self, **params: Any) -> str:
        """Validate, execute, and normalize one wrapper call."""

        cleaned = {key: value for key, value in params.items() if value is not None}
        source = self.document.source_interfaces[0]
        try:
            data = self._execute(cleaned)
            return ToolResult(
                ok=True,
                tool_name=self.document.tool_name,
                source=source,
                params=cleaned,
                data=data,
                acquired_at=datetime.now(UTC).isoformat(),
            ).model_dump_json()
        except Exception as error:
            return ToolResult(
                ok=False,
                tool_name=self.document.tool_name,
                source=source,
                params=cleaned,
                acquired_at=datetime.now(UTC).isoformat(),
                error=ToolError(
                    code=self._error_code(error),
                    message=f"{type(error).__name__}: {error}",
                    retryable=isinstance(error, (ConnectionError, TimeoutError)),
                ),
            ).model_dump_json()

    def _execute(self, params: dict[str, Any]) -> Any:
        mode_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "resolve_stock": self._resolve_stock,
            "realtime_quote": self._realtime_quote,
            "history": self._history,
            "company": self._company,
            "news": self._news,
            "financial": self._financial,
        }
        handler = mode_handlers.get(self.document.mode)
        if handler is not None:
            return handler(params)

        endpoint = self.document.source_interfaces[0]
        return normalize_data(self._call_endpoint(endpoint, params))

    def _resolve_stock(self, params: dict[str, Any]) -> Any:
        return self.resolver.resolve(str(params["stock"])).model_dump()

    def _realtime_quote(self, params: dict[str, Any]) -> Any:
        stock = self.resolver.resolve(str(params["stock"]))
        try:
            frame = self._call_endpoint("realtime_quote", {"stock": stock.code})
        except (AttributeError, TypeError):
            frame = pd.DataFrame()
        if frame.empty:
            frame = self.tushare.latest_basic(ts_code=to_ts_code(stock.code))
        return normalize_data(frame, 10)

    def _history(self, params: dict[str, Any]) -> Any:
        stock = self.resolver.resolve(str(params["stock"]))
        days = int(params.get("days", 30))
        endpoint = self.document.source_interfaces[0]
        period = str(params.get("period", "")).casefold()
        if period == "weekly":
            endpoint = "weekly"
        if period == "monthly":
            endpoint = "monthly"
        frame = self._call_endpoint(
            endpoint,
            {"stock": stock.code, "days": days, "adjust": params.get("adjust")},
        )
        return normalize_data(frame.tail(100))

    def _company(self, params: dict[str, Any]) -> Any:
        stock = self.resolver.resolve(str(params["stock"]))
        frame = self.tushare.stock_basic()
        matched = frame[frame["ts_code"].astype(str) == to_ts_code(stock.code)]
        if matched.empty and "symbol" in frame.columns:
            matched = frame[frame["symbol"].astype(str).str.zfill(6) == stock.code]
        if matched.empty:
            raise ValueError(f"公司信息中未找到 {stock.code}")
        return normalize_data(matched, 1)[0]

    def _news(self, params: dict[str, Any]) -> Any:
        stock = self.resolver.resolve(str(params["stock"]))
        limit = int(params.get("limit", 5))
        frame = self._call_endpoint("news", {})
        if frame.empty:
            raise ValueError(f"新闻中未找到 {stock.code}")
        text_columns = [
            column
            for column in ("title", "content", "新闻标题", "新闻内容")
            if column in frame.columns
        ]
        if text_columns:
            mask = pd.Series(False, index=frame.index)
            for column in text_columns:
                values = frame[column].astype(str)
                mask = mask | values.str.contains(stock.name, regex=False)
                mask = mask | values.str.contains(stock.code, regex=False)
            frame = frame[mask]
        return normalize_data(frame, limit)

    def _financial(self, params: dict[str, Any]) -> Any:
        stock = self.resolver.resolve(str(params["stock"]))
        start_year = str(params.get("start_year", date.today().year - 2))
        frame = self._call_endpoint(
            "fina_indicator",
            {"stock": stock.code, "start_date": f"{start_year}0101"},
        )
        return normalize_data(frame, 20)

    def _call_endpoint(self, endpoint: str, params: dict[str, Any]) -> pd.DataFrame:
        call_params = self._to_tushare_params(params)
        if endpoint == "stock_basic":
            return self.tushare.stock_basic(**call_params)
        if endpoint == "daily":
            return self.tushare.daily(**call_params)
        if endpoint == "weekly":
            return self.tushare.weekly(**call_params)
        if endpoint == "monthly":
            return self.tushare.monthly(**call_params)
        if endpoint == "daily_basic":
            return self.tushare.latest_basic(**call_params)
        return self.tushare.call(endpoint, **call_params)

    @staticmethod
    def _to_tushare_params(params: dict[str, Any]) -> dict[str, Any]:
        call_params = dict(params)
        stock = call_params.pop("stock", None)
        symbol = call_params.pop("symbol", None)
        if stock is not None:
            call_params.setdefault("ts_code", to_ts_code(str(stock)))
        if symbol is not None:
            call_params.setdefault("ts_code", to_ts_code(str(symbol)))

        date_value = call_params.pop("date", None)
        if date_value is not None:
            call_params.setdefault("trade_date", str(date_value))

        days = call_params.pop("days", None)
        call_params.pop("period", None)
        call_params.pop("adjust", None)
        if days is not None:
            call_params["days"] = int(days)
        return call_params

    @staticmethod
    def _error_code(error: Exception) -> str:
        if isinstance(error, (ConnectionError, TimeoutError)):
            return "UPSTREAM_UNAVAILABLE"
        if isinstance(error, (KeyError, TypeError, ValueError)):
            return "INVALID_REQUEST"
        if isinstance(error, (ImportError, RuntimeError)):
            return "CONFIGURATION_ERROR"
        return "TOOL_EXECUTION_FAILED"
