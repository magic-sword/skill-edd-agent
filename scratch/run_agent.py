"""
エージェントを直接動作させ、ダミースキルを生成させるテストスクリプト。
内部で edd-agent-tools の run_system_command ツールを使用します。
"""
import sys
import os

# パスの解決 (edd-agent-toolsの開発用ローカルパスを優先)
sys.path.append("/workspace/edd-agent-tools/src")

from edd_agent_tools.utils import run_system_command
from google.adk.tools import ToolContext
from edd_agent_tools.testing import MockInvocationContext

def main():
    prompt = (
        "src/skills/dummy-skill ディレクトリに、入力された数値を2倍にする "
        "dummy-skill スキルを生成してください。"
    )
    print("エージェントに以下の指示を送信します:")
    print(f"「{prompt}」\n")
    
    # 環境変数 GEMINI_API_KEY を確認
    if not os.environ.get("GEMINI_API_KEY"):
        print("エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
        sys.exit(1)
        
    print("エージェント実行中 (run_system_command を経由して同期実行)...")
    
    venv_python = "/workspace/.venv/bin/python"
    command_str = f"{venv_python} -m google.adk.cli run -v /workspace/src \"{prompt}\""
    
    # ToolContextのセットアップ
    context = ToolContext(invocation_context=MockInvocationContext())
    context.state["command"] = command_str
    context.state["cwd"] = "/workspace"
    context.state["timeout_seconds"] = 300  # エージェント実行用に長めのタイムアウト
    
    # 同期実行
    result_message = run_system_command(context)
    print("\n--- 実行結果 ---")
    print(result_message)

if __name__ == "__main__":
    main()
