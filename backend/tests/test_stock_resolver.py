"""Tests for backend.app.tools.stock_resolver."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from backend.app.tools.stock_resolver import StockResolver


def _mock_client_with_stocks() -> MagicMock:
    """Create a mock TushareClient with a basic stock list."""
    client = MagicMock()
    client.stock_basic.return_value = pd.DataFrame(
        {
            "ts_code": ["600519.SH", "000001.SZ", "300750.SZ"],
            "symbol": ["600519", "000001", "300750"],
            "name": ["贵州茅台", "平安银行", "宁德时代"],
        }
    )
    return client


class TestStockResolver:
    """Tests for StockResolver."""

    def test_resolve_by_code(self) -> None:
        client = _mock_client_with_stocks()
        resolver = StockResolver(tushare_client=client)
        result = resolver.resolve("600519")
        assert result.code == "600519"
        assert result.name == "贵州茅台"

    def test_resolve_by_exact_name(self) -> None:
        client = _mock_client_with_stocks()
        resolver = StockResolver(tushare_client=client)
        result = resolver.resolve("贵州茅台")
        assert result.code == "600519"
        assert result.name == "贵州茅台"

    def test_resolve_by_partial_name_unique(self) -> None:
        client = _mock_client_with_stocks()
        resolver = StockResolver(tushare_client=client)
        result = resolver.resolve("茅台")
        assert result.code == "600519"

    def test_resolve_unknown_raises(self) -> None:
        client = _mock_client_with_stocks()
        resolver = StockResolver(tushare_client=client)
        with pytest.raises(ValueError, match="未找到"):
            resolver.resolve("不存在的股票")

    def test_resolve_ambiguous_name_raises(self) -> None:
        client = MagicMock()
        client.stock_basic.return_value = pd.DataFrame(
            {
                "ts_code": ["600519.SH", "600520.SH"],
                "symbol": ["600519", "600520"],
                "name": ["贵州茅台", "茅台科技"],
            }
        )
        resolver = StockResolver(tushare_client=client)
        with pytest.raises(ValueError, match="不明确"):
            resolver.resolve("茅台")

    def test_resolve_code_not_in_list(self) -> None:
        client = _mock_client_with_stocks()
        resolver = StockResolver(tushare_client=client)
        result = resolver.resolve("999999")
        assert result.code == "999999"
        assert result.name == "999999"

    def test_resolve_strips_whitespace(self) -> None:
        client = _mock_client_with_stocks()
        resolver = StockResolver(tushare_client=client)
        result = resolver.resolve("  贵州茅台  ")
        assert result.code == "600519"

    def test_resolve_case_insensitive_name(self) -> None:
        # Chinese names don't have case, but test the casefold logic
        client = _mock_client_with_stocks()
        resolver = StockResolver(tushare_client=client)
        result = resolver.resolve("贵州茅台")
        assert result.code == "600519"

    def test_empty_stock_list_raises(self) -> None:
        from backend.app.tools.stock_resolver import _load_stock_list

        _load_stock_list.cache_clear()
        client = MagicMock()
        client.stock_basic.return_value = pd.DataFrame()
        resolver = StockResolver(tushare_client=client)
        # Use a name query (not a 6-digit code) to avoid the try/except in resolve()
        with pytest.raises(ValueError, match="为空"):
            resolver.resolve("贵州茅台")
