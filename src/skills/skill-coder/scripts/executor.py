import os
import json
import asyncio
from .models import Output
# from .code_generator import CodeGenerator # logic.py に移動
# from .agent_executor import SkillDeveloperAgentExecutor # logic.py に移動

from .logic import SkillLogic

class SkillExecutor:
    """
    SkillDeveloperAgent を統制し、アセットおよびモジュールコード生成を実行する
    オブジェクト指向のビジネスロジックエグゼキューター。
    """
    def __init__(self, prompt: str, skill: str = None, design_path: str = None, output_dir: str = None):
        self.prompt = prompt
        self.skill = skill
        self.design_path = design_path
        self.output_dir = output_dir

    def execute(self) -> Output:
        # ビジネスロジックを SkillLogic に委譲
        logic_instance = SkillLogic(
            prompt=self.prompt,
            skill=self.skill,
            design_path=self.design_path,
            output_dir=self.output_dir
        )
        return logic_instance.execute()

    # _run_safe メソッドは logic.py に移動したため、ここからは削除
