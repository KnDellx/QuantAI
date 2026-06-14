"""Tests for backend.app.tools.tushare_client helpers."""

from __future__ import annotations

import pytest

from backend.app.tools.tushare_client import (
    TushareClient,
    date_range_for_days,
    from_ts_code,
    to_ts_code,
)


class TestToTsCode:
    """Tests for to_ts_code conversion."""

    def test_shanghai_main(self) -> None:
        assert to_ts_code("600519") == "600519.SH"

    def test_shanghai_9_prefix(self) -> None:
        assert to_ts_code("900001") == "900001.SH"

    def test_shenzhen_main(self) -> None:
        assert to_ts_code("000001") == "000001.SZ"

    def test_shenzhen_gem(self) -> None:
        assert to_ts_code("300750") == "300750.SZ"

    def test_shenzhen_sme(self) -> None:
        assert to_ts_code("002594") == "002594.SZ"

    def test_beijing_bse(self) -> None:
        assert to_ts_code("830799") == "830799.BJ"

    def test_beijing_neeq(self) -> None:
        assert to_ts_code("430047") == "430047.BJ"

    def test_already_has_suffix(self) -> None:
        assert to_ts_code("600519.SH") == "600519.SH"

    def test_lowercase_suffix(self) -> None:
        assert to_ts_code("600519.sh") == "600519.SH"

    def test_whitespace_stripped(self) -> None:
        assert to_ts_code(" 600519 ") == "600519.SH"

    def test_unknown_prefix_passthrough(self) -> None:
        assert to_ts_code("500001") == "500001"


class TestFromTsCode:
    """Tests for from_ts_code extraction."""

    def test_sh_code(self) -> None:
        assert from_ts_code("600519.SH") == "600519"

    def test_sz_code(self) -> None:
        assert from_ts_code("000001.SZ") == "000001"

    def test_bj_code(self) -> None:
        assert from_ts_code("830799.BJ") == "830799"

    def test_no_suffix(self) -> None:
        assert from_ts_code("600519") == "600519"

    def test_short_code_padded(self) -> None:
        assert from_ts_code("1.SZ") == "000001"


class TestDateRangeForDays:
    """Tests for date_range_for_days."""

    def test_returns_start_and_end(self) -> None:
        result = date_range_for_days(30)
        assert "start_date" in result
        assert "end_date" in result

    def test_format_is_yyyymmdd(self) -> None:
        result = date_range_for_days(30)
        for value in result.values():
            assert len(value) == 8
            assert value.isdigit()

    def test_end_is_today(self) -> None:
        from datetime import date

        result = date_range_for_days(30)
        assert result["end_date"] == date.today().strftime("%Y%m%d")


class TestTushareClient:
    """Tests for TushareClient initialization."""

    def test_init_with_token(self) -> None:
        client = TushareClient(token="test-token")
        assert client.token == "test-token"

    def test_init_without_token_uses_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TUSHARE_TOKEN", "env-token")
        client = TushareClient()
        assert client.token == "env-token"

    def test_init_no_token_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
        client = TushareClient()
        assert client.token is None

    def test_pro_api_raises_without_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
        client = TushareClient()
        with pytest.raises(RuntimeError, match="Missing TUSHARE_TOKEN"):
            _ = client.pro_api

    def test_pro_api_uses_injected_api(self) -> None:
        class FakeApi:
            pass

        fake = FakeApi()
        client = TushareClient(token="x", pro_api=fake)
        assert client.pro_api is fake
