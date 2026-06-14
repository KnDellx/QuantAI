"""Tests for backend.app.model.schemas."""

from __future__ import annotations

import pytest

from backend.app.model.schemas import StockRef, ToolError, ToolResult


class TestStockRef:
    """Tests for StockRef model."""

    def test_valid_six_digit_code(self) -> None:
        ref = StockRef(code="600519", name="贵州茅台")
        assert ref.code == "600519"
        assert ref.name == "贵州茅台"

    def test_invalid_code_pattern(self) -> None:
        with pytest.raises(Exception):
            StockRef(code="abc", name="test")

    def test_invalid_code_length(self) -> None:
        with pytest.raises(Exception):
            StockRef(code="12345", name="test")

    def test_non_digit_code(self) -> None:
        with pytest.raises(Exception):
            StockRef(code="60051a", name="test")


class TestToolError:
    """Tests for ToolError model."""

    def test_basic_error(self) -> None:
        err = ToolError(code="TEST", message="something failed")
        assert err.code == "TEST"
        assert err.message == "something failed"
        assert err.retryable is False

    def test_retryable_error(self) -> None:
        err = ToolError(code="UPSTREAM", message="timeout", retryable=True)
        assert err.retryable is True


class TestToolResult:
    """Tests for ToolResult model."""

    def test_success_result(self) -> None:
        result = ToolResult(
            ok=True,
            source="daily",
            acquired_at="2026-01-01T00:00:00Z",
            tool_name="get_stock_daily",
            data=[{"close": 100}],
        )
        assert result.ok is True
        assert result.data == [{"close": 100}]
        assert result.error is None

    def test_error_result_with_string(self) -> None:
        result = ToolResult(
            ok=False,
            source="daily",
            acquired_at="2026-01-01T00:00:00Z",
            error="something went wrong",
        )
        assert result.ok is False
        assert result.error == "something went wrong"

    def test_error_result_with_tool_error(self) -> None:
        tool_err = ToolError(code="FAIL", message="bad", retryable=False)
        result = ToolResult(
            ok=False,
            source="daily",
            acquired_at="2026-01-01T00:00:00Z",
            error=tool_err,
        )
        assert result.ok is False
        assert isinstance(result.error, ToolError)
        assert result.error.code == "FAIL"

    def test_result_with_stock_ref(self) -> None:
        ref = StockRef(code="600519", name="贵州茅台")
        result = ToolResult(
            ok=True,
            source="daily",
            acquired_at="2026-01-01T00:00:00Z",
            stock=ref,
        )
        assert result.stock is not None
        assert result.stock.code == "600519"

    def test_defaults(self) -> None:
        result = ToolResult(ok=True, source="test", acquired_at="2026-01-01")
        assert result.tool_name is None
        assert result.params == {}
        assert result.stock is None
        assert result.data is None
        assert result.error is None

    def test_serialization_roundtrip(self) -> None:
        result = ToolResult(
            ok=True,
            source="daily",
            acquired_at="2026-01-01T00:00:00Z",
            tool_name="test",
            params={"stock": "600519"},
            data={"close": 100},
        )
        json_str = result.model_dump_json()
        restored = ToolResult.model_validate_json(json_str)
        assert restored.ok == result.ok
        assert restored.tool_name == result.tool_name
        assert restored.params == result.params
