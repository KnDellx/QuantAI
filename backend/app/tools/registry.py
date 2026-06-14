"""Registry that exposes only selected whitelisted wrappers to the LLM."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field, create_model

from backend.app.docs_index.loader import load_tool_docs
from backend.app.docs_index.schemas import ToolDocument
from backend.app.tools.base import TushareWrapper
from backend.app.tools.stock_resolver import StockResolver
from backend.app.tools.tushare_client import TushareClient

PARAMETER_TYPES: dict[str, type[Any]] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict[str, Any],
}


class ToolRegistry:
    """Own wrapper instances and construct LangChain tools on demand."""

    def __init__(
        self,
        documents: list[ToolDocument] | None = None,
        resolver: StockResolver | None = None,
        tushare_client: TushareClient | None = None,
    ) -> None:
        self.documents = documents or load_tool_docs().tools
        self.resolver = resolver or StockResolver(tushare_client)
        self._documents = {document.tool_name: document for document in self.documents}
        self._wrappers = {
            document.tool_name: TushareWrapper(
                document,
                self.resolver,
                tushare_client=tushare_client,
            )
            for document in self.documents
        }

    def get_document(self, name: str) -> ToolDocument:
        """Return one registered contract."""

        return self._documents[name]

    def invoke(self, name: str, **params: Any) -> str:
        """Invoke a wrapper by its whitelisted name."""

        return self._wrappers[name].invoke(**params)

    def langchain_tools(self, names: list[str]) -> list[BaseTool]:
        """Build only the selected LangChain tools."""

        return [self._to_langchain_tool(self._documents[name]) for name in names]

    def _to_langchain_tool(self, document: ToolDocument) -> BaseTool:
        fields: dict[str, Any] = {}
        for name, parameter in document.params.items():
            value_type = PARAMETER_TYPES.get(parameter.type, str)
            if parameter.required:
                annotation = value_type
                default = Field(description=parameter.description)
            else:
                annotation = value_type | None
                default = Field(
                    default=parameter.default, description=parameter.description
                )
            fields[name] = (annotation, default)
        args_schema = create_model(f"{document.tool_name.title()}Input", **fields)

        def execute(**params: Any) -> str:
            return self.invoke(document.tool_name, **params)

        return StructuredTool.from_function(
            func=execute,
            name=document.tool_name,
            description=document.description,
            args_schema=args_schema,
        )
