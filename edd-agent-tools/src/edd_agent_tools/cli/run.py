"""
Unified CLI runner for executing agent skills dynamically based on their handler schema.
"""
import sys
import os
import argparse
import json

# Ensure edd-agent-tools is in path if executed directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from google.adk.tools import ToolContext
from edd_agent_tools.testing.mock_context import MockInvocationContext
from edd_agent_tools.cli.loader import SkillLoader
from edd_agent_tools.cli.parser import SchemaArgumentParser

class SkillRunner:
    """
    動的にロードされたスキルを実行し、ToolContext のセットアップと結果の出力を管理するランナー。
    """
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        self.loader = SkillLoader(skill_name)

    def run(self):
        # 1. handler.py から定義をロード
        try:
            metadata, InputSchema, process_message = self.loader.load()
        except Exception as e:
            print(f"Error loading skill module: {e}", file=sys.stderr)
            sys.exit(1)

        description = metadata.get("description", f"CLI runner for {self.skill_name}")

        # 2. Pydanticから引数パーサーを構築・実行
        arg_parser = SchemaArgumentParser(InputSchema, description)
        try:
            validated_input, parsed_args = arg_parser.parse_and_validate(sys.argv[1:])
        except Exception as e:
            print(f"Validation Error: {e}", file=sys.stderr)
            sys.exit(1)

        # 3. ToolContext の初期化と Mock Context のバインド
        tool_context = ToolContext(invocation_context=MockInvocationContext())
        tool_context.state["validated_input"] = validated_input

        # 4. ビジネスロジック（process_message）の呼び出し
        try:
            process_message(tool_context)
        except Exception as e:
            print(f"Error executing business logic: {e}", file=sys.stderr)
            tool_context.state.update({
                "status": "failed",
                "message": str(e)
            })
            sys.exit(1)

        # 5. 結果の出力およびファイル保存
        state_data = tool_context.state.to_dict() if hasattr(tool_context.state, "to_dict") else dict(tool_context.state)
        
        # Pydanticオブジェクトはシリアライズできないため除外
        if "validated_input" in state_data:
            del state_data["validated_input"]

        result_json = json.dumps(state_data, ensure_ascii=False, indent=2)
        print(result_json)

        if parsed_args.output_json:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(parsed_args.output_json)), exist_ok=True)
                with open(parsed_args.output_json, 'w', encoding='utf-8') as f:
                    f.write(result_json)
            except Exception as e:
                print(f"Error writing to output_json: {e}", file=sys.stderr)
                sys.exit(1)

def run_cli():
    # 予備パースで最初の --skill_name のみを取得 (どのローダーを初期化するか決定するため)
    skill_name = None
    try:
        idx = sys.argv.index("--skill_name")
        if idx + 1 < len(sys.argv):
            skill_name = sys.argv[idx + 1]
    except ValueError:
        pass

    if not skill_name:
        print("Error: --skill_name is required.", file=sys.stderr)
        sys.exit(1)

    runner = SkillRunner(skill_name)
    runner.run()

if __name__ == "__main__":
    run_cli()
