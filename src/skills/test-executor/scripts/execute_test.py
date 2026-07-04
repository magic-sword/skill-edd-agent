import argparse
import subprocess
import os
import sys
import re
from google.adk.tools import ToolContext
import subprocess



def execute_test_logic(tool_context: ToolContext):
    skill_name = tool_context.state.get("skill_name")
    eval_set_path = tool_context.state.get("eval_set_path")
    threshold_accuracy = tool_context.state.get("threshold_accuracy", 1.0)
    timeout_seconds = tool_context.state.get("timeout_seconds", 180)
    eval_mode = tool_context.state.get("eval_mode", 1)

    if not skill_name or not eval_set_path:
        raise ValueError("エラー: --skill_name と --eval_set_path、もしくは --input_json は必須です。")
        
    # パスの検証
    if not os.path.isabs(eval_set_path):
        eval_set_path = os.path.abspath(os.path.join("/workspace", eval_set_path))
        
    if not os.path.exists(eval_set_path):
        raise FileNotFoundError(f"エラー: テストファイルが存在しません: {eval_set_path}")
        
    print(f"Running test-executor for skill: {skill_name}")
    print(f"Eval set: {eval_set_path}")
    print(f"Threshold accuracy: {threshold_accuracy:.2f}, Timeout: {timeout_seconds}s, Eval mode: {eval_mode}")
    
    # adk evalの環境変数の設定 (ハング防止の env -i)
    env = {
        "HOME": "/home/vscode",
        "PATH": os.environ.get("PATH", "/workspace/.venv/bin:/usr/local/bin:/usr/bin:/bin"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
        "ADK_EVAL_MODE": str(eval_mode)
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
 
    # SystemCommand の引数リストを定義
    args = ["eval", "/workspace/src", eval_set_path]
    if config_file:
        args.extend(["--config_file_path", config_file])
    
    print(f"Executing: adk {' '.join(args)}")
    
    # 評価エンジンのための多言語パッチ環境変数の構成
    patched_env = os.environ.copy() if env is None else env.copy()
    patch_dir = os.path.abspath(os.path.join("/workspace/edd-agent-tools/src/edd_agent_tools/testing/patch"))
    current_pythonpath = patched_env.get("PYTHONPATH", "")
    if current_pythonpath:
        patched_env["PYTHONPATH"] = f"{patch_dir}:{current_pythonpath}"
    else:
        patched_env["PYTHONPATH"] = patch_dir
        
    edd_tools_path = os.path.abspath("/workspace/edd-agent-tools/src")
    patched_env["PYTHONPATH"] = f"{edd_tools_path}:{patched_env['PYTHONPATH']}"

    try:
        cmd_args = ["adk"] + args
        result = subprocess.run(
            cmd_args,
            env=patched_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            cwd="/workspace"
        )
        if result.returncode != 0:
            print(f"Subprocess 'adk' failed with exit code {result.returncode}.", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            sys.exit(1)
    except subprocess.TimeoutExpired as e:
        print(f"\n❌ エラー: テスト実行がタイムアウト（{timeout_seconds}秒）しました。デッドロック防止のため終了します。", file=sys.stderr)
        if e.stdout:
            print(f"STDOUT:\n{e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"STDERR:\n{e.stderr}", file=sys.stderr)
        
        tool_context.state.update({
            "status": "failed",
            "message": f"Timeout after {timeout_seconds} seconds.",
            "accuracy": 0.0,
            "threshold_accuracy": threshold_accuracy
        })
        raise RuntimeError(f"Timeout after {timeout_seconds} seconds.") from e
        
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
    status = "passed" if accuracy >= threshold_accuracy else "failed"
    message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
    
    tool_context.state.update({
        "status": status,
        "message": message,
        "accuracy": accuracy,
        "threshold_accuracy": threshold_accuracy
    })
    
    if status == "passed":
        print(f"\n🎉 テスト合格! 精度 {accuracy:.4f} >= 閾値 {threshold_accuracy:.4f}")
    else:
        print(f"\n❌ テスト不合格! 精度 {accuracy:.4f} < 閾値 {threshold_accuracy:.4f}", file=sys.stderr)
        raise RuntimeError(message)

def run_skill_tests(eval_mode: int, threshold_accuracy: float, tool_context: ToolContext) -> str:
    """
    指定されたスキルのテストを実行します。
    引数:
      eval_mode: 1 (単体テスト評価用) または 0 (トリガー評価用)
      threshold_accuracy: 合格に必要な精度の閾値（0.0〜1.0）
    """
    skill_name = tool_context.state.get("skill_name")
    
    if eval_mode == 1:
        eval_set_path = tool_context.state.get("eval_set_path")
        step_name = "04_ut_exec"
    else:
        eval_set_path = tool_context.state.get("trig_eval_set_path")
        step_name = "06_trig_exec"
        
    if not skill_name or not eval_set_path:
        raise ValueError("セッション状態に 'skill_name' または 'eval_set_path' / 'trig_eval_set_path' が設定されていません。")
        
    output_json_path = f"/workspace/src/.workflow_tmp/{skill_name}/{step_name}_out.json"
    
    # 共通ランナー（edd-run）を用いたスキル CLI サブプロセス実行
    cmd_args = [
        sys.executable, "-m", "edd_agent_tools.cli.run",
        "--skill_name", "test-executor",
        "--skill_name", skill_name,
        "--eval_set_path", eval_set_path,
        "--threshold_accuracy", str(threshold_accuracy),
        "--eval_mode", str(eval_mode),
        "--output_json", output_json_path
    ]
    
    # 評価エンジンのための多言語パッチ環境変数の構成
    patched_env = os.environ.copy()
    patch_dir = os.path.abspath(os.path.join("/workspace/edd-agent-tools/src/edd_agent_tools/testing/patch"))
    current_pythonpath = patched_env.get("PYTHONPATH", "")
    if current_pythonpath:
        patched_env["PYTHONPATH"] = f"{patch_dir}:{current_pythonpath}"
    else:
        patched_env["PYTHONPATH"] = patch_dir
        
    edd_tools_path = os.path.abspath("/workspace/edd-agent-tools/src")
    patched_env["PYTHONPATH"] = f"{edd_tools_path}:{patched_env['PYTHONPATH']}"
        
    print(f"Executing: {' '.join(cmd_args)}")
    result = subprocess.run(
        cmd_args,
        env=patched_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/workspace"
    )
    
    print("--- SUBPROCESS OUTPUT ---")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
        
    if result.returncode != 0:
        raise RuntimeError(f"テストが不合格またはエラーが発生しました (exit code {result.returncode})。")
        
    return f"Success: Tests passed with accuracy >= {threshold_accuracy}."
