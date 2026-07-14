"""
コード生成用の各種ジェネレータクラスのエントリーポイントおよびファクトリ。
"""
from typing import List
from edd_agent_tools.skills import Skill
from edd_agent_tools import SkillDesign, ModuleType

from .generators.base import BaseCodeGenerator
from .generators.skill_generator import ToolSkillCodeGenerator
from .generators.workflow_generator import WorkflowAgentCodeGenerator


class CodeGenerator:
    """
    スキルまたはワークフローの実装に必要なコードファイルを
    決定論的に自動生成するファクトリラッパークラス。
    """
    def __init__(self, 
                 design: SkillDesign, 
                 target_root_dir: str, 
                 coder_skill: Skill):
        # module_type に応じて適切なジェネレータを選択
        if design.module_type == ModuleType.WORKFLOW:
            self._generator = WorkflowAgentCodeGenerator(design, target_root_dir, coder_skill)
        else:
            self._generator = ToolSkillCodeGenerator(design, target_root_dir, coder_skill)

    def generate_all(self) -> List[str]:
        """
        すべての決定論的ファイルを生成します。
        生成されたファイルの相対パスリストを返します。
        """
        return self._generator.generate()
