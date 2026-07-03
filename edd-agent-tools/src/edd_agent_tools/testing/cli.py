import argparse
import json
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.testing.mock_context import MockInvocationContext

# インポートキャッシュの不整合対策
sys.modules.pop('google', None)
sys.modules.pop('google.adk', None)

def run_skill_as_cli(process_func):
    """スキルスクリプトをCLIから直接実行可能にするための共通ラッパー"""
    parser = argparse.ArgumentParser(description="Skill Script CLI Wrapper")
    parser.add_argument("--input_json", type=str, help="JSON string containing input parameters")
    parser.add_argument("--output_json", type=str, help="Path to write the output JSON to")

    args = parser.parse_args()
    
    # ToolContextの初期化
    tool_context = ToolContext(invocation_context=MockInvocationContext())

    # 入力JSONのロードとstateのアップデート
    if args.input_json:
        try:
            input_data = json.loads(args.input_json)
            tool_context.state.update(input_data)
        except Exception as e:
            print(f"Error parsing input_json: {e}", file=sys.stderr)
            sys.exit(1)

    # 渡されたビジネスロジックを実行
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
