# QuantAI 开发者文档

## 运行流程

```text
用户问题
  -> LangGraph preprocess
  -> ToolRouter 检索本地 docs_index
  -> route_tools 选择最多 top-k 个工具
  -> 仅绑定 selected_tools
  -> LLM 发出 tool call
  -> ToolRegistry 调用对应 AKShareWrapper
  -> 调用白名单 AKShare 接口
  -> 返回统一 ToolResult
  -> LLM 输出中文答案
```

路由过程完全在本地执行，不会一次性将 50 个工具暴露给 LLM。默认 `top_k=5`，
可以通过 `Settings.tool_top_k` 调整，最大为 8。

## docs_index

Agent 使用的工具索引位于 `docs/akshare/tools/stock_tools.json`。每条工具契约包含：

- `tool_name`：Agent 调用的稳定名称。
- `category`：工具分类。
- `description`：用于路由和 LLM 工具说明。
- `params`：参数 Schema。
- `returns`：标准化返回说明。
- `example_query`：自然语言检索样例。
- `source_interfaces`：允许调用的 AKShare 接口白名单。
- `aliases`：本地路由关键词。
- `mode`：专用适配器或受控通用 wrapper。

`scripts/build_tool_docs_index.py` 是 50 个工具契约的生成源。修改后运行：

```bash
uv run python scripts/build_tool_docs_index.py
```

## Wrapper

`AKShareWrapper` 负责：

1. 清理并标准化参数。
2. 仅调用工具契约声明的 AKShare 接口。
3. 将 DataFrame、Series 等结果转为 JSON。
4. 返回统一 `ToolResult`。

核心股票解析、实时行情、历史行情、公司资料、新闻和财务指标使用专用适配逻辑。
其他工具通过注册表中的明确白名单执行，LLM 无法提供任意 AKShare 函数名。

## 数据读取

所有金融数据查询均直接调用对应的 AKShare API。项目不保存或读取本地行情缓存，
因此连续执行相同查询也会再次访问上游数据源。

## 测试分层

默认运行：

```bash
uv run pytest
```

测试包括：

- **Schema Test**：50 个工具均有合法 docs_index 和 LangChain 参数 Schema。
- **Wrapper Mock Test**：50 个工具均能通过 Mock AKShare 执行，连续调用会重复访问上游。
- **Router Test**：常见自然语言问题能选中正确工具，且数量不超过 top-k。
- **Agent Flow Test**：验证先路由、后动态绑定，LLM 看不到全部工具。
- **原有单元测试**：旧工具、股票解析器和文档同步的兼容测试。

真实上游测试不会作为默认 CI 必跑：

```bash
uv run pytest -m integration
```

如需生成 50 个工具逐条 prompt 的模型评测报告，可运行：

```bash
RUN_LIVE_TOOL_PROMPT_REPORT=1 uv run pytest -m integration backend/tests/integration/test_tool_prompt_report.py
```

报告会写入 `backend/tests/artifacts/tool_prompt_test_results.json`，包含：

- 顶层 `metadata`：`model_id`、生成时间、运行时长、`base_url`、`tool_top_k` 等。
- 每条 `results`：对应 `tool_name`、`prompt`、`selected_tools`、`token_usage`、`latency_ms`、状态和错误信息。

Mock 测试覆盖工具契约和项目逻辑，不代表所有 AKShare 上游接口在任意时刻都可用。
Integration Test 只抽样核心接口，以避免限流、交易时间和第三方站点波动导致默认 CI
不稳定。

## 新增或修改工具

1. 在 `scripts/build_tool_docs_index.py` 中新增或修改工具契约。
2. 运行脚本重新生成 `stock_tools.json`。
3. 专用参数转换或结果处理应加入 `AKShareWrapper` 的明确 mode handler。
4. 确保 Schema Test 和参数化 Mock Test自动覆盖该工具。
5. 对核心接口增加单独的行为测试，必要时加入非默认 Integration Test。
6. 运行 Ruff、格式检查和完整默认测试。
