import sys
import os
from typing import Tuple, Dict, Any, Type
from pydantic import BaseModel
from edd_agent_tools.registry import SkillRegistry

class SkillLoader:
    """
    指定されたスキル名に基づいて、scripts/handler.py を動的インポートし、
    メタデータ、Inputスキーマ、process_message関数を抽出・検証するローダー。
    """
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.skill_dir = None
        self.handler_module = None

    def load(self) -> Tuple[Dict[str, Any], Type[BaseModel], Any]:
        # 1. レジストリを介して対象モジュールを安全にロード
        registry = SkillRegistry()
        self.skill_dir = registry.get_skill_dir(self.skill_name)
        
        try:
            self.handler_module = registry.load_handler(self.skill_name)
        except Exception as e:
            raise ImportError(f"Failed to load handler for skill '{self.skill_name}': {e}")
            
        # 2. 必要なモジュール定義の存在確認と抽出
        if not hasattr(self.handler_module, "Input"):
            raise AttributeError(f"'Input' schema class not defined in scripts/handler.py of '{self.skill_name}'.")
        if not hasattr(self.handler_module, "process_message"):
            raise AttributeError(f"'process_message' function not defined in scripts/handler.py of '{self.skill_name}'.")
            
        InputSchema = getattr(self.handler_module, "Input")
        process_message = getattr(self.handler_module, "process_message")
        metadata = getattr(self.handler_module, "SKILL_METADATA", {})
        
        return metadata, InputSchema, process_message
