import argparse
import subprocess
import os
import sys
import re

def parse_args():
    parser = argparse.ArgumentParser(description="ADK evalテストを実行し、合格閾値に基づいて判定を行います。")
    parser.add_argument("--skill_name", type=str, required=True, help="テスト対象のスキル名")
    parser.add_argument("--eval_set_path", type=str, required=True, help="テストケース定義ファイルのパス")
    parser.add_argument("--threshold_accuracy", type=float, default=1.0, help="合格に必要な精度の閾値（0.0〜1.0）")
    parser.add_argument("--timeout_seconds", type=int, default=180, help="テスト実行のタイムアウト制限（秒）")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # パスの検証
    eval_set_path = args.eval_set_path
    if not os.path.isabs(eval_set_path):
        eval_set_path = os.path.abspath(os.path.join("/workspace", eval_set_path))
        
    if not os.path.exists(eval_set_path):
        print(f"エラー: テストファイルが存在しません: {eval_set_path}", file=sys.stderr)
        sys.exit(1)
        
    print(f"Running test-executor for skill: {args.skill_name}")
    print(f"Eval set: {eval_set_path}")
    print(f"Threshold accuracy: {args.threshold_accuracy:.2f}, Timeout: {args.timeout_seconds}s")
    
    # adk evalの環境変数の設定 (ハング防止の env -i)
    env = {
        "HOME": "/home/vscode",
        "PATH": os.environ.get("PATH", "/workspace/.venv/bin:/usr/local/bin:/usr/bin:/bin"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
        "ADK_EVAL_MODE": "1" # 評価モードをオンにし、EnvironmentToolsetの干渉を防ぐ
    }
    
    # テストディレクトリに eval_config.json または test_config.json があればそれを指定する
    eval_dir = os.path.dirname(eval_set_path)
    config_file = None
    for cf in ["eval_config.json", "test_config.json"]:
        p = os.path.join(eval_dir, cf)
        if os.path.exists(p):
            config_file = p
            break
            
    # なければ、test-executor用のデフォルト設定 (response_match_scoreのみで判定し、軌跡評価を除外する) を使用
    if not config_file:
        default_config_dir = "/workspace/src/skills/test-executor/assets"
        os.makedirs(default_config_dir, exist_ok=True)
        default_config_path = os.path.join(default_config_dir, "default_eval_config.json")
        if not os.path.exists(default_config_path):
            import json
            with open(default_config_path, "w", encoding="utf-8") as f:
                json.dump({"criteria": {"response_match_score": 0.8}}, f, indent=2)
        config_file = default_config_path

    # 実行するadk evalコマンド
    adk_command = [
        "/workspace/.venv/bin/adk",
        "eval",
        "/workspace/src",
        eval_set_path
    ]
    
    if config_file:
        adk_command.extend(["--config_file_path", config_file])
    
    print(f"Executing: {' '.join(adk_command)}")
    
    try:
        # タイムアウト付きでサブプロセスを実行
        result = subprocess.run(
            adk_command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=args.timeout_seconds
        )
    except subprocess.TimeoutExpired as e:
        print(f"\n❌ エラー: テスト実行がタイムアウト（{args.timeout_seconds}秒）しました。デッドロック防止のため終了します。", file=sys.stderr)
        if e.stdout:
            print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"STDERR:\n{e.stderr}", file=sys.stderr)
        sys.exit(124) # timeoutの標準的な終了コード
        
    # 結果の表示
    print("--- ADK EVAL OUTPUT ---")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    print("-----------------------")
    
    # ログからパス数と失敗数を解析
    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")
    
    passed_match = re.search(r"Tests passed:\s*(\d+)", combined_output)
    failed_match = re.search(r"Tests failed:\s*(\d+)", combined_output)
    
    accuracy = 0.0
    parsed = False
    
    if passed_match and failed_match:
        passed = int(passed_match.group(1))
        failed = int(failed_match.group(1))
        total = passed + failed
        if total > 0:
            accuracy = passed / total
            parsed = True
            print(f"解析結果: 合格 = {passed}, 不合格 = {failed}, 合計 = {total}, 精度 = {accuracy:.4f}")
        else:
            print("警告: 合計テスト数が 0 件です。")
    
    # 正規表現でパースできなかった場合のフォールバック判定
    if not parsed:
        print("警告: ログからテスト結果数を抽出できませんでした。終了コードから合否を判定します。")
        if result.returncode == 0:
            accuracy = 1.0
            print("解析結果(フォールバック): 正常終了 (精度 1.0)")
        else:
            accuracy = 0.0
            print("解析結果(フォールバック): 異常終了 (精度 0.0)")
            
    # 合格判定
    if accuracy >= args.threshold_accuracy:
        print(f"\n🎉 テスト合格! 精度 {accuracy:.4f} >= 閾値 {args.threshold_accuracy:.4f}")
        sys.exit(0)
    else:
        print(f"\n❌ テスト不合格! 精度 {accuracy:.4f} < 閾値 {args.threshold_accuracy:.4f}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
