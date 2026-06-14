"""Tests for backend.app.tools.registry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.app.docs_index.schemas import ToolDocument, ToolParameter, ToolReturn
from backend.app.tools.registry import ToolRegistry


def _make_document(name: str, **overrides) -> ToolDocument:
    defaults = dict(
        tool_name=name,
        category="test",
        description=f"test tool {name}",
        params={
            "stock": ToolParameter(type="string", required=True, description="code"),
        },
        returns=ToolReturn(description="data"),
        example_query=["test query"],
        source_interfaces=["daily"],
        mode="generic",
    )
    defaults.update(overrides)
    return ToolDocument(**defaults)


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_init_with_documents(self) -> None:
        docs = [_make_document("tool_a"), _make_document("tool_b")]
        registry = ToolRegistry(documents=docs, tushare_client=MagicMock())
        assert len(registry.documents) == 2

    def test_get_document(self) -> None:
        docs = [_make_document("tool_a"), _make_document("tool_b")]
        registry = ToolRegistry(documents=docs, tushare_client=MagicMock())
        doc = registry.get_document("tool_a")
        assert doc.tool_name == "tool_a"

    def test_get_document_not_found(self) -> None:
        docs = [_make_document("tool_a")]
        registry = ToolRegistry(documents=docs, tushare_client=MagicMock())
        with pytest.raises(KeyError):
            registry.get_document("nonexistent")

    def test_invoke(self) -> None:
        docs = [_make_document("tool_a", mode="resolve_stock")]
        registry = ToolRegistry(documents=docs, tushare_client=MagicMock())
        result_json = registry.invoke("tool_a", stock="600519")
        import json

        result = json.loads(result_json)
        assert result["ok"] is True

    def test_langchain_tools(self) -> None:
        docs = [_make_document("tool_a"), _make_document("tool_b")]
        registry = ToolRegistry(documents=docs, tushare_client=MagicMock())
        tools = registry.langchain_tools(["tool_a"])
        assert len(tools) == 1
        assert tools[0].name == "tool_a"

    def test_langchain_tools_builds_schema(self) -> None:
        docs = [_make_document("tool_a")]
        registry = ToolRegistry(documents=docs, tushare_client=MagicMock())
        tools = registry.langchain_tools(["tool_a"])
        schema = tools[0].args_schema
        assert schema is not None
        assert "stock" in schema.model_fields

    def test_no_akshare_module_param(self) -> None:
        """Verify akshare_module parameter has been removed."""
        import inspect

        sig = inspect.signature(ToolRegistry.__init__)
        assert "akshare_module" not in sig.parameters
