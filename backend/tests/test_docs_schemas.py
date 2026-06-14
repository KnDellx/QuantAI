"""Tests for backend.app.docs_index.schemas."""

from __future__ import annotations

import pytest

from backend.app.docs_index.schemas import (
    ToolDocsIndex,
    ToolDocument,
    ToolParameter,
    ToolReturn,
)


class TestToolParameter:
    """Tests for ToolParameter model."""

    def test_required_param(self) -> None:
        param = ToolParameter(type="string", required=True, description="stock code")
        assert param.type == "string"
        assert param.required is True
        assert param.default is None

    def test_optional_param_with_default(self) -> None:
        param = ToolParameter(
            type="integer", required=False, description="days", default=30
        )
        assert param.default == 30

    def test_examples(self) -> None:
        param = ToolParameter(type="string", description="code", examples=["600519"])
        assert param.examples == ["600519"]


class TestToolReturn:
    """Tests for ToolReturn model."""

    def test_defaults(self) -> None:
        ret = ToolReturn(description="result data")
        assert ret.type == "object"
        assert ret.description == "result data"


class TestToolDocument:
    """Tests for ToolDocument model."""

    def _make_document(self, **overrides) -> ToolDocument:
        defaults = dict(
            tool_name="get_stock_daily",
            category="history",
            description="查询日线行情",
            params={},
            returns=ToolReturn(description="行情数据"),
            example_query=["贵州茅台日线"],
            source_interfaces=["daily"],
        )
        defaults.update(overrides)
        return ToolDocument(**defaults)

    def test_basic_document(self) -> None:
        doc = self._make_document()
        assert doc.tool_name == "get_stock_daily"
        assert doc.enabled is True
        assert doc.mode == "generic"
        assert doc.aliases == []

    def test_source_interfaces_must_not_be_empty(self) -> None:
        with pytest.raises(Exception):
            self._make_document(source_interfaces=[])

    def test_with_params(self) -> None:
        doc = self._make_document(
            params={
                "stock": ToolParameter(type="string", required=True, description="code")
            }
        )
        assert "stock" in doc.params

    def test_disabled_tool(self) -> None:
        doc = self._make_document(enabled=False)
        assert doc.enabled is False


class TestToolDocsIndex:
    """Tests for ToolDocsIndex model."""

    def test_valid_index(self) -> None:
        doc = ToolDocument(
            tool_name="test_tool",
            category="test",
            description="test",
            params={},
            returns=ToolReturn(description="test"),
            example_query=["test"],
            source_interfaces=["test_ep"],
        )
        index = ToolDocsIndex(tools=[doc])
        assert len(index.tools) == 1
        assert index.schema_version == 1

    def test_empty_index(self) -> None:
        index = ToolDocsIndex(tools=[])
        assert len(index.tools) == 0
