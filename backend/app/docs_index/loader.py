"""Load and validate the curated tool documentation index."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.app.docs_index.schemas import ToolDocsIndex

DEFAULT_INDEX_PATH = Path("docs/tushare/tools/stock_tools.json")


@lru_cache(maxsize=1)
def load_tool_docs(path: Path | str = DEFAULT_INDEX_PATH) -> ToolDocsIndex:
    """Load the Agent-facing tool index from JSON (cached per path)."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    index = ToolDocsIndex.model_validate(payload)
    names = [tool.tool_name for tool in index.tools]
    if len(names) != len(set(names)):
        raise ValueError("docs_index contains duplicate tool_name values")
    return index
