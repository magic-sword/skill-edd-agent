import os
import sys
import json

class Command:
    """サブプロセスで実行可能なコマンドの基底抽象クラス"""
    def build_cmd_args(self) -> list[str]:
        """サブプロセス起動用の引数リスト（リストの第1要素はバイナリ）を返します。"""
        raise NotImplementedError


class SkillCommand(Command):
    """登録されたスキルを実行するためのコマンドクラス"""
    def __init__(self, skill_name: str, args: list[str] = None, input_data: dict = None, registry=None):
        self.skill_name = skill_name
        self.args = args or []
        self.input_data = input_data
        from edd_agent_tools.registry import SkillRegistry
        self.registry = registry or SkillRegistry()
        self.registry.load()

    def build_cmd_args(self) -> list[str]:
        skill_dir = self.registry.resolve_skill_dir(self.skill_name)
        main_py_path = os.path.join(skill_dir, "scripts", "main.py")
        if not os.path.exists(main_py_path):
            main_py_path = os.path.join(skill_dir, "main.py")
            
        python_bin = sys.executable or "python3"
        cmd = [python_bin, main_py_path]
        
        if self.args:
            cmd.extend(self.args)
        if self.input_data:
            cmd.extend(["--input_json", json.dumps(self.input_data)])
        return cmd


class SystemCommand(Command):
    """外部システムコマンドを実行するためのコマンドクラス"""
    def __init__(self, command_name: str, args: list[str] = None):
        self.command_name = command_name
        self.args = args or []

    def build_cmd_args(self) -> list[str]:
        cmd = [self.command_name]
        if self.args:
            cmd.extend(self.args)
        return cmd
