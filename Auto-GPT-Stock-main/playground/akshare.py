from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

import akshare as ak
import pandas as pd

from backend.app.core.akshare_compat import install_akshare_compat

SAMPLE_CODE = "000001"

install_akshare_compat()


@dataclass
class TestResult:
    name: str
    ok: bool
    elapsed: float
    shape: tuple[int, int] | None = None
    columns: list[str] | None = None
    sample: list[dict[str, Any]] | dict[str, Any] | None = None
    error: str | None = None


def _frame_summary(
    frame: pd.DataFrame,
) -> tuple[tuple[int, int], list[str], list[dict[str, Any]]]:
    preview = frame.head(3).where(pd.notna(frame.head(3)), None)
    return (
        frame.shape,
        [str(column) for column in frame.columns],
        preview.to_dict(orient="records"),
    )


def _run_test(name: str, loader: Callable[[], pd.DataFrame]) -> TestResult:
    started_at = time.perf_counter()
    try:
        frame = loader()
        elapsed = time.perf_counter() - started_at
        shape, columns, sample = _frame_summary(frame)
        return TestResult(
            name=name,
            ok=not frame.empty,
            elapsed=elapsed,
            shape=shape,
            columns=columns,
            sample=sample,
            error=None if not frame.empty else "AKShare returned an empty DataFrame",
        )
    except Exception as error:
        elapsed = time.perf_counter() - started_at
        return TestResult(
            name=name,
            ok=False,
            elapsed=elapsed,
            error=f"{type(error).__name__}: {error}",
        )


def build_project_akshare_tests() -> list[tuple[str, Callable[[], pd.DataFrame]]]:
    end = date.today()
    start = end - timedelta(days=30)
    start_year = str(date.today().year - 2)

    return [
        ("stock_info_a_code_name", ak.stock_info_a_code_name),
        ("stock_zh_a_spot_em", ak.stock_zh_a_spot_em),
        (
            "stock_zh_a_hist",
            lambda: ak.stock_zh_a_hist(
                symbol=SAMPLE_CODE,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust="",
            ),
        ),
        (
            "stock_individual_info_em",
            lambda: ak.stock_individual_info_em(symbol=SAMPLE_CODE),
        ),
        ("stock_news_em", lambda: ak.stock_news_em(symbol=SAMPLE_CODE)),
        (
            "stock_financial_analysis_indicator",
            lambda: ak.stock_financial_analysis_indicator(
                symbol=SAMPLE_CODE,
                start_year=start_year,
            ),
        ),
    ]


def main() -> None:
    tests = build_project_akshare_tests()
    results = [_run_test(name, loader) for name, loader in tests]

    print("AKShare project interface smoke test")
    print("=" * 80)
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name} ({result.elapsed:.2f}s)")
        if result.shape is not None:
            print(f"  shape: {result.shape}")
        if result.columns is not None:
            print(f"  columns: {result.columns[:12]}")
        if result.sample is not None:
            print(f"  sample: {result.sample}")
        if result.error is not None:
            print(f"  error: {result.error}")
        print("-" * 80)

    passed = sum(1 for result in results if result.ok)
    print(f"Summary: {passed}/{len(results)} interfaces passed.")


if __name__ == "__main__":
    main()
