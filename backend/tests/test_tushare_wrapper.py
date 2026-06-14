"""Tests for backend.app.tools.base (TushareWrapper)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd

from backend.app.docs_index.schemas import ToolDocument, ToolParameter, ToolReturn
from backend.app.model.schemas import StockRef
from backend.app.tools.base import TushareWrapper, normalize_data
from backend.app.tools.stock_resolver import StockResolver


def _make_document(**overrides) -> ToolDocument:
    defaults = dict(
        tool_name="get_stock_daily_history",
        category="stock_history",
        description="查询日线行情",
        params={
            "stock": ToolParameter(type="string", required=True, description="code"),
        },
        returns=ToolReturn(description="行情数据"),
        example_query=["贵州茅台日线"],
        source_interfaces=["daily"],
        mode="history",
    )
    defaults.update(overrides)
    return ToolDocument(**defaults)


def _mock_resolver() -> MagicMock:
    resolver = MagicMock(spec=StockResolver)
    resolver.resolve.return_value = StockRef(code="600519", name="贵州茅台")
    return resolver


class TestNormalizeData:
    """Tests for normalize_data helper."""

    def test_dataframe(self) -> None:
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        result = normalize_data(df)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_dataframe_limit(self) -> None:
        df = pd.DataFrame({"a": range(200)})
        result = normalize_data(df, limit=10)
        assert len(result) == 10

    def test_series(self) -> None:
        series = pd.Series([1, 2, 3], name="val")
        result = normalize_data(series)
        assert isinstance(result, dict)

    def test_primitive(self) -> None:
        result = normalize_data(42)
        assert result == 42

    def test_dict(self) -> None:
        result = normalize_data({"key": "value"})
        assert result == {"key": "value"}


class TestTushareWrapper:
    """Tests for TushareWrapper."""

    def test_invoke_success(self) -> None:
        doc = _make_document(mode="resolve_stock")
        resolver = _mock_resolver()
        client = MagicMock()
        wrapper = TushareWrapper(doc, resolver, tushare_client=client)

        result_json = wrapper.invoke(stock="贵州茅台")
        import json

        result = json.loads(result_json)
        assert result["ok"] is True
        assert result["tool_name"] == "get_stock_daily_history"

    def test_invoke_error_handling(self) -> None:
        doc = _make_document(mode="resolve_stock")
        resolver = MagicMock(spec=StockResolver)
        resolver.resolve.side_effect = ValueError("test error")
        client = MagicMock()
        wrapper = TushareWrapper(doc, resolver, tushare_client=client)

        result_json = wrapper.invoke(stock="bad")
        import json

        result = json.loads(result_json)
        assert result["ok"] is False
        assert result["error"]["code"] == "INVALID_REQUEST"

    def test_invoke_filters_none_params(self) -> None:
        doc = _make_document(mode="resolve_stock")
        resolver = _mock_resolver()
        client = MagicMock()
        wrapper = TushareWrapper(doc, resolver, tushare_client=client)

        result_json = wrapper.invoke(stock="贵州茅台", unused=None)
        import json

        result = json.loads(result_json)
        assert "unused" not in result["params"]

    def test_generic_mode_falls_through(self) -> None:
        doc = _make_document(mode="generic", source_interfaces=["stock_basic"])
        resolver = _mock_resolver()
        client = MagicMock()
        client.stock_basic.return_value = pd.DataFrame(
            {"ts_code": ["600519.SH"], "name": ["贵州茅台"]}
        )
        wrapper = TushareWrapper(doc, resolver, tushare_client=client)

        result_json = wrapper.invoke(stock="贵州茅台")
        import json

        result = json.loads(result_json)
        assert result["ok"] is True
