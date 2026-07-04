import os
import sys
from google.adk.tools import ToolContext
from edd_agent_tools.registry import SkillRegistry

from .config_manager import ConfigManager
from .output_parser import OutputParser
from .test_runner import TestRunner

def process_message(tool_context: ToolContext):
    """
    ADK eval テストを実行し、結果を ToolContext.state に格納します。
    """
    skill_name = tool_context.state.get("skill_name")
    eval_set_path = tool_context.state.get("eval_set_path")
    threshold_accuracy = tool_context.state.get("threshold_accuracy", 1.0)
    timeout_seconds = tool_context.state.get("timeout_seconds", 180)
    eval_mode = tool_context.state.get("eval_mode", 1)

    if not skill_name or not eval_set_path:
        raise ValueError("エラー: 'skill_name' と 'eval_set_path' は必須です。")
        
    registry = SkillRegistry()
    skill_directory = registry.get_skill_directory(name="test-executor")

    config_manager = ConfigManager(skill_directory)
    test_runner = TestRunner()
    output_parser = OutputParser()

    try:
        # 1. 設定ファイルパスの取得
        config_file_path = config_manager.get_eval_config_path(eval_set_path)
        print(f"Using eval config file: {config_file_path}")

        # 2. adk eval の実行
        stdout, stderr, return_code = test_runner.run_adk_eval(
            skill_name=skill_name,
            eval_set_path=eval_set_path,
            config_file_path=config_file_path,
            timeout_seconds=timeout_seconds,
            eval_mode=eval_mode
        )

        # 3. 出力結果の解析
        combined_output = stdout + "\n" + stderr
        parsed_results = output_parser.parse_adk_eval_output(combined_output, return_code)
        
        accuracy = parsed_results["accuracy"]
        
        if parsed_results["parsed_from_log"]:
            print(f"解析結果: 合格 = {parsed_results['passed']}, 不合格 = {parsed_results['failed']}, 合計 = {parsed_results['total']}, 精度 = {accuracy:.4f}")
        else:
            print(f"警告: ログからテスト結果数を抽出できませんでした。フォールバック結果を使用します。精度 = {accuracy:.4f}")

        # 4. 合否判定
        status = "passed" if accuracy >= threshold_accuracy else "failed"
        message = f"Accuracy {accuracy:.4f} is {'greater than or equal to' if status == 'passed' else 'less than'} threshold {threshold_accuracy:.4f}."
        
        # 5. 結果を ToolContext.state に格納
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

    except FileNotFoundError as e:
        tool_context.state.update({
            "status": "failed",
            "message": str(e),
            "accuracy": 0.0,
            "threshold_accuracy": threshold_accuracy
        })
        print(f"エラー: {e}", file=sys.stderr)
        raise
    except RuntimeError as e:
        # test_runner からのタイムアウトエラーなど
        # state は test_runner 内で更新されているはずだが、念のため。
        if "status" not in tool_context.state:
             tool_context.state.update({
                "status": "failed",
                "message": str(e),
                "accuracy": 0.0,
                "threshold_accuracy": threshold_accuracy
            })
        print(f"エラー: {e}", file=sys.stderr)
        raise
    except Exception as e:
        tool_context.state.update({
            "status": "failed",
            "message": f"予期せぬエラーが発生しました: {str(e)}",
            "accuracy": 0.0,
            "threshold_accuracy": threshold_accuracy
        })
        print(f"予期せぬエラー: {e}", file=sys.stderr)
        raise

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
    import subprocess
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