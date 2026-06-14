# QuantAI A 股查询 Agent

一个使用 LangChain、显式 LangGraph 状态图和 AKShare 构建的 A 股自然语言
查询 Agent。

## 功能

- 股票名称或六位代码解析
- 实时行情、历史行情、公司信息、新闻和财务指标查询
- 从本地 `docs_index` 检索 50 个白名单工具，并只向 LLM 动态绑定 top-k
- 多轮对话
- 每次查询直接调用 AKShare API，不读取本地行情缓存
- AKShare 官方接口文档快照与可检索 JSON 索引
- 仅允许调用白名单工具，不执行任意 Python

## 架构

```text
User query
  -> 本地 docs_index ToolRouter
  -> 选择 top-k 工具
  -> 动态创建只绑定所选工具的 ReAct Agent
  -> ToolRegistry
  -> AKShareWrapper
  -> AKShare API
  -> 统一 ToolResult
  -> LLM 总结
```

Agent 使用的 50 个工具契约位于
[`docs/akshare/tools/stock_tools.json`](docs/akshare/tools/stock_tools.json)。
完整设计和扩展方式见 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

## 安装

```bash
uv sync
uv run python scripts/install_runtime_compat.py
```

复制 `.env.example` 为 `.env`，填写模型服务配置：

```dotenv
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://gw-stg.tradingbase.ai/v1
OPENAI_MODEL=gpt-4.1
```

API key 不要提交到 Git。

第二条安装命令会启用项目内的 AKShare 网络兼容层。它只修复
`stock_zh_a_spot_em` 在部分网络环境下访问东方财富分片节点时的连接问题，
不使用本地行情缓存。重建 `.venv` 后需要重新执行该命令。

## 运行

```bash
uv run python main.py
```

CLI 命令：

- `/help`：显示帮助
- `/new`：开始新对话
- `/exit`：退出

AKShare 文档上下文的设计与更新方式见
[`docs/akshare/README.md`](docs/akshare/README.md)。

示例问题：

```text
贵州茅台现在多少钱？
看看 600519 过去一个月走势
介绍一下宁德时代
平安银行最近有什么新闻？
贵州茅台最近财务指标如何？
```

## 质量检查

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

默认测试不会调用真实 AKShare 上游。单独运行核心接口冒烟测试：

```bash
uv run pytest -m integration
```

查询结果仅供信息参考，不构成投资建议。
