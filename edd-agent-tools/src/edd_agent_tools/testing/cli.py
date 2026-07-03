import argparse
import json
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing.mock_context import MockInvocationContext


class SkillCommandLineRunner:
    """スキルスクリプトをオブジェクト指向でCLIから直接実行可能にするための共通ランナー"""
    def __init__(self, description="Skill Script CLI Runner"):
        self.parser = argparse.ArgumentParser(description=description)
        self.parser.add_argument("--input_json", type=str, help="JSON string containing input parameters")
        self.parser.add_argument("--output_json", type=str, help="Path to write the output JSON to")

    def add_argument(self, *args, **kwargs):
        """内部パーサーに独自引数を登録します。"""
        self.parser.add_argument(*args, **kwargs)

    def run(self, process_func):
        """引数のパース、状態のマージ、およびビジネスロジックの実行を行います。"""
        args = self.parser.parse_args()
        
        # ToolContextの初期化
        tool_context = ToolContext(invocation_context=MockInvocationContext())

        # 1. 独自引数を自動的に state にマージ (input_json と output_json は除外)
        for key, value in vars(args).items():
            if key not in ["input_json", "output_json"] and value is not None:
                tool_context.state[key] = value

        # 2. 入力JSONのロードとstateのアップデート
        if args.input_json:
            try:
                input_data = json.loads(args.input_json)
                tool_context.state.update(input_data)
            except Exception as e:
                print(f"Error parsing input_json: {e}", file=sys.stderr)
                sys.exit(1)

        # 3. 渡されたビジネスロジックを実行
        try:
            process_func(tool_context)
        except Exception as e:
            print(f"Error executing business logic: {e}", file=sys.stderr)
            sys.exit(1)

        # 常に結果を stdout に出力する（呼び出し元エージェントや検証ツールが結果を確認できるようにするため）
        state_data = tool_context.state.to_dict() if hasattr(tool_context.state, "to_dict") else dict(tool_context.state)
        result_json = json.dumps(state_data, ensure_ascii=False, indent=2)
        print(result_json)

        # 指定があればファイルにも書き出す
        if args.output_json:
            try:
                with open(args.output_json, 'w', encoding='utf-8') as f:
                    f.write(result_json)
            except Exception as e:
                print(f"Error writing to output_json: {e}", file=sys.stderr)
                sys.exit(1)

# 後方互換性のためのブリッジ（非推奨）
def get_base_parser(description="Skill Script CLI Wrapper") -> argparse.ArgumentParser:
    """【非推奨】代わりに SkillCommandLineRunner を使用してください。"""
    runner = SkillCommandLineRunner(description=description)
    return runner.parser

def run_skill_as_cli(process_func, parser=None):
    """【非推奨】代わりに SkillCommandLineRunner を使用してください。"""
    if parser is None:
        runner = SkillCommandLineRunner()
    else:
        # 既存パーサーを流用
        runner = SkillCommandLineRunner()
        runner.parser = parser
    runner.run(process_func)


def get_patched_env(base_env: dict = None) -> dict:
    """ADK 評価エンジンで日本語などの多言語トークナイズを有効にするためのパッチ済みの環境変数を取得します。"""
    import os
    if base_env is None:
        base_env = os.environ.copy()
        
    # patch ディレクトリの絶対パスを解決
    patch_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "patch"))
    
    # PYTHONPATH に追加する
    current_pythonpath = base_env.get("PYTHONPATH", "")
    if current_pythonpath:
        base_env["PYTHONPATH"] = f"{patch_dir}:{current_pythonpath}"
    else:
        base_env["PYTHONPATH"] = patch_dir
    return base_env


