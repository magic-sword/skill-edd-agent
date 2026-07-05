import sys
import os
from typing import Tuple, Dict, Any, Type
from pydantic import BaseModel
from edd_agent_tools.registry import SkillRegistry

class SkillLoader:
    """
    指定されたスキル名に基づいて、scripts/__init__.py を動的ロードし、
    メタデータ、Inputスキーマ、process_message関数を抽出・検証するローダー。
    """
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.skill_dir = None
        self.handler_module = None

    def load(self) -> Tuple[Dict[str, Any], Type[BaseModel], Any]:
        # 1. レジストリを介して対象モジュールを安全にロード
        registry = SkillRegistry()
        skill_obj = registry.get_skill(self.skill_name)
        self.skill_dir = skill_obj.root_dir
        
        try:
            self.handler_module = skill_obj.load_module()
        except Exception as e:
            raise ImportError(f"Failed to load skill for '{self.skill_name}': {e}")
            
        # 2. 必要なモジュール定義の存在確認と抽出
        if not hasattr(self.handler_module, "Input"):
            raise AttributeError(f"'Input' schema class not defined in scripts/__init__.py of '{self.skill_name}'.")
        if not hasattr(self.handler_module, "process_message"):
            raise AttributeError(f"'process_message' function not defined in scripts/__init__.py of '{self.skill_name}'.")
            
        InputSchema = getattr(self.handler_module, "Input")
        process_message = getattr(self.handler_module, "process_message")
        metadata = getattr(self.handler_module, "SKILL_METADATA", {})
        
        return metadata, InputSchema, process_message
