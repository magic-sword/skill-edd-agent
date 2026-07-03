import os
import sys
import json

class Command:
    """サブプロセスまたはインプロセスで実行可能なコマンドの基底抽象クラス"""
    def build_cmd_args(self) -> list[str]:
        """サブプロセス起動用の引数リスト（リストの第1要素はバイナリ）を返します。"""
        raise NotImplementedError

    def build_exec_args(self) -> tuple[list, dict]:
        """インプロセス実行時にビジネスロジック関数に手渡す引数（args, kwargs）を構築します。"""
        raise NotImplementedError

    def handle_result(self, exec_args: list) -> None:
        """ビジネスロジック実行完了後に結果の出力・永続化処理を行います。"""
        pass


class SkillCommand(Command):
    """登録されたスキルを実行するためのコマンドクラス"""
    def __init__(self, skill_name: str, args: list[str] = None, input_data: dict = None, registry=None):
        self.skill_name = skill_name
        self.args = args or []
        self.input_data = input_data or {}
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
            # 外部プロセス用に --input_json 引数にする
            cmd.extend(["--input_json", json.dumps(self.input_data, ensure_ascii=False)])
        return cmd

    @classmethod
    def from_argv(cls, skill_name: str, argv: list[str]) -> 'SkillCommand':
        """CLI 引数リストから SkillCommand を動的にパース・構築します。"""
        import argparse
        
        parser = argparse.ArgumentParser(description=f"{skill_name} Command Parser")
        parser.add_argument("--input_json", type=str, help="JSON string containing input parameters")
        parser.add_argument("--output_json", type=str, help="Path to write the output JSON to")
        
        # 固有引数を透過的に許容するため parse_known_args を使用
        known_args, unknown_args = parser.parse_known_args(argv)
        
        input_data = {}
        if known_args.input_json:
            try:
                input_data = json.loads(known_args.input_json)
            except Exception as e:
                raise ValueError(f"Error parsing input_json: {e}")
                
        if known_args.output_json:
            input_data["output_json"] = known_args.output_json
            
        # 簡易キーバリューパーサーで未知の引数（--param value）をパースしてマージ
        i = 0
        while i < len(unknown_args):
            arg = unknown_args[i]
            if arg.startswith("--"):
                key = arg[2:]
                if i + 1 < len(unknown_args) and not unknown_args[i+1].startswith("--"):
                    val = unknown_args[i+1]
                    # 数値やブーリアンの簡易変換
                    if val.lower() == "true": val = True
                    elif val.lower() == "false": val = False
                    else:
                        try:
                            if "." in val: val = float(val)
                            else: val = int(val)
                        except ValueError:
                            pass
                    input_data[key] = val
                    i += 2
                else:
                    input_data[key] = True
                    i += 1
            else:
                i += 1
                
        return cls(skill_name=skill_name, args=argv, input_data=input_data)

    def build_exec_args(self) -> tuple[list, dict]:
        from google.adk.tools import ToolContext
        from edd_agent_tools.testing.mock_context import MockInvocationContext
        
        # ToolContext の初期化と Mock Context のバインド
        tool_context = ToolContext(invocation_context=MockInvocationContext())
        
        # 入力データをマージ
        if self.input_data:
            tool_context.state.update(self.input_data)
            
        # ビジネスロジックには第1引数として ToolContext を渡す
        return [tool_context], {}

    def handle_result(self, exec_args: list) -> None:
        if not exec_args:
            return
        tool_context = exec_args[0]
        
        # 結果を stdout に書き出し
        state_data = tool_context.state.to_dict() if hasattr(tool_context.state, "to_dict") else dict(tool_context.state)
        result_json = json.dumps(state_data, ensure_ascii=False, indent=2)
        print(result_json)
        
        # output_json が指定されていれば保存
        output_json = self.input_data.get("output_json")
        if output_json:
            try:
                with open(output_json, 'w', encoding='utf-8') as f:
                    f.write(result_json)
            except Exception as e:
                print(f"Error writing to output_json: {e}", file=sys.stderr)
                sys.exit(1)


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

    def build_exec_args(self) -> tuple[list, dict]:
        # 外部コマンドは ToolContext を必要としないため空
        return [], {}
