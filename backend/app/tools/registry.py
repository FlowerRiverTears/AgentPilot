from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ToolRead:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class ToolResult:
    tool_id: str
    name: str
    content: str


class ToolRegistry:
    def list_tools(self) -> list[ToolRead]:
        return [
            ToolRead(
                id="current_time",
                name="当前时间",
                description="回答涉及当前日期、当前时间、今天、现在等问题时使用。",
            ),
            ToolRead(
                id="order_lookup",
                name="订单查询示例",
                description="演示从应用系统查询订单状态，适合测试业务数据不是知识库的场景。",
            ),
        ]

    async def run_for_input(self, enabled_tool_ids: list[str], user_input: str) -> list[ToolResult]:
        results: list[ToolResult] = []
        enabled = set(enabled_tool_ids)
        text = user_input.lower()

        if "current_time" in enabled and self._mentions_time(text):
            now = datetime.now(timezone.utc).astimezone()
            results.append(
                ToolResult(
                    tool_id="current_time",
                    name="当前时间",
                    content=f"当前服务器时间：{now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                )
            )

        if "order_lookup" in enabled and self._mentions_order(text):
            order_id = self._extract_order_id(user_input)
            results.append(
                ToolResult(
                    tool_id="order_lookup",
                    name="订单查询示例",
                    content=(
                        f"订单号：{order_id or '未提供'}\n"
                        "状态：待发货\n"
                        "支付状态：已支付\n"
                        "预计发货：下一个工作日\n"
                        "说明：这是内置示例工具结果，后续可替换为真实业务 API。"
                    ),
                )
            )

        return results

    def _mentions_time(self, text: str) -> bool:
        return any(keyword in text for keyword in ("time", "date", "today", "now", "时间", "日期", "今天", "现在"))

    def _mentions_order(self, text: str) -> bool:
        return any(keyword in text for keyword in ("order", "订单", "物流", "发货", "快递"))

    def _extract_order_id(self, text: str) -> str:
        for token in text.replace("：", " ").replace(":", " ").split():
            if any(char.isdigit() for char in token) and len(token) >= 4:
                return token.strip(",，。")
        return ""


tool_registry = ToolRegistry()
