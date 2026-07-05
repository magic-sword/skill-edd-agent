import os
from edd_agent_tools.registry import SkillRegistry
from edd_agent_tools.directory import SkillDirectory

class PathResolver:
    """
    スキルディレクトリ、出力ディレクトリ、ソースコードディレクトリなど、
    各種パスの解決と決定に関するロロジックを提供します。
    """
    def __init__(self):
        self._registry = SkillRegistry()

    def resolve_paths(self, skill_name: str | None, output_dir: str | None, source_code_dir: str | None) -> dict:
        """
        与えられたパラメータに基づいて、スキル関連のパスを解決します。
        
        Args:
            skill_name: 既存のスキル名。
            output_dir: 生成されたdesign.jsonを保存するディレクトリのパス。
            source_code_dir: 再設計のベースとなる既存のスキル実装コードのディレクトリ（またはファイル）パス。

        Returns:
            解決されたパス情報を含む辞書。
        """
        design_path_fallback = None
        if not skill_name and output_dir:
            design_path_fallback = os.path.join(os.path.abspath(output_dir), "assets", "design.json")

        directory: SkillDirectory = self._registry.get_skill_directory(name=skill_name, design_path=design_path_fallback)
        
        resolved_output_dir = os.path.abspath(output_dir or directory.root_dir)
        resolved_scan_target = os.path.abspath(source_code_dir or directory.source_code_dir)

        return {
            "existing_name": directory.name,
            "output_dir": resolved_output_dir,
            "scan_target": resolved_scan_target,
            "skill_directory": directory # SkillDirectoryオブジェクトも返す
        }
