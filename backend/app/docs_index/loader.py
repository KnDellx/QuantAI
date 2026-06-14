"""Load and validate the curated tool documentation index."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.docs_index.schemas import ToolDocsIndex

DEFAULT_INDEX_PATH = Path("docs/akshare/tools/stock_tools.json")
TUSHARE_SOURCE_BY_TOOL: dict[str, str] = {
    "resolve_stock": "stock_basic",
    "list_a_share_stocks": "stock_basic",
    "get_stock_company_profile": "stock_basic",
    "get_stock_listing_info": "stock_basic",
    "get_stock_realtime_quote": "realtime_quote",
    "get_a_share_market_snapshot": "realtime_list",
    "get_stock_bid_ask": "realtime_quote",
    "get_stock_intraday_ticks": "stk_tick",
    "get_stock_intraday_minutes": "stk_mins",
    "get_stock_order_book": "realtime_quote",
    "get_stock_realtime_trades": "stk_tick",
    "get_stock_market_status": "trade_cal",
    "get_stock_daily_history": "daily",
    "get_stock_weekly_history": "weekly",
    "get_stock_monthly_history": "monthly",
    "get_stock_adjusted_history": "daily",
    "get_stock_period_performance": "daily",
    "get_stock_volatility": "daily",
    "get_stock_price_summary": "daily",
    "get_stock_financial_indicators": "fina_indicator",
    "get_stock_balance_sheet": "balancesheet",
    "get_stock_income_statement": "income",
    "get_stock_cash_flow_statement": "cashflow",
    "get_stock_profitability": "fina_indicator",
    "get_stock_growth_metrics": "fina_indicator",
    "get_stock_solvency_metrics": "fina_indicator",
    "get_stock_operating_metrics": "fina_indicator",
    "get_stock_dupont_analysis": "fina_indicator",
    "get_stock_financial_forecast": "forecast",
    "get_stock_shareholders": "stk_holdernumber",
    "get_stock_top_shareholders": "top10_holders",
    "get_stock_shareholder_changes": "stk_holdernumber",
    "get_stock_dividend_history": "dividend",
    "get_stock_share_capital": "stock_basic",
    "get_stock_restricted_share_unlocks": "share_float",
    "get_stock_buybacks": "repurchase",
    "get_stock_news": "news",
    "get_stock_announcements": "anns",
    "get_stock_major_events": "anns",
    "get_stock_management_changes": "stk_managers",
    "get_stock_suspension_events": "suspend_d",
    "get_stock_valuation": "daily_basic",
    "get_stock_fund_flow": "moneyflow",
    "get_stock_northbound_holding": "hk_hold",
    "get_stock_margin_trading": "margin_detail",
    "get_stock_dragon_tiger_list": "top_list",
    "get_market_overview": "daily_basic",
    "get_industry_rankings": "stock_basic",
    "get_concept_rankings": "concept",
    "get_index_realtime_quote": "index_daily",
}


def load_tool_docs(path: Path | str = DEFAULT_INDEX_PATH) -> ToolDocsIndex:
    """Load the Agent-facing tool index from JSON."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    index = ToolDocsIndex.model_validate(payload)
    names = [tool.tool_name for tool in index.tools]
    if len(names) != len(set(names)):
        raise ValueError("docs_index contains duplicate tool_name values")
    return index.model_copy(
        update={
            "tools": [
                tool.model_copy(
                    update={
                        "source_interfaces": [TUSHARE_SOURCE_BY_TOOL[tool.tool_name]],
                        "returns": tool.returns.model_copy(
                            update={
                                "description": tool.returns.description.replace(
                                    "AKShare", "Tushare"
                                )
                            }
                        ),
                    }
                )
                for tool in index.tools
            ]
        }
    )
