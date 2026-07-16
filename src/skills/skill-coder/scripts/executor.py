import os
import json
import asyncio
from .models import SkillCoderOutput


from .logic import SkillLogic

class SkillExecutor:
    """
    SkillDeveloperAgent を統制し、アセットおよびモジュールコード生成を実行する
    オブジェクト指向のビジネスロジックエグゼキューター。
    """
    def __init__(self):
        pass

    def skill_coder(self, prompt: str | None = None, skill: str | None = None, design_path: str | None = None, output_dir: str | None = None) -> SkillCoderOutput:
        # ビジネスロジックを SkillLogic に委譲
        logic_instance = SkillLogic(
            prompt=prompt,
            skill=skill,
            design_path=design_path,
            output_dir=output_dir
        )
        return logic_instance.execute()


