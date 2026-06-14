"""Explicit LangGraph wrapper around the LangChain ReAct stock agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from backend.app.core.config import Settings
from backend.app.docs_index.router import ToolRouter
from backend.app.tools.registry import ToolRegistry

SYSTEM_PROMPT = """
你是一名谨慎的 A 股信息查询助手。
你只能使用本次查询动态提供的 Tushare 白名单工具获取数据。

规则：
1. 用户可以提供股票名称或六位代码。工具会负责解析，名称不明确时请要求用户澄清。
2. 对需要事实数据的问题必须调用工具，绝不编造价格、新闻、财务指标或公司信息。
3. 可以组合多个工具，但不要调用与问题无关的工具。
4. 某个工具失败时，解释失败来源，并尽量使用其他已成功获得的数据继续回答。
5. 使用中文输出，包含：简洁摘要、关键数据、股票名称和代码、Tushare 接口名、
   数据获取时间。
6. 最后一行必须写：仅供信息参考，不构成投资建议。
""".strip()


class AgentState(TypedDict, total=False):
    """State persisted by the outer stock-query graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    query: str
    selected_tools: list[str]
    answer: str


def build_agent_graph(
    settings: Settings,
    *,
    model: Any | None = None,
    registry: ToolRegistry | None = None,
    router: ToolRouter | None = None,
    agent_factory: Callable[..., Any] | None = None,
) -> Any:
    """Create and compile the stock-query LangGraph."""

    chat_model = model or ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=0,
    )
    tool_registry = registry or ToolRegistry()
    tool_router = router or ToolRouter(
        tool_registry.documents, top_k=settings.tool_top_k
    )

    def preprocess(state: AgentState) -> dict[str, str]:
        messages = state.get("messages", [])
        query = str(messages[-1].content).strip() if messages else ""
        return {"query": query}

    def route_tools(state: AgentState) -> dict[str, list[str]]:
        selected = tool_router.route(state["query"])
        return {"selected_tools": [tool.tool_name for tool in selected]}

    def run_agent(state: AgentState) -> dict[str, list[AnyMessage]]:
        tools = tool_registry.langchain_tools(state["selected_tools"])
        factory = agent_factory or create_react_agent
        react_agent = factory(model=chat_model, tools=tools)
        result = react_agent.invoke({"messages": state["messages"]})
        return {"messages": result["messages"]}

    def finalize(state: AgentState) -> dict[str, str]:
        messages = state.get("messages", [])
        answer = str(messages[-1].content) if messages else "没有生成回答。"
        return {"answer": answer}

    builder = StateGraph(AgentState)
    builder.add_node("preprocess", preprocess)
    builder.add_node("route_tools", route_tools)
    builder.add_node("react_agent", run_agent)
    builder.add_node("finalize", finalize)
    builder.add_edge(START, "preprocess")
    builder.add_edge("preprocess", "route_tools")
    builder.add_edge("route_tools", "react_agent")
    builder.add_edge("react_agent", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=InMemorySaver())
