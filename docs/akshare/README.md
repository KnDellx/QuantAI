# AKShare 文档上下文

本目录保存 AKShare 官方接口文档的项目内快照，供开发和 Agent 检索使用。

同步清单覆盖 AKShare 数据导航中的全部独立文档。波动率、多因子和政策不确定性
在官方导航中是三个条目，但共同保存在 `article/article` 文档中，因此本地只生成
一份 `article.md`。奇货可查的导航页由 RST 和六份 Markdown 子文档组成，因此分别
保存为 `qhkc.md` 和六份 `qhkc_*.md`，确保接口正文完整。

## 方案评估

推荐保留两种表示：

- `raw/*.md`：官方 Sphinx 源 Markdown，信息完整，适合阅读和按段检索。
- `index/*.json`：从原文抽取的接口名、标题路径、目标地址、描述和限量，适合先定位接口。
- `tools/stock_tools.json`：Agent 实际允许选择和调用的 50 个语义工具契约。

这些本地文档只用于选择工具，不保存任何金融查询结果。

不推荐抓取渲染后的 HTML 或浏览器开发者工具内容。AKShare 官方站点已经公开
`_sources/data/.../*.md.txt`，它比 HTML 更稳定、更小，也避免页面导航和样式噪声。
JSON 只作为索引，不应替代原文，因为参数表、示例代码和数据示例仍然只在原文中。

运行时不要把整份文档直接放入系统提示词。应先在 JSON 索引中按接口名或描述检索，
再从对应 Markdown 的标题附近读取相关段落。接口文档只能帮助模型选择接口；实际数据
仍应通过白名单工具调用 AKShare 获取。

## 更新

从 AKShare 官方站点同步全部支持的文档：

```bash
uv run python scripts/sync_akshare_docs.py
```

从已有本地快照导入，适合离线或首次迁移：

```bash
uv run python scripts/sync_akshare_docs.py \
  --source-directory Auto-GPT-Stock-main/data
```

只更新股票文档：

```bash
uv run python scripts/sync_akshare_docs.py --documents stock
```

每次更新后应审查原始文档和索引的 diff，并运行测试。索引包含原文 SHA-256，可用于
确认索引与快照是否匹配。

重新生成 Agent 使用的 50 工具索引：

```bash
uv run python scripts/build_tool_docs_index.py
```
