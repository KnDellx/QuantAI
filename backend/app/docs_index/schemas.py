"""Schemas for the curated Agent-facing stock tool index."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """One Agent-visible tool parameter."""

    type: str
    required: bool = False
    description: str
    default: Any = None
    examples: list[Any] = Field(default_factory=list)


class ToolReturn(BaseModel):
    """Description of a tool's normalized return value."""

    type: str = "object"
    description: str


class ToolDocument(BaseModel):
    """Searchable contract for one whitelisted wrapper."""

    tool_name: str
    category: str
    description: str
    params: dict[str, ToolParameter]
    returns: ToolReturn
    example_query: list[str]
    source_interfaces: list[str] = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    enabled: bool = True
    mode: str = "generic"


class ToolDocsIndex(BaseModel):
    """Versioned collection of Agent-facing tool contracts."""

    schema_version: int = 1
    tools: list[ToolDocument]
