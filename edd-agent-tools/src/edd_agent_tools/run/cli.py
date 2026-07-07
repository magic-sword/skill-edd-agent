"""
Unified CLI runner for executing agent skills dynamically based on their handler schema.
"""
import sys
import os
import argparse
import json

# 多言語パッチ（モンキーパッチ）の強制インプロセス適用
try:
    import edd_agent_tools.run.patch.usercustomize
except ImportError:
    pass

# Ensure edd-agent-tools is in path if executed directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from google.adk.tools import ToolContext
from edd_agent_tools.run.mock_context import MockInvocationContext
from edd_agent_tools.run.loader import SkillLoader
from edd_agent_tools.run.cli_parser import SchemaArgumentParser

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
            validated_input, parsed_args = arg_parser.parse_and_validate(sys.argv[2:])
        except Exception as e:
            print(f"Validation Error: {e}", file=sys.stderr)
            sys.exit(1)

        # 3. ToolContext の初期化と Mock Context のバインド
        tool_context = ToolContext(invocation_context=MockInvocationContext())
        tool_context.state["validated_input"] = validated_input

        # 4. ビジネスロジック（process_message）の呼び出し
        try:
            result_message = process_message(validated_input, tool_context)
            if result_message and isinstance(result_message, str):
                tool_context.state["message"] = result_message
                if "status" not in tool_context.state:
                    tool_context.state["status"] = "passed"
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
    # 最初の引数を位置引数としてスキル名を取得
    # ただし、位置引数（スキル名）の前に --min-tier オプションがある場合は、それを除去・解析する
    args = sys.argv[1:]
    min_tier_val = None  # デフォルトは None (save側で READ_ONLY になる)
    
    filtered_args = []
    i = 0
    while i < len(args):
        if args[i] in ("--min-tier", "--min_tier"):
            if i + 1 < len(args):
                try:
                    # 数値（0〜3）での指定を想定
                    min_tier_val = int(args[i+1])
                except ValueError:
                    # 文字列名（SANDBOX 等）での指定もサポート
                    from edd_agent_tools.skills.models import SkillTier
                    try:
                        min_tier_val = SkillTier[args[i+1].upper()]
                    except KeyError:
                        print(f"Error: Invalid --min-tier value: {args[i+1]}", file=sys.stderr)
                        sys.exit(1)
                i += 2
                continue
        filtered_args.append(args[i])
        i += 1

    if not filtered_args or filtered_args[0].startswith("-"):
        print("Error: Skill name is required as the first argument.", file=sys.stderr)
        print("Usage: python3 -m edd_agent_tools.run [--min-tier <val>] <skill_name> [options]", file=sys.stderr)
        sys.exit(1)

    skill_name = filtered_args[0]
    
    # sys.argv 自体を書き換えて、下流の SchemaArgumentParser などのパース処理が正しく動作するように調整する
    # argv[0] はそのまま残し、残りの引数を filtered_args[1:] で置き換える
    sys.argv = [sys.argv[0], skill_name] + filtered_args[1:]

    # 【最新設定の同期と skills.json の出力（自動同期）】
    try:
        from edd_agent_tools.skills import SkillsState, SkillTier
        state = SkillsState()
        state.load()
        
        # 閾値が指定された場合は Pydantic Enum 型に変換して save に引き渡す
        filter_tier = None
        if min_tier_val is not None:
            filter_tier = SkillTier(min_tier_val)
            
        state.save(filter_tier=filter_tier)
    except Exception as e:
        print(f"Warning: Failed to sync and generate skills.json: {e}", file=sys.stderr)

    runner = SkillRunner(skill_name)
    runner.run()

if __name__ == "__main__":
    run_cli()
