import os
from edd_agent_tools.skills import SkillsState, Skill

class PathResolver:
    """
    ワークフローディレクトリ、出力ディレクトリなど、
    各種パスの解決と決定に関するロジックを提供します。
    """
    def __init__(self):
        self._state = SkillsState()

    def resolve_paths(self, skill_name: str | None, output_dir: str | None, target_entry: str | None = "workflow") -> dict:
        """
        与えられたパラメータに基づいて、ワークフロー関連のパスを解決します。
        """
        design_path_fallback = None
        if output_dir:
            design_path_fallback = os.path.join(os.path.abspath(output_dir), "assets", "design.json")

        skill_obj: Skill = self._state.get_skill(name=skill_name, design_path=design_path_fallback, target_entry=target_entry)
        
        resolved_output_dir = os.path.abspath(output_dir or skill_obj.root_dir)

        return {
            "existing_name": skill_obj.name,
            "output_dir": resolved_output_dir,
            "skill_directory": skill_obj
        }
