from typing import Any, Protocol
from google.adk.tools import ToolContext

class ToolMock(Protocol):
    """個々のツールモック挙動を定義するポリモーフィズム用のインターフェース。"""
    async def before_tool(self, tool: Any, args: dict[str, Any], tool_context: ToolContext) -> Any | None:
        """ツール実行前に割り込み、モック結果を返します。
        
        Returns:
            Any | None: 辞書等を返した場合は実実行がバイパスされ、None の場合は次の処理へ流れます。
        """
        ...

class UniversalToolMock(ToolMock):
    """すべてのツール呼び出しをバイパスし、ステートにトリガー履歴を記録した上でダミーレスポンスを返す汎用モック。"""
    async def before_tool(self, tool: Any, args: dict[str, Any], tool_context: ToolContext) -> Any | None:
        # 1. 呼び出されたツールから「スキル名」を特定する
        if tool.name == "load_skill":
            skill_name = args.get("skill") or args.get("skill_name")
        else:
            # ツール名（例: skill_coder）からスキル名（例: skill-coder）を復元
            skill_name = tool.name.replace('_', '-')

        # 2. ADKの合否チェック対象となるステートへ記録（追跡）
        if skill_name:
            agent_name = tool_context.agent_name
            state_key = f"_adk_activated_skill_{agent_name}"
            activated_skills = list(tool_context.state.get(state_key) or [])
            if skill_name not in activated_skills:
                activated_skills.append(skill_name)
                tool_context.state[state_key] = activated_skills

        # 3. 実実行をバイパスするためのダミーレスポンスを返却
        return {
            "status": "success",
            "generated_files": [],
            "result_message": f"Mock execution for tool '{tool.name}' succeeded."
        }

class MockEnvironment:
    """複数の ToolMock オブジェクトを統括管理し、ADK用の統合コールバックを提供するコンテキストオブジェクト。"""
    def __init__(self, mocks: list[ToolMock]):
        self._mocks = mocks

    async def handle_before_tool(self, tool: Any, args: dict[str, Any], tool_context: ToolContext) -> Any | None:
        """登録されたモックを順次評価（ポリモーフィズムによる呼び出し）します。"""
        for mock in self._mocks:
            result = await mock.before_tool(tool, args, tool_context)
            if result is not None:
                return result
        return None
