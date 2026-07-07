import os
import json
import asyncio
from google.adk.tools import ToolContext
# from edd_agent_tools.skills import SkillsState # logic.py に移動
# from edd_agent_tools.models import SkillDesign # logic.py に移動
from .models import Input, Output
# from .code_generator import CodeGenerator # logic.py に移動
# from .agent_executor import SkillDeveloperAgentExecutor # logic.py に移動

from .logic import SkillLogic

class SkillExecutor:
    """
    SkillDeveloperAgent を統制し、アセットおよびモジュールコード生成を実行する
    オブジェクト指向のビジネスロジックエグゼキューター。
    """
    def __init__(self, params: Input, tool_context: ToolContext):
        self.params = params
        self.tool_context = tool_context
        # self.state = SkillsState() # logic.py に移動

    def execute(self) -> Output:
        # ビジネスロジックを SkillLogic に委譲
        logic_instance = SkillLogic(self.params, self.tool_context)
        return logic_instance.execute()

    # _run_safe メソッドは logic.py に移動したため、ここからは削除
