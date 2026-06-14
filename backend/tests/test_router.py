"""Tests for backend.app.docs_index.router."""

from __future__ import annotations

import pytest

from backend.app.docs_index.router import ToolRouter
from backend.app.docs_index.schemas import ToolDocument, ToolReturn


def _make_tool(name: str, category: str, description: str, **kw) -> ToolDocument:
    defaults = dict(
        params={},
        returns=ToolReturn(description="data"),
        example_query=[],
        source_interfaces=["ep"],
    )
    defaults.update(kw)
    return ToolDocument(
        tool_name=name,
        category=category,
        description=description,
        **defaults,
    )


class TestToolRouter:
    """Tests for ToolRouter."""

    @pytest.fixture()
    def tools(self) -> list[ToolDocument]:
        return [
            _make_tool(
                "resolve_stock",
                "identity",
                "解析 A 股名称或代码",
                aliases=["股票代码", "解析股票"],
                example_query=["贵州茅台的代码是什么"],
            ),
            _make_tool(
                "get_stock_realtime_quote",
                "stock_realtime",
                "查询单只 A 股最新价格",
                aliases=["实时行情", "最新价"],
                example_query=["贵州茅台现在多少钱"],
            ),
            _make_tool(
                "get_stock_daily_history",
                "stock_history",
                "查询股票日线历史行情",
                aliases=["历史行情", "日线"],
                example_query=["贵州茅台过去一个月走势"],
            ),
            _make_tool(
                "get_stock_company_profile",
                "company",
                "查询上市公司基本资料",
                aliases=["公司资料", "公司信息"],
                example_query=["介绍一下宁德时代"],
            ),
            _make_tool(
                "get_stock_financial_indicators",
                "financial",
                "查询股票综合财务分析指标",
                aliases=["财务指标", "财报"],
                example_query=["贵州茅台最近财务指标"],
                enabled=False,
            ),
        ]

    def test_route_by_alias(self, tools: list[ToolDocument]) -> None:
        router = ToolRouter(tools, top_k=3)
        result = router.route("实时行情")
        names = [t.tool_name for t in result]
        assert "get_stock_realtime_quote" in names

    def test_route_by_description(self, tools: list[ToolDocument]) -> None:
        router = ToolRouter(tools, top_k=3)
        result = router.route("日线行情")
        names = [t.tool_name for t in result]
        assert "get_stock_daily_history" in names

    def test_route_by_example_query(self, tools: list[ToolDocument]) -> None:
        router = ToolRouter(tools, top_k=3)
        result = router.route("贵州茅台现在多少钱")
        names = [t.tool_name for t in result]
        assert "get_stock_realtime_quote" in names

    def test_route_respects_top_k(self, tools: list[ToolDocument]) -> None:
        router = ToolRouter(tools, top_k=2)
        result = router.route("股票")
        assert len(result) <= 2

    def test_route_excludes_disabled(self, tools: list[ToolDocument]) -> None:
        router = ToolRouter(tools, top_k=10)
        result = router.route("财务指标")
        names = [t.tool_name for t in result]
        assert "get_stock_financial_indicators" not in names

    def test_route_returns_defaults_on_no_match(
        self, tools: list[ToolDocument]
    ) -> None:
        router = ToolRouter(tools, top_k=5)
        result = router.route("xyzzy_nothing_matches")
        names = [t.tool_name for t in result]
        assert "resolve_stock" in names

    def test_top_k_must_be_positive(self, tools: list[ToolDocument]) -> None:
        with pytest.raises(ValueError, match="positive"):
            ToolRouter(tools, top_k=0)

    def test_route_chinese_tokens(self, tools: list[ToolDocument]) -> None:
        router = ToolRouter(tools, top_k=3)
        result = router.route("公司资料")
        names = [t.tool_name for t in result]
        assert "get_stock_company_profile" in names
