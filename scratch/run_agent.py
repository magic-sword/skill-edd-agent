"""
エージェントを直接動作させ、ダミースキルを生成させるテストスクリプト。
内部で ADK CLI の run コマンドをサブプロセスで呼び出します。
"""
import sys
import os
import subprocess

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
        
    print("エージェント実行中 (ADK CLI を経由して実行)...")
    
    venv_python = "/workspace/.venv/bin/python"
    command = [
        venv_python, "-m", "google.adk.cli", "run",
        "-v",
        "/workspace/src",
        prompt
    ]
    
    result = subprocess.run(command, capture_output=False, text=True)
    if result.returncode == 0:
        print("\n🎉 エージェントの実行が正常に完了しました！")
    else:
        print(f"\n❌ エージェントの実行中にエラーが発生しました（Exit Code: {result.returncode}）")

if __name__ == "__main__":
    main()
