"""Pydantic schemas shared by stock tools and the agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StockRef(BaseModel):
    """Canonical identity for an A-share stock."""

    code: str = Field(pattern=r"^\d{6}$")
    name: str


class ToolError(BaseModel):
    """Machine-readable wrapper error."""

    code: str
    message: str
    retryable: bool = False


class ToolResult(BaseModel):
    """Stable result envelope returned by every stock data tool."""

    ok: bool
    source: str
    acquired_at: str
    tool_name: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    stock: StockRef | None = None
    data: Any = None
    error: str | ToolError | None = None


class StockQueryInput(BaseModel):
    """Input containing a stock name or six-digit code."""

    stock: str = Field(description="A股名称或六位股票代码")


class HistoryQueryInput(StockQueryInput):
    """Input for historical prices."""

    days: int = Field(default=30, ge=1, le=365)
    adjust: str = Field(
        default="",
        description="复权方式：空字符串为不复权，qfq 为前复权，hfq 为后复权",
        pattern=r"^(|qfq|hfq)$",
    )


class NewsQueryInput(StockQueryInput):
    """Input for recent stock news."""

    limit: int = Field(default=5, ge=1, le=20)
