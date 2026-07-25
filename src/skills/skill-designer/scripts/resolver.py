import os
from edd_agent_tools.skills import SkillsState, Skill

class PathResolver:
    """スキルディレクトリ、出力ディレクトリ、ソースコードディレクトリなど、
    各種パスの解決と決定に関するロジックを提供します。
    """
    def __init__(self):
        self._state = SkillsState()

    def resolve_paths(self, skill_name: str | None, output_dir: str | None, source_code_dir: str | None, target_entry: str | None = None) -> dict:
        """与えられたパラメータに基づいて、スキル関連のパスを明確に解決します。
        
        Args:
            skill_name: 明示された対象スキル名（更新モード時のみ渡される）。
            output_dir: 生成された design.json を保存するディレクトリのパス。
            source_code_dir: ベースとなる実装コードディレクトリ。
            target_entry: 優先する論理配置先名。

        Returns:
            解決されたパス情報を含む辞書。
        """
        if skill_name:
            # 既存スキルの改修（updateモード）: 明示されたスキル名でスキルオブジェクトを取得
            skill_obj: Skill = self._state.get_skill(name=skill_name, target_entry=target_entry)
            resolved_output_dir = os.path.abspath(output_dir or skill_obj.root_dir)
            resolved_scan_target = os.path.abspath(source_code_dir or skill_obj.source_code_dir)
            existing_name = skill_obj.name
        else:
            # 新規スキルの構築（createモード）: 曖昧な自動解決を廃止し、output_dir のフォルダ名をスキル名として仮決定
            new_skill_name = None
            if output_dir:
                new_skill_name = os.path.basename(output_dir.rstrip("/"))
            
            skill_obj: Skill = self._state.get_skill(name=new_skill_name, target_entry=target_entry)
            resolved_output_dir = os.path.abspath(output_dir or skill_obj.root_dir)
            resolved_scan_target = os.path.abspath(source_code_dir or skill_obj.source_code_dir)
            existing_name = None  # 新規作成のため既存名は None

        return {
            "existing_name": existing_name,
            "output_dir": resolved_output_dir,
            "scan_target": resolved_scan_target,
            "skill_directory": skill_obj
        }
