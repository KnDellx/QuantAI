"""Optional live Tushare smoke tests."""

import os

import pytest

from backend.app.tools.tushare_client import TushareClient


@pytest.mark.integration
def test_live_a_share_code_table() -> None:
    if not os.environ.get("TUSHARE_TOKEN"):
        pytest.skip("Set TUSHARE_TOKEN to run the live Tushare smoke test.")

    frame = TushareClient().stock_basic()

    assert not frame.empty
