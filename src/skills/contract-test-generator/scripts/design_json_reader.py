import json
from pathlib import Path
from typing import Optional

from edd_agent_tools.skills import SkillsState
from .types import DesignJson

class DesignJsonReader:
    """design.jsonファイルの読み込みとパースを行うクラス。"""
    def __init__(self):
        self._state = SkillsState()

    def get_design_json_path(self, skill_name: str) -> Path:
        """
        指定されたスキルのdesign.jsonファイルのパスを構築します。

        Args:
            skill_name: 対象スキルの名前。

        Returns:
            design.jsonファイルへのPathオブジェクト。
        """
        skill_obj = self._state.get_skill(skill_name)
        return Path(skill_obj.design_path)

    def parse_design_json_content(self, content: str) -> Optional[DesignJson]:
        """
        design.jsonのJSON文字列をパースし、DesignJsonオブジェクトとして返します。

        Args:
            content: design.jsonファイルのJSON文字列。

        Returns:
            DesignJsonオブジェクト、またはパース失敗の場合はNone。
        """
        try:
            design_data = json.loads(content)
            return DesignJson(**design_data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing design.json content: {e}")
            return None
