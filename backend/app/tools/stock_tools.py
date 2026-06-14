"""LangChain tools backed by whitelisted Tushare stock interfaces."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Callable

import pandas as pd
from langchain.tools import BaseTool, tool

from backend.app.model.schemas import (
    HistoryQueryInput,
    NewsQueryInput,
    StockQueryInput,
    ToolResult,
)
from backend.app.tools.stock_resolver import StockResolver
from backend.app.tools.tushare_client import TushareClient, to_ts_code

TUSHARE = TushareClient()
RESOLVER = StockResolver(TUSHARE)


def _records(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    """Convert a DataFrame into compact JSON-compatible records."""

    selected = frame.head(limit) if limit is not None else frame
    return json.loads(
        selected.to_json(orient="records", force_ascii=False, date_format="iso")
    )


def _error(source: str, error: Exception) -> str:
    result = ToolResult(
        ok=False,
        source=source,
        acquired_at=datetime.now(UTC).isoformat(),
        error=f"{type(error).__name__}: {error}",
    )
    return result.model_dump_json()


def _live_result(
    source: str,
    stock_query: str,
    loader: Callable[[], Any],
) -> str:
    try:
        stock = RESOLVER.resolve(stock_query)
        data = loader()
        return ToolResult(
            ok=True,
            source=source,
            acquired_at=datetime.now(UTC).isoformat(),
            stock=stock,
            data=data,
        ).model_dump_json()
    except Exception as error:
        return _error(source, error)


@tool(args_schema=StockQueryInput)
def resolve_stock(stock: str) -> str:
    """将 A 股名称或六位代码解析为标准股票代码和名称。"""

    try:
        resolved = RESOLVER.resolve(stock)
        return ToolResult(
            ok=True,
            source="stock_basic",
            acquired_at=datetime.now(UTC).isoformat(),
            stock=resolved,
            data=resolved.model_dump(),
        ).model_dump_json()
    except Exception as error:
        return _error("stock_basic", error)


@tool(args_schema=StockQueryInput)
def get_realtime_quote(stock: str) -> str:
    """查询 A 股最新行情快照。"""

    def loader() -> list[dict[str, Any]]:
        resolved = RESOLVER.resolve(stock)
        try:
            frame = TUSHARE.call("realtime_quote", ts_code=to_ts_code(resolved.code))
        except (AttributeError, TypeError):
            frame = TUSHARE.latest_basic(ts_code=to_ts_code(resolved.code))
        if frame.empty:
            raise ValueError(f"最新行情中未找到 {resolved.code}")
        return _records(frame, 10)

    return _live_result("realtime_quote", stock, loader)


@tool(args_schema=HistoryQueryInput)
def get_price_history(stock: str, days: int = 30, adjust: str = "") -> str:
    """查询 A 股最近若干自然日的日线历史行情，最多 365 天。"""

    del adjust

    def loader() -> list[dict[str, Any]]:
        resolved = RESOLVER.resolve(stock)
        frame = TUSHARE.daily(ts_code=to_ts_code(resolved.code), days=days)
        if frame.empty:
            raise ValueError(f"历史行情中未找到 {resolved.code}")
        return _records(frame.tail(60))

    return _live_result("daily", stock, loader)


@tool(args_schema=StockQueryInput)
def get_company_info(stock: str) -> str:
    """查询 A 股公司名称、行业、上市时间等基本信息。"""

    def loader() -> dict[str, Any]:
        resolved = RESOLVER.resolve(stock)
        frame = TUSHARE.stock_basic()
        matched = frame[frame["ts_code"].astype(str) == to_ts_code(resolved.code)]
        if matched.empty and "symbol" in frame.columns:
            matched = frame[frame["symbol"].astype(str).str.zfill(6) == resolved.code]
        if matched.empty:
            raise ValueError(f"公司信息中未找到 {resolved.code}")
        return _records(matched, 1)[0]

    return _live_result("stock_basic", stock, loader)


@tool(args_schema=NewsQueryInput)
def get_stock_news(stock: str, limit: int = 5) -> str:
    """查询市场最近新闻，并尽量筛选指定股票相关内容。"""

    def loader() -> list[dict[str, Any]]:
        resolved = RESOLVER.resolve(stock)
        frame = TUSHARE.call("news")
        if frame.empty:
            raise ValueError("Tushare 新闻接口未返回数据")
        columns = [column for column in ("title", "content") if column in frame.columns]
        if columns:
            mask = pd.Series(False, index=frame.index)
            for column in columns:
                values = frame[column].astype(str)
                mask = mask | values.str.contains(resolved.name, regex=False)
                mask = mask | values.str.contains(resolved.code, regex=False)
            frame = frame[mask]
        return _records(frame, limit)

    return _live_result("news", stock, loader)


@tool(args_schema=StockQueryInput)
def get_financial_indicators(stock: str) -> str:
    """查询 A 股最近财务分析指标，包括盈利、偿债和成长能力指标。"""

    def loader() -> list[dict[str, Any]]:
        resolved = RESOLVER.resolve(stock)
        frame = TUSHARE.call("fina_indicator", ts_code=to_ts_code(resolved.code))
        if frame.empty:
            raise ValueError(f"财务指标中未找到 {resolved.code}")
        return _records(frame.head(8))

    return _live_result("fina_indicator", stock, loader)


def get_stock_tools() -> list[BaseTool]:
    """Return the complete whitelist of stock tools."""

    return [
        resolve_stock,
        get_realtime_quote,
        get_price_history,
        get_company_info,
        get_stock_news,
        get_financial_indicators,
    ]
