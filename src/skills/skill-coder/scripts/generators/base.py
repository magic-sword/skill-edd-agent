import os
from abc import ABC, abstractmethod
from typing import List

from edd_agent_tools.skills import Skill
from edd_agent_tools import SkillDesign

class BaseCodeGenerator(ABC):
    """
    コードファイル自動生成の抽象基底クラス。
    """
    def __init__(self, 
                 design: SkillDesign, 
                 target_root_dir: str, 
                 coder_skill: Skill):
        self.design = design
        self.target_root_dir = target_root_dir
        self.scripts_dir = os.path.join(target_root_dir, "scripts")
        self.coder_skill = coder_skill

    def create_common_directories(self):
        """共通ディレクトリの作成"""
        os.makedirs(self.scripts_dir, exist_ok=True)
        os.makedirs(os.path.join(self.target_root_dir, "assets"), exist_ok=True)
        os.makedirs(os.path.join(self.target_root_dir, "references"), exist_ok=True)

    @abstractmethod
    def generate(self) -> List[str]:
        """各モジュールタイプに応じた具体的なコード生成処理"""
        pass
