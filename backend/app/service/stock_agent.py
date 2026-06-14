"""Service facade for the stock-query graph."""

from __future__ import annotations

from uuid import uuid4

from langchain_core.messages import HumanMessage

from backend.app.core.config import Settings, get_settings
from backend.app.graph.agent_graph import build_agent_graph


class StockAgentService:
    """Manage stock-agent conversations."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.graph = build_agent_graph(settings or get_settings())

    @staticmethod
    def new_thread_id() -> str:
        """Create a fresh conversation identifier."""

        return str(uuid4())

    def ask(self, question: str, thread_id: str) -> str:
        """Ask a question in a persistent conversation thread."""

        if not question.strip():
            raise ValueError("问题不能为空")

        result = self.graph.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={"configurable": {"thread_id": thread_id}},
        )
        return result["answer"]
