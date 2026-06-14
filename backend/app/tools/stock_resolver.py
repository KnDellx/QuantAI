"""Resolve natural-language A-share names to stock codes."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.app.model.schemas import StockRef
from backend.app.tools.tushare_client import TushareClient, from_ts_code

STOCK_LIST_SOURCE = "stock_basic"


class StockResolver:
    """Resolve stock codes and names using Tushare's A-share code table."""

    def __init__(self, tushare_client: TushareClient | None = None) -> None:
        self.tushare_client = tushare_client or TushareClient()

    def resolve(self, query: str) -> StockRef:
        """Resolve an exact code/name or an unambiguous partial name."""

        normalized = query.strip()
        if normalized.isdigit() and len(normalized) == 6:
            try:
                match = next(
                    (item for item in self._stock_list() if item["code"] == normalized),
                    None,
                )
            except Exception:
                match = None
            return StockRef(
                code=normalized, name=match["name"] if match else normalized
            )

        exact = [
            item
            for item in self._stock_list()
            if item["name"].casefold() == normalized.casefold()
        ]
        if len(exact) == 1:
            return StockRef(**exact[0])

        partial = [
            item
            for item in self._stock_list()
            if normalized.casefold() in item["name"].casefold()
        ]
        if len(partial) == 1:
            return StockRef(**partial[0])
        if not partial:
            raise ValueError(f"未找到 A 股股票：{query}")

        choices = "、".join(f"{item['name']}({item['code']})" for item in partial[:5])
        raise ValueError(f"股票名称不明确，请使用代码或完整名称。候选：{choices}")

    def _stock_list(self) -> list[dict[str, str]]:
        return _load_stock_list(self.tushare_client)


@lru_cache(maxsize=8)
def _load_stock_list(client: TushareClient) -> list[dict[str, str]]:
    frame = client.stock_basic()
    if frame.empty:
        raise ValueError("Tushare 返回的 A 股代码表为空")

    columns: dict[str, Any] = {str(column): column for column in frame.columns}
    code_column = columns.get("symbol") or columns.get("code")
    ts_code_column = columns.get("ts_code")
    name_column = columns.get("name") or columns.get("名称")
    if name_column is None or (code_column is None and ts_code_column is None):
        raise ValueError("无法识别 Tushare A 股代码表字段")

    records: list[dict[str, str]] = []
    for _, row in frame.iterrows():
        code = (
            str(row[code_column]).zfill(6)
            if code_column is not None
            else from_ts_code(str(row[ts_code_column]))
        )
        records.append({"code": code, "name": str(row[name_column])})
    return records
