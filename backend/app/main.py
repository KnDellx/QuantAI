"""Interactive command-line entry point."""

from pydantic import ValidationError

from backend.app.service.stock_agent import StockAgentService

HELP_TEXT = """
命令：
  /help  显示帮助
  /new   开始新对话
  /exit  退出

示例：
  贵州茅台现在多少钱？
  看看 600519 过去一个月走势
  平安银行最近有什么新闻？
""".strip()


def main() -> None:
    """Run the interactive stock-agent CLI."""

    try:
        service = StockAgentService()
    except ValidationError:
        print("缺少模型配置。请设置 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL。")
        return

    thread_id = service.new_thread_id()
    print("A 股自然语言查询 Agent 已启动。输入 /help 查看帮助。")

    while True:
        try:
            question = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return

        if question == "/exit":
            print("再见。")
            return
        if question == "/help":
            print(HELP_TEXT)
            continue
        if question == "/new":
            thread_id = service.new_thread_id()
            print("已开始新对话。")
            continue
        if not question:
            continue

        try:
            print(f"\nAgent> {service.ask(question, thread_id)}")
        except Exception as error:
            print(f"\nAgent 调用失败：{type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
