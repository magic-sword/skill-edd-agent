import os
from edd_agent_tools.skills import SkillsState, Skill

class PathResolver:
    """
    スキルディレクトリ、出力ディレクトリ、ソースコードディレクトリなど、
    各種パスの解決と決定に関するロロジックを提供します。
    """
    def __init__(self):
        self._state = SkillsState()

    def resolve_paths(self, skill_name: str | None, output_dir: str | None, source_code_dir: str | None, target_entry: str | None = None) -> dict:
        """
        与えられたパラメータに基づいて、スキル関連のパスを解決します。
        
        Args:
            skill_name: 既存のスキル名。
            output_dir: 生成されたdesign.jsonを保存するディレクトリのパス。
            source_code_dir: 再設計のベースとなる既存のスキル実装コードのディレクトリ（またはファイル）パス。
            target_entry: 優先する論理配置先名。

        Returns:
            解決されたパス情報を含む辞書。
        """
        design_path_fallback = None
        if output_dir:
            design_path_fallback = os.path.join(os.path.abspath(output_dir), "assets", "design.json")

        skill_obj: Skill = self._state.get_skill(name=skill_name, design_path=design_path_fallback, target_entry=target_entry)
        
        resolved_output_dir = os.path.abspath(output_dir or skill_obj.root_dir)
        resolved_scan_target = os.path.abspath(source_code_dir or skill_obj.source_code_dir)

        return {
            "existing_name": skill_obj.name,
            "output_dir": resolved_output_dir,
            "scan_target": resolved_scan_target,
            "skill_directory": skill_obj # Skillオブジェクトも返す
        }
