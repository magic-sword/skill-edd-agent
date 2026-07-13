import sys
import os
from typing import Dict, Any, Callable
from edd_agent_tools.skills import SkillsState

class SkillLoader:
    """
    指定されたスキル名に基づいて、scripts/__init__.py を動的ロードし、
    公開されているすべての callableな関数を抽出・検証するローダー。
    """
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.skill_dir = None
        self.handler_module = None

    def load(self) -> Dict[str, Callable]:
        """
        対象モジュールをロードし、__all__ に宣言されている callable な公開関数を返します。
        """
        # 1. 状態管理を介して対象モジュールを安全にロード
        state = SkillsState()
        skill_obj = state.get_skill(self.skill_name)
        self.skill_dir = skill_obj.root_dir
        
        try:
            self.handler_module = skill_obj.load_module()
        except Exception as e:
            raise ImportError(f"Failed to load skill for '{self.skill_name}': {e}")
            
        # 2. __all__ に宣言されている属性のうち、callableな関数を抽出
        if not hasattr(self.handler_module, "__all__"):
            raise AttributeError(f"__all__ is not defined in scripts/__init__.py of '{self.skill_name}'.")
            
        exports = getattr(self.handler_module, "__all__")
        functions = {}
        for name in exports:
            attr = getattr(self.handler_module, name, None)
            # Pydanticモデルなどのクラスではなく、callable（関数）のみを対象とする
            if attr and callable(attr) and not isinstance(attr, type):
                functions[name] = attr
                
        if not functions:
            raise AttributeError(f"No callable functions exported in __all__ of '{self.skill_name}'.")
            
        return functions
