"""Deterministic local retrieval over the curated stock tool index."""

from __future__ import annotations

import re

from backend.app.docs_index.schemas import ToolDocument

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]{2,}")


class ToolRouter:
    """Select a small relevant tool set without asking the LLM."""

    def __init__(self, tools: list[ToolDocument], top_k: int = 5) -> None:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.tools = [tool for tool in tools if tool.enabled]
        self.top_k = top_k

    def route(self, query: str) -> list[ToolDocument]:
        """Return at most top-k tools ranked by local lexical relevance."""

        normalized = query.casefold().strip()
        query_tokens = set(TOKEN_PATTERN.findall(normalized))
        scored = [
            (self._score(tool, normalized, query_tokens), tool) for tool in self.tools
        ]
        matches = [item for item in scored if item[0] > 0]
        matches.sort(key=lambda item: (-item[0], item[1].tool_name))
        if matches:
            return [tool for _, tool in matches[: self.top_k]]

        defaults = {
            "resolve_stock",
            "get_stock_realtime_quote",
            "get_stock_company_profile",
        }
        return [tool for tool in self.tools if tool.tool_name in defaults][: self.top_k]

    @staticmethod
    def _score(tool: ToolDocument, query: str, query_tokens: set[str]) -> int:
        searchable = " ".join(
            [
                tool.tool_name.replace("_", " "),
                tool.category.replace("_", " "),
                tool.description,
                *tool.aliases,
                *tool.example_query,
            ]
        ).casefold()
        score = sum(2 for token in query_tokens if token in searchable)
        score += sum(6 for alias in tool.aliases if alias.casefold() in query)
        score += sum(3 for example in tool.example_query if query in example.casefold())
        return score
