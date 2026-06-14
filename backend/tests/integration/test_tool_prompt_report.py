"""Live prompt evaluation that writes a JSON tool-test report."""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter, sleep
from typing import Any
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from backend.app.core.config import Settings, get_settings
from backend.app.docs_index.loader import load_tool_docs
from backend.app.docs_index.schemas import ToolDocument
from backend.app.graph.agent_graph import build_agent_graph

pytestmark = pytest.mark.integration

REPORT_PATH = Path("backend/tests/artifacts/tool_prompt_test_results.json")
INDEX = load_tool_docs()


def _build_prompt_cases() -> list[tuple[ToolDocument, int, str]]:
    """Return one live test case for each tool prompt."""

    missing_prompts = [
        document.tool_name for document in INDEX.tools if not document.example_query
    ]
    if missing_prompts:
        raise ValueError(
            "Each tool must define at least one example_query before live testing: "
            + ", ".join(missing_prompts)
        )
    return [
        (document, prompt_index, prompt)
        for document in INDEX.tools
        for prompt_index, prompt in enumerate(document.example_query)
    ]


PROMPT_CASES = _build_prompt_cases()
PROMPT_CASE_IDS = [
    f"{document.tool_name}-prompt-{prompt_index + 1}"
    for document, prompt_index, _ in PROMPT_CASES
]


def _default_usage() -> dict[str, int | None]:
    """Return the empty token-usage envelope."""

    return {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }


def _normalize_usage(message: Any) -> dict[str, int] | None:
    """Return one message's token usage in a normalized shape."""

    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict) and usage:
        return {
            "prompt_tokens": int(usage.get("input_tokens", 0) or 0),
            "completion_tokens": int(usage.get("output_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }

    response_metadata = getattr(message, "response_metadata", None)
    if not isinstance(response_metadata, dict):
        return None

    token_usage = response_metadata.get("token_usage") or response_metadata.get(
        "usage"
    )
    if not isinstance(token_usage, dict):
        return None
    return {
        "prompt_tokens": int(token_usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(token_usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(token_usage.get("total_tokens", 0) or 0),
    }


def _collect_usage(messages: list[object]) -> dict[str, int | None]:
    """Aggregate token usage across all model turns for one prompt."""

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    found_usage = False

    for message in messages:
        usage = _normalize_usage(message)
        if usage is None:
            continue
        found_usage = True
        prompt_tokens += usage["prompt_tokens"]
        completion_tokens += usage["completion_tokens"]
        total_tokens += usage["total_tokens"]

    if not found_usage:
        return _default_usage()
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _sum_usage(results: list[dict[str, Any]]) -> dict[str, int | None]:
    """Aggregate token usage across all recorded prompt results."""

    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    found_usage = False

    for result in results:
        usage = result.get("token_usage")
        if not isinstance(usage, dict):
            continue
        if usage.get("total_tokens") is None:
            continue
        found_usage = True
        prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        total_tokens += int(usage.get("total_tokens", 0) or 0)

    if not found_usage:
        return _default_usage()
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _build_settings() -> Settings:
    """Load runtime settings and widen top-k for the tool evaluation pass."""

    base = get_settings()
    return base.model_copy(update={"tool_top_k": 8})


def _read_delay_seconds(name: str, default: float) -> float:
    """Read one non-negative pacing value from the environment."""

    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError:
        return default
    return max(value, 0.0)


def _is_upstream_blocked(error_message: str | None) -> bool:
    """Return whether the upstream response looks like a temporary WAF block."""

    if not error_message:
        return False

    normalized = error_message.casefold()
    markers = (
        "permissiondeniederror",
        "网站防火墙",
        "不合法参数",
        "无法访问",
    )
    return any(marker.casefold() in normalized for marker in markers)


@dataclass(slots=True)
class PromptRateLimiter:
    """Enforce a minimum delay between live tool prompt test cases."""

    min_interval_seconds: float
    blocked_cooldown_seconds: float
    _last_started_perf: float | None = None

    def wait_before_next_case(self) -> float:
        """Sleep until the minimum gap since the previous case has elapsed."""

        if self._last_started_perf is None:
            self._last_started_perf = perf_counter()
            return 0.0

        elapsed = perf_counter() - self._last_started_perf
        remaining = self.min_interval_seconds - elapsed
        if remaining > 0:
            sleep(remaining)

        self._last_started_perf = perf_counter()
        return round(max(remaining, 0.0), 3)

    def cool_down_after_block(self) -> float:
        """Sleep after a temporary upstream block to reduce repeated failures."""

        if self.blocked_cooldown_seconds <= 0:
            return 0.0

        sleep(self.blocked_cooldown_seconds)
        self._last_started_perf = perf_counter()
        return round(self.blocked_cooldown_seconds, 3)


@dataclass(slots=True)
class ToolPromptReportCollector:
    """Collect prompt-level live-test records and write one JSON report."""

    settings: Settings
    total_tools: int
    total_prompts: int
    min_interval_seconds: float
    blocked_cooldown_seconds: float
    report_path: Path = REPORT_PATH
    run_id: str = field(default_factory=lambda: uuid4().hex)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_perf: float = field(default_factory=perf_counter)
    results: list[dict[str, Any]] = field(default_factory=list)

    def add_result(self, record: dict[str, Any]) -> None:
        """Store one prompt result."""

        self.results.append(record)
        self.write(finished=False)

    def write(self, *, finished: bool) -> None:
        """Write the current report to disk."""

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(UTC)
        status = "completed" if finished else "running"
        aggregate_usage = _sum_usage(self.results)
        passed = sum(1 for result in self.results if result["status"] == "passed")
        failed = sum(1 for result in self.results if result["status"] == "failed")
        errored = sum(1 for result in self.results if result["status"] == "error")
        metadata: dict[str, Any] = {
            "report_name": "tool_prompt_test_results",
            "report_version": 2,
            "run_id": self.run_id,
            "status": status,
            "generated_at": generated_at.isoformat(),
            "started_at": self.started_at.isoformat(),
            "finished_at": generated_at.isoformat() if finished else None,
            "duration_ms": round((perf_counter() - self.started_perf) * 1000, 3),
            "model_id": self.settings.openai_model,
            "base_url": self.settings.openai_base_url,
            "tool_top_k": self.settings.tool_top_k,
            "total_tools": self.total_tools,
            "total_prompts": self.total_prompts,
            "completed_prompts": len(self.results),
            "passed_prompts": passed,
            "failed_prompts": failed,
            "errored_prompts": errored,
            "aggregate_token_usage": aggregate_usage,
            "delay_between_tests_seconds": self.min_interval_seconds,
            "blocked_cooldown_seconds": self.blocked_cooldown_seconds,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "timezone": "UTC",
            "report_path": str(self.report_path),
        }
        report = {
            "metadata": metadata,
            "results": self.results,
        }
        self.report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


@dataclass(slots=True)
class LiveReportContext:
    """Session-level state shared by the live tool prompt tests."""

    settings: Settings
    graph: Any
    collector: ToolPromptReportCollector
    rate_limiter: PromptRateLimiter


@pytest.fixture(scope="session")
def live_report_context() -> Any:
    """Build the live graph once and write the JSON report at session end."""

    if os.environ.get("RUN_LIVE_TOOL_PROMPT_REPORT") != "1":
        pytest.skip(
            "Set RUN_LIVE_TOOL_PROMPT_REPORT=1 to run the live tool prompt report."
        )

    try:
        settings = _build_settings()
    except ValidationError as error:
        pytest.skip(f"Missing model configuration for live prompt report: {error}")

    min_interval_seconds = _read_delay_seconds(
        "TOOL_PROMPT_REPORT_DELAY_SECONDS", 5.0
    )
    blocked_cooldown_seconds = _read_delay_seconds(
        "TOOL_PROMPT_REPORT_BLOCKED_COOLDOWN_SECONDS", 60.0
    )
    collector = ToolPromptReportCollector(
        settings=settings,
        total_tools=len(INDEX.tools),
        total_prompts=len(PROMPT_CASES),
        min_interval_seconds=min_interval_seconds,
        blocked_cooldown_seconds=blocked_cooldown_seconds,
    )
    graph = build_agent_graph(settings)
    context = LiveReportContext(
        settings=settings,
        graph=graph,
        collector=collector,
        rate_limiter=PromptRateLimiter(
            min_interval_seconds=min_interval_seconds,
            blocked_cooldown_seconds=blocked_cooldown_seconds,
        ),
    )
    try:
        yield context
    finally:
        collector.write(finished=True)


@pytest.mark.parametrize(
    ("document", "prompt_index", "prompt"),
    PROMPT_CASES,
    ids=PROMPT_CASE_IDS,
)
def test_generate_tool_prompt_report_json(
    document: ToolDocument,
    prompt_index: int,
    prompt: str,
    live_report_context: LiveReportContext,
) -> None:
    """Run one live prompt per tool and append it to the JSON report."""

    thread_id = f"tool-report-{document.tool_name}-{prompt_index}-{uuid4()}"
    started_at = datetime.now(UTC)
    started = perf_counter()
    record: dict[str, Any] = {
        "tool_name": document.tool_name,
        "category": document.category,
        "prompt_index": prompt_index,
        "prompt": prompt,
        "expected_source_interfaces": document.source_interfaces,
        "started_at": started_at.isoformat(),
        "thread_id": thread_id,
    }
    waited_seconds = live_report_context.rate_limiter.wait_before_next_case()
    record["waited_before_start_seconds"] = waited_seconds

    try:
        result = live_report_context.graph.invoke(
            {"messages": [HumanMessage(content=prompt)]},
            config={"configurable": {"thread_id": thread_id}},
        )
        elapsed_ms = round((perf_counter() - started) * 1000, 3)
        selected_tools = list(result.get("selected_tools", []))
        expected_selected = document.tool_name in selected_tools
        messages = list(result.get("messages", []))
        usage = _collect_usage(messages)
        answer = str(result.get("answer", ""))

        record.update(
            {
                "status": "passed" if expected_selected else "failed",
                "selected_tools": selected_tools,
                "expected_tool_selected": expected_selected,
                "latency_ms": elapsed_ms,
                "token_usage": usage,
                "answer_preview": answer[:500],
                "error": None,
                "finished_at": datetime.now(UTC).isoformat(),
            }
        )
    except Exception as error:
        elapsed_ms = round((perf_counter() - started) * 1000, 3)
        error_message = f"{type(error).__name__}: {error}"
        record.update(
            {
                "status": "error",
                "selected_tools": [],
                "expected_tool_selected": False,
                "latency_ms": elapsed_ms,
                "token_usage": _default_usage(),
                "answer_preview": "",
                "error": error_message,
                "finished_at": datetime.now(UTC).isoformat(),
            }
        )
        if _is_upstream_blocked(error_message):
            record["blocked_cooldown_seconds"] = (
                live_report_context.rate_limiter.cool_down_after_block()
            )
    finally:
        live_report_context.collector.add_result(record)

    assert record["status"] == "passed", (
        f"{document.tool_name} did not pass live prompt evaluation: "
        f"status={record['status']}, "
        f"selected_tools={record.get('selected_tools')}, "
        f"error={record.get('error')}. "
        f"See {REPORT_PATH} for details."
    )
